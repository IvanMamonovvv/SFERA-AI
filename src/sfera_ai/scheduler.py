import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.platform_db import CHANGE_DETECTION_TABLES, reflect_platform_tables
from sfera_ai.services.job_detection import detect_and_enqueue
from sfera_ai.services.job_processing import process_batch, requeue_stuck_jobs
from sfera_ai.services.pii_retention import purge_expired_hh_lead_resumes

logger = logging.getLogger(__name__)


def run_tick(settings: Settings) -> None:
    """03_TDD.md, «6. Processing Queue» — один тик: сперва детекция (постановка
    `PENDING`-джоб), затем разбор очереди тем же вызовом. Свой процесс/контейнер,
    не `core/scheduler.py` backend'а."""
    write_engine = make_write_engine(settings)
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=CHANGE_DETECTION_TABLES)

    with Session(write_engine) as session:
        created = detect_and_enqueue(session, platform_base)
        logger.info("тик: поставлено %d новых джоб", len(created))
        processed = process_batch(
            session,
            platform_base,
            limit=settings.ai_analysis_max_concurrent_jobs,
            dry_run=settings.ai_processing_dry_run,
        )
        logger.info("тик: обработано %d джоб (dry_run=%s)", len(processed), settings.ai_processing_dry_run)


def run_requeue_stuck(settings: Settings) -> None:
    """03_TDD.md, «6. Processing Queue» → «Зависшие PROCESSING» — отдельный часовой cron,
    не завязан на тик detection+processing."""
    write_engine = make_write_engine(settings)
    with Session(write_engine) as session:
        requeued = requeue_stuck_jobs(session, threshold_hours=settings.ai_stuck_job_threshold_hours)
        logger.info("requeue: %d зависших джоб вернуто в PENDING", len(requeued))


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
