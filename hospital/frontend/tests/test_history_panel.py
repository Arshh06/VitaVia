"""Pure helper tests for the read-only emergency-history presentation."""

from components.history_panel import (
    build_history_nearest_vs_suitable_explanation,
    format_infrastructure,
    friendly_history_status,
)


def test_history_status_formatting_is_human_friendly() -> None:
    """Stored backend status codes are rendered without changing their values."""
    assert friendly_history_status("ARRIVED") == "✅ Arrived"
    assert friendly_history_status("RESET") == "↺ Reset"
    assert friendly_history_status("EN_ROUTE") == "🚑 En Route"


def test_history_explanation_uses_stored_rejection_reason() -> None:
    """A historical faster ineligible hospital is explained, not reconsidered by the frontend."""
    evaluations = [
        {
            "hospital_id": "HOSP002",
            "hospital_name": "Metro Emergency Institute",
            "eligible": True,
            "eta_minutes": 10.0,
            "selected": True,
            "missing_infrastructure": [],
        },
        {
            "hospital_id": "HOSP003",
            "hospital_name": "GreenCross Trauma Centre",
            "eligible": False,
            "eta_minutes": 7.0,
            "selected": False,
            "missing_infrastructure": ["icu"],
        },
    ]

    explanation = build_history_nearest_vs_suitable_explanation(evaluations)

    assert explanation is not None
    assert "GreenCross Trauma Centre" in explanation
    assert "7.0 min" in explanation
    assert "ICU" in explanation
    assert "Metro Emergency Institute" in explanation


def test_history_explanation_is_omitted_when_no_faster_rejected_hospital_exists() -> None:
    """The UI does not force a nearest-vs-suitable message when stored data does not support it."""
    evaluations = [
        {
            "hospital_name": "VitaCare Medical Centre",
            "eligible": True,
            "eta_minutes": 8.0,
            "selected": True,
        },
        {
            "hospital_name": "Metro Emergency Institute",
            "eligible": True,
            "eta_minutes": 10.0,
            "selected": False,
        },
    ]

    assert build_history_nearest_vs_suitable_explanation(evaluations) is None


def test_required_infrastructure_formatting_is_readable() -> None:
    """Stored resource IDs stay understandable in the audit view."""
    assert format_infrastructure(["emergency_bed", "icu", "emergency_team"]) == (
        "✓ Emergency Bed · ✓ ICU · ✓ Emergency Team"
    )
