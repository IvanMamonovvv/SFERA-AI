from sqlalchemy import create_engine

from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.platform_db import reflect_platform_tables, CHANGE_DETECTION_TABLES
from sfera_ai.services.change_detection import needs_profile_rebuild


def _platform_base(*, application=None, progress=None, answers=(), hh_negotiation=None):
    """application: (id, candidate_id, course_id, modified_at) | None
    progress: modified_at str | None
    answers: [(id, attempt_id)]
    hh_negotiation: (id, modified_at, hh_resume_id) | None"""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER, "
            "course_id INTEGER, modified_at DATETIME)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE courses_progress (id INTEGER PRIMARY KEY, candidate_id INTEGER, "
            "course_id INTEGER, modified_at DATETIME)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_testattempt (id INTEGER PRIMARY KEY, candidate_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, attempt_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, "
            "modified_at DATETIME, hh_resume_id TEXT)"
        )
        if application is not None:
            app_id, candidate_id, course_id, modified_at = application
            conn.exec_driver_sql(
                f"INSERT INTO courses_application (id, candidate_id, course_id, modified_at) "
                f"VALUES ({app_id}, {candidate_id}, {course_id}, '{modified_at}')"
            )
            conn.exec_driver_sql(
                f"INSERT INTO testchecks_testattempt (id, candidate_id) VALUES (1, {candidate_id})"
            )
            if progress is not None:
                conn.exec_driver_sql(
                    f"INSERT INTO courses_progress (id, candidate_id, course_id, modified_at) "
                    f"VALUES (1, {candidate_id}, {course_id}, '{progress}')"
                )
            for answer_id, attempt_id in answers:
                conn.exec_driver_sql(
                    f"INSERT INTO testchecks_answer (id, attempt_id) VALUES ({answer_id}, {attempt_id})"
                )
        if hh_negotiation is not None:
            hh_id, modified_at, hh_resume_id = hh_negotiation
            resume_sql = f"'{hh_resume_id}'" if hh_resume_id is not None else "NULL"
            conn.exec_driver_sql(
                f"INSERT INTO headhunter_hhnegotiationrecord (id, modified_at, hh_resume_id) "
                f"VALUES ({hh_id}, '{modified_at}', {resume_sql})"
            )
    return reflect_platform_tables(engine, tables=CHANGE_DETECTION_TABLES)


def test_stale_when_answer_added_since_snapshot():
    platform_base = _platform_base(
        application=(7, 100, 5, "2026-08-20T10:00:00"),
        progress="2026-08-20T10:00:00",
        answers=[(1, 1), (2, 1)],
    )
    profile = CandidateProfile(
        application_id=7,
        sources_snapshot={
            "application_updated_at": "2026-08-20T10:00:00",
            "progress_updated_at": "2026-08-20T10:00:00",
            "max_answer_id": 1,  # снепшот снят до второго ответа
            "hh_negotiation_updated_at": None,
            "hh_resume_id": None,
        },
    )
    assert needs_profile_rebuild(platform_base, profile) is True


def test_not_stale_when_snapshot_matches_current_state():
    platform_base = _platform_base(
        application=(7, 100, 5, "2026-08-20T10:00:00"),
        progress="2026-08-20T10:00:00",
        answers=[(1, 1)],
    )
    profile = CandidateProfile(
        application_id=7,
        sources_snapshot={
            "application_updated_at": "2026-08-20T10:00:00",
            "progress_updated_at": "2026-08-20T10:00:00",
            "max_answer_id": 1,
            "hh_negotiation_updated_at": None,
            "hh_resume_id": None,
        },
    )
    assert needs_profile_rebuild(platform_base, profile) is False


def test_boundary_hh_only_profile_without_application():
    """Профиль только с hh_negotiation_id (NEW_HH_LEAD, application ещё нет) — блок
    application/progress/max_answer_id не выполняется вовсе, сравнение идёт только
    по HH-полям."""
    platform_base = _platform_base(hh_negotiation=(99, "2026-08-20T10:00:00", "hh-resume-1"))
    profile = CandidateProfile(
        hh_negotiation_id=99,
        sources_snapshot={
            "application_updated_at": None,
            "progress_updated_at": None,
            "max_answer_id": None,
            "hh_negotiation_updated_at": "2026-08-20T10:00:00",
            "hh_resume_id": "hh-resume-1",
        },
    )
    assert needs_profile_rebuild(platform_base, profile) is False
