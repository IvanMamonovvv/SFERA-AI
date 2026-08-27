from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.services.candidate_transition import promote_hh_lead_to_application


def test_promote_updates_existing_profile_in_place(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()
        profile_id = profile.id

        updated = promote_hh_lead_to_application(session, hh_negotiation_id=42, application_id=7)

        assert updated is True
        session.refresh(profile)
        assert profile.id == profile_id  # тот же профиль, не пересоздан
        assert profile.application_id == 7


def test_promote_is_noop_if_already_promoted(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        session.add(CandidateProfile(hh_negotiation_id=42, application_id=7))
        session.commit()

        updated = promote_hh_lead_to_application(session, hh_negotiation_id=42, application_id=7)

        assert updated is False
