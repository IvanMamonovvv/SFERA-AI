from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.resume_extract import ResumeExtract


def purge_expired_hh_lead_resumes(session: Session, *, ttl_days: int) -> list[ResumeExtract]:
    """step-E5-06 — стирает `raw_text`/`structured_data` у `ResumeExtract` профилей,
    которые всё ещё только `hh_negotiation` (не конвертировались в `Application`) и
    старше TTL. Строка не удаляется, `status` не меняется — иначе change detection
    решит, что источника нет, и перезапустит парсинг (152-ФЗ: платформа не может
    удалить сам `HHNegotiationRecord`, только AI-сервис чистит свою копию сырого текста)."""
    threshold = datetime.now(UTC) - timedelta(days=ttl_days)
    expired = session.scalars(
        select(ResumeExtract)
        .join(CandidateProfile, ResumeExtract.candidate_profile_id == CandidateProfile.id)
        .where(
            CandidateProfile.application_id.is_(None),
            ResumeExtract.processed_at < threshold,
        )
    ).all()

    for extract in expired:
        extract.raw_text = ""
        extract.structured_data = {}

    session.commit()
    return expired
