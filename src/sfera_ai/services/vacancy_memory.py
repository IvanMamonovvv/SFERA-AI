from datetime import UTC, datetime

from sqlalchemy.orm import Session

from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.models.vacancy_memory import VacancyMemory
from sfera_ai.services.job_detection import enqueue_fit_recalc_for_course

_SENTIMENT_TO_WEIGHT_HINT = {
    "NEGATIVE": "PENALIZE",
    "POSITIVE": "BOOST",
    "NEUTRAL": "INFO_ONLY",
}


class FeedbackAlreadyAppliedError(Exception):
    """Повторный `approve_feedback` уже применённого фидбека (step-E7-03, DoD п.2) —
    не создаёт вторую `VacancyMemory` от того же `feedback`."""


def approve_feedback(
    session: Session, feedback: VacancyFeedback, *, approved_by: int, weight_hint: str | None = None,
) -> VacancyMemory:
    """`VacancyFeedback` → `VacancyMemory(is_active=True)` + `feedback.applied=True` в
    одной транзакции (03_TDD.md, «Positive feedback» — тот же путь для обоих
    сентиментов, различается только `weight_hint`)."""
    if feedback.applied:
        raise FeedbackAlreadyAppliedError(f"feedback {feedback.id} already applied")

    resolved_weight_hint = weight_hint or _SENTIMENT_TO_WEIGHT_HINT[feedback.sentiment]

    memory = VacancyMemory(
        course_id=feedback.course_id,
        rule_text=feedback.ai_suggested_rule,
        weight_hint=resolved_weight_hint,
        source_feedback_id=feedback.id,
        approved_by_id=approved_by,
        approved_at=datetime.now(UTC),
        is_active=True,
    )
    feedback.applied = True

    session.add(memory)
    session.commit()
    session.refresh(memory)

    enqueue_fit_recalc_for_course(session, feedback.course_id)
    return memory
