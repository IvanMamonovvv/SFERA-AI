from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.ai_processing_job import AIProcessingJob
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.platform_db import CHANGE_DETECTION_TABLES, reflect_platform_tables
from sfera_ai.services.job_detection import detect_and_enqueue


def _platform_base(*, applications=(), hh_records=()):
    """applications: [(id, candidate_id, course_id)]
    hh_records: [(id, application_id, hh_resume_id)]"""
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
            "application_id INTEGER, modified_at DATETIME, hh_resume_id TEXT)"
        )
        for app_id, candidate_id, course_id in applications:
            conn.exec_driver_sql(
                f"INSERT INTO courses_application (id, candidate_id, course_id, modified_at) "
                f"VALUES ({app_id}, {candidate_id}, {course_id}, '2026-08-20T10:00:00')"
            )
        for hh_id, application_id, hh_resume_id in hh_records:
            app_sql = str(application_id) if application_id is not None else "NULL"
            resume_sql = f"'{hh_resume_id}'" if hh_resume_id is not None else "NULL"
            conn.exec_driver_sql(
                f"INSERT INTO headhunter_hhnegotiationrecord (id, application_id, modified_at, hh_resume_id) "
                f"VALUES ({hh_id}, {app_sql}, '2026-08-20T10:00:00', {resume_sql})"
            )
    return reflect_platform_tables(engine, tables=CHANGE_DETECTION_TABLES)


def test_new_hh_lead_creates_profile_and_job(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(hh_records=[(1, None, "hh-resume-1")])
    with Session(tmp_engine) as session:
        created = detect_and_enqueue(session, platform_base)

        assert [j.reason for j in created] == ["NEW_HH_LEAD"]
        profile = session.query(CandidateProfile).one()
        assert profile.hh_negotiation_id == 1
        assert profile.application_id is None


def test_new_application_creates_profile_and_job(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(applications=[(7, 100, 5)])
    with Session(tmp_engine) as session:
        created = detect_and_enqueue(session, platform_base)

        assert [j.reason for j in created] == ["NEW_APPLICATION"]
        profile = session.query(CandidateProfile).one()
        assert profile.application_id == 7
        assert profile.hh_negotiation_id is None


def test_hh_lead_promoted_to_application_without_new_application_job(tmp_engine):
    """Лид сначала пришёл один (тик 1), заявка появилась позже и связалась с тем же
    HH-record (тик 2) — переход, не новая заявка. NEW_APPLICATION не должен создаться,
    но профиль устарел (появилась заявка) → CANDIDATE_DATA_CHANGED."""
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        existing = CandidateProfile(hh_negotiation_id=1, sources_snapshot={})
        session.add(existing)
        session.commit()

        platform_base = _platform_base(
            applications=[(7, 100, 5)],
            hh_records=[(1, 7, "hh-resume-1")],
        )
        created = detect_and_enqueue(session, platform_base)

        assert "NEW_APPLICATION" not in [j.reason for j in created]
        assert "NEW_HH_LEAD" not in [j.reason for j in created]
        assert [j.reason for j in created] == ["CANDIDATE_DATA_CHANGED"]
        session.refresh(existing)
        assert existing.application_id == 7


def test_candidate_data_changed_when_existing_profile_stale(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(applications=[(7, 100, 5)])
    with Session(tmp_engine) as session:
        session.add(
            CandidateProfile(
                application_id=7,
                sources_snapshot={
                    "application_updated_at": "2000-01-01T00:00:00",  # заведомо устарело
                    "progress_updated_at": None,
                    "max_answer_id": None,
                    "hh_negotiation_updated_at": None,
                    "hh_resume_id": None,
                },
            )
        )
        session.commit()

        created = detect_and_enqueue(session, platform_base)

        assert [j.reason for j in created] == ["CANDIDATE_DATA_CHANGED"]


def test_no_new_jobs_on_repeat_tick_without_changes(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(hh_records=[(1, None, "hh-resume-1")])
    with Session(tmp_engine) as session:
        first = detect_and_enqueue(session, platform_base)
        assert len(first) == 1
        second = detect_and_enqueue(session, platform_base)
        assert second == []
        assert session.query(AIProcessingJob).count() == 1


def test_no_duplicate_job_when_pending_already_exists(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base(applications=[(7, 100, 5)])
    with Session(tmp_engine) as session:
        profile = CandidateProfile(application_id=7, sources_snapshot={})
        session.add(profile)
        session.commit()
        session.add(AIProcessingJob(candidate_profile_id=profile.id, reason="CANDIDATE_DATA_CHANGED"))
        session.commit()

        created = detect_and_enqueue(session, platform_base)

        assert created == []
        assert session.query(AIProcessingJob).count() == 1
