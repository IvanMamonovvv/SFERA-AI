from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as PlatformSession

from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.providers import OpenRouterClient
from sfera_ai.services.candidate_facts import build_or_update_candidate_facts
from sfera_ai.services.change_detection import needs_profile_rebuild
from sfera_ai.services.fit_scoring import run_fit_scoring
from sfera_ai.services.resume_pipeline import ensure_resume_processed

BACKOFF_BASE_MINUTES = 5

# Вакансийные reason'ы (E7, ещё не создаются детекцией) → E6-03 fit-scoring; все
# остальные (включая MANUAL/BACKFILL) → E6-01 сборка/обновление фактов кандидата
# (step-E6-04-queue-integration.md, п.1).
VACANCY_REASONS = ("VACANCY_PROFILE_CHANGED", "FEEDBACK_APPLIED")


def backoff(attempts: int) -> timedelta:
    """Экспоненциальный backoff: 5, 10, 20, 40... минут (03_TDD.md, «6. Processing Queue»)."""
    return timedelta(minutes=BACKOFF_BASE_MINUTES * (2 ** max(attempts - 1, 0)))


def _still_relevant(platform_base, job: AIProcessingJob, profile: CandidateProfile) -> bool:
    """Идемпотентность: перепроверяет условие постановки джобы перед обработкой — если
    оно уже неверно (профиль пересобран другой джобой раньше), реальный AI-вызов не нужен."""
    if job.reason == "CANDIDATE_DATA_CHANGED":
        return needs_profile_rebuild(platform_base, profile)
    return True


def _job_course_id(platform_base, job: AIProcessingJob, profile: CandidateProfile) -> int | None:
    """На каком course реально спишется AI-бюджет — для пилот-скоупинга (п.2 DoD).
    Вакансийные джобы несут `course_id` явно; профильные привязки к course не имеют —
    единственный путь узнать её — через `application_id` → `courses_application.course_id`
    на платформе (владелец подтвердил этот вариант 2026-08-27)."""
    if job.course_id is not None:
        return job.course_id
    if profile.application_id is None:
        return None
    Application = platform_base.classes.courses_application
    with PlatformSession(platform_base.engine) as platform_session:
        application = platform_session.get(Application, profile.application_id)
    return application.course_id if application is not None else None


def _current_vacancy_profile(session: Session, course_id: int | None) -> VacancyProfile | None:
    if course_id is None:
        return None
    return session.scalar(
        select(VacancyProfile).where(
            VacancyProfile.course_id == course_id, VacancyProfile.is_current.is_(True)
        )
    )


def _run_real_ai_call(
    session: Session,
    platform_base,
    llm_client: OpenRouterClient | None,
    job: AIProcessingJob,
    profile: CandidateProfile,
    *,
    hh_client,
    s3_client,
    s3_bucket: str | None,
) -> None:
    ensure_resume_processed(
        profile, platform_base=platform_base, hh_client=hh_client, s3_client=s3_client,
        s3_bucket=s3_bucket, llm_client=llm_client, session=session,
    )
    if job.reason in VACANCY_REASONS:
        vacancy_profile = _current_vacancy_profile(session, job.course_id)
        if vacancy_profile is None:
            raise ValueError(f"нет текущего VacancyProfile для course_id={job.course_id}")
        build_or_update_candidate_facts(session, platform_base, llm_client, profile)
        run_fit_scoring(
            session, candidate_profile=profile, vacancy_profile=vacancy_profile, llm_client=llm_client
        )
    else:
        build_or_update_candidate_facts(session, platform_base, llm_client, profile)


def process_batch(
    session: Session,
    platform_base,
    llm_client: OpenRouterClient | None = None,
    *,
    limit: int,
    dry_run: bool,
    pilot_course_id: int | None = None,
    hh_client=None,
    s3_client=None,
    s3_bucket: str | None = None,
) -> list[AIProcessingJob]:
    """03_TDD.md, «6. Processing Queue» — блокирует до `limit` `PENDING`-джоб
    (`SKIP LOCKED`), каждую обрабатывает в своём try/except (падение одной не блокирует
    остальные партии). `dry_run=True` — реальный AI-вызов не делается, только повторная
    change detection (идемпотентность), джоба закрывается `DONE`. `pilot_course_id`
    (step-E6-04) — при снятом dry-run ограничивает реальные AI-вызовы одним course
    (владелец подтверждает перед прод-пилотом, «7. Риски» → Cost Protection); джобы
    вне пилота остаются `PENDING` нетронутыми — их подхватит следующий тик после
    расширения пилота."""
    jobs = session.scalars(
        select(AIProcessingJob)
        .where(AIProcessingJob.status == "PENDING")
        .order_by(AIProcessingJob.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()

    for job in jobs:
        profile = session.get(CandidateProfile, job.candidate_profile_id)

        if (
            not dry_run
            and pilot_course_id is not None
            and profile is not None
            and _job_course_id(platform_base, job, profile) != pilot_course_id
        ):
            continue  # вне пилота — остаётся PENDING нетронутой

        job.status = "PROCESSING"
        job.started_at = datetime.now(UTC)
        session.commit()

        try:
            if profile is None:
                raise ValueError(f"candidate_profile {job.candidate_profile_id} не найден")
            # _still_relevant всегда вычисляется (идемпотентность — только чтение), но
            # реальный AI-вызов делаем лишь когда условие ещё истинно и dry-run снят.
            if _still_relevant(platform_base, job, profile) and not dry_run:
                _run_real_ai_call(
                    session, platform_base, llm_client, job, profile,
                    hh_client=hh_client, s3_client=s3_client, s3_bucket=s3_bucket,
                )
            job.status = "DONE"
            job.finished_at = datetime.now(UTC)
        except Exception as exc:
            job.status = "FAILED"
            job.attempts += 1
            job.last_error = str(exc)[:2000]
            job.retry_after = datetime.now(UTC) + backoff(job.attempts)
            job.finished_at = datetime.now(UTC)
        session.commit()

    return jobs


def requeue_stuck_jobs(session: Session, *, threshold_hours: int) -> list[AIProcessingJob]:
    """03_TDD.md, «6. Processing Queue» → «Зависшие PROCESSING» — контейнер мог упасть
    между `status="PROCESSING"` и закрытием джобы; отдельный часовой cron возвращает такие
    джобы в `PENDING` (не `FAILED` — не вина джобы) с инкрементом `attempts`, чтобы их
    подхватил следующий тик `process_batch`."""
    threshold = datetime.now(UTC) - timedelta(hours=threshold_hours)
    stuck = session.scalars(
        select(AIProcessingJob).where(
            AIProcessingJob.status == "PROCESSING",
            AIProcessingJob.started_at < threshold,
        )
    ).all()

    for job in stuck:
        job.status = "PENDING"
        job.attempts += 1
        job.started_at = None

    session.commit()
    return stuck
