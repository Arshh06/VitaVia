"""Tests for the deterministic in-memory Stage 7 ambulance journey."""

from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.main import app
from app.models.schemas import Acknowledgement, TriageResult


client = TestClient(app)


def test_initial_journey_status_is_not_started() -> None:
    """A reset simulation must expose a safe normal no-journey status."""
    client.post("/simulation/reset")

    response = client.get("/journey/status")

    assert response.status_code == 200
    assert response.json()["active"] is False
    assert response.json()["status"] == "NOT_STARTED"
    assert response.json()["progress_percent"] == 0.0


def test_journey_starts_from_the_backend_selected_hospital() -> None:
    """Journey start uses HOSP002 from the backend decision, never a client hospital ID."""
    client.post("/simulation/reset")

    response = client.post("/journey/start")
    journey = response.json()

    assert response.status_code == 200
    assert journey["selected_hospital_id"] == "HOSP002"
    assert journey["acknowledgement_status"] == "ACCEPTED"
    assert journey["active"] is True
    assert journey["status"] == "EN_ROUTE"
    assert journey["progress_percent"] == 0.0


def test_active_journey_destination_cannot_be_restarted() -> None:
    """A second start request cannot overwrite the fixed in-progress destination."""
    client.post("/simulation/reset")
    client.post("/journey/start")

    response = client.post("/journey/start")

    assert response.status_code == 409
    assert "already active" in response.json()["detail"]


def test_one_journey_update_advances_gps_eta_and_vitals() -> None:
    """One step moves toward the fixed destination and updates shared simulated vitals."""
    client.post("/simulation/reset")
    started = client.post("/journey/start").json()

    response = client.post("/journey/update")
    payload = response.json()
    journey, snapshot = payload["journey"], payload["snapshot"]

    assert response.status_code == 200
    assert journey["step_number"] == 1
    assert journey["progress_percent"] > 0
    assert journey["remaining_eta_minutes"] < started["remaining_eta_minutes"]
    assert journey["current_location"] != started["current_location"]
    assert snapshot["ambulance"]["location"] == journey["current_location"]
    assert 75.0 <= snapshot["vitals"]["spo2"] <= 100.0
    assert 40 <= snapshot["vitals"]["heart_rate"] <= 180


def test_progress_is_monotonic_and_eta_never_increases() -> None:
    """Repeated deterministic steps only progress forward toward arrival."""
    client.post("/simulation/reset")
    client.post("/journey/start")
    progress_values, eta_values = [], []

    for _ in range(5):
        journey = client.post("/journey/update").json()["journey"]
        progress_values.append(journey["progress_percent"])
        eta_values.append(journey["remaining_eta_minutes"])

    assert progress_values == sorted(progress_values)
    assert eta_values == sorted(eta_values, reverse=True)


def test_journey_arrives_after_fixed_number_of_steps() -> None:
    """The final fixed step reaches the exact fictional destination and arrival status."""
    client.post("/simulation/reset")
    started = client.post("/journey/start").json()

    for _ in range(10):
        final_payload = client.post("/journey/update").json()

    journey, snapshot = final_payload["journey"], final_payload["snapshot"]
    assert journey["status"] == "ARRIVED"
    assert journey["active"] is False
    assert journey["progress_percent"] == 100.0
    assert journey["remaining_eta_minutes"] == 0.0
    assert journey["current_location"] == started["destination_location"]
    assert snapshot["ambulance"]["status"] == "ARRIVED_AT_HOSPITAL"


def test_update_after_arrival_does_not_overrun() -> None:
    """An already arrived ambulance remains fixed and safe on later update calls."""
    client.post("/simulation/reset")
    client.post("/journey/start")
    for _ in range(10):
        client.post("/journey/update")
    arrived = client.get("/journey/status").json()

    response = client.post("/journey/update")
    journey = response.json()["journey"]

    assert response.status_code == 200
    assert journey["current_location"] == arrived["current_location"]
    assert journey["progress_percent"] == 100.0
    assert journey["remaining_eta_minutes"] == 0.0
    assert journey["status"] == "ARRIVED"


def test_simulation_reset_clears_active_journey() -> None:
    """Reset clears destination state and restores original Stage 2 ambulance coordinates."""
    client.post("/simulation/reset")
    client.post("/journey/start")
    client.post("/journey/update")

    reset_snapshot = client.post("/simulation/reset").json()
    journey = client.get("/journey/status").json()

    assert journey["status"] == "NOT_STARTED"
    assert journey["progress_percent"] == 0.0
    assert journey["selected_hospital_id"] is None
    assert reset_snapshot["ambulance"]["location"] == {
        "latitude": 12.9716,
        "longitude": 77.5946,
    }


def test_no_suitable_hospital_returns_controlled_start_error(monkeypatch) -> None:
    """Journey start must fail safely when the backend has no selected hospital."""
    client.post("/simulation/reset")

    def no_suitable_decision(snapshot, hospitals):
        return (
            TriageResult(
                severity="HIGH",
                required_infrastructure=["emergency_bed", "icu", "emergency_team"],
                explanation="Test-only no suitable hospital state.",
                source="deterministic",
            ),
            [],
            None,
            Acknowledgement(
                status="NO_SUITABLE_HOSPITAL",
                message="No suitable hospital.",
            ),
        )

    monkeypatch.setattr(api_routes, "run_decision_pipeline", no_suitable_decision)
    response = client.post("/journey/start")

    assert response.status_code == 409
    assert "No accepted hospital decision" in response.json()["detail"]
