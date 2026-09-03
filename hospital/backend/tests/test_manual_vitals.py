"""Tests for manual patient-vital entry in the VITAVIA prototype."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.persistence_service import persistence_service


client = TestClient(app)

CUSTOM_VITALS = {
    "spo2": 95.0,
    "heart_rate": 105,
    "systolic_bp": 110,
    "diastolic_bp": 70,
    "temperature": 37.5,
}
LOW_ACUITY_VITALS = {
    "spo2": 97.0,
    "heart_rate": 80,
    "systolic_bp": 120,
    "diastolic_bp": 80,
    "temperature": 36.8,
}


def test_manual_vital_submission_updates_the_current_snapshot() -> None:
    """Valid dashboard-style readings replace the backend's current in-memory vitals."""
    assert client.post("/simulation/reset").status_code == 200

    response = client.post("/simulation/vitals", json=CUSTOM_VITALS)

    assert response.status_code == 200
    assert response.json()["vitals"] == CUSTOM_VITALS
    assert client.get("/simulation/snapshot").json()["vitals"] == CUSTOM_VITALS


def test_analysis_uses_the_current_manually_submitted_vitals() -> None:
    """Manual readings, not the default demo values, drive deterministic triage."""
    assert client.post("/simulation/reset").status_code == 200
    assert client.post("/simulation/vitals", json=LOW_ACUITY_VITALS).status_code == 200

    analysis = client.post("/analysis")

    assert analysis.status_code == 200
    assert analysis.json()["severity"] == "LOW"
    assert analysis.json()["required_infrastructure"] == ["emergency_bed"]
    assert analysis.json()["source"] == "deterministic"


def test_decision_uses_manually_submitted_vitals() -> None:
    """The existing deterministic pipeline receives manual vitals without a hardcoded default."""
    assert client.post("/simulation/reset").status_code == 200
    assert client.post("/simulation/vitals", json=LOW_ACUITY_VITALS).status_code == 200

    decision = client.post("/emergency/decision")

    assert decision.status_code == 200
    payload = decision.json()
    assert payload["vitals"] == LOW_ACUITY_VITALS
    assert payload["triage"]["severity"] == "LOW"
    assert payload["triage"]["required_infrastructure"] == ["emergency_bed"]
    # HOSP003 becomes eligible only because these manually entered values do not require ICU.
    assert payload["selected_hospital"]["hospital_id"] == "HOSP003"


def test_out_of_range_spo2_returns_validation_error() -> None:
    """Prototype input bounds produce FastAPI's controlled Pydantic validation response."""
    response = client.post("/simulation/vitals", json={**CUSTOM_VITALS, "spo2": 120.0})

    assert response.status_code == 422


def test_out_of_range_temperature_returns_validation_error() -> None:
    """Invalid temperatures cannot overwrite the current simulated patient state."""
    response = client.post("/simulation/vitals", json={**CUSTOM_VITALS, "temperature": 60.0})

    assert response.status_code == 422


def test_reset_restores_the_default_demo_vitals_after_manual_entry() -> None:
    """A new simulation begins with the established reproducible Stage 1–10 defaults."""
    assert client.post("/simulation/vitals", json=CUSTOM_VITALS).status_code == 200

    reset = client.post("/simulation/reset")

    assert reset.status_code == 200
    assert reset.json()["vitals"] == {
        "spo2": 89.0,
        "heart_rate": 122,
        "systolic_bp": 90,
        "diastolic_bp": 60,
        "temperature": 38.1,
    }


def test_manual_vital_reading_is_persisted_in_the_active_emergency_history() -> None:
    """The saved manual reading is retained in SQLite history before any analysis or journey."""
    assert client.post("/simulation/reset").status_code == 200
    emergency_id = persistence_service.current_emergency_id
    assert emergency_id is not None
    assert client.post("/simulation/vitals", json=CUSTOM_VITALS).status_code == 200

    detail = client.get(f"/history/emergencies/{emergency_id}")

    assert detail.status_code == 200
    saved_reading = detail.json()["vital_history"][-1]
    assert {field: saved_reading[field] for field in CUSTOM_VITALS} == CUSTOM_VITALS


def test_manual_vitals_are_rejected_once_a_journey_is_active() -> None:
    """Journey simulation owns changing vitals after the selected destination is fixed."""
    assert client.post("/simulation/reset").status_code == 200
    assert client.post("/journey/start").status_code == 200

    response = client.post("/simulation/vitals", json=CUSTOM_VITALS)

    assert response.status_code == 409
