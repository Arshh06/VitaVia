"""Tests for the Stage 1 backend system endpoints."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_expected_service_status() -> None:
    """The health endpoint must confirm that the VITAVIA backend is available."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "VITAVIA Backend",
    }
