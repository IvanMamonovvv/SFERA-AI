from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as PlatformSession

from sfera_ai.models.candidate_profile import CandidateProfile


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def needs_profile_rebuild(platform_base, profile: CandidateProfile) -> bool:
    """03_TDD.md, раздел «5. Change Detection» — сравнивает `sources_snapshot` профиля
    с текущим состоянием платформенных источников (Application/Progress/max Answer id/
    HH negotiation/hh_resume_id). Чистый read-only запрос, без AI-вызовов."""
    Application = platform_base.classes.courses_application
    Progress = platform_base.classes.courses_progress
    Answer = platform_base.classes.testchecks_answer
    TestAttempt = platform_base.classes.testchecks_testattempt
    HHNegotiationRecord = platform_base.classes.headhunter_hhnegotiationrecord

    with PlatformSession(platform_base.engine) as platform_session:
        application = (
            platform_session.get(Application, profile.application_id)
            if profile.application_id is not None
            else None
        )
        progress_updated_at = None
        max_answer_id = None
        if application is not None:
            progress_updated_at = platform_session.scalar(
                select(Progress.modified_at).where(
                    Progress.candidate_id == application.candidate_id,
                    Progress.course_id == application.course_id,
                )
            )
            max_answer_id = platform_session.scalar(
                select(func.max(Answer.id))
                .join(TestAttempt, Answer.attempt_id == TestAttempt.id)
                .where(TestAttempt.candidate_id == application.candidate_id)
            )
        hh_negotiation = (
            platform_session.get(HHNegotiationRecord, profile.hh_negotiation_id)
            if profile.hh_negotiation_id is not None
            else None
        )
        current = {
            # платформа — Django-модели, timestamp-поле называется `modified_at`, не
            # `updated_at` (найдено на реальном прогоне на staging 2026-08-27, юнит-тесты
            # с самодельной SQLite-схемой этого разрыва не ловили).
            "application_updated_at": _iso(application.modified_at) if application else None,
            "progress_updated_at": _iso(progress_updated_at),
            "max_answer_id": max_answer_id,
            "hh_negotiation_updated_at": _iso(hh_negotiation.modified_at) if hh_negotiation else None,
            "hh_resume_id": hh_negotiation.hh_resume_id if hh_negotiation else None,
        }

    return current != profile.sources_snapshot


# needs_fit_recalc(profile, course) — TDD 03_TDD.md раздел 5 — отложен до появления
# CandidateVacancyAnalysis (E6-02) и VacancyMemory (E7-01) в коде. См. step-E5-02-change-detection.md.
