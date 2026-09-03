"""Read-only Streamlit presentation for persisted VITAVIA emergency history."""

from datetime import datetime
from typing import Any, Iterable, Mapping, Optional

import pandas as pd
import streamlit as st

from components.presentation import format_required_resources, friendly_ai_source
from components.route_panel import friendly_routing_source


_STATUS_LABELS = {
    "ARRIVED": "✅ Arrived",
    "RESET": "↺ Reset",
    "EN_ROUTE": "🚑 En Route",
    "ARRIVING": "🟠 Arriving",
    "NOT_STARTED": "Not Started",
    "ACTIVE": "Active",
    "DECIDED": "Decision Recorded",
}

def render_history_list(history_items: Iterable[Mapping[str, Any]]) -> None:
    """Render recent backend-returned emergency summaries without querying SQLite directly."""
    rows = [
        {
            "Emergency ID": item.get("emergency_id", "—"),
            "Status": friendly_history_status(item.get("status")),
            "Ambulance": item.get("ambulance_id", "—"),
            "Patient": item.get("patient_id", "—"),
            "Severity": item.get("triage_severity") or "—",
            "Selected Hospital": item.get("selected_hospital_name") or "—",
            "Acknowledgement": item.get("acknowledgement_status") or "—",
            "Started (UTC)": format_history_timestamp(item.get("started_at")),
            "Completed (UTC)": format_history_timestamp(item.get("completed_at")),
        }
        for item in history_items
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def render_history_selector(
    history_items: Iterable[Mapping[str, Any]], selected_emergency_id: Optional[str]
) -> Optional[str]:
    """Render a small selector and return only the stored emergency ID the user viewed."""
    entries = list(history_items)
    emergency_ids = [
        str(item.get("emergency_id"))
        for item in entries
        if item.get("emergency_id") is not None
    ]
    if not emergency_ids:
        return None
    selected_index = (
        emergency_ids.index(selected_emergency_id)
        if selected_emergency_id in emergency_ids
        else 0
    )
    summaries = {str(item.get("emergency_id")): item for item in entries}
    return st.selectbox(
        "View emergency",
        emergency_ids,
        index=selected_index,
        format_func=lambda emergency_id: _selector_label(emergency_id, summaries[emergency_id]),
    )


def render_history_detail(detail: Mapping[str, Any]) -> None:
    """Render stored audit data only; no AI, routing, or selection work occurs here."""
    emergency = detail.get("emergency") or {}
    st.subheader("Selected Historical Emergency (Read-only)")
    _render_detail_summary(emergency)
    _render_stored_triage(detail, emergency)
    _render_historical_hospital_evaluations(detail.get("hospital_evaluations") or [])
    _render_vital_history(detail.get("vital_history") or [])
    _render_location_history(detail.get("location_history") or [])


def friendly_history_status(status: Any) -> str:
    """Format a stored backend status for display without changing its persisted value."""
    text = str(status or "—")
    return _STATUS_LABELS.get(text, text.replace("_", " ").title())


def format_history_timestamp(value: Any) -> str:
    """Render stored UTC timestamps readably while preserving backend timestamp data unchanged."""
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    return parsed.strftime("%d %b %Y, %I:%M %p UTC")


def format_infrastructure(resources: Iterable[Any]) -> str:
    """Turn stored infrastructure codes into clear history-view labels."""
    return format_required_resources(resources)


def build_history_nearest_vs_suitable_explanation(
    evaluations: Iterable[Mapping[str, Any]]
) -> Optional[str]:
    """Explain a stored rejection without recomputing or replacing the saved selection."""
    candidates = [item for item in evaluations if isinstance(item, Mapping)]
    selected = next((item for item in candidates if item.get("selected")), None)
    if selected is None or not isinstance(selected.get("eta_minutes"), (int, float)):
        return None

    faster_rejected = [
        item
        for item in candidates
        if not item.get("eligible")
        and isinstance(item.get("eta_minutes"), (int, float))
        and item["eta_minutes"] < selected["eta_minutes"]
    ]
    if not faster_rejected:
        return None

    rejected = min(faster_rejected, key=lambda item: item["eta_minutes"])
    missing = format_infrastructure(rejected.get("missing_infrastructure") or [])
    rejected_name = rejected.get("hospital_name") or rejected.get("name") or "A faster hospital"
    selected_name = selected.get("hospital_name") or selected.get("name") or "The selected hospital"
    return (
        f"{rejected_name} had a shorter {rejected['eta_minutes']} min ETA but was rejected because "
        f"{missing} was unavailable. The stored decision selected {selected_name} because it was "
        "eligible and had the lowest ETA among eligible hospitals."
    )


def _render_detail_summary(emergency: Mapping[str, Any]) -> None:
    """Show the stored emergency audit summary before its detailed timelines."""
    rows = [
        ("Emergency ID", emergency.get("emergency_id")),
        ("Ambulance", emergency.get("ambulance_id")),
        ("Patient", emergency.get("patient_id")),
        ("Emergency type", emergency.get("emergency_type")),
        ("Final status", friendly_history_status(emergency.get("status"))),
        ("Severity", emergency.get("triage_severity") or "—"),
        ("Triage source", friendly_ai_source(emergency.get("triage_source"))),
        ("Selected hospital", emergency.get("selected_hospital_name") or "—"),
        ("Acknowledgement", emergency.get("acknowledgement_status") or "—"),
        ("Routing Source", friendly_routing_source(emergency.get("routing_source"))),
        ("Initial ETA", _format_eta(emergency.get("initial_eta_minutes"))),
        ("Started (UTC)", format_history_timestamp(emergency.get("started_at"))),
        ("Completed (UTC)", format_history_timestamp(emergency.get("completed_at"))),
    ]
    columns = st.columns(3)
    for index, (label, value) in enumerate(rows):
        columns[index % 3].metric(label, value or "—")


def _render_stored_triage(detail: Mapping[str, Any], emergency: Mapping[str, Any]) -> None:
    """Display exactly the triage summary stored at the time of the emergency."""
    st.markdown("#### Stored Triage")
    severity = emergency.get("triage_severity") or "—"
    if severity == "CRITICAL":
        st.error(f"Severity: {severity}")
    elif severity == "HIGH":
        st.warning(f"Severity: {severity}")
    elif severity == "MODERATE":
        st.info(f"Severity: {severity}")
    else:
        st.success(f"Severity: {severity}")
    st.caption(f"Source: {friendly_ai_source(emergency.get('triage_source'))}")
    st.markdown(
        "**Required infrastructure:** "
        + format_infrastructure(detail.get("required_infrastructure") or [])
    )
    st.write(detail.get("triage_explanation") or "No stored triage explanation available.")


def _render_historical_hospital_evaluations(evaluations: Iterable[Mapping[str, Any]]) -> None:
    """Render stored candidate records distinctly from the live hospital decision cards."""
    entries = list(evaluations)
    st.markdown("#### Historical Hospital Evaluations")
    if not entries:
        st.info("No stored hospital evaluations are available for this emergency.")
        return

    insight = build_history_nearest_vs_suitable_explanation(entries)
    if insight:
        st.info(f"**Why wasn't the fastest hospital selected?** {insight}")

    for hospital in entries:
        eligible = bool(hospital.get("eligible"))
        selected = bool(hospital.get("selected"))
        status = "✅ ELIGIBLE" if eligible else "❌ INELIGIBLE"
        selected_label = " · ⭐ SELECTED" if selected else ""
        with st.container(border=True):
            st.markdown(f"**{hospital.get('hospital_name', 'Unknown Hospital')}**")
            st.caption(f"{hospital.get('hospital_id', '—')} · {status}{selected_label}")
            metrics = st.columns(4)
            metrics[0].metric("Distance", _format_distance(hospital.get("distance_km")))
            metrics[1].metric("Traffic", hospital.get("traffic_condition") or "—")
            metrics[2].metric("ETA", _format_eta(hospital.get("eta_minutes")))
            metrics[3].metric("Routing Source", friendly_routing_source(hospital.get("routing_source")))
            missing = hospital.get("missing_infrastructure") or []
            if missing:
                st.warning(f"Missing required infrastructure: {format_infrastructure(missing)}")
            else:
                st.success("All stored required infrastructure was available.")
            st.caption(f"Acknowledgement: {hospital.get('acknowledgement_status') or '—'}")


def _render_vital_history(vital_history: Iterable[Mapping[str, Any]]) -> None:
    """Present stored simulated vital readings in a table plus lightweight native charts."""
    entries = list(vital_history)
    st.markdown("#### Vital History")
    if not entries:
        st.info("No stored vital readings are available for this emergency.")
        return

    table_rows = [
        {
            "Recorded (UTC)": format_history_timestamp(item.get("recorded_at")),
            "SpO2 (%)": item.get("spo2"),
            "Heart Rate (BPM)": item.get("heart_rate"),
            "Systolic BP": item.get("systolic_bp"),
            "Diastolic BP": item.get("diastolic_bp"),
            "Temperature (°C)": item.get("temperature"),
        }
        for item in entries
    ]
    st.dataframe(table_rows, width="stretch", hide_index=True)
    if len(entries) > 1:
        chart_data = pd.DataFrame(entries)
        chart_data.index = range(1, len(chart_data) + 1)
        st.caption("Recorded simulated vital trends")
        spo2_chart, heart_rate_chart, temperature_chart = st.columns(3)
        spo2_chart.line_chart(chart_data[["spo2"]])
        heart_rate_chart.line_chart(chart_data[["heart_rate"]])
        temperature_chart.line_chart(chart_data[["temperature"]])


def _render_location_history(location_history: Iterable[Mapping[str, Any]]) -> None:
    """Present stored GPS/journey records in a table plus simple progress and ETA charts."""
    entries = list(location_history)
    st.markdown("#### Journey & Location History")
    if not entries:
        st.info("No stored ambulance location records are available for this emergency.")
        return

    table_rows = [
        {
            "Recorded (UTC)": format_history_timestamp(item.get("recorded_at")),
            "Latitude": item.get("latitude"),
            "Longitude": item.get("longitude"),
            "Ambulance Status": friendly_history_status(item.get("ambulance_status")),
            "Journey Status": friendly_history_status(item.get("journey_status")),
            "Progress (%)": item.get("progress_percent"),
            "Remaining ETA (min)": item.get("remaining_eta_minutes"),
        }
        for item in entries
    ]
    st.dataframe(table_rows, width="stretch", hide_index=True)
    journey_points = [
        item
        for item in entries
        if isinstance(item.get("progress_percent"), (int, float))
        or isinstance(item.get("remaining_eta_minutes"), (int, float))
    ]
    if len(journey_points) > 1:
        chart_data = pd.DataFrame(journey_points)
        chart_data.index = range(1, len(chart_data) + 1)
        chart_columns = [
            column
            for column in ("progress_percent", "remaining_eta_minutes")
            if column in chart_data
        ]
        if chart_columns:
            st.caption("Stored simulated journey progress and remaining ETA")
            progress_chart, eta_chart = st.columns(2)
            if "progress_percent" in chart_columns:
                progress_chart.line_chart(chart_data[["progress_percent"]])
            if "remaining_eta_minutes" in chart_columns:
                eta_chart.line_chart(chart_data[["remaining_eta_minutes"]])


def friendly_triage_source(source: Any) -> str:
    """Label stored triage provenance without implying autonomous diagnosis."""
    return friendly_ai_source(source)


def _selector_label(emergency_id: str, summary: Mapping[str, Any]) -> str:
    """Keep selector entries compact while showing their final stored state."""
    return f"{emergency_id} · {friendly_history_status(summary.get('status'))}"


def _format_distance(value: Any) -> str:
    """Format an optional stored routing distance."""
    return f"{value} km" if value is not None else "—"


def _format_eta(value: Any) -> str:
    """Format an optional stored routing ETA."""
    return f"{value} min" if value is not None else "—"
