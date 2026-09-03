"""Shared user-facing terminology for VITAVIA's display-only frontend components."""

from typing import Any, Iterable


_RESOURCE_LABELS = {
    "emergency_bed": "Emergency Bed",
    "icu": "ICU",
    "ventilator": "Ventilator",
    "emergency_team": "Emergency Team",
}


def friendly_resource(resource: Any) -> str:
    """Translate one backend infrastructure key into consistent dashboard terminology."""
    value = str(resource)
    return _RESOURCE_LABELS.get(value, value.replace("_", " ").title())


def format_required_resources(resources: Iterable[Any]) -> str:
    """Format stored or live backend infrastructure requirements for display only."""
    labels = [friendly_resource(resource) for resource in resources]
    return " · ".join(f"✓ {label}" for label in labels) if labels else "—"


def friendly_ai_source(source: Any) -> str:
    """Describe triage provenance without implying autonomous clinical decision-making."""
    if source in {"gemini", "gemini_guarded"}:
        return "Gemini-assisted + deterministic guard"
    return "Deterministic fallback"
