"""Patient vital-sign presentation for the VITAVIA hospital control room."""

from typing import Any, Mapping

import streamlit as st


def render_vitals_panel(
    vitals: Mapping[str, Any], *, triage_severity: Any = None
) -> None:
    """Render backend values with an existing backend-urgency indicator only."""
    columns = st.columns(4)
    columns[0].metric("SpO₂", _format_value(vitals.get("spo2"), "%"))
    columns[1].metric("Heart Rate", _format_value(vitals.get("heart_rate"), "BPM"))
    blood_pressure = f"{vitals.get('systolic_bp', '—')}/{vitals.get('diastolic_bp', '—')} mmHg"
    columns[2].metric("Blood Pressure", blood_pressure)
    columns[3].metric("Temperature", _format_value(vitals.get("temperature"), "°C"))
    indicator = _backend_urgency_indicator(triage_severity)
    for column in columns:
        column.caption(indicator)


def _format_value(value: Any, suffix: str) -> str:
    """Format a displayed vital value while preserving missing-state clarity."""
    return f"{value} {suffix}" if value is not None else "—"


def _backend_urgency_indicator(severity: Any) -> str:
    """Avoid a second frontend assessment by reusing only stored backend urgency."""
    if severity in {"CRITICAL", "HIGH"}:
        return f"⚠ Backend urgency: {severity}"
    if severity == "MODERATE":
        return "🟡 Backend urgency: MODERATE"
    if severity == "LOW":
        return "🟢 Backend urgency: LOW"
    return "• Awaiting backend assessment"
