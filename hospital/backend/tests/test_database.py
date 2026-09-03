"""SQLite audit-history tests for the VITAVIA simulation prototype."""

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from fastapi.testclient import TestClient

from app.data.hospitals import get_all_hospitals
from app.db import database
from app.db.models import HospitalEvaluationRecord
from app.main import app
from app.services.persistence_service import persistence_service
from app.services.selection_service import run_decision_pipeline
from app.services.simulation_service import simulation_service
from app.services.triage_service import analyze_vitals


client = TestClient(app)


def test_database_initialization_creates_history_tables() -> None:
    """The configured temporary SQLite database initializes all audit tables safely."""
    table_names = set(inspect(database.engine).get_table_names())

    assert {
        "emergency_records",
        "vital_reading_records",
        "ambulance_location_records",
        "hospital_evaluation_records",
    }.issubset(table_names)


def test_create_emergency_saves_unique_simulated_session() -> None:
    """Emergency IDs are unique session IDs, rather than reusable AMB001/PAT001 values."""
    snapshot = simulation_service.reset_simulation()
    emergency_id = persistence_service.create_emergency(snapshot)
    details = persistence_service.get_emergency_details(emergency_id)

    assert emergency_id.startswith("EMG-")
    assert details is not None
    assert details["emergency"]["ambulance_id"] == "AMB001"
    assert details["emergency"]["patient_id"] == "PAT001"
    assert details["emergency"]["status"] == "ACTIVE"
    assert details["emergency"]["started_at"].tzinfo is not None


def test_triage_is_persisted_on_the_emergency_summary() -> None:
    """Deterministic prototype triage stays available in the history audit record."""
    snapshot = simulation_service.reset_simulation()
    emergency_id = persistence_service.create_emergency(snapshot)
    triage = analyze_vitals(snapshot.vitals)
    persistence_service.save_triage(emergency_id, triage)

    details = persistence_service.get_emergency_details(emergency_id)

    assert details is not None
    assert details["emergency"]["triage_severity"] == "HIGH"
    assert details["emergency"]["triage_source"] == "deterministic"
    assert details["required_infrastructure"] == ["emergency_bed", "icu", "emergency_team"]


def test_default_decision_persists_selected_and_rejected_hospitals() -> None:
    """Audit history preserves the key fastest-suitable rather than nearest-hospital outcome."""
    snapshot = simulation_service.reset_simulation()
    emergency_id = persistence_service.create_emergency(snapshot)
    triage, decisions, selected, acknowledgement = run_decision_pipeline(
        snapshot, get_all_hospitals()
    )
    persistence_service.save_decision(
        emergency_id, triage, decisions, selected, acknowledgement
    )

    details = persistence_service.get_emergency_details(emergency_id)
    assert details is not None
    evaluations = {item["hospital_id"]: item for item in details["hospital_evaluations"]}

    assert details["emergency"]["selected_hospital_id"] == "HOSP002"
    assert details["emergency"]["acknowledgement_status"] == "ACCEPTED"
    assert len(evaluations) == 4
    assert evaluations["HOSP002"]["selected"] is True
    assert evaluations["HOSP003"]["selected"] is False
    assert evaluations["HOSP003"]["missing_infrastructure"] == ["icu"]


def test_repeated_decision_replaces_evaluation_snapshot_without_duplicates() -> None:
    """Repeated dashboard decisions retain exactly one latest candidate row per hospital."""
    snapshot = simulation_service.reset_simulation()
    emergency_id = persistence_service.create_emergency(snapshot)
    triage, decisions, selected, acknowledgement = run_decision_pipeline(
        snapshot, get_all_hospitals()
    )
    persistence_service.save_decision(
        emergency_id, triage, decisions, selected, acknowledgement
    )
    persistence_service.save_decision(
        emergency_id, triage, decisions, selected, acknowledgement
    )

    with database.session_scope() as session:
        rows = session.scalars(
            select(HospitalEvaluationRecord).where(
                HospitalEvaluationRecord.emergency_id == emergency_id
            )
        ).all()

    assert len(rows) == 4


