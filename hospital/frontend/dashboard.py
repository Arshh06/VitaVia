"""Hospital-side Streamlit emergency control room for existing VITAVIA backend data."""

from datetime import datetime
from typing import Any, Mapping, Optional

import streamlit as st

from api_client import ApiClientError, VitaviaApiClient
from components.history_panel import (
    render_history_detail,
    render_history_list,
    render_history_selector,
)
from components.presentation import format_required_resources, friendly_ai_source
from components.route_panel import friendly_routing_source
from components.vitals_panel import render_vitals_panel


st.set_page_config(
    page_title="VitaVia Hospital Emergency Control Room",
    page_icon="🏥",
    layout="wide",
)


def main() -> None:
    """Render a read-only hospital console from the existing FastAPI data flow."""
    _initialize_session_state()
    client = VitaviaApiClient()
    connected = _refresh_connection_state(client)

    hospital = _render_header_and_hospital_selector(connected)
    _render_hospital_feed(connected, hospital)
    _render_history_section(client, connected)


def _initialize_session_state() -> None:
    """Create only the local presentation state required by the hospital console."""
    defaults = {
        "current_snapshot": None,
        "journey_state": None,
        "hospital_catalog": None,
        "selected_hospital_id": None,
        "backend_connected": False,
        "live_mission_summary": None,
        "live_mission_detail": None,
        "incoming_emergency": None,
        "hospital_feed_error": None,
        "history_items": None,
        "selected_emergency_id": None,
        "selected_emergency_detail": None,
        "history_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _refresh_connection_state(client: VitaviaApiClient) -> bool:
    """Load initial backend-owned data while keeping a temporary outage user-friendly."""
    try:
        health = client.get_health()
    except ApiClientError:
        st.session_state.backend_connected = False
        return False

    connected = health.get("status") == "ok"
    st.session_state.backend_connected = connected
    if not connected:
        return False

    _refresh_hospital_catalog(client)
    _refresh_live_mission(client)
    if st.session_state.history_items is None:
        _refresh_history(client)
    return True


def _refresh_hospital_catalog(client: VitaviaApiClient) -> None:
    """Load simulated hospital readiness data from FastAPI, never frontend mock data."""
    if st.session_state.hospital_catalog is not None:
        return
    try:
        hospitals = client.get_hospitals()
    except ApiClientError:
        return
    st.session_state.hospital_catalog = hospitals
    if hospitals and st.session_state.selected_hospital_id is None:
        st.session_state.selected_hospital_id = hospitals[0].get("hospital_id")


def _refresh_live_mission(client: VitaviaApiClient) -> None:
    """Poll telemetry, history, and latest ambulance request without calling AI or selection."""
    errors = []
    try:
        st.session_state.current_snapshot = client.get_snapshot()
    except ApiClientError:
        errors.append("ambulance telemetry")

    try:
        st.session_state.journey_state = client.get_journey_status()
    except ApiClientError:
        errors.append("journey status")

    try:
        st.session_state.incoming_emergency = client.get_incoming_emergency(
            st.session_state.selected_hospital_id
        )
    except ApiClientError:
        errors.append("incoming emergency request")

    try:
        recent = client.get_emergency_history(limit=1)
    except ApiClientError:
        errors.append("emergency request")
    else:
        summary = recent[0] if recent else None
        st.session_state.live_mission_summary = summary
        if isinstance(summary, Mapping) and summary.get("emergency_id"):
            try:
                st.session_state.live_mission_detail = client.get_emergency_detail(
                    str(summary["emergency_id"])
                )
            except ApiClientError:
                errors.append("emergency request detail")
        else:
            st.session_state.live_mission_detail = None

    st.session_state.hospital_feed_error = (
        "Some live hospital-console information is temporarily unavailable: "
        + ", ".join(errors)
        + "."
        if errors
        else None
    )


def _render_header_and_hospital_selector(connected: bool) -> Optional[Mapping[str, Any]]:
    """Show selected hospital identity and compact control-room status at the top."""
    st.title("🏥 VitaVia | Hospital Emergency Control Room")
    st.caption("Hospital-side view • Ambulance telemetry and decisions arrive through FastAPI")
    st.info("Simulation prototype only — not for real medical decision-making.")

    hospitals = st.session_state.hospital_catalog or []
    if hospitals:
        hospital_ids = [str(hospital.get("hospital_id", "")) for hospital in hospitals]
        if st.session_state.selected_hospital_id not in hospital_ids:
            st.session_state.selected_hospital_id = hospital_ids[0]
        selected_hospital_id = st.selectbox(
            "Hospital control room",
            hospital_ids,
            format_func=lambda hospital_id: _hospital_selector_label(hospital_id, hospitals),
        )
        st.session_state.selected_hospital_id = selected_hospital_id
        hospital = next(
            (entry for entry in hospitals if entry.get("hospital_id") == selected_hospital_id),
            None,
        )
    else:
        hospital = None
        st.warning("Simulated hospital data is unavailable from the backend.")

    hospital_name = hospital.get("name", "Hospital data unavailable") if hospital else "—"
    hospital_id = hospital.get("hospital_id", "—") if hospital else "—"
    status_columns = st.columns(5)
    status_columns[0].metric("Hospital", hospital_name)
    status_columns[1].metric("Hospital ID", hospital_id)
    status_columns[2].metric("Emergency Department", "ONLINE" if connected else "OFFLINE")
    status_columns[3].metric("Backend", "CONNECTED" if connected else "OFFLINE")
    status_columns[4].metric("Local time", datetime.now().strftime("%d %b %Y · %I:%M %p"))
    return hospital


@st.fragment(run_every=2)
def _render_hospital_feed(connected: bool, hospital: Optional[Mapping[str, Any]]) -> None:
    """Refresh and render a selected hospital's incoming emergency view every two seconds."""
    client = VitaviaApiClient()
    if connected:
        _refresh_live_mission(client)

    if st.session_state.hospital_feed_error:
        st.warning(st.session_state.hospital_feed_error)
    if not connected:
        st.error(f"FastAPI backend is not reachable at {client.base_url}")
        st.caption("Start the backend with: cd backend && uvicorn app.main:app --reload")
        return
    if hospital is None:
        st.info("Hospital-specific emergency information will appear when the hospital catalog is available.")
        return

    snapshot = st.session_state.current_snapshot or {}
    mission_detail = st.session_state.live_mission_detail or {}
    mission_summary = st.session_state.live_mission_summary or {}
    incoming_state = st.session_state.incoming_emergency or {}
    external_request_active = bool(incoming_state.get("has_active_request"))
    external_request = incoming_state.get("incoming_request")
    if not isinstance(external_request, Mapping):
        external_request = None
    selected_evaluation = _selected_hospital_evaluation(mission_detail)
    simulated_incoming = _is_incoming_for_hospital(selected_evaluation, hospital)
    is_incoming = bool(external_request) if external_request_active else simulated_incoming

    _render_incoming_emergency_request(
        snapshot,
        mission_summary,
        selected_evaluation,
        hospital,
        is_incoming,
        external_request=external_request,
        external_request_active=external_request_active,
    )
    _render_hospital_readiness(
        hospital,
        mission_detail,
        is_incoming,
        external_request=external_request,
        external_request_active=external_request_active,
    )
    if is_incoming:
        _render_patient_vitals(snapshot, mission_detail, external_request=external_request)
        _render_ai_clinical_assessment(mission_detail, external_request=external_request)
    else:
        st.caption(
            "Patient telemetry and clinical assessment are shown only to the backend-selected "
            "destination hospital."
        )
    _render_emergency_response(
        mission_summary,
        mission_detail,
        selected_evaluation,
        is_incoming,
        external_request=external_request,
        external_request_active=external_request_active,
    )
    _render_ambulance_tracking(
        snapshot,
        selected_evaluation,
        is_incoming,
        external_request=external_request,
        external_request_active=external_request_active,
    )
    _render_arrival(
        mission_summary,
        mission_detail,
        snapshot,
        selected_evaluation,
        is_incoming,
        external_request_active=external_request_active,
    )


def _render_incoming_emergency_request(
    snapshot: Mapping[str, Any],
    mission_summary: Mapping[str, Any],
    decision: Optional[Mapping[str, Any]],
    hospital: Mapping[str, Any],
    is_incoming: bool,
    *,
    external_request: Optional[Mapping[str, Any]],
    external_request_active: bool,
) -> None:
    """Present only a backend-selected request for the currently selected hospital."""
    st.divider()
    hospital_name = hospital.get("name", "this hospital")
    if external_request_active:
        if external_request:
            st.subheader("🚨 INCOMING EMERGENCY REQUEST")
            _render_communicated_incoming_request(external_request, hospital)
        else:
            selected_hospital_id = (st.session_state.incoming_emergency or {}).get(
                "selected_hospital_id", "another hospital"
            )
            st.caption(
                f"This ambulance request is assigned to **{selected_hospital_id}**, not "
                f"**{hospital_name}**."
            )
        return

    st.subheader("Incoming Emergency Request")
    selected_name = mission_summary.get("selected_hospital_name")
    if not is_incoming:
        if selected_name:
            st.info(
                f"🟢 No incoming emergency request for **{hospital_name}**. "
                f"The current backend-selected destination is **{selected_name}**."
            )
        else:
            st.info("🟢 No incoming emergency requests")
        return

    ambulance = snapshot.get("ambulance") or {}
    patient = snapshot.get("patient") or {}
    journey = st.session_state.journey_state or {}
    eta = _current_eta(decision, journey)
    with st.container(border=True):
        st.error("🚨 INCOMING EMERGENCY")
        identity, patient_details, route_details = st.columns(3)
        with identity:
            st.markdown("**Ambulance**")
            st.write(f"ID: {ambulance.get('ambulance_id', 'Not provided by backend')}")
            st.write(f"Status: {_current_ambulance_status(snapshot, journey, decision)}")
        with patient_details:
            st.markdown("**Patient (simulated)**")
            st.write(f"Patient ID: {patient.get('patient_id', 'Not provided by backend')}")
            st.write("Patient name: Not provided by backend")
            st.write(f"Age: {patient.get('age', 'Not provided by backend')}")
            st.write(f"Gender: {patient.get('gender', 'Not provided by backend')}")
            st.write(f"Chief complaint: {patient.get('emergency_type', 'Not provided by backend')}")
        with route_details:
            st.markdown("**Ambulance route**")
            st.write("Dispatch origin: Not provided by backend")
            st.write(f"ETA: {_format_eta(eta)}")
            st.write(f"Route distance: {_format_distance(decision.get('distance_km') if decision else None)}")
            st.write("Distance remaining: Not provided by backend")


def _render_communicated_incoming_request(
    request: Mapping[str, Any], hospital: Mapping[str, Any]
) -> None:
    """Render the received ambulance payload as a hospital-ready control-room alert."""
    triage_level = str(request.get("triage_level") or "—").upper()
    hospital_name = str(hospital.get("name") or "Selected hospital")
    hospital_id = str(hospital.get("hospital_id") or request.get("selected_hospital_id") or "—")

    with st.container(border=True):
        _render_incoming_urgency_banner(triage_level)
        st.success("🚑 Ambulance En Route")
        st.caption(f"Request intended for **{hospital_name}** · Hospital ID: **{hospital_id}**")

        patient_column, transport_column = st.columns([3, 2])
        with patient_column:
            with st.container(border=True):
                st.markdown("##### PATIENT")
                details = st.columns(2)
                details[0].markdown(
                    f"**Patient Name**  \n{request.get('patient_name', '—')}\n\n"
                    f"**Patient ID**  \n{request.get('patient_id', '—')}"
                )
                details[1].markdown(
                    f"**Age / Gender**  \n{request.get('age', '—')} / "
                    f"{request.get('gender', '—')}\n\n"
                    f"**Chief Complaint**  \n{request.get('chief_complaint', '—')}"
                )
        with transport_column:
            with st.container(border=True):
                st.markdown("##### EMERGENCY / TRANSPORT")
                st.metric("Ambulance ID", request.get("ambulance_id", "—"))
                st.metric("Triage / Urgency", triage_level)
                st.caption(f"Dispatch origin: {request.get('dispatch_origin', '—')}")
                eta_column, distance_column = st.columns(2)
                eta_column.metric("ETA", _format_eta(request.get("eta_minutes")))
                distance_column.metric(
                    "Distance Remaining", _format_distance(request.get("distance_km"))
                )

        with st.container(border=True):
            st.markdown("##### VITALS")
            vitals = st.columns(4)
            vitals[0].metric("SpO₂", _format_measurement(request.get("spo2"), "%"))
            vitals[1].metric(
                "Heart Rate", _format_measurement(request.get("heart_rate"), "BPM")
            )
            vitals[2].metric(
                "Blood Pressure",
                f"{request.get('systolic_bp', '—')} / "
                f"{request.get('diastolic_bp', '—')} mmHg",
            )
            vitals[3].metric(
                "Temperature", _format_measurement(request.get("temperature"), "°C")
            )
            st.caption(
                "Values received from the ambulance application. "
                "No clinical analysis is run by this view."
            )


def _render_incoming_urgency_banner(triage_level: str) -> None:
    """Highlight ambulance-supplied urgency without producing a frontend assessment."""
    if triage_level == "CRITICAL":
        st.error("🚨 CRITICAL-URGENCY INCOMING EMERGENCY")
    elif triage_level == "HIGH":
        st.warning("⚠ HIGH-URGENCY INCOMING EMERGENCY")
    elif triage_level == "MODERATE":
        st.info("🟡 MODERATE-URGENCY INCOMING EMERGENCY")
    else:
        st.info(f"Incoming emergency request · Triage level: {triage_level}")


def _render_patient_vitals(
    snapshot: Mapping[str, Any],
    mission_detail: Mapping[str, Any],
    *,
    external_request: Optional[Mapping[str, Any]],
) -> None:
    """Render current ambulance-provided values with existing backend urgency indicators."""
    st.subheader("Patient Vitals")
    st.caption("Current values supplied by the ambulance-side system.")
    if external_request:
        vitals = {
            "spo2": external_request.get("spo2"),
            "heart_rate": external_request.get("heart_rate"),
            "systolic_bp": external_request.get("systolic_bp"),
            "diastolic_bp": external_request.get("diastolic_bp"),
            "temperature": external_request.get("temperature"),
        }
        render_vitals_panel(vitals, triage_severity=external_request.get("triage_level"))
        return

    emergency = mission_detail.get("emergency") or {}
    render_vitals_panel(
        snapshot.get("vitals") or {},
        triage_severity=emergency.get("triage_severity"),
    )


def _render_ai_clinical_assessment(
    mission_detail: Mapping[str, Any], *, external_request: Optional[Mapping[str, Any]]
) -> None:
    """Display stored backend assessment without invoking Gemini or triage from this UI."""
    st.subheader("🤖 AI Clinical Assessment")
    st.caption(
        "AI-assisted clinical decision support. Final medical decisions remain with qualified "
        "medical staff."
    )
    if external_request:
        st.info(f"Received triage level: **{external_request.get('triage_level', '—')}**")
        st.caption(
            "The ambulance request did not include a clinical summary or AI source. "
            "This hospital dashboard does not run clinical analysis."
        )
        return

    emergency = mission_detail.get("emergency") or {}
    severity = emergency.get("triage_severity")
    required = mission_detail.get("required_infrastructure") or []
    explanation = mission_detail.get("triage_explanation")
    if not severity:
        st.info("No clinical assessment has been received from the backend for the current emergency.")
        return

    if severity in {"CRITICAL", "HIGH"}:
        st.warning(f"Urgency: **{severity}**")
    elif severity == "MODERATE":
        st.info(f"Urgency: **{severity}**")
    else:
        st.success(f"Urgency: **{severity}**")
    summary_column, source_column = st.columns([3, 1])
    summary_column.markdown(
        f"**Clinical summary:** {explanation or 'Not provided by backend'}"
    )
    source_column.metric("Assessment source", friendly_ai_source(emergency.get("triage_source")))
    st.markdown("**Required infrastructure:** " + format_required_resources(required))


def _render_hospital_readiness(
    hospital: Mapping[str, Any],
    mission_detail: Mapping[str, Any],
    is_incoming: bool,
    *,
    external_request: Optional[Mapping[str, Any]],
    external_request_active: bool,
) -> None:
    """Show only actual availability booleans for the selected simulated hospital."""
    st.subheader("Hospital Infrastructure")
    st.caption("Current simulated hospital availability supplied by FastAPI.")
    availability = hospital.get("availability") or {}
    resources = (
        ("Emergency Bed", "emergency_bed"),
        ("ICU", "icu"),
        ("Ventilator", "ventilator"),
        ("Emergency Team", "emergency_team"),
    )
    columns = st.columns(4)
    for column, (label, key) in zip(columns, resources):
        available = bool(availability.get(key))
        column.metric(label, "AVAILABLE" if available else "UNAVAILABLE")
        column.caption("🟢 Ready" if available else "🔴 Unavailable")

    if external_request_active:
        if external_request:
            st.success("✅ This hospital is the ambulance-selected destination for this request.")
        else:
            st.info("An active ambulance request is directed to another simulated hospital.")
        return

    evaluation = _evaluation_for_hospital(mission_detail, hospital.get("hospital_id"))
    if not evaluation:
        st.info("This hospital has not yet received a backend infrastructure evaluation.")
        return
    if is_incoming:
        st.success("✅ This hospital is the backend-selected destination for the current emergency.")
    elif evaluation.get("eligible"):
        st.info("This hospital is eligible, but another eligible hospital was selected by the backend.")
    else:
        missing = evaluation.get("missing_infrastructure") or []
        st.warning(
            "This hospital is ineligible for the current request: "
            + format_required_resources(missing)
        )


def _render_emergency_response(
    mission_summary: Mapping[str, Any],
    mission_detail: Mapping[str, Any],
    decision: Optional[Mapping[str, Any]],
    is_incoming: bool,
    *,
    external_request: Optional[Mapping[str, Any]],
    external_request_active: bool,
) -> None:
    """Expose current backend acknowledgement and honest limits for manual responses."""
    st.subheader("Emergency Response")
    if external_request_active:
        if not external_request:
            st.info("No hospital response is required for the request assigned to another hospital.")
            return
        st.info("Incoming ambulance request received. No acknowledgement was supplied in this payload.")
        actions = st.columns(2)
        actions[0].button("ACCEPT & PREPARE", disabled=True, width="stretch")
        actions[1].button("CANNOT ACCEPT", disabled=True, width="stretch")
        st.caption(
            "Manual hospital acceptance and rejection require future backend endpoints. "
            "This communication endpoint only receives and displays the ambulance request."
        )
        return

    if not is_incoming or decision is None:
        st.info("No hospital response is required in this control room for the current assignment.")
        return

    acknowledgement_status = decision.get("acknowledgement_status") or mission_summary.get(
        "acknowledgement_status"
    )
    if acknowledgement_status == "ACCEPTED":
        st.success("🟢 HOSPITAL ACCEPTED")
    else:
        st.info(f"Acknowledgement status: {acknowledgement_status or 'Not provided by backend'}")

    details = st.columns(4)
    details[0].metric("Acknowledgement", acknowledgement_status or "—")
    details[1].metric("Acknowledgement ID", "Not provided")
    details[2].metric("Assigned resource", "Not provided")
    details[3].metric("Standby status", "Not provided")
    st.markdown(
        "**Required infrastructure:** "
        + format_required_resources(mission_detail.get("required_infrastructure") or [])
    )

    actions = st.columns(2)
    actions[0].button("ACCEPT & PREPARE", disabled=True, width="stretch")
    actions[1].button("CANNOT ACCEPT", disabled=True, width="stretch")
    st.caption(
        "The existing backend creates acknowledgement automatically as part of its deterministic "
        "selection simulation. Manual acceptance and rejection endpoints are future scope."
    )


def _render_ambulance_tracking(
    snapshot: Mapping[str, Any],
    decision: Optional[Mapping[str, Any]],
    is_incoming: bool,
    *,
    external_request: Optional[Mapping[str, Any]],
    external_request_active: bool,
) -> None:
    """Show existing backend journey telemetry without inventing maps or road geometry."""
    st.subheader("🚑 Incoming Ambulance")
    if external_request_active:
        if not external_request:
            st.info("Tracking is shown only to the hospital selected by the ambulance request.")
            return
        metrics = st.columns(4)
        metrics[0].metric("Status", "Not provided")
        metrics[1].metric("ETA", _format_eta(external_request.get("eta_minutes")))
        metrics[2].metric("Distance", _format_distance(external_request.get("distance_km")))
        metrics[3].metric("Progress", "Not provided")
        st.caption(
            "The incoming request payload does not currently include ambulance GPS, "
            "journey status, or progress updates."
        )
        return

    if not is_incoming or decision is None:
        st.info("Tracking is shown when this hospital is the backend-selected destination.")
        return

    journey = st.session_state.journey_state or {}
    status = _current_ambulance_status(snapshot, journey, decision)
    progress = _display_progress(journey.get("progress_percent"))
    eta = _current_eta(decision, journey)
    metrics = st.columns(5)
    metrics[0].metric("Status", status.replace("_", " "))
    metrics[1].metric("ETA", _format_eta(eta))
    metrics[2].metric("Route distance", _format_distance(decision.get("distance_km")))
    metrics[3].metric("Progress", f"{progress:.0f}%")
    metrics[4].metric("Routing source", friendly_routing_source(decision.get("routing_source")))
    st.progress(progress / 100, text=f"Incoming journey progress: {progress:.0f}%")

    ambulance = snapshot.get("ambulance") or {}
    location = ambulance.get("location") or {}
    st.caption(
        "Current simulated GPS: "
        f"{_format_location(location)} · Distance remaining is not supplied by the current backend."
    )
    st.caption("Map rendering is not available from the current project data and dependencies.")


def _render_arrival(
    mission_summary: Mapping[str, Any],
    mission_detail: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    decision: Optional[Mapping[str, Any]],
    is_incoming: bool,
    *,
    external_request_active: bool,
) -> None:
    """Surface an arrival only when existing backend telemetry reports it for this destination."""
    if external_request_active:
        return

    journey = st.session_state.journey_state or {}
    arrived = is_incoming and (
        journey.get("status") == "ARRIVED"
        or (snapshot.get("ambulance") or {}).get("status") == "ARRIVED_AT_HOSPITAL"
    )
    if not arrived:
        return

    st.subheader("Arrival")
    st.success("🟢 PATIENT ARRIVED")
    patient = snapshot.get("patient") or {}
    ambulance = snapshot.get("ambulance") or {}
    details = st.columns(4)
    details[0].metric("Patient", patient.get("patient_id", "—"))
    details[1].metric("Ambulance", ambulance.get("ambulance_id", "—"))
    details[2].metric("Arrival time", _format_timestamp(mission_summary.get("completed_at")))
    details[3].metric(
        "Acknowledgement", decision.get("acknowledgement_status") if decision else "—"
    )
    st.markdown(
        "**Required infrastructure:** "
        + format_required_resources(mission_detail.get("required_infrastructure") or [])
    )
    st.caption("Assigned resource: Not provided by backend.")
    st.button("PATIENT RECEIVED", disabled=True, width="content")
    st.caption("Patient-received persistence is future backend integration; no endpoint exists today.")


def _render_history_section(client: VitaviaApiClient, connected: bool) -> None:
    """Retain existing read-only emergency history without affecting live operations."""
    st.divider()
    st.subheader("Emergency History")
    refresh_column, detail_column = st.columns([1, 3])
    if refresh_column.button("Refresh History", disabled=not connected, width="stretch"):
        _refresh_history(client)

    if not connected:
        detail_column.caption("History is unavailable while the backend is offline.")
        return
    if st.session_state.history_error:
        st.warning(st.session_state.history_error)

    history_items = st.session_state.history_items
    if not history_items:
        st.info("No emergency history is available yet.")
        return

    st.markdown("#### Recent Emergencies")
    render_history_list(history_items)
    selected_emergency_id = render_history_selector(
        history_items, st.session_state.selected_emergency_id
    )
    if selected_emergency_id is None:
        return
    if selected_emergency_id != st.session_state.selected_emergency_id:
        st.session_state.selected_emergency_id = selected_emergency_id
        _load_history_detail(client, selected_emergency_id)
    elif st.session_state.selected_emergency_detail is None:
        _load_history_detail(client, selected_emergency_id)

    detail = st.session_state.selected_emergency_detail
    if detail:
        render_history_detail(detail)


def _refresh_history(client: VitaviaApiClient) -> None:
    """Refresh read-only history only on page load or explicit operator request."""
    try:
        history_items = client.get_emergency_history()
    except ApiClientError:
        st.session_state.history_error = "Emergency history is temporarily unavailable."
        return

    st.session_state.history_items = history_items
    st.session_state.history_error = None
    emergency_ids = [
        item.get("emergency_id")
        for item in history_items
        if isinstance(item, Mapping) and item.get("emergency_id")
    ]
    if st.session_state.selected_emergency_id not in emergency_ids:
        st.session_state.selected_emergency_id = emergency_ids[0] if emergency_ids else None
        st.session_state.selected_emergency_detail = None
    if st.session_state.selected_emergency_id:
        _load_history_detail(client, st.session_state.selected_emergency_id)


def _load_history_detail(client: VitaviaApiClient, emergency_id: str) -> None:
    """Load an audit record without triggering AI, routing, selection, or journey updates."""
    try:
        st.session_state.selected_emergency_detail = client.get_emergency_detail(emergency_id)
    except ApiClientError:
        st.session_state.selected_emergency_detail = None
        st.session_state.history_error = "Emergency history is temporarily unavailable."
        return
    st.session_state.history_error = None


def _selected_hospital_evaluation(
    mission_detail: Mapping[str, Any],
) -> Optional[Mapping[str, Any]]:
    """Read, rather than recompute, the hospital selected in persisted backend decision data."""
    evaluations = mission_detail.get("hospital_evaluations") or []
    return next(
        (
            evaluation
            for evaluation in evaluations
            if isinstance(evaluation, Mapping) and evaluation.get("selected")
        ),
        None,
    )


def _evaluation_for_hospital(
    mission_detail: Mapping[str, Any], hospital_id: Any
) -> Optional[Mapping[str, Any]]:
    """Look up this hospital's existing backend evaluation without changing it."""
    return next(
        (
            evaluation
            for evaluation in mission_detail.get("hospital_evaluations") or []
            if isinstance(evaluation, Mapping) and evaluation.get("hospital_id") == hospital_id
        ),
        None,
    )


def _is_incoming_for_hospital(
    selected_evaluation: Optional[Mapping[str, Any]], hospital: Mapping[str, Any]
) -> bool:
    """Treat a request as incoming only when the backend selected this hospital exactly."""
    return bool(
        selected_evaluation
        and selected_evaluation.get("hospital_id") == hospital.get("hospital_id")
    )


def _current_eta(
    decision: Optional[Mapping[str, Any]], journey: Mapping[str, Any]
) -> Optional[float]:
    """Prefer backend journey ETA for the fixed selected destination when available."""
    if decision and journey.get("selected_hospital_id") == decision.get("hospital_id"):
        remaining = journey.get("remaining_eta_minutes")
        if isinstance(remaining, (int, float)):
            return float(remaining)
    if decision and isinstance(decision.get("eta_minutes"), (int, float)):
        return float(decision["eta_minutes"])
    return None


def _current_ambulance_status(
    snapshot: Mapping[str, Any],
    journey: Mapping[str, Any],
    decision: Optional[Mapping[str, Any]],
) -> str:
    """Use journey state only for its fixed selected destination; otherwise show raw telemetry."""
    if decision and journey.get("selected_hospital_id") == decision.get("hospital_id"):
        journey_status = journey.get("status")
        if journey_status and journey_status != "NOT_STARTED":
            return str(journey_status)
    return str((snapshot.get("ambulance") or {}).get("status", "Not provided by backend"))


def _hospital_selector_label(hospital_id: str, hospitals: list[Mapping[str, Any]]) -> str:
    """Keep selector options concise and identify each fictional hospital clearly."""
    hospital = next(
        (entry for entry in hospitals if entry.get("hospital_id") == hospital_id), {}
    )
    return f"{hospital.get('name', 'Unknown Hospital')} · {hospital_id}"


def _display_progress(value: Any) -> float:
    """Constrain a backend progress value only for safe Streamlit display."""
    if not isinstance(value, (int, float)):
        return 0.0
    return max(0.0, min(float(value), 100.0))


def _format_eta(value: Any) -> str:
    """Format an existing backend ETA without creating a new estimate."""
    return f"{value:.1f} min" if isinstance(value, (int, float)) else "Not provided"


def _format_distance(value: Any) -> str:
    """Format existing backend route distance without calculating road geometry."""
    return f"{value:.1f} km" if isinstance(value, (int, float)) else "Not provided"


def _format_measurement(value: Any, unit: str) -> str:
    """Format a value supplied by the ambulance without creating a new interpretation."""
    return f"{value} {unit}" if value is not None else "—"


def _format_location(location: Mapping[str, Any]) -> str:
    """Format existing simulated GPS coordinates without rendering a fabricated route map."""
    latitude, longitude = location.get("latitude"), location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return "Not provided"
    return f"{latitude:.6f}, {longitude:.6f}"


def _format_timestamp(value: Any) -> str:
    """Display stored backend timestamp without changing its timezone semantics."""
    return str(value) if value else "Not provided by backend"


if __name__ == "__main__":
    main()
