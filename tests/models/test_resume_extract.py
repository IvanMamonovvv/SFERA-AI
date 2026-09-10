import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract


def test_resume_extract_has_expected_columns():
    columns = {c.name for c in ResumeExtract.__table__.columns}
    assert columns == {
        "id", "candidate_profile_id", "source_type", "source_answer_id", "hh_resume_id",
        "raw_text", "structured_data", "status", "error", "provider", "model",
        "prompt_version", "processed_at", "attempts", "retry_after", "created_at", "updated_at",
    }


def test_resume_extract_requires_exactly_one_source(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id, source_type="ANKETA_FILE",
                source_answer_id=None, hh_resume_id=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_resume_extract_rejects_both_sources(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(
                candidate_profile_id=profile.id, source_type="ANKETA_FILE",
                source_answer_id=1, hh_resume_id="hh-1",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_resume_extract_duplicate_source_answer_rejected(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=42)
        )
        session.commit()
        session.add(
            ResumeExtract(candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=42)
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_resume_extract_duplicate_hh_resume_for_same_candidate_rejected(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=1)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1")
        )
        session.commit()
        session.add(
            ResumeExtract(candidate_profile_id=profile.id, source_type="HH_RESUME", hh_resume_id="hh-1")
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_resume_extract_allows_multiple_hh_leads_without_hh_resume_id(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=1)
        session.add(profile)
        session.commit()
        session.add(
            ResumeExtract(candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=1)
        )
        session.add(
            ResumeExtract(candidate_profile_id=profile.id, source_type="ANKETA_FILE", source_answer_id=2)
        )
        session.commit()
