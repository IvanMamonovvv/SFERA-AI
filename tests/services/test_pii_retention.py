from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract
from sfera_ai.services.pii_retention import purge_expired_hh_lead_resumes

TTL_DAYS = 90


def _make_extract(session: Session, *, application_id, processed_at):
    profile = CandidateProfile(
        application_id=application_id,
        hh_negotiation_id=None if application_id else 1,
        sources_snapshot={},
    )
    session.add(profile)
    session.commit()
    extract = ResumeExtract(
        candidate_profile_id=profile.id,
        source_type="hh_resume",
        hh_resume_id="hh-1",
        raw_text="конфиденциальный текст резюме",
        structured_data={"skills": ["python"]},
        status="DONE",
        processed_at=processed_at,
    )
    session.add(extract)
    session.commit()
    return profile, extract


def test_expired_hh_lead_only_resume_is_wiped(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        _, extract = _make_extract(
            session,
            application_id=None,
            processed_at=datetime.now(UTC) - timedelta(days=TTL_DAYS + 1),
        )

        purged = purge_expired_hh_lead_resumes(session, ttl_days=TTL_DAYS)

        assert [e.id for e in purged] == [extract.id]
        session.refresh(extract)
        assert extract.raw_text == ""
        assert extract.structured_data == {}
        assert extract.status == "DONE"


def test_converted_application_not_touched_even_if_old(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        _, extract = _make_extract(
            session,
            application_id=1,
            processed_at=datetime.now(UTC) - timedelta(days=TTL_DAYS + 1),
        )

        purged = purge_expired_hh_lead_resumes(session, ttl_days=TTL_DAYS)

        assert purged == []
        session.refresh(extract)
        assert extract.raw_text == "конфиденциальный текст резюме"
        assert extract.structured_data == {"skills": ["python"]}


def test_fresh_hh_lead_only_resume_not_touched(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        _, extract = _make_extract(
            session,
            application_id=None,
            processed_at=datetime.now(UTC) - timedelta(days=TTL_DAYS - 1),
        )

        purged = purge_expired_hh_lead_resumes(session, ttl_days=TTL_DAYS)

        assert purged == []
        session.refresh(extract)
        assert extract.raw_text == "конфиденциальный текст резюме"
