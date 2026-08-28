import pytest
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile  # noqa: F401 транзитивная FK-зависимость CandidateVacancyAnalysis
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis  # noqa: F401 регистрирует FK-таблицу в metadata
from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.models.vacancy_memory import VacancyMemory
from sfera_ai.models.vacancy_profile import VacancyProfile  # noqa: F401 транзитивная FK-зависимость CandidateVacancyAnalysis
from sfera_ai.services.vacancy_memory import FeedbackAlreadyAppliedError, approve_feedback


def _make_feedback(session: Session, *, sentiment: str) -> VacancyFeedback:
    feedback = VacancyFeedback(
        course_id=1, text="фидбек", sentiment=sentiment, ai_suggested_rule="предлагаемое правило",
    )
    session.add(feedback)
    session.commit()
    return feedback


@pytest.mark.parametrize(
    ("sentiment", "expected_weight_hint"),
    [("NEGATIVE", "PENALIZE"), ("POSITIVE", "BOOST"), ("NEUTRAL", "INFO_ONLY")],
)
def test_approve_feedback_maps_sentiment_to_weight_hint(tmp_engine, sentiment, expected_weight_hint):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        feedback = _make_feedback(session, sentiment=sentiment)

        memory = approve_feedback(session, feedback, approved_by=42)

        assert memory.weight_hint == expected_weight_hint
        assert memory.course_id == feedback.course_id
        assert memory.rule_text == "предлагаемое правило"
        assert memory.source_feedback_id == feedback.id
        assert memory.approved_by_id == 42
        assert memory.approved_at is not None
        assert memory.is_active is True
        assert feedback.applied is True


def test_approve_feedback_explicit_weight_hint_overrides_sentiment_mapping(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        feedback = _make_feedback(session, sentiment="POSITIVE")

        memory = approve_feedback(session, feedback, approved_by=1, weight_hint="INFO_ONLY")

        assert memory.weight_hint == "INFO_ONLY"


def test_approve_feedback_twice_raises_and_does_not_create_second_memory(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        feedback = _make_feedback(session, sentiment="POSITIVE")
        approve_feedback(session, feedback, approved_by=1)

        with pytest.raises(FeedbackAlreadyAppliedError):
            approve_feedback(session, feedback, approved_by=1)

        assert session.query(VacancyMemory).count() == 1
