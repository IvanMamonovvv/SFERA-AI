from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.services.change_detection import needs_profile_rebuild

BACKOFF_BASE_MINUTES = 5


def backoff(attempts: int) -> timedelta:
    """Экспоненциальный backoff: 5, 10, 20, 40... минут (03_TDD.md, «6. Processing Queue»)."""
    return timedelta(minutes=BACKOFF_BASE_MINUTES * (2 ** max(attempts - 1, 0)))


def _still_relevant(platform_base, job: AIProcessingJob, profile: CandidateProfile) -> bool:
    """Идемпотентность: перепроверяет условие постановки джобы перед обработкой — если
    оно уже неверно (профиль пересобран другой джобой раньше), реальный AI-вызов не нужен."""
    if job.reason == "CANDIDATE_DATA_CHANGED":
        return needs_profile_rebuild(platform_base, profile)
    return True


def process_batch(
    session: Session, platform_base, *, limit: int, dry_run: bool
) -> list[AIProcessingJob]:
    """03_TDD.md, «6. Processing Queue» — блокирует до `limit` `PENDING`-джоб
    (`SKIP LOCKED`), каждую обрабатывает в своём try/except (падение одной не блокирует
    остальные партии). `dry_run=True` — реальный AI-вызов не делается, только повторная
    change detection (идемпотентность), джоба закрывается `DONE`."""
    jobs = session.scalars(
        select(AIProcessingJob)
        .where(AIProcessingJob.status == "PENDING")
        .order_by(AIProcessingJob.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()

    for job in jobs:
        job.status = "PROCESSING"
        job.started_at = datetime.now(UTC)
        session.commit()

        try:
            profile = session.get(CandidateProfile, job.candidate_profile_id)
            if profile is None:
                raise ValueError(f"candidate_profile {job.candidate_profile_id} не найден")
            _still_relevant(platform_base, job, profile)  # идемпотентность — только чтение
            if not dry_run:
                raise NotImplementedError("реальный AI-вызов ещё не реализован (см. E6/E7)")
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
