from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_vacancy_transfer import CandidateVacancyTransfer


def mark_candidate_transferred(
    session: Session, *, candidate_profile_id: int, course_id: int
) -> CandidateVacancyTransfer:
    """Upsert по `(candidate_profile_id, course_id)` — повторная выгрузка обновляет
    `transferred_at` на текущее время, не «ничего не делает» (design doc «Данные»,
    решение владельца 2026-09-09)."""
    existing = session.scalar(
        select(CandidateVacancyTransfer).where(
            CandidateVacancyTransfer.candidate_profile_id == candidate_profile_id,
            CandidateVacancyTransfer.course_id == course_id,
        )
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.transferred_at = now
        session.commit()
        return existing

    transfer = CandidateVacancyTransfer(
        candidate_profile_id=candidate_profile_id, course_id=course_id, transferred_at=now
    )
    session.add(transfer)
    session.commit()
    return transfer
