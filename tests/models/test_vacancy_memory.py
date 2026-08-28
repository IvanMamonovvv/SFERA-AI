from sqlalchemy import event
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis  # noqa: F401 регистрирует FK-таблицу в metadata
from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.models.vacancy_memory import VacancyMemory
from sfera_ai.models.vacancy_profile import VacancyProfile  # noqa: F401 транзитивная FK-зависимость CandidateVacancyAnalysis


def _enable_sqlite_fk(engine):
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))


def test_vacancy_memory_has_expected_columns():
    columns = {c.name for c in VacancyMemory.__table__.columns}
    assert columns == {
        "id", "course_id", "rule_text", "weight_hint", "source_feedback_id",
        "approved_by_id", "approved_at", "is_active", "created_at", "updated_at",
    }


def test_vacancy_memory_has_course_is_active_index():
    index_columns = {
        tuple(c.name for c in idx.columns)
        for idx in VacancyMemory.__table__.indexes
    }
    assert ("course_id", "is_active") in index_columns


def test_vacancy_memory_defaults(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        memory = VacancyMemory(course_id=1, rule_text="требовать опыт 3+ года", weight_hint="BOOST")
        session.add(memory)
        session.commit()
        session.refresh(memory)
        assert memory.is_active is True
        assert memory.source_feedback_id is None
        assert memory.approved_at is None


def test_vacancy_memory_source_feedback_fk_is_set_null(tmp_engine):
    _enable_sqlite_fk(tmp_engine)
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        feedback = VacancyFeedback(course_id=1, text="фидбек", sentiment="POSITIVE")
        session.add(feedback)
        session.commit()
        memory = VacancyMemory(
            course_id=1, rule_text="правило", weight_hint="INFO_ONLY", source_feedback_id=feedback.id
        )
        session.add(memory)
        session.commit()

        session.delete(feedback)
        session.commit()
        session.refresh(memory)

        assert memory.source_feedback_id is None
