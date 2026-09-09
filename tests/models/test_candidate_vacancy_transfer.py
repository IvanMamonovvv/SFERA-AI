from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile  # noqa: F401 — регистрирует FK-таргет в Base.metadata
from sfera_ai.models.candidate_vacancy_transfer import CandidateVacancyTransfer


def test_candidate_vacancy_transfer_has_expected_columns():
    columns = {c.name for c in CandidateVacancyTransfer.__table__.columns}
    assert columns == {
        "id", "candidate_profile_id", "course_id", "transferred_at", "created_at", "updated_at",
    }


def test_candidate_vacancy_transfer_unique_candidate_course(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    now = datetime.now(timezone.utc)
    with Session(tmp_engine) as session:
        session.add(CandidateVacancyTransfer(candidate_profile_id=1, course_id=10, transferred_at=now))
        session.commit()

        session.add(CandidateVacancyTransfer(candidate_profile_id=1, course_id=10, transferred_at=now))
        with pytest.raises(IntegrityError):
            session.commit()
