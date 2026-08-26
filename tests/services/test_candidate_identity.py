from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.candidate_identity import resolve_or_create_candidate_profile


def _platform_base_with_hh_record(application_id_for_hh=None):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, application_id INTEGER)"
        )
        if application_id_for_hh is not None:
            conn.exec_driver_sql(
                f"INSERT INTO headhunter_hhnegotiationrecord (id, application_id) VALUES (99, {application_id_for_hh})"
            )
    base = reflect_platform_tables(engine, tables=("courses_application", "headhunter_hhnegotiationrecord"))
    return base


def test_new_hh_lead_creates_profile_with_hh_negotiation_only(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_hh_record()
    with Session(tmp_engine) as session:
        profile = resolve_or_create_candidate_profile(
            session, platform_base=platform_base, hh_negotiation_id=42,
        )
        assert profile.hh_negotiation_id == 42
        assert profile.application_id is None


def test_new_application_creates_profile_when_no_hh_link(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_hh_record()  # нет привязанного HH-лида
    with Session(tmp_engine) as session:
        profile = resolve_or_create_candidate_profile(
            session, platform_base=platform_base, application_id=7,
        )
        assert profile.application_id == 7
        assert profile.hh_negotiation_id is None


def test_new_application_resolves_existing_hh_lead_profile_no_duplicate(tmp_engine):
    """Гонка: Application уже привязан к HHNegotiationRecord(id=99) в платформе,
    но AI-профиль по этому лиду ещё существует только с hh_negotiation_id=99.
    Вызов resolve_or_create с application_id=7 не должен создать второй CandidateProfile."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_hh_record(application_id_for_hh=7)
    with Session(tmp_engine) as session:
        existing = CandidateProfile(hh_negotiation_id=99)
        session.add(existing)
        session.commit()

        resolved = resolve_or_create_candidate_profile(
            session, platform_base=platform_base, application_id=7,
        )

        assert resolved.id == existing.id
        assert resolved.hh_negotiation_id == 99
        assert resolved.application_id == 7  # дозаполнено на месте

        count = session.query(CandidateProfile).count()
        assert count == 1


def test_concurrent_insert_race_resolves_to_winner_no_crash(tmp_engine):
    """_insert_or_resolve_race — прямой юнит-тест на путь IntegrityError: строка с тем же
    application_id уже вставлена (эмулирует выигравшую параллельную джобу, коммит между
    чужим SELECT-miss и своим INSERT — 03_TDD.md, «Processing Queue», параллельный batch).
    Второй insert обязан упасть на UniqueConstraint и резолвиться в выигравшую строку, не
    пробрасывая IntegrityError наружу."""
    from sfera_ai.services.candidate_identity import _insert_or_resolve_race

    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        winner = CandidateProfile(application_id=7)
        session.add(winner)
        session.commit()
        winner_id = winner.id

        loser = CandidateProfile(application_id=7)
        resolved = _insert_or_resolve_race(
            session, loser,
            lookup_column=CandidateProfile.application_id, lookup_value=7,
        )
        assert resolved.id == winner_id
        assert session.query(CandidateProfile).count() == 1
