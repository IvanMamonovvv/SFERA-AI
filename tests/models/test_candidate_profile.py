import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile


def test_candidate_profile_has_expected_columns():
    columns = {c.name for c in CandidateProfile.__table__.columns}
    assert columns == {
        "id", "application_id", "hh_negotiation_id", "facts", "data_completeness",
        "sources_snapshot", "version", "built_at", "is_superseded", "superseded_by_id",
        "created_at", "updated_at",
    }


def test_candidate_profile_requires_at_least_one_anchor(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        session.add(CandidateProfile(application_id=None, hh_negotiation_id=None))
        with pytest.raises(IntegrityError):
            session.commit()


def test_candidate_profile_allows_hh_lead_only(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        assert profile.version == 1
        assert profile.data_completeness == "MINIMAL"
