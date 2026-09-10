from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.vacancy_profile import (
    VacancyProfile,  # noqa: F401 — регистрирует FK-таргет для Base.metadata
)
from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.api_read import resolve_candidate_platform_name

TABLES = ("courses_application", "users_customuser")


def _platform_base(*, application_id: int, candidate_id: int, user_name: str | None):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql("CREATE TABLE users_customuser (id INTEGER PRIMARY KEY, name TEXT)")
        conn.exec_driver_sql(
            f"INSERT INTO courses_application (id, candidate_id) VALUES ({application_id}, {candidate_id})"
        )
        if user_name is not None:
            conn.exec_driver_sql(f"INSERT INTO users_customuser (id, name) VALUES ({candidate_id}, '{user_name}')")
    return reflect_platform_tables(engine, tables=TABLES)


def test_resolves_name_via_application_candidate_id_not_own_profile_id(tmp_engine):
    """Регрессия 2026-09-10: profile.id (свой PK этого сервиса) != users_customuser.id
    (реальный platform candidate_id). Раньше `resolve_candidate_platform_name` путал их —
    здесь `profile.id` намеренно НЕ совпадает с `candidate_id`, чтобы поймать регресс."""
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()
        assert profile.id != 555  # candidate_id платформы намеренно другое число

        platform_base = _platform_base(application_id=7, candidate_id=555, user_name="Иванов Иван Иванович")

        assert resolve_candidate_platform_name(platform_base, profile) == "Иванов Иван Иванович"


def test_returns_none_when_no_application_id(tmp_engine):
    """HH-лид без application_id — candidate_id ещё не существует на платформе."""
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()

        platform_base = _platform_base(application_id=7, candidate_id=555, user_name="Иванов Иван Иванович")

        assert resolve_candidate_platform_name(platform_base, profile) is None


def test_returns_none_when_user_not_found(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7)
        session.add(profile)
        session.commit()

        platform_base = _platform_base(application_id=7, candidate_id=555, user_name=None)

        assert resolve_candidate_platform_name(platform_base, profile) is None
