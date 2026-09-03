"""Offline tests for VITAVIA's optional Gemini-assisted triage layer."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import TriageResult
from app.services import gemini_service, triage_service
from app.services.simulation_service import simulation_service


client = TestClient(app)
DEFAULT_REQUIREMENTS = ["emergency_bed", "icu", "emergency_team"]


def test_no_api_key_uses_deterministic_fallback(monkeypatch) -> None:
    """A missing key must leave the prototype fully usable without an SDK request."""
    monkeypatch.setattr(gemini_service.settings, "gemini_api_key", None)

    result = triage_service.analyze_vitals_assisted(_default_vitals())

    assert result.severity == "HIGH"
    assert result.required_infrastructure == DEFAULT_REQUIREMENTS
    assert result.source == "deterministic"


def test_valid_gemini_result_is_normalized_and_used(monkeypatch) -> None:
    """A valid mocked SDK response is normalized before the guard uses it."""
    _configure_fake_gemini(
        monkeypatch,
        {
            "severity": "HIGH",
            "required_infrastructure": [
                "emergency_bed",
                "icu",
                "icu",
                "emergency_team",
            ],
            "explanation": "AI-assisted simulated triage result.",
        },
    )

    gemini_result = gemini_service.analyze_vitals_with_gemini(_default_vitals())

    assert gemini_result is not None
    assert gemini_result.source == "gemini"
    assert gemini_result.required_infrastructure == DEFAULT_REQUIREMENTS
    monkeypatch.setattr(
        triage_service,
        "analyze_vitals_with_gemini",
        lambda vitals, emergency_type: TriageResult(
            severity="HIGH",
            required_infrastructure=DEFAULT_REQUIREMENTS,
            explanation="AI-assisted simulated triage result.",
            source="gemini",
        ),
    )

    result = triage_service.analyze_vitals_assisted(_default_vitals())

    assert result.source == "gemini"
    assert result.severity == "HIGH"
    assert result.required_infrastructure == DEFAULT_REQUIREMENTS


def test_malformed_gemini_response_falls_back_to_deterministic(monkeypatch) -> None:
    """Unsupported Gemini values are rejected before they can affect the pipeline."""
    malformed_payload = {
        "severity": "URGENT",
        "required_infrastructure": ["emergency_bed", "teleporter"],
        "explanation": "Invalid simulated output.",
    }
    _configure_fake_gemini(monkeypatch, malformed_payload)
    assert gemini_service.analyze_vitals_with_gemini(_default_vitals()) is None
    monkeypatch.setattr(triage_service, "analyze_vitals_with_gemini", lambda vitals, emergency_type: None)

    result = triage_service.analyze_vitals_assisted(_default_vitals())

    assert result.source == "deterministic"
    assert result.required_infrastructure == DEFAULT_REQUIREMENTS


def test_gemini_exception_falls_back_without_reaching_the_api(monkeypatch) -> None:
    """An unexpected Gemini-service exception cannot escape the triage orchestrator."""
    monkeypatch.setattr(gemini_service.settings, "gemini_api_key", "test-key")

    def raise_client_error():
        raise RuntimeError("simulated SDK failure")

    monkeypatch.setattr(gemini_service, "_create_gemini_client", raise_client_error)
    assert gemini_service.analyze_vitals_with_gemini(_default_vitals()) is None

    def raise_gemini_error(vitals, emergency_type):
        raise RuntimeError("simulated Gemini failure")

    monkeypatch.setattr(triage_service, "analyze_vitals_with_gemini", raise_gemini_error)

    result = triage_service.analyze_vitals_assisted(_default_vitals())

    assert result.source == "deterministic"
    assert result.severity == "HIGH"


def test_deterministic_guard_prevents_gemini_downgrade(monkeypatch) -> None:
    """Gemini cannot reduce the default HIGH/ICU-capable requirement set."""
    monkeypatch.setattr(
        triage_service,
        "analyze_vitals_with_gemini",
        lambda vitals, emergency_type: TriageResult(
            severity="LOW",
            required_infrastructure=["emergency_bed"],
            explanation="AI attempted a lower simulated acuity.",
            source="gemini",
        ),
    )

    result = triage_service.analyze_vitals_assisted(_default_vitals())

    assert result.source == "gemini"
    assert result.severity == "HIGH"
    assert result.required_infrastructure == DEFAULT_REQUIREMENTS


def test_gemini_can_add_higher_acuity_infrastructure(monkeypatch) -> None:
    """Gemini can augment the deterministic result with a higher simulated requirement."""
    monkeypatch.setattr(
        triage_service,
        "analyze_vitals_with_gemini",
        lambda vitals, emergency_type: TriageResult(
            severity="CRITICAL",
            required_infrastructure=[
                "emergency_bed",
                "icu",
                "emergency_team",
                "ventilator",
            ],
            explanation="AI-assisted simulated triage added ventilator support.",
            source="gemini",
        ),
    )

    result = triage_service.analyze_vitals_assisted(_default_vitals())

    assert result.source == "gemini"
    assert result.severity == "CRITICAL"
    assert result.required_infrastructure == [
        "emergency_bed",
        "icu",
        "emergency_team",
        "ventilator",
    ]


def test_decision_endpoint_keeps_hospital_selection_deterministic(monkeypatch) -> None:
    """A valid Gemini analysis cannot bypass ICU filtering or ETA-based selection."""
    monkeypatch.setattr(
        triage_service,
        "analyze_vitals_with_gemini",
        lambda vitals, emergency_type: TriageResult(
            severity="HIGH",
            required_infrastructure=DEFAULT_REQUIREMENTS,
            explanation="AI-assisted simulated triage result.",
            source="gemini",
        ),
    )
    client.post("/simulation/reset")

    response = client.post("/emergency/decision")
    payload = response.json()
    hospitals = {hospital["hospital_id"]: hospital for hospital in payload["hospitals"]}

    assert response.status_code == 200
    assert payload["triage"]["source"] == "gemini"
    assert hospitals["HOSP003"]["eligible"] is False
    assert hospitals["HOSP003"]["missing_infrastructure"] == ["icu"]
    assert payload["selected_hospital"]["hospital_id"] == "HOSP002"
    assert payload["acknowledgement"]["status"] == "ACCEPTED"


def test_decision_endpoint_survives_gemini_failure(monkeypatch) -> None:
    """A Gemini failure still returns the complete deterministic decision response."""
    def raise_gemini_error(vitals, emergency_type):
        raise RuntimeError("simulated Gemini failure")

    monkeypatch.setattr(triage_service, "analyze_vitals_with_gemini", raise_gemini_error)
    client.post("/simulation/reset")

    response = client.post("/emergency/decision")
    payload = response.json()

    assert response.status_code == 200
    assert payload["triage"]["source"] == "deterministic"
    assert payload["selected_hospital"]["hospital_id"] == "HOSP002"
    assert payload["acknowledgement"]["status"] == "ACCEPTED"


def test_analysis_endpoint_uses_no_key_fallback(monkeypatch) -> None:
    """The dedicated analysis endpoint remains functional without Gemini configuration."""
    monkeypatch.setattr(gemini_service.settings, "gemini_api_key", None)
    client.post("/simulation/reset")

    response = client.post("/analysis")

    assert response.status_code == 200
    assert response.json()["source"] == "deterministic"


def _default_vitals():
    """Return the original Stage 2 simulated vitals for each isolated test."""
    simulation_service.reset_simulation()
    return simulation_service.get_current_snapshot().vitals


def _configure_fake_gemini(monkeypatch, payload: dict) -> None:
    """Install a local fake SDK response so Gemini tests never use the network."""
    class FakeResponse:
        parsed = payload

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    class FakeTypes:
        class GenerateContentConfig:
            def __init__(self, **kwargs) -> None:
                self.options = kwargs

    monkeypatch.setattr(gemini_service.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        gemini_service,
        "_create_gemini_client",
        lambda: (FakeClient(), FakeTypes),
    )
