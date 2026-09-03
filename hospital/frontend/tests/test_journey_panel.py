"""Focused tests for safe, display-only journey helpers."""

from components.journey_panel import friendly_journey_status


def test_friendly_journey_status_formats_backend_codes() -> None:
    """The frontend only formats backend journey state; it does not derive it."""
    assert friendly_journey_status("EN_ROUTE") == "En Route"
    assert friendly_journey_status("ARRIVED") == "Arrived"
