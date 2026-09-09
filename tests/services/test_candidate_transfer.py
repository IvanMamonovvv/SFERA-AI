from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile  # noqa: F401 — регистрирует FK-таргет в Base.metadata
from sfera_ai.models.candidate_vacancy_transfer import CandidateVacancyTransfer
from sfera_ai.services.candidate_transfer import mark_candidate_transferred


def test_mark_candidate_transferred_creates_row(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        transfer = mark_candidate_transferred(session, candidate_profile_id=1, course_id=10)
        assert transfer.id is not None
        assert transfer.candidate_profile_id == 1
        assert transfer.course_id == 10


def test_mark_candidate_transferred_upserts_transferred_at(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        first = mark_candidate_transferred(session, candidate_profile_id=1, course_id=10)
        first_transferred_at = first.transferred_at

        second = mark_candidate_transferred(session, candidate_profile_id=1, course_id=10)

        assert second.id == first.id
        assert second.transferred_at >= first_transferred_at

        rows = session.scalars(
            select(CandidateVacancyTransfer).where(
                CandidateVacancyTransfer.candidate_profile_id == 1,
                CandidateVacancyTransfer.course_id == 10,
            )
        ).all()
        assert len(rows) == 1
