"""Focused tests for consistent user-facing VITAVIA terminology."""

from components.presentation import format_required_resources, friendly_ai_source, friendly_resource


def test_resource_labels_use_consistent_medical_resource_names() -> None:
    """Internal resource keys remain unchanged while the UI uses readable labels."""
    assert friendly_resource("icu") == "ICU"
    assert format_required_resources(["emergency_bed", "icu", "emergency_team"]) == (
        "✓ Emergency Bed · ✓ ICU · ✓ Emergency Team"
    )


def test_ai_source_labels_keep_the_deterministic_guard_visible() -> None:
    """Dashboard wording never presents Gemini as an autonomous medical authority."""
    assert friendly_ai_source("gemini") == "Gemini-assisted + deterministic guard"
    assert friendly_ai_source("deterministic") == "Deterministic fallback"
