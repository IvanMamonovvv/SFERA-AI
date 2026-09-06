from datetime import UTC, datetime

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
        conn.exec_driver_sql("CREATE TABLE courses_course (id INTEGER PRIMARY KEY, course_uuid TEXT)")
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


def _client(write_engine, platform_engine):
    app = create_app(
        engine_factory=lambda: write_engine,
        platform_engine_factory=lambda: platform_engine,
        bff_shared_secret=SECRET,
    )
    return TestClient(app)


def _seed_two_versions(write_engine):
    session = sessionmaker(bind=write_engine)()
    profile = CandidateProfile(application_id=1, facts=[{"key": "experience_years", "value": "5"}])
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
                fit_score=52,
                input_snapshot={"max_answer_id": 10, "vacancy_profile_id": vacancy.id},
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
                fit_score=87,
                summary="Хороший кандидат",
                input_snapshot={"max_answer_id": 25, "vacancy_profile_id": vacancy.id},
                analyzed_at=datetime.now(UTC),
            ),
        ]
    )
    session.commit()
    profile_id = profile.id
    session.close()
    return profile_id


def test_candidate_detail_returns_current_facts_and_compressed_history():
    write_engine = _write_engine()
    profile_id = _seed_two_versions(write_engine)
    client = _client(write_engine, _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/{profile_id}/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_profile_id"] == profile_id
    assert body["resume_status"] == "MISSING"
    assert body["current"]["fit_score"] == 87
    assert body["current"]["recommendation"] == "STRONG_MATCH"
    assert body["current"]["summary"] == "Хороший кандидат"
    assert body["facts"] == [{"key": "experience_years", "value": "5"}]
    assert [item["version"] for item in body["history"]] == [1, 2]
    assert body["history"][0]["changed"] == []
    assert set(body["history"][1]["changed"]) == {
        "fit_score",
        "confidence",
        "data_completeness",
        "recommendation",
    }


def test_candidate_detail_unknown_candidate_returns_404():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/999/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 404


def test_candidate_detail_unknown_course_returns_404():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            "/api/v1/courses/unknown-course/ai-analysis/candidates/1/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 404


def test_candidate_history_returns_versions_with_readable_diff():
    write_engine = _write_engine()
    profile_id = _seed_two_versions(write_engine)
    client = _client(write_engine, _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/{profile_id}/history/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_profile_id"] == profile_id
    assert len(body["items"]) == 2
    assert body["items"][0]["input_snapshot_diff"] == {}
    assert body["items"][1]["input_snapshot_diff"] == {"max_answer_id": {"old": 10, "new": 25}}
    assert body["items"][1]["fit_score"] == 87


def test_candidate_history_unknown_candidate_returns_404():
    client = _client(_write_engine(), _platform_engine())

    with client:
        response = client.get(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/candidates/999/history/",
            headers={"X-BFF-Shared-Secret": SECRET},
        )

    assert response.status_code == 404
