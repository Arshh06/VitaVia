"""Tests for VITAVIA's deterministic Stage 3 decision pipeline."""

from fastapi.testclient import TestClient

from app.data.hospitals import get_all_hospitals
from app.main import app
from app.models.schemas import HospitalDecision
from app.services.hospital_service import evaluate_hospitals
from app.services.selection_service import create_acknowledgement, select_fastest_eligible_hospital
from app.services.simulation_service import simulation_service
from app.services.triage_service import analyze_vitals


client = TestClient(app)
DEFAULT_REQUIREMENTS = ["emergency_bed", "icu", "emergency_team"]


def test_default_vitals_produce_high_deterministic_triage() -> None:
    """The default demo emergency must require an ICU-capable emergency hospital."""
    simulation_service.reset_simulation()

    triage = analyze_vitals(simulation_service.get_current_snapshot().vitals)

    assert triage.severity == "HIGH"
    assert triage.required_infrastructure == DEFAULT_REQUIREMENTS
    assert triage.source == "deterministic"


def test_infrastructure_filtering_marks_missing_resources() -> None:
    """Infrastructure, not distance or traffic, determines initial eligibility."""
    evaluations = evaluate_hospitals(DEFAULT_REQUIREMENTS, get_all_hospitals())
    evaluation_by_id = {evaluation.hospital_id: evaluation for evaluation in evaluations}

    assert evaluation_by_id["HOSP001"].eligible is True
    assert evaluation_by_id["HOSP002"].eligible is True
    assert evaluation_by_id["HOSP003"].eligible is False
    assert evaluation_by_id["HOSP003"].missing_infrastructure == ["icu"]
    assert evaluation_by_id["HOSP004"].eligible is False
    assert evaluation_by_id["HOSP004"].missing_infrastructure == ["emergency_bed"]


def test_nearest_unsuitable_hospital_is_not_selected() -> None:
    """HOSP003 has the shortest mock route but no ICU, so it cannot be selected."""
    response = _reset_and_get_decision()
    hospitals = _hospitals_by_id(response.json())

    assert hospitals["HOSP003"]["distance_km"] == 4.0
    assert hospitals["HOSP003"]["eta_minutes"] == 7.0
    assert hospitals["HOSP003"]["eligible"] is False
    assert hospitals["HOSP003"]["missing_infrastructure"] == ["icu"]
    assert hospitals["HOSP003"]["selected"] is False


def test_fastest_eligible_hospital_is_selected() -> None:
    """HOSP002 wins because it has the lowest ETA among eligible hospitals."""
    response = _reset_and_get_decision()
    payload = response.json()
    hospitals = _hospitals_by_id(payload)

    assert hospitals["HOSP001"]["eligible"] is True
    assert hospitals["HOSP001"]["eta_minutes"] == 17.0
    assert hospitals["HOSP001"]["selected"] is False
    assert hospitals["HOSP002"]["eligible"] is True
    assert hospitals["HOSP002"]["eta_minutes"] == 10.0
    assert hospitals["HOSP002"]["selected"] is True
    assert payload["selected_hospital"]["hospital_id"] == "HOSP002"


def test_selected_hospital_and_response_are_acknowledged() -> None:
    """The selected hospital must be the only one receiving an accepted acknowledgement."""
    response = _reset_and_get_decision()
    payload = response.json()
    hospitals = _hospitals_by_id(payload)

    assert hospitals["HOSP002"]["acknowledgement_status"] == "ACCEPTED"
    assert payload["acknowledgement"]["status"] == "ACCEPTED"
    assert payload["acknowledgement"]["hospital_id"] == "HOSP002"


def test_decision_endpoint_returns_complete_default_response() -> None:
    """The public endpoint combines simulation, triage, selection, and acknowledgement."""
    response = _reset_and_get_decision()
    payload = response.json()

    assert response.status_code == 200
    assert payload["ambulance"]["ambulance_id"] == "AMB001"
    assert payload["patient"]["patient_id"] == "PAT001"
    assert payload["triage"]["severity"] == "HIGH"
    assert len(payload["hospitals"]) == 4
    assert payload["selected_hospital"]["hospital_id"] == "HOSP002"
    assert payload["acknowledgement"]["status"] == "ACCEPTED"


def test_selector_handles_no_eligible_hospitals() -> None:
    """No eligible option returns a safe null selection and clear acknowledgement."""
    rejected = HospitalDecision(
        hospital_id="HOSP999",
        name="Unavailable Demo Hospital",
        eligible=False,
        missing_infrastructure=["icu"],
        selected=False,
        acknowledgement_status="INELIGIBLE",
    )

    selected_hospital = select_fastest_eligible_hospital([rejected])
    acknowledgement = create_acknowledgement(selected_hospital)

    assert selected_hospital is None
    assert acknowledgement.status == "NO_SUITABLE_HOSPITAL"
    assert acknowledgement.hospital_id is None


def _reset_and_get_decision():
    """Start each API pipeline test from the immutable Stage 2 demo state."""
    reset_response = client.post("/simulation/reset")
    assert reset_response.status_code == 200
    return client.post("/emergency/decision")


def _hospitals_by_id(payload: dict) -> dict:
    """Make decision assertions readable by indexing the response hospital list."""
    return {hospital["hospital_id"]: hospital for hospital in payload["hospitals"]}
