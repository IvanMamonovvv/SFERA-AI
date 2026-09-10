import logging

import boto3
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.integrations.hh_client import HHClient
from sfera_ai.platform_db import RESUME_DETECTION_TABLES, reflect_platform_tables
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.job_detection import detect_and_enqueue
from sfera_ai.services.job_processing import process_batch, requeue_stuck_jobs
from sfera_ai.services.pii_retention import purge_expired_hh_lead_resumes
from sfera_ai.services.resume_pipeline import requeue_failed_resumes

logger = logging.getLogger(__name__)


def run_tick(settings: Settings) -> None:
    """03_TDD.md, «6. Processing Queue» — один тик: сперва детекция (постановка
    `PENDING`-джоб), затем разбор очереди тем же вызовом. Свой процесс/контейнер,
    не `core/scheduler.py` backend'а."""
    write_engine = make_write_engine(settings)
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=RESUME_DETECTION_TABLES)

    llm_client = OpenRouterClient(
        api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url
    )
    hh_client = HHClient(
        base_url=settings.hh_backend_base_url,
        login=settings.hh_backend_admin_login,
        password=settings.hh_backend_admin_password,
        host_header=settings.hh_backend_host_header,
    )
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )

    with Session(write_engine) as session:
        created = detect_and_enqueue(session, platform_base)
        logger.info("тик: поставлено %d новых джоб", len(created))
        processed = process_batch(
            session,
            platform_base,
            llm_client,
            limit=settings.ai_analysis_max_concurrent_jobs,
            dry_run=settings.ai_processing_dry_run,
            pilot_course_id=settings.ai_processing_pilot_course_id,
            hh_client=hh_client,
            s3_client=s3_client,
            s3_bucket=settings.s3_bucket,
        )
        logger.info("тик: обработано %d джоб (dry_run=%s)", len(processed), settings.ai_processing_dry_run)


def run_requeue_stuck(settings: Settings) -> None:
    """03_TDD.md, «6. Processing Queue» → «Зависшие PROCESSING» — отдельный часовой cron,
    не завязан на тик detection+processing."""
    write_engine = make_write_engine(settings)
    with Session(write_engine) as session:
        requeued = requeue_stuck_jobs(session, threshold_hours=settings.ai_stuck_job_threshold_hours)
        logger.info("requeue: %d зависших джоб вернуто в PENDING", len(requeued))


def run_resume_retry(settings: Settings) -> None:
    """step-E18-03 — отдельный cron раз в 2 часа, ретраит ResumeExtract.status=FAILED
    с истёкшим backoff. Не завязан на run_tick/детекцию."""
    write_engine = make_write_engine(settings)
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=RESUME_DETECTION_TABLES)

    llm_client = OpenRouterClient(
        api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url
    )
    hh_client = HHClient(
        base_url=settings.hh_backend_base_url,
        login=settings.hh_backend_admin_login,
        password=settings.hh_backend_admin_password,
        host_header=settings.hh_backend_host_header,
    )
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )

    with Session(write_engine) as session:
        retried = requeue_failed_resumes(
            session,
            platform_base,
            hh_client=hh_client,
            s3_client=s3_client,
            s3_bucket=settings.s3_bucket,
            llm_client=llm_client,
            max_attempts=settings.resume_extract_max_attempts,
        )
        logger.info("resume_retry: %d FAILED резюме повторно обработано", len(retried))


def run_pii_retention(settings: Settings) -> None:
    """step-E5-06 — отдельный суточный cron, не завязан на тик/requeue-джобы."""
    write_engine = make_write_engine(settings)
    with Session(write_engine) as session:
        purged = purge_expired_hh_lead_resumes(session, ttl_days=settings.resume_pii_ttl_days)
        logger.info("pii_retention: очищено %d просроченных резюме hh-лидов", len(purged))


def build_scheduler(settings: Settings | None = None) -> BackgroundScheduler:
    settings = settings or Settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_tick,
        # 2026-08-27 — было 3 фиксированных тика/сутки (8/15/19), пересчитано под реальный
        # приток (100-200 кандидатов/сутки) — раз в 30 минут, вместе с лимитом 200/тик
        # (config.py) даёт запас на порядок; max_instances=1 не даст следующему запуску
        # начаться, пока предыдущий ещё не закончил (пропустит тик, не встанет в очередь).
        CronTrigger(minute="*/30"),
        args=[settings],
        max_instances=1,  # тик не параллелится сам с собой — только джобы внутри тика
    )
    scheduler.add_job(
        run_requeue_stuck,
        CronTrigger(minute=0),  # раз в час, отдельно от получасового тика
        args=[settings],
        max_instances=1,
    )
    scheduler.add_job(
        run_resume_retry,
        # step-E18-03 — реже получасового тика: каждый вызов делает реальные HH/S3/LLM
        # запросы (в отличие от run_requeue_stuck, только UPDATE), 2 часа согласовано с владельцем.
        CronTrigger(hour="*/2", minute=0),
        args=[settings],
        max_instances=1,
    )
    scheduler.add_job(
        run_pii_retention,
        CronTrigger(hour=3, minute=0),  # раз в сутки, в 3 ночи — вне пиковой нагрузки
        args=[settings],
        max_instances=1,
    )
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_scheduler().start()
    import time

    while True:
        time.sleep(3600)
