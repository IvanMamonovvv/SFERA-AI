from sqlalchemy import event
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis  # noqa: F401 регистрирует FK-таблицу в metadata
from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.models.vacancy_profile import VacancyProfile  # noqa: F401 транзитивная FK-зависимость CandidateVacancyAnalysis


def _enable_sqlite_fk(engine):
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))


def test_vacancy_feedback_has_expected_columns():
    columns = {c.name for c in VacancyFeedback.__table__.columns}
    assert columns == {
        "id", "course_id", "candidate_profile_id", "analysis_id", "author_id",
        "text", "sentiment", "ai_suggested_rule", "applied", "created_at", "updated_at",
    }


def test_vacancy_feedback_has_course_applied_index():
    index_columns = {
        tuple(c.name for c in idx.columns)
        for idx in VacancyFeedback.__table__.indexes
    }
    assert ("course_id", "applied") in index_columns


def test_vacancy_feedback_defaults(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        feedback = VacancyFeedback(course_id=1, text="кандидат хорошо держится", sentiment="POSITIVE")
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
        assert feedback.applied is False
        assert feedback.ai_suggested_rule == ""
        assert feedback.candidate_profile_id is None


def test_vacancy_feedback_candidate_profile_fk_is_cascade(tmp_engine):
    _enable_sqlite_fk(tmp_engine)
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        feedback = VacancyFeedback(
            course_id=1, candidate_profile_id=profile.id, text="фидбек", sentiment="NEUTRAL"
        )
        session.add(feedback)
        session.commit()
        feedback_id = feedback.id

        session.delete(profile)
        session.commit()

        assert session.get(VacancyFeedback, feedback_id) is None
