"""Presentation for the backend-controlled VITAVIA journey simulation."""

from typing import Any, Mapping, Optional

import streamlit as st

from components.route_panel import friendly_routing_source


def render_journey_panel(journey: Mapping[str, Any]) -> None:
    """Render journey data returned by FastAPI without changing its state or destination."""
    st.subheader("Live Ambulance Journey (Simulation)")
    status = str(journey.get("status", "NOT_STARTED"))
    selected_name = journey.get("selected_hospital_name") or "No destination selected"

    if status == "ARRIVED":
        st.success(f"✅ Ambulance arrived at {selected_name}")
    elif journey.get("active"):
        icon = "🟠" if status == "ARRIVING" else "🚑"
        st.info(f"{icon} {friendly_journey_status(status)} — destination: {selected_name}")
    else:
        st.caption("Journey has not started. Run the backend decision, then start the journey.")
        return

    progress = _clamp_progress(journey.get("progress_percent"))
    st.progress(progress / 100, text=f"Journey progress: {progress:.0f}%")
    eta = journey.get("remaining_eta_minutes")
    metrics = st.columns(3)
    metrics[0].metric("Status", friendly_journey_status(status))
    metrics[1].metric("Remaining ETA", f"{eta} min" if eta is not None else "—")
    metrics[2].metric("Routing Source", friendly_routing_source(journey.get("routing_source")))

    current = journey.get("current_location") or {}
    destination = journey.get("destination_location") or {}
    locations = st.columns(2)
    locations[0].caption(
        "Current GPS: " + _format_location(current)
    )
    locations[1].caption(
        "Destination GPS: " + _format_location(destination)
    )


def friendly_journey_status(status: Any) -> str:
    """Turn a backend status code into a concise dashboard label."""
    return str(status).replace("_", " ").title()


def _clamp_progress(value: Optional[Any]) -> float:
    """Safely constrain display-only progress to Streamlit's accepted range."""
    if not isinstance(value, (int, float)):
        return 0.0
    return max(0.0, min(float(value), 100.0))


def _format_location(location: Mapping[str, Any]) -> str:
    """Format a response location without attempting frontend navigation."""
    latitude, longitude = location.get("latitude"), location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return "—"
    return f"{latitude:.6f}, {longitude:.6f}"
