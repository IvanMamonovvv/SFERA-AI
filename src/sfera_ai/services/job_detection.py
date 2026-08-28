from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as PlatformSession

from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.services.candidate_identity import resolve_or_create_candidate_profile
from sfera_ai.services.candidate_transition import promote_hh_lead_to_application
from sfera_ai.services.change_detection import needs_profile_rebuild

ACTIVE_STATUSES = ("PENDING", "PROCESSING")
MANUAL_REANALYZE_RATE_LIMIT = timedelta(minutes=5)


class ReanalyzeRateLimitedError(Exception):
    """Ручной reanalyze этого кандидата уже ставился в пределах rate-limit окна
    (step-E8-05, порог 5 минут — решение владельца, 2026-08-28)."""


def _create_job_if_absent(
    session: Session, *, candidate_profile_id: int, reason: str, course_id: int | None = None,
) -> AIProcessingJob | None:
    """Partial UniqueConstraint (candidate_profile, course, reason) WHERE status IN
    (PENDING, PROCESSING) защищает от гонки между процессами; эта проверка — та же
    защита на уровне приложения, без похода в БД дважды на конфликте."""
    existing = session.scalar(
        select(AIProcessingJob).where(
            AIProcessingJob.candidate_profile_id == candidate_profile_id,
            AIProcessingJob.course_id == course_id,
            AIProcessingJob.reason == reason,
            AIProcessingJob.status.in_(ACTIVE_STATUSES),
        )
    )
    if existing is not None:
        return None
    job = AIProcessingJob(candidate_profile_id=candidate_profile_id, reason=reason, course_id=course_id)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def enqueue_manual_reanalyze(
    session: Session, *, candidate_profile_id: int, course_id: int | None = None,
) -> AIProcessingJob:
    """step-E8-05 — ручной reanalyze всегда ставится (без проверки needs_profile_rebuild,
    в отличие от `_create_job_if_absent`), но защищён rate-limit окном по времени
    создания последней MANUAL-джобы этого кандидата, а не по активным статусам —
    предыдущая ручная джоба обычно уже DONE к моменту повторного клика."""
    cutoff = datetime.now(UTC) - MANUAL_REANALYZE_RATE_LIMIT
    recent = session.scalar(
        select(AIProcessingJob).where(
            AIProcessingJob.candidate_profile_id == candidate_profile_id,
            AIProcessingJob.reason == "MANUAL",
            AIProcessingJob.created_at >= cutoff,
        )
    )
    if recent is not None:
        raise ReanalyzeRateLimitedError(candidate_profile_id)

    job = AIProcessingJob(candidate_profile_id=candidate_profile_id, reason="MANUAL", course_id=course_id)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def enqueue_fit_recalc_for_course(session: Session, course_id: int) -> list[AIProcessingJob]:
    """03_TDD.md, «Vacancy Profile + Vacancy Memory workflow» п.5 — появление активной
    `VacancyMemory` или новой `is_current=True` версии `VacancyProfile` ставит
    `AIProcessingJob(reason=VACANCY_PROFILE_CHANGED)` для всех `is_current`-анализов
    этого `course` (только пересчёт Fit, без пересборки `CandidateProfile`).
    Переиспользует дедупликацию `_create_job_if_absent` — повторный вызов без новых
    `is_current`-анализов не создаёт дублирующих `PENDING`-джоб."""
    candidate_profile_ids = session.scalars(
        select(CandidateVacancyAnalysis.candidate_profile_id).where(
            CandidateVacancyAnalysis.course_id == course_id,
            CandidateVacancyAnalysis.is_current.is_(True),
        )
    ).all()

    created: list[AIProcessingJob] = []
    for candidate_profile_id in candidate_profile_ids:
        job = _create_job_if_absent(
            session, candidate_profile_id=candidate_profile_id,
            reason="VACANCY_PROFILE_CHANGED", course_id=course_id,
        )
        if job is not None:
            created.append(job)
    return created


def detect_and_enqueue(session: Session, platform_base) -> list[AIProcessingJob]:
    """03_TDD.md, «6. Processing Queue» — обходит источники событий, создаёт
    `AIProcessingJob` идемпотентно. `VACANCY_PROFILE_CHANGED`/`FEEDBACK_APPLIED` не
    реализованы здесь — зависят от `CandidateVacancyAnalysis` (E6-02) и `VacancyMemory`
    (E7-01), которых ещё нет в коде (см. step-E5-03-job-creation.md). `NEW_ANSWER`/
    `NEW_RESUME`/`NEW_VIDEO` объединены в один reason `CANDIDATE_DATA_CHANGED` — на
    уровне детекции доступен только общий флаг `needs_profile_rebuild`, без разбора
    какой конкретно источник изменился (решение владельца, 2026-08-27)."""
    HHNegotiationRecord = platform_base.classes.headhunter_hhnegotiationrecord
    Application = platform_base.classes.courses_application

    with PlatformSession(platform_base.engine) as platform_session:
        hh_records = platform_session.scalars(select(HHNegotiationRecord)).all()
        applications = platform_session.scalars(select(Application)).all()

    created: list[AIProcessingJob] = []
    newly_created_profile_ids: set[int] = set()

    known_hh_ids = set(
        session.scalars(select(CandidateProfile.hh_negotiation_id).where(CandidateProfile.hh_negotiation_id.is_not(None)))
    )
    known_application_ids = set(
        session.scalars(select(CandidateProfile.application_id).where(CandidateProfile.application_id.is_not(None)))
    )

    for record in hh_records:
        if record.id in known_hh_ids:
            continue
        profile = resolve_or_create_candidate_profile(
            session, platform_base=platform_base,
            hh_negotiation_id=record.id, application_id=record.application_id,
        )
        known_hh_ids.add(record.id)
        if profile.application_id is not None:
            known_application_ids.add(profile.application_id)
        newly_created_profile_ids.add(profile.id)
        job = _create_job_if_absent(session, candidate_profile_id=profile.id, reason="NEW_HH_LEAD")
        if job is not None:
            created.append(job)

    for record in hh_records:
        if record.application_id is None:
            continue
        promote_hh_lead_to_application(
            session, hh_negotiation_id=record.id, application_id=record.application_id,
        )
        known_application_ids.add(record.application_id)  # конверсия лида, не новая заявка

    for application in applications:
        if application.id in known_application_ids:
            continue
        profile = resolve_or_create_candidate_profile(
            session, platform_base=platform_base, application_id=application.id,
        )
        known_application_ids.add(application.id)
        newly_created_profile_ids.add(profile.id)
        job = _create_job_if_absent(session, candidate_profile_id=profile.id, reason="NEW_APPLICATION")
        if job is not None:
            created.append(job)

    profiles_with_active_job = set(
        session.scalars(
            select(AIProcessingJob.candidate_profile_id).where(AIProcessingJob.status.in_(ACTIVE_STATUSES))
        )
    )
    existing_profiles = session.scalars(
        select(CandidateProfile).where(CandidateProfile.is_superseded.is_(False))
    ).all()
    for profile in existing_profiles:
        if profile.id in newly_created_profile_ids or profile.id in profiles_with_active_job:
            continue  # уже есть активная джоба (в этом тике или с прошлого) — она и так пересоберёт профиль
        if needs_profile_rebuild(platform_base, profile):
            job = _create_job_if_absent(session, candidate_profile_id=profile.id, reason="CANDIDATE_DATA_CHANGED")
            if job is not None:
                created.append(job)

    return created
