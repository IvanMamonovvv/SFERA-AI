from sqlalchemy import update
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile


def promote_hh_lead_to_application(session: Session, *, hh_negotiation_id: int, application_id: int) -> bool:
    """UPDATE одной строки — переход HH Lead в Platform Candidate на месте, без INSERT."""
    result = session.execute(
        update(CandidateProfile)
        .where(CandidateProfile.hh_negotiation_id == hh_negotiation_id, CandidateProfile.application_id.is_(None))
        .values(application_id=application_id)
    )
    session.commit()
    return result.rowcount > 0
