"""Tests for the Stage 2 simulated emergency and hospital endpoints."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_snapshot_returns_the_initial_simulated_emergency() -> None:
    """The snapshot endpoint returns the default ambulance, patient, and vitals."""
    client.post("/simulation/reset")

    response = client.get("/simulation/snapshot")

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["ambulance"]["ambulance_id"] == "AMB001"
    assert snapshot["patient"]["patient_id"] == "PAT001"
    assert snapshot["vitals"]


def test_hospitals_returns_four_fictional_hospitals_with_availability() -> None:
    """The hospital endpoint exposes all simulation infrastructure data."""
    response = client.get("/hospitals")

    assert response.status_code == 200
    hospitals = response.json()
    assert len(hospitals) == 4
    assert all("availability" in hospital for hospital in hospitals)


def test_update_returns_a_complete_snapshot_with_bounded_vitals() -> None:
    """A simulation update keeps values in the prototype's allowed ranges."""
    client.post("/simulation/reset")

    response = client.post("/simulation/update")

    assert response.status_code == 200
    snapshot = response.json()
    assert {"ambulance", "patient", "vitals"}.issubset(snapshot)
    assert {"latitude", "longitude"}.issubset(snapshot["ambulance"]["location"])

    vitals = snapshot["vitals"]
    assert 75.0 <= vitals["spo2"] <= 100.0
    assert 40 <= vitals["heart_rate"] <= 180
    assert 70 <= vitals["systolic_bp"] <= 180
    assert 40 <= vitals["diastolic_bp"] <= 120
    assert 34.0 <= vitals["temperature"] <= 42.0


def test_reset_restores_the_initial_vital_signs_and_location() -> None:
    """Reset must make the public simulation values exactly reproducible."""
    client.post("/simulation/update")

    response = client.post("/simulation/reset")

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["ambulance"]["location"] == {
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    assert snapshot["vitals"] == {
        "spo2": 89.0,
        "heart_rate": 122,
        "systolic_bp": 90,
        "diastolic_bp": 60,
        "temperature": 38.1,
    }
