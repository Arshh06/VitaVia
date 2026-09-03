"""Tests for the isolated ambulance-to-hospital communication endpoints."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

INCOMING_REQUEST = {
    "ambulance_id": "AMB-07",
    "patient_id": "PAT-9901",
    "patient_name": "Rajesh Kumar",
    "age": 58,
    "gender": "Male",
    "chief_complaint": "Severe breathing difficulty",
    "spo2": 87.5,
    "heart_rate": 128,
    "systolic_bp": 92,
    "diastolic_bp": 58,
    "temperature": 38.4,
    "dispatch_origin": "Trinity Junction Central",
    "selected_hospital_id": "HOSP002",
    "eta_minutes": 9.9,
    "distance_km": 5.92,
    "triage_level": "HIGH",
}


def test_post_incoming_emergency_accepts_and_stores_latest_request() -> None:
    """A valid ambulance payload becomes the current in-memory hospital request."""
    response = client.post("/emergency/incoming", json=INCOMING_REQUEST)

    assert response.status_code == 200
    payload = response.json()
    assert payload["exists"] is True
    assert payload["has_active_request"] is True
    assert payload["incoming_request"] == INCOMING_REQUEST
    assert payload["received_at"] is not None


def test_get_incoming_emergency_returns_the_latest_request() -> None:
    """Hospital polling retrieves the precise request most recently sent by the ambulance."""
    client.post("/emergency/incoming", json=INCOMING_REQUEST)

    response = client.get("/emergency/incoming")

    assert response.status_code == 200
    assert response.json()["incoming_request"]["patient_name"] == "Rajesh Kumar"
    assert response.json()["selected_hospital_id"] == "HOSP002"


def test_hospital_id_filter_hides_request_from_other_hospital() -> None:
    """A request is visible only to its ambulance-specified selected hospital."""
    client.post("/emergency/incoming", json=INCOMING_REQUEST)

    matching = client.get("/emergency/incoming?hospital_id=HOSP002")
    non_matching = client.get("/emergency/incoming?hospital_id=HOSP003")

    assert matching.status_code == 200
    assert matching.json()["exists"] is True
    assert matching.json()["incoming_request"]["ambulance_id"] == "AMB-07"
    assert non_matching.status_code == 200
    assert non_matching.json()["has_active_request"] is True
    assert non_matching.json()["exists"] is False
    assert non_matching.json()["incoming_request"] is None


def test_invalid_incoming_payload_returns_validation_error() -> None:
    """Out-of-range prototype vital data is rejected without storing a request."""
    response = client.post(
        "/emergency/incoming",
        json={**INCOMING_REQUEST, "spo2": 120.0},
    )

    assert response.status_code == 422
