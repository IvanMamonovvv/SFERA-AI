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
from sfera_ai.models.candidate_vacancy_transfer import CandidateVacancyTransfer
from sfera_ai.models.vacancy_profile import VacancyProfile

SECRET = "test-secret"
COURSE_ID = 5
COURSE_UUID = "course-uuid-1"


def _memory_engine():
    """TestClient рвёт lifespan/запросы в отдельный anyio-поток — обычный sqlite
    ':memory:' движок single-thread-bound, StaticPool + check_same_thread=False
    держат одно соединение доступным из любого потока."""
    return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def _platform_engine(*, applications=(), progress=()):
    """applications: [(id, candidate_id, course_id)]
    progress: [(candidate_id, course_id, completed_lessons, total_lessons)]"""
    engine = _memory_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_course (id INTEGER PRIMARY KEY, course_uuid TEXT)")
        conn.exec_driver_sql(
            f"INSERT INTO courses_course (id, course_uuid) VALUES ({COURSE_ID}, '{COURSE_UUID}')"
        )
        conn.exec_driver_sql(
            "CREATE TABLE courses_application (id INTEGER PRIMARY KEY, candidate_id INTEGER, course_id INTEGER)"
        )
        for app_id, candidate_id, course_id in applications:
            conn.exec_driver_sql(
                f"INSERT INTO courses_application (id, candidate_id, course_id) "
                f"VALUES ({app_id}, {candidate_id}, {course_id})"
            )
        conn.exec_driver_sql(
            "CREATE TABLE courses_progress (id INTEGER PRIMARY KEY, candidate_id INTEGER, course_id INTEGER, "
            "completed_lessons INTEGER, total_lessons INTEGER)"
        )
        for i, (candidate_id, course_id, completed, total) in enumerate(progress, start=1):
            conn.exec_driver_sql(
                f"INSERT INTO courses_progress (id, candidate_id, course_id, completed_lessons, total_lessons) "
                f"VALUES ({i}, {candidate_id}, {course_id}, {completed}, {total})"
            )
    return engine


def _write_engine():
    engine = _memory_engine()
    Base.metadata.create_all(engine)
    return engine


def _client(write_engine, platform_engine):
    app = create_app(
        engine_factory=lambda: write_engine,
        platform_engine_factory=lambda: platform_engine,
        bff_shared_secret=SECRET,
    )
    return TestClient(app)


def test_summary_zero_for_course_with_no_data():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/summary/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    assert response.json() == {"total": 0, "processed": 0, "queued": 0, "errors": 0}


def test_summary_counts_jobs_and_analyses():
    write_engine = _write_engine()
    session = sessionmaker(bind=write_engine)()
    profile1 = CandidateProfile(application_id=1)
    profile2 = CandidateProfile(application_id=2)
    session.add_all([profile1, profile2])
    session.flush()
    vacancy = VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={})
    session.add(vacancy)
    session.flush()
    session.add_all(
        [
            AIProcessingJob(candidate_profile_id=profile1.id, course_id=COURSE_ID, status="PENDING", reason="MANUAL"),
            AIProcessingJob(candidate_profile_id=profile2.id, course_id=COURSE_ID, status="FAILED", reason="MANUAL"),
            CandidateVacancyAnalysis(
                candidate_profile_id=profile1.id,
                course_id=COURSE_ID,
                vacancy_profile_id=vacancy.id,
                version=1,
                is_current=True,
                data_completeness=80,
                confidence="HIGH",
                recommendation="STRONG_MATCH",
                fit_score=90,
                analyzed_at=datetime.now(UTC),
            ),
        ]
    )
    session.commit()
    session.close()

    client = _client(write_engine, _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/summary/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    assert response.json() == {"total": 2, "processed": 1, "queued": 1, "errors": 1}


def test_summary_unknown_course_returns_404():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            "/api/v1/courses/unknown-course/ai-analysis/summary/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 404


def test_summary_requires_bff_secret():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(f"/api/v1/courses/{COURSE_UUID}/ai-analysis/summary/")

    assert response.status_code == 401


def test_candidates_list_empty_course():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_candidates_list_returns_contract_fields_with_fit_delta_and_demo_progress():
    write_engine = _write_engine()
    session = sessionmaker(bind=write_engine)()
    profile = CandidateProfile(application_id=1)
    session.add(profile)
    session.flush()
    vacancy = VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={})
    session.add(vacancy)
    session.flush()
    session.add_all(
        [
            CandidateVacancyAnalysis(
                candidate_profile_id=profile.id,
                course_id=COURSE_ID,
                vacancy_profile_id=vacancy.id,
                version=1,
                is_current=False,
                data_completeness=50,
                confidence="LOW",
                recommendation="NOT_ENOUGH_DATA",
                fit_score=40,
                analyzed_at=datetime.now(UTC),
            ),
            CandidateVacancyAnalysis(
                candidate_profile_id=profile.id,
                course_id=COURSE_ID,
                vacancy_profile_id=vacancy.id,
                version=2,
                is_current=True,
                data_completeness=90,
                confidence="HIGH",
                recommendation="STRONG_MATCH",
                fit_score=85,
                analyzed_at=datetime.now(UTC),
            ),
        ]
    )
    session.commit()
    profile_id = profile.id
    session.close()

    platform_engine = _platform_engine(applications=[(1, 100, COURSE_ID)], progress=[(100, COURSE_ID, 3, 4)])
    client = _client(write_engine, platform_engine)

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"] == [
        {
            "candidate_profile_id": profile_id,
            "fit_score": 85,
            "confidence": "HIGH",
            "data_completeness": 90,
            "recommendation": "STRONG_MATCH",
            "fit_delta": 45,
            "demo_progress": 75,
            "resume_status": "MISSING",
        }
    ]


