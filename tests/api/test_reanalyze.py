from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfera_ai.api.app import create_app
from sfera_ai.db.base import Base
from sfera_ai.models.ai_processing_job import AIProcessingJob
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
        conn.exec_driver_sql("CREATE TABLE courses_course (id INTEGER PRIMARY KEY, course_uuid TEXT)")
        conn.exec_driver_sql("CREATE TABLE companies_company (id INTEGER PRIMARY KEY, slug TEXT)")
        conn.exec_driver_sql(
            "CREATE TABLE companies_companyfeature (id INTEGER PRIMARY KEY, company_id INTEGER, feature_key TEXT)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_vacancycoursemapping (id INTEGER PRIMARY KEY, course_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, mapping_id INTEGER)"
        )
        conn.exec_driver_sql(
            f"INSERT INTO courses_course (id, course_uuid) VALUES ({COURSE_ID}, '{COURSE_UUID}')"
        )
        conn.exec_driver_sql(
            "CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER, course_id INTEGER)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE courses_progress (id INTEGER PRIMARY KEY, candidate_id INTEGER, course_id INTEGER, "
            "completed_lessons INTEGER, total_lessons INTEGER)"
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
        bff_shared_secret=SECRET,
    )
    return TestClient(app)


def _headers():
    return {"X-BFF-Shared-Secret": SECRET}


def _seed_candidate(write_engine) -> int:
    session = sessionmaker(bind=write_engine)()
    profile = CandidateProfile(application_id=1, facts=[])
    session.add(profile)
    session.flush()
    vacancy = VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={})
    session.add(vacancy)
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


def test_reanalyze_creates_manual_job():
    write_engine = _write_engine()
    candidate_profile_id = _seed_candidate(write_engine)
    client = _client(write_engine)

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/{candidate_profile_id}/reanalyze/",
            headers=_headers(),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "PENDING"

        session = sessionmaker(bind=write_engine)()
        job = session.get(AIProcessingJob, body["id"])
        session.close()
        assert job.reason == "MANUAL"
        assert job.candidate_profile_id == candidate_profile_id
        assert job.course_id == COURSE_ID


def test_reanalyze_repeated_request_within_window_returns_429():
    write_engine = _write_engine()
    candidate_profile_id = _seed_candidate(write_engine)
    client = _client(write_engine)

    with client:
        first = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/{candidate_profile_id}/reanalyze/",
            headers=_headers(),
        )
        second = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/{candidate_profile_id}/reanalyze/",
            headers=_headers(),
        )

    assert first.status_code == 201
    assert second.status_code == 429


def test_reanalyze_unknown_candidate_returns_404():
    client = _client(_write_engine())

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/999/reanalyze/",
            headers=_headers(),
        )

    assert response.status_code == 404
