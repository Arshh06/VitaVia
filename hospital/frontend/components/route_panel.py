"""Selected-hospital, acknowledgement, and routing-summary presentation."""

from typing import Any, Iterable, Mapping, Optional

import streamlit as st

from components.presentation import friendly_resource


def render_route_panel(decision: Mapping[str, Any]) -> None:
    """Render the backend-selected hospital and acknowledgement without recalculating selection."""
    st.subheader("Selected Hospital")
    selected_hospital = decision.get("selected_hospital")
    acknowledgement = decision.get("acknowledgement") or {}
    if not isinstance(selected_hospital, Mapping):
        st.error("No suitable hospital is currently available for the required infrastructure.")
        st.caption(acknowledgement.get("message", "No acknowledgement was received."))
        return

    st.success(f"Selected: {selected_hospital.get('name', 'Unknown Hospital')}")
    metrics = st.columns(4)
    metrics[0].metric("ETA", _format_eta(selected_hospital.get("eta_minutes")))
    metrics[1].metric("Distance", _format_distance(selected_hospital.get("distance_km")))
    metrics[2].metric("Traffic", selected_hospital.get("traffic_condition") or "—")
    metrics[3].metric("Routing Source", friendly_routing_source(selected_hospital.get("routing_source")))
    acknowledgement_status = acknowledgement.get("status", "—")
    acknowledgement_message = acknowledgement.get("message", "No acknowledgement message.")
    st.markdown(f"**Acknowledgement:** {'✅' if acknowledgement_status == 'ACCEPTED' else 'ℹ️'} {acknowledgement_status}")
    st.caption(acknowledgement_message)

    insight = build_nearest_vs_suitable_explanation(decision)
    if insight:
        st.info(f"**Why wasn't the closest hospital selected?** {insight}")


def friendly_routing_source(source: Optional[str]) -> str:
    """Translate backend routing provenance into a clear, non-misleading label."""
    if source == "google_maps":
        return "Google Maps Routes"
    if source == "mock":
        return "Mock routing (simulated)"
    return "—"


def build_nearest_vs_suitable_explanation(decision: Mapping[str, Any]) -> Optional[str]:
    """Explain backend eligibility outcomes without making a frontend selection decision."""
    selected_hospital = decision.get("selected_hospital")
    hospitals = decision.get("hospitals")
    if not isinstance(selected_hospital, Mapping) or not isinstance(hospitals, Iterable):
        return None

    selected_eta = selected_hospital.get("eta_minutes")
    if not isinstance(selected_eta, (int, float)):
        return None
    rejected_faster = [
        hospital
        for hospital in hospitals
        if isinstance(hospital, Mapping)
        and not hospital.get("eligible")
        and isinstance(hospital.get("eta_minutes"), (int, float))
        and hospital["eta_minutes"] < selected_eta
    ]
    if not rejected_faster:
        return None

    rejected_hospital = min(rejected_faster, key=lambda hospital: hospital["eta_minutes"])
    missing = rejected_hospital.get("missing_infrastructure") or []
    missing_text = _format_resources(missing) if missing else "required infrastructure"
    return (
        f"{rejected_hospital.get('name', 'A closer hospital')} has a shorter "
        f"{_format_eta(rejected_hospital.get('eta_minutes'))} ETA, but it is ineligible because "
        f"{missing_text} is unavailable. {selected_hospital.get('name', 'The selected hospital')} "
        "was selected by the backend because it has the required infrastructure and the lowest ETA "
        "among eligible hospitals."
    )


def _format_resources(resources: Iterable[str]) -> str:
    """Turn resource codes into readable labels."""
    return ", ".join(friendly_resource(resource) for resource in resources)


def _format_distance(value: Any) -> str:
    """Format optional route distance."""
    return f"{value} km" if value is not None else "—"


def _format_eta(value: Any) -> str:
    """Format optional route ETA."""
    return f"{value} min" if value is not None else "—"
