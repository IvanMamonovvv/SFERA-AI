from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfera_ai.api.app import create_app
from sfera_ai.db.base import Base
from sfera_ai.models.vacancy_feedback import VacancyFeedback
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.providers import LLMProviderError, LLMResult

SECRET = "test-secret"
COURSE_ID = 5
COURSE_UUID = "course-uuid-1"


def _memory_engine():
    return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def _platform_engine():
    engine = _memory_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_course (id INTEGER PRIMARY KEY, course_uuid TEXT)")
        conn.exec_driver_sql(f"INSERT INTO courses_course (id, course_uuid) VALUES ({COURSE_ID}, '{COURSE_UUID}')")
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


class _StubLLMClient:
    def __init__(self, content: str = "Учитывать позитивный настрой.", error: Exception | None = None):
        self._content = content
        self._error = error
        self.calls: list[dict] = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return LLMResult(
            content=self._content, provider="openrouter", model="test-model",
            tokens_input=10, tokens_output=5, latency_ms=10,
        )


def _client(write_engine, platform_engine=None, llm_client=None):
    app = create_app(
        engine_factory=lambda: write_engine,
        platform_engine_factory=lambda: platform_engine or _platform_engine(),
        llm_client_factory=lambda: llm_client or _StubLLMClient(),
        bff_shared_secret=SECRET,
    )
    return TestClient(app)


def _headers():
    return {"X-BFF-Shared-Secret": SECRET}


def test_get_vacancy_profile_returns_404_when_no_current_version():
    client = _client(_write_engine())

    with client:
        response = client.get(f"/api/v1/courses/{COURSE_UUID}/ai-analysis/vacancy-profile/", headers=_headers())

    assert response.status_code == 404


def test_post_vacancy_profile_creates_first_version():
    client = _client(_write_engine())

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/vacancy-profile/",
            headers=_headers(),
            json={"requirements": {"skills": ["python"]}, "notes": "junior", "created_by_id": 7},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["course_id"] == COURSE_ID
    assert body["version"] == 1
    assert body["is_current"] is True
    assert body["requirements"] == {"skills": ["python"]}
    assert body["notes"] == "junior"
    assert body["created_by_id"] == 7


def test_post_vacancy_profile_creates_new_version_and_supersedes_previous():
    write_engine = _write_engine()
    session = sessionmaker(bind=write_engine)()
    session.add(VacancyProfile(course_id=COURSE_ID, version=1, is_current=True, requirements={"a": 1}, notes=""))
    session.commit()
    session.close()

    client = _client(write_engine)

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/vacancy-profile/",
            headers=_headers(),
            json={"requirements": {"a": 2}, "notes": "updated"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["version"] == 2
        assert body["is_current"] is True

        session = sessionmaker(bind=write_engine)()
        versions = session.query(VacancyProfile).order_by(VacancyProfile.version).all()
        session.close()
        assert [v.is_current for v in versions] == [False, True]


def test_post_vacancy_profile_invalid_body_returns_422():
    client = _client(_write_engine())

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/vacancy-profile/",
            headers=_headers(),
            json={"notes": "missing requirements"},
        )

    assert response.status_code == 422


def test_get_feedback_list_empty():
    client = _client(_write_engine())

    with client:
        response = client.get(f"/api/v1/courses/{COURSE_UUID}/ai-analysis/feedback/", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_post_feedback_creates_and_interprets():
    llm_client = _StubLLMClient(content="  Отмечать уверенность как плюс.  ")
    client = _client(_write_engine(), llm_client=llm_client)

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/feedback/",
            headers=_headers(),
            json={"text": "кандидат уверенно отвечал", "sentiment": "POSITIVE", "author_id": 3},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["course_id"] == COURSE_ID
    assert body["text"] == "кандидат уверенно отвечал"
    assert body["sentiment"] == "POSITIVE"
    assert body["ai_suggested_rule"] == "Отмечать уверенность как плюс."
    assert body["applied"] is False
    assert len(llm_client.calls) == 1


def test_post_feedback_llm_failure_leaves_rule_empty():
    llm_client = _StubLLMClient(error=LLMProviderError("boom"))
    client = _client(_write_engine(), llm_client=llm_client)

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/feedback/",
            headers=_headers(),
            json={"text": "фидбек", "sentiment": "NEGATIVE"},
        )

    assert response.status_code == 201
    assert response.json()["ai_suggested_rule"] == ""


def test_post_feedback_invalid_sentiment_returns_422():
    client = _client(_write_engine())

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/feedback/",
            headers=_headers(),
            json={"text": "фидбек", "sentiment": "MAYBE"},
        )

    assert response.status_code == 422


def test_approve_feedback_creates_memory_and_marks_applied():
    write_engine = _write_engine()
    session = sessionmaker(bind=write_engine)()
    feedback = VacancyFeedback(course_id=COURSE_ID, text="фидбек", sentiment="POSITIVE")
    session.add(feedback)
    session.commit()
    feedback_id = feedback.id
    session.close()

    client = _client(write_engine)

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/feedback/{feedback_id}/approve/",
            headers=_headers(),
            json={"approved_by": 42},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["course_id"] == COURSE_ID
        assert body["weight_hint"] == "BOOST"
        assert body["approved_by_id"] == 42
        assert body["is_active"] is True

        session = sessionmaker(bind=write_engine)()
        refreshed = session.get(VacancyFeedback, feedback_id)
        session.close()
        assert refreshed.applied is True


def test_approve_feedback_already_applied_returns_409():
    write_engine = _write_engine()
    session = sessionmaker(bind=write_engine)()
    feedback = VacancyFeedback(course_id=COURSE_ID, text="фидбек", sentiment="POSITIVE", applied=True)
    session.add(feedback)
    session.commit()
    feedback_id = feedback.id
    session.close()

    client = _client(write_engine)

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/feedback/{feedback_id}/approve/",
            headers=_headers(),
            json={"approved_by": 1},
        )

    assert response.status_code == 409


def test_approve_feedback_unknown_id_returns_404():
    client = _client(_write_engine())

    with client:
        response = client.post(
            f"/api/v1/courses/{COURSE_UUID}/ai-analysis/feedback/999/approve/",
            headers=_headers(),
            json={"approved_by": 1},
        )

    assert response.status_code == 404
