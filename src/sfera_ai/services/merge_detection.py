from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as PlatformSession

from sfera_ai.models.ai_service_state import AiServiceState
from sfera_ai.models.candidate_profile import CandidateProfile

MERGE_LOG_CURSOR_KEY = "last_seen_merge_log_id"


def _get_cursor(session: Session) -> int:
    state = session.get(AiServiceState, MERGE_LOG_CURSOR_KEY)
    return int(state.value) if state is not None and state.value is not None else 0


def _set_cursor(session: Session, value: int) -> None:
    state = session.get(AiServiceState, MERGE_LOG_CURSOR_KEY)
    if state is None:
        session.add(AiServiceState(key=MERGE_LOG_CURSOR_KEY, value=str(value)))
    else:
        state.value = str(value)


def detect_and_process_merges(session: Session, platform_base) -> None:
    """03_TDD.md, «Candidate Identity — Merge кандидатов» — переносит AI-историю на
    выжившего кандидата после ручного platform-merge (`CandidateMergeLog`)."""
    CandidateMergeLog = platform_base.classes.courses_candidatemergelog

    last_seen = _get_cursor(session)
    with PlatformSession(platform_base.engine) as platform_session:
        new_merges = platform_session.scalars(
            select(CandidateMergeLog)
            .where(CandidateMergeLog.id > last_seen)
            .order_by(CandidateMergeLog.id)
        ).all()

    if not new_merges:
        return

    for log in new_merges:
        source_profile = session.scalar(
            select(CandidateProfile).where(CandidateProfile.application_id == log.duplicate_application_id)
        )
        if source_profile is not None and not source_profile.is_superseded:
            target_profile = session.scalar(
                select(CandidateProfile).where(CandidateProfile.application_id == log.canonical_application_id)
            )
            if target_profile is None:
                source_profile.application_id = log.canonical_application_id
            else:
                source_profile.is_superseded = True
                source_profile.superseded_by_id = target_profile.id

    _set_cursor(session, new_merges[-1].id)
    session.commit()