def test_journey_updates_create_vital_and_location_timeline() -> None:
    """Active journey steps append matching simulated vital and GPS history events."""
    reset = client.post("/simulation/reset")
    assert reset.status_code == 200
    client.post("/emergency/decision")
    started = client.post("/journey/start")
    assert started.status_code == 200
    emergency_id = persistence_service.current_emergency_id
    assert emergency_id is not None

    for _ in range(3):
        assert client.post("/journey/update").status_code == 200

    details = persistence_service.get_emergency_details(emergency_id)
    assert details is not None
    locations = details["location_history"]
    assert len(details["vital_history"]) >= 5
    assert len(locations) >= 5
    progress = [item["progress_percent"] for item in locations if item["progress_percent"] is not None]
    remaining_eta = [
        item["remaining_eta_minutes"]
        for item in locations
        if item["remaining_eta_minutes"] is not None
    ]
    assert progress == sorted(progress)
    assert remaining_eta == sorted(remaining_eta, reverse=True)


def test_arrival_marks_emergency_complete() -> None:
    """The final journey event records simulated arrival and a completion timestamp."""
    client.post("/simulation/reset")
    client.post("/journey/start")
    emergency_id = persistence_service.current_emergency_id
    assert emergency_id is not None

    for _ in range(10):
        client.post("/journey/update")

    details = persistence_service.get_emergency_details(emergency_id)
    assert details is not None
    summary = details["emergency"]
    assert summary["status"] == "ARRIVED"
    assert summary["completed_at"] is not None
    assert summary["selected_hospital_id"] == "HOSP002"
    assert summary["acknowledgement_status"] == "ACCEPTED"


def test_history_list_endpoint_returns_created_emergency() -> None:
    """Recent-history API returns the currently persisted simulated session."""
    client.post("/simulation/reset")
    emergency_id = persistence_service.current_emergency_id
    assert emergency_id is not None

    response = client.get("/history/emergencies")

    assert response.status_code == 200
    assert response.json()[0]["emergency_id"] == emergency_id


def test_history_detail_endpoint_returns_full_audit_data() -> None:
    """History detail includes triage, candidate evaluations, vital readings, and locations."""
    client.post("/simulation/reset")
    client.post("/analysis")
    client.post("/emergency/decision")
    emergency_id = persistence_service.current_emergency_id
    assert emergency_id is not None

    response = client.get(f"/history/emergencies/{emergency_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["emergency"]["triage_severity"] == "HIGH"
    assert len(payload["hospital_evaluations"]) == 4
    assert payload["vital_history"]
    assert payload["location_history"]


def test_unknown_history_id_returns_controlled_not_found() -> None:
    """Unknown history IDs receive a normal 404 instead of a database traceback."""
    response = client.get("/history/emergencies/EMG-NOTFOUND")

    assert response.status_code == 404


def test_decision_remains_available_if_a_history_write_fails(monkeypatch) -> None:
    """SQLite audit failure is logged safely but cannot replace the working decision response."""
    client.post("/simulation/reset")

    def fail_history_write(*args, **kwargs):
        raise SQLAlchemyError("simulated test-only persistence failure")

    monkeypatch.setattr(persistence_service, "save_decision", fail_history_write)
    response = client.post("/emergency/decision")

    assert response.status_code == 200
    assert response.json()["selected_hospital"]["hospital_id"] == "HOSP002"


def test_end_to_end_persistence_records_full_arrived_emergency() -> None:
    """The full deterministic no-key workflow creates a complete persisted audit record."""
    assert client.post("/simulation/reset").status_code == 200
    assert client.post("/analysis").status_code == 200
    decision = client.post("/emergency/decision")
    assert decision.status_code == 200
    assert decision.json()["selected_hospital"]["hospital_id"] == "HOSP002"
    assert client.post("/journey/start").status_code == 200
    emergency_id = persistence_service.current_emergency_id
    assert emergency_id is not None

    for _ in range(10):
        assert client.post("/journey/update").status_code == 200

    history = client.get(f"/history/emergencies/{emergency_id}")
    assert history.status_code == 200
    payload = history.json()
    evaluations = {item["hospital_id"]: item for item in payload["hospital_evaluations"]}
    assert payload["emergency"]["status"] == "ARRIVED"
    assert payload["emergency"]["triage_severity"] == "HIGH"
    assert payload["emergency"]["selected_hospital_id"] == "HOSP002"
    assert payload["emergency"]["acknowledgement_status"] == "ACCEPTED"
    assert evaluations["HOSP003"]["missing_infrastructure"] == ["icu"]
    assert payload["vital_history"]
    assert payload["location_history"]
