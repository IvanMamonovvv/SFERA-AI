import zipfile
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfera_ai.api.app import create_app
from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.models.candidate_vacancy_analysis import CandidateVacancyAnalysis
from sfera_ai.models.vacancy_profile import VacancyProfile

SECRET = "test-secret"
COURSE_ID = 5
COURSE_UUID = "course-uuid-1"


def _memory_engine():
    return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def _platform_engine():
    engine = _memory_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_course (id INTEGER PRIMARY KEY, course_uuid TEXT, company_id INTEGER)")
        conn.exec_driver_sql("CREATE TABLE companies_company (id INTEGER PRIMARY KEY, slug TEXT, name TEXT)")
        conn.exec_driver_sql(
            "CREATE TABLE companies_companyfeature (id INTEGER PRIMARY KEY, company_id INTEGER, feature_key TEXT)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_vacancycoursemapping "
            "(id INTEGER PRIMARY KEY, course_id INTEGER, hh_vacancy_title TEXT)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, mapping_id INTEGER)"
        )
        conn.exec_driver_sql("CREATE TABLE users_customuser (id INTEGER PRIMARY KEY, name TEXT)")
        conn.exec_driver_sql(f"INSERT INTO courses_course (id, course_uuid) VALUES ({COURSE_ID}, '{COURSE_UUID}')")
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql(
            "CREATE TABLE courses_progress (id INTEGER PRIMARY KEY, candidate_id INTEGER, course_id INTEGER, "
            "completed_lessons INTEGER, total_lessons INTEGER)"
        )
        conn.exec_driver_sql("CREATE TABLE testchecks_testattempt (id INTEGER PRIMARY KEY, candidate_id INTEGER)")
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY, attempt_id INTEGER, file TEXT)")
        conn.exec_driver_sql(
            "CREATE TABLE testchecks_transcriptionjob (id INTEGER PRIMARY KEY, answer_id INTEGER, status TEXT)"
        )
    return engine


def _write_engine():
    engine = _memory_engine()
    Base.metadata.create_all(engine)
    return engine


def _client(write_engine, platform_engine=None):
    app = create_app(
        engine_factory=lambda: write_engine,
        platform_engine_factory=lambda: platform_engine or _platform_engine(),
        hh_client_factory=lambda: MagicMock(),
        s3_client_factory=lambda: MagicMock(),
        bff_shared_secret=SECRET,
    )
    return TestClient(app)


def _headers():
    return {"X-BFF-Shared-Secret": SECRET}


def _seed_candidate(write_engine) -> int:
    session = sessionmaker(bind=write_engine)()
    vacancy = VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={})
    session.add(vacancy)
    session.flush()
    profile = CandidateProfile(application_id=1, facts=[])
    session.add(profile)
    session.flush()
    session.add(
        CandidateVacancyAnalysis(
            candidate_profile_id=profile.id,
            course_id=COURSE_ID,
            vacancy_profile_id=vacancy.id,
            version=1,
            is_current=True,
            data_completeness=50,
            confidence="LOW",
            recommendation="NOT_ENOUGH_DATA",
            fit_score=52,
            input_snapshot={},
            analyzed_at=datetime.now(UTC),
        )
    )
    session.commit()
    candidate_profile_id = profile.id
    session.close()
    return candidate_profile_id


def test_export_returns_zip_with_candidate_folder():
    write_engine = _write_engine()
    candidate_profile_id = _seed_candidate(write_engine)
    client = _client(write_engine)

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/export/",
            json={"candidate_profile_ids": [candidate_profile_id]},
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        assert f"candidate_{candidate_profile_id}/card.pdf" in archive.namelist()


def test_export_unknown_course_returns_404():
    client = _client(_write_engine())

    with client:
        response = client.post(
            "/api/v1/courses/unknown-course/ai-analysis/export/",
            json={"candidate_profile_ids": [1]},
            headers=_headers(),
        )

    assert response.status_code == 404
