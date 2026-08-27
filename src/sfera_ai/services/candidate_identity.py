from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile


def _insert_or_resolve_race(session: Session, profile: CandidateProfile, *, lookup_column, lookup_value) -> CandidateProfile:
    """Вставляет profile; если параллельный вызов уже успел вставить строку с тем же
    application_id/hh_negotiation_id (UniqueConstraint), не падает наружу — резолвит
    в выигравшую строку. Защита от гонки двух джоб на одном тике (03_TDD.md, «Processing
    Queue» — параллельная обработка батча)."""
    session.add(profile)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        winner = session.scalar(select(CandidateProfile).where(lookup_column == lookup_value))
        if winner is None:
            raise  # не гонка за этот якорь — реальная ошибка, пробрасываем
        return winner
    session.refresh(profile)
    return profile


def _find_hh_negotiation_for_application(platform_base, application_id: int) -> int | None:
    """Читает платформенную таблицу headhunter_hhnegotiationrecord через reflection —
    есть ли запись с application_id == данный (обратная OneToOne). Read-only."""
    from sqlalchemy.orm import Session as PlatformSession

    HHNegotiationRecord = platform_base.classes.headhunter_hhnegotiationrecord
    with PlatformSession(platform_base.engine) as platform_session:
        record = platform_session.scalar(
            select(HHNegotiationRecord).where(HHNegotiationRecord.application_id == application_id)
        )
        return record.id if record is not None else None


def resolve_or_create_candidate_profile(
    session: Session,
    *,
    platform_base,
    application_id: int | None = None,
    hh_negotiation_id: int | None = None,
) -> CandidateProfile:
    if application_id is None and hh_negotiation_id is None:
        raise ValueError("either application_id or hh_negotiation_id is required")

    if hh_negotiation_id is not None:
        existing = session.scalar(
            select(CandidateProfile).where(CandidateProfile.hh_negotiation_id == hh_negotiation_id)
        )
        if existing is not None:
            return existing
        profile = CandidateProfile(hh_negotiation_id=hh_negotiation_id, application_id=application_id)
        return _insert_or_resolve_race(
            session, profile,
            lookup_column=CandidateProfile.hh_negotiation_id, lookup_value=hh_negotiation_id,
        )

    # application_id задан, hh_negotiation_id — нет: проверить гонку через reflection
    linked_hh_id = _find_hh_negotiation_for_application(platform_base, application_id)
    if linked_hh_id is not None:
        existing = session.scalar(
            select(CandidateProfile).where(CandidateProfile.hh_negotiation_id == linked_hh_id)
        )
        if existing is not None:
            if existing.application_id is None:
                existing.application_id = application_id
                session.commit()
                session.refresh(existing)
            return existing
        # HH-лид есть на платформе, но AI-профиля по нему ещё нет — создать сразу с обоими якорями
        profile = CandidateProfile(hh_negotiation_id=linked_hh_id, application_id=application_id)
        return _insert_or_resolve_race(
            session, profile,
            lookup_column=CandidateProfile.hh_negotiation_id, lookup_value=linked_hh_id,
        )

    existing = session.scalar(
        select(CandidateProfile).where(CandidateProfile.application_id == application_id)
    )
    if existing is not None:
        return existing

    profile = CandidateProfile(application_id=application_id)
    return _insert_or_resolve_race(
        session, profile,
        lookup_column=CandidateProfile.application_id, lookup_value=application_id,
    )
