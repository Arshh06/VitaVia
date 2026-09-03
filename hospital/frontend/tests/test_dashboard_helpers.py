"""Pure helper tests for dashboard explanations that do not require Streamlit automation."""

from components.route_panel import build_nearest_vs_suitable_explanation


def test_nearest_unsuitable_explanation_uses_backend_decision_data() -> None:
    """The dashboard explains a rejected faster hospital without selecting one itself."""
    decision = {
        "selected_hospital": {
            "hospital_id": "HOSP002",
            "name": "Metro Emergency Institute",
            "eta_minutes": 10.0,
        },
        "hospitals": [
            {
                "hospital_id": "HOSP002",
                "name": "Metro Emergency Institute",
                "eligible": True,
                "eta_minutes": 10.0,
                "missing_infrastructure": [],
            },
            {
                "hospital_id": "HOSP003",
                "name": "GreenCross Trauma Centre",
                "eligible": False,
                "eta_minutes": 7.0,
                "missing_infrastructure": ["icu"],
            },
        ],
    }

    explanation = build_nearest_vs_suitable_explanation(decision)

    assert explanation is not None
    assert "GreenCross Trauma Centre" in explanation
    assert "7.0 min" in explanation
    assert "ICU" in explanation
    assert "Metro Emergency Institute" in explanation
