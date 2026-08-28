from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from sfera_ai.api.app import create_app


def test_health_returns_200_when_db_reachable():
    app = create_app(
        engine_factory=lambda: create_engine("sqlite:///:memory:"),
        bff_shared_secret="test-secret",
    )
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_require_bff_secret():
    app = create_app(
        engine_factory=lambda: create_engine("sqlite:///:memory:"),
        bff_shared_secret="test-secret",
    )
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