def test_candidates_list_pagination():
    write_engine = _write_engine()
    session = sessionmaker(bind=write_engine)()
    vacancy = VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={})
    session.add(vacancy)
    session.flush()
    profiles = [CandidateProfile(application_id=i) for i in range(1, 4)]
    session.add_all(profiles)
    session.flush()
    for profile in profiles:
        session.add(
            CandidateVacancyAnalysis(
                candidate_profile_id=profile.id,
                course_id=COURSE_ID,
                vacancy_profile_id=vacancy.id,
                version=1,
                is_current=True,
                data_completeness=50,
                confidence="MEDIUM",
                recommendation="POSSIBLE_MATCH",
                fit_score=50,
                analyzed_at=datetime.now(UTC),
            )
        )
    session.commit()
    profile_ids = [p.id for p in profiles]
    session.close()

    client = _client(write_engine, _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/?limit=2&offset=1",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [item["candidate_profile_id"] for item in body["items"]] == profile_ids[1:3]


def test_screening_candidates_empty_course():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/screening/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_screening_candidates_filters_sorts_and_flags_transferred():
    write_engine = _write_engine()
    session = sessionmaker(bind=write_engine)()
    vacancy = VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={})
    session.add(vacancy)
    session.flush()
    below, passing_low, passing_high = (
        CandidateProfile(application_id=1),
        CandidateProfile(application_id=2),
        CandidateProfile(application_id=3),
    )
    session.add_all([below, passing_low, passing_high])
    session.flush()
    session.add_all(
        [
            CandidateVacancyAnalysis(
                candidate_profile_id=below.id,
                course_id=COURSE_ID,
                vacancy_profile_id=vacancy.id,
                version=1,
                is_current=True,
                data_completeness=50,
                confidence="LOW",
                recommendation="NOT_ENOUGH_DATA",
                fit_score=59,
                analyzed_at=datetime.now(UTC),
            ),
            CandidateVacancyAnalysis(
                candidate_profile_id=passing_low.id,
                course_id=COURSE_ID,
                vacancy_profile_id=vacancy.id,
                version=1,
                is_current=True,
                data_completeness=60,
                confidence="MEDIUM",
                recommendation="POSSIBLE_MATCH",
                fit_score=60,
                analyzed_at=datetime.now(UTC),
            ),
            CandidateVacancyAnalysis(
                candidate_profile_id=passing_high.id,
                course_id=COURSE_ID,
                vacancy_profile_id=vacancy.id,
                version=1,
                is_current=True,
                data_completeness=90,
                confidence="HIGH",
                recommendation="STRONG_MATCH",
                fit_score=85,
                analyzed_at=datetime.now(UTC),
            ),
        ]
    )
    session.add(
        CandidateVacancyTransfer(
            candidate_profile_id=passing_high.id,
            course_id=COURSE_ID,
            transferred_at=datetime.now(UTC),
        )
    )
    session.commit()
    passing_low_id, passing_high_id = passing_low.id, passing_high.id
    session.close()

    client = _client(write_engine, _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/screening/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    body = response.json()
    assert [item["candidate_profile_id"] for item in body["items"]] == [passing_high_id, passing_low_id]
    assert body["items"][0]["transferred"] is True
    assert body["items"][1]["transferred"] is False
    assert body["items"][0]["application_id"] == 3
    assert body["items"][1]["application_id"] == 2


def test_screening_candidates_unknown_course_returns_404():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            "/api/v1/courses/unknown-course/ai-analysis/candidates/screening/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 404
