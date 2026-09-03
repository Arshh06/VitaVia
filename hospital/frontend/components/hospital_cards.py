"""Hospital-decision card presentation for the VITAVIA dashboard."""

from typing import Any, Iterable, Mapping

import streamlit as st

from components.presentation import format_required_resources
from components.route_panel import friendly_routing_source


def render_hospital_cards(hospitals: Iterable[Mapping[str, Any]]) -> None:
    """Render backend decision data for every hospital without selecting a winner locally."""
    st.subheader("Hospital Evaluation (Simulated Availability)")
    for hospital in hospitals:
        _render_hospital_card(hospital)


def _render_hospital_card(hospital: Mapping[str, Any]) -> None:
    """Render one compact eligibility and routing card."""
    eligible = bool(hospital.get("eligible"))
    selected = bool(hospital.get("selected"))
    status = "✅ ELIGIBLE" if eligible else "❌ INELIGIBLE"
    selected_label = " · ⭐ SELECTED" if selected else ""

    with st.container(border=True):
        st.markdown(f"**{hospital.get('name', 'Unknown Hospital')}**  ")
        st.caption(f"{hospital.get('hospital_id', '—')} · {status}{selected_label}")
        details = st.columns(4)
        details[0].metric("Distance", _format_distance(hospital.get("distance_km")))
        details[1].metric("Traffic", hospital.get("traffic_condition") or "—")
        details[2].metric("ETA", _format_eta(hospital.get("eta_minutes")))
        details[3].metric("Routing Source", friendly_routing_source(hospital.get("routing_source")))

        missing = hospital.get("missing_infrastructure") or []
        if missing:
            st.warning(f"Missing required infrastructure: {format_required_resources(missing)}")
        else:
            st.success("All backend-required infrastructure is available.")
        acknowledgement = hospital.get("acknowledgement_status") or "—"
        st.caption(f"Acknowledgement: {acknowledgement}")


def _format_distance(value: Any) -> str:
    """Format an optional backend distance."""
    return f"{value} km" if value is not None else "—"


def _format_eta(value: Any) -> str:
    """Format an optional backend ETA."""
    return f"{value} min" if value is not None else "—"
