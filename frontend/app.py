"""
VitaVia - Emergency Response Command Dashboard
Interactive Streamlit application demonstrating operator patient intake,
AI-assisted clinical triage, deterministic hospital infrastructure verification,
traffic-aware fastest hospital routing, and live IoT ambulance simulation.
"""

import streamlit as st
import requests
import json
import os
import time
import folium
from streamlit_folium import st_folium
from datetime import datetime

from ambulance.simulator import PRESET_SCENARIOS, AmbulanceSimulator, DEFAULT_START_LOCATION
from backend.models import GeoPoint, HospitalAcknowledgment, PatientInfo, PatientVitals

# Page configuration
st.set_page_config(
    page_title="VitaVia - Connected Ambulance & Traffic-Aware Routing",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech Emergency Command Center CSS
st.markdown("""
<style>
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    .main-header {
        font-size: 2.3rem;
        font-weight: 850;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #ef4444, #f97316, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
        padding-top: 0px;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 0.95rem;
        font-weight: 500;
        margin-top: 0px;
        margin-bottom: 16px;
    }
    
    /* Intake Form Containers */
    .intake-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    }
    .intake-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 8px;
    }
    
    /* Telemetry Cards */
    .telemetry-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    .telemetry-label {
        font-size: 0.75rem;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .telemetry-value {
        font-size: 1.45rem;
        font-weight: 800;
        color: #f8fafc;
        line-height: 1.2;
    }
    .telemetry-sub {
        font-size: 0.78rem;
        font-weight: 600;
        margin-top: 3px;
    }
    .sub-critical { color: #f87171; }
    .sub-warning { color: #fbbf24; }
    .sub-normal { color: #4ade80; }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 750;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-critical { background-color: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; }
    .badge-high { background-color: #7c2d12; color: #fed7aa; border: 1px solid #f97316; }
    .badge-moderate { background-color: #713f12; color: #fef08a; border: 1px solid #eab308; }
    .badge-low { background-color: #14532d; color: #bbf7d0; border: 1px solid #22c55e; }
    
    .badge-status-dispatched { background-color: #854d0e; color: #fef08a; border: 1px solid #eab308; }
    .badge-status-enroute { background-color: #1e3a8a; color: #bfdbfe; border: 1px solid #3b82f6; }
    .badge-status-arrived { background-color: #064e3b; color: #a7f3d0; border: 1px solid #10b981; }
    
    .badge-traffic-heavy { background-color: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; }
    .badge-traffic-mod { background-color: #713f12; color: #fef08a; border: 1px solid #eab308; }
    .badge-traffic-low { background-color: #14532d; color: #86efac; border: 1px solid #22c55e; }
    
    .tag-pill {
        display: inline-block;
        background: #1e293b;
        color: #e2e8f0;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 3px 9px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 4px;
        margin-bottom: 4px;
    }
    
    .ack-box {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%);
        border: 1.5px solid #059669;
        border-radius: 10px;
        padding: 16px 18px;
        color: #ecfdf5;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = os.getenv("VITAVIA_API_URL", "http://127.0.0.1:8000")
HOSPITAL_BACKEND_URL = os.getenv("VITAVIA_HOSPITAL_API_URL", "http://127.0.0.1:8001")
HOSPITAL_ID_MAP = {"HOSP-A": "HOSP001", "HOSP-B": "HOSP002", "HOSP-C": "HOSP003", "HOSP-D": "HOSP004", "HOSP-E": "HOSP005"}

# State initialization
if "simulator" not in st.session_state:
    st.session_state.simulator = AmbulanceSimulator()

if "dispatch_data" not in st.session_state:
    st.session_state.dispatch_data = None

if "auto_sim" not in st.session_state:
    st.session_state.auto_sim = False

# Default intake form state initialization
if "form_ambulance_id" not in st.session_state:
    st.session_state.form_ambulance_id = "AMB-07"
if "form_patient_id" not in st.session_state:
    st.session_state.form_patient_id = "PAT-9901"
if "form_name" not in st.session_state:
    st.session_state.form_name = "Rajesh Kumar"
if "form_age" not in st.session_state:
    st.session_state.form_age = 58
if "form_gender" not in st.session_state:
    st.session_state.form_gender = "Male"
if "form_complaint" not in st.session_state:
    st.session_state.form_complaint = "Severe retrosternal crushing chest pain radiating to left arm, acute dyspnea, and diaphoresis."
if "form_spo2" not in st.session_state:
    st.session_state.form_spo2 = 87.5
if "form_hr" not in st.session_state:
    st.session_state.form_hr = 128
if "form_sbp" not in st.session_state:
    st.session_state.form_sbp = 92
if "form_dbp" not in st.session_state:
    st.session_state.form_dbp = 58
if "form_temp" not in st.session_state:
    st.session_state.form_temp = 38.4
if "form_location" not in st.session_state:
    st.session_state.form_location = "Trinity Junction Central (Dispatch Origin)"
if "form_notes" not in st.session_state:
    st.session_state.form_notes = "Onset 35 minutes prior. High-flow oxygen (15L/min NRB mask) initiated on scene by paramedic."

sim: AmbulanceSimulator = st.session_state.simulator

# ==========================================
# SIDEBAR: Operational Controls & Grid
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/ambulance.png", width=54)
    st.markdown("### 🚑 Mission Control Center")
    
    # Check backend connectivity
    backend_status_placeholder = st.empty()
    backend_online = False
    try:
        r = requests.get(f"{BACKEND_URL}/", timeout=1.5)
        if r.status_code == 200:
            backend_online = True
            backend_status_placeholder.success("🟢 Backend Active (Port 8000)")
        else:
            backend_status_placeholder.warning("🟠 Backend Error")
    except Exception:
        backend_status_placeholder.error("🔴 Backend Offline (Run uvicorn backend.main:app)")

    st.markdown("---")
    st.markdown("#### 🏥 Live Hospital Resource Grid")
    st.caption("Toggle resource availability to demonstrate real-time deterministic eligibility checks:")
    
    if backend_online:
        try:
            hosp_list = requests.get(f"{BACKEND_URL}/api/hospitals").json()
            for h in hosp_list:
                with st.expander(f"🏥 {h['name'][:20]}..."):
                    icu_state = st.checkbox(
                        "ICU Bed Available",
                        value=h["infrastructure"]["icu_available"],
                        key=f"icu_{h['id']}"
                    )
                    vent_state = st.checkbox(
                        "Ventilator Available",
                        value=h["infrastructure"]["ventilator_available"],
                        key=f"vent_{h['id']}"
                    )
                    if (icu_state != h["infrastructure"]["icu_available"] or 
                        vent_state != h["infrastructure"]["ventilator_available"]):
                        requests.put(
                            f"{BACKEND_URL}/api/hospitals/{h['id']}",
                            json={"icu_available": icu_state, "ventilator_available": vent_state}
                        )
                        st.toast(f"Updated {h['name']} capacity!")
        except Exception as e:
            st.error(f"Could not load hospitals: {e}")

    if st.button("🔄 Reset All Hospital Capacities", use_container_width=True):
        if backend_online:
            requests.post(f"{BACKEND_URL}/api/hospitals/reset")
            st.success("All hospitals reset to baseline configuration!")

    st.markdown("---")
    if st.button("⏮ Reset Dashboard / New Mission", use_container_width=True):
        st.session_state.dispatch_data = None
        st.session_state.auto_sim = False
        sim.reset()
        st.rerun()

# ==========================================
# MAIN DASHBOARD AREA
# ==========================================
st.markdown('<div class="main-header">VITAVIA</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">AI-Assisted Intelligent Connected Ambulance & Traffic-Aware Hospital Routing System</div>',
    unsafe_allow_html=True
)

# If no active dispatch, show the Operator Intake & Activation Form
if not st.session_state.dispatch_data:
    st.markdown("### 🚑 Ambulance Activation & Patient Intake")
    st.caption("Operator/Paramedic: Enter patient details, emergency complaints, and initial IoT telemetry to activate AI triage & fastest hospital routing.")

    # Optional Demo Quick-Fill Bar
    with st.expander("⚡ Optional Demo Preset Quick-Fill (Click to auto-populate fields for fast demonstration)", expanded=False):
        p_col1, p_col2 = st.columns([3, 1])
        with p_col1:
            chosen_preset = st.selectbox(
                "Select clinical scenario preset:",
                list(PRESET_SCENARIOS.keys()),
                label_visibility="collapsed"
            )
        with p_col2:
            if st.button("⚡ Autofill Form", use_container_width=True):
                sc = PRESET_SCENARIOS[chosen_preset]
                p = sc["patient"]
                v = sc["vitals"]
                st.session_state.form_patient_id = p.patient_id
                st.session_state.form_name = p.name
                st.session_state.form_age = p.age
                st.session_state.form_gender = p.gender
                st.session_state.form_complaint = p.chief_complaint
                st.session_state.form_spo2 = float(v.spo2)
                st.session_state.form_hr = int(v.heart_rate)
                st.session_state.form_sbp = int(v.systolic_bp)
                st.session_state.form_dbp = int(v.diastolic_bp)
                st.session_state.form_temp = float(v.temperature)
                st.session_state.form_notes = f"Preset scenario: {sc['description']}"
                st.toast(f"Form populated with '{chosen_preset}'!")
                st.rerun()

    # Operator Intake Form Grid
    intake_col1, intake_col2, intake_col3 = st.columns([1.2, 1.2, 1.1])

    with intake_col1:
        st.markdown(
            '<div class="intake-card">'
            '<div class="intake-title">👤 Patient Demographics & ID</div>',
            unsafe_allow_html=True
        )
        amb_id_input = st.text_input("Ambulance Unit ID *", value=st.session_state.form_ambulance_id, key="input_amb_id")
        pat_id_input = st.text_input("Patient ID *", value=st.session_state.form_patient_id, key="input_pat_id")
        pat_name_input = st.text_input("Patient Full Name *", value=st.session_state.form_name, key="input_name")
        
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            pat_age_input = st.number_input("Age (Years) *", min_value=1, max_value=120, value=st.session_state.form_age, step=1, key="input_age")
        with sub_col2:
            gender_options = ["Male", "Female", "Other"]
            default_gender_idx = gender_options.index(st.session_state.form_gender) if st.session_state.form_gender in gender_options else 0
            pat_gender_input = st.selectbox("Gender *", gender_options, index=default_gender_idx, key="input_gender")

        pat_complaint_input = st.text_area(
            "Chief Emergency Complaint *",
            value=st.session_state.form_complaint,
            height=95,
            key="input_complaint",
            placeholder="e.g. Acute severe dyspnea, crushing chest pain, diaphoresis..."
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with intake_col2:
        st.markdown(
            '<div class="intake-card">'
            '<div class="intake-title">🩺 Initial Vitals & Sensor Readings</div>',
            unsafe_allow_html=True
        )
        v_sub1, v_sub2 = st.columns(2)
        with v_sub1:
            spo2_input = st.number_input("Oxygen SpO2 (%) *", min_value=50.0, max_value=100.0, value=st.session_state.form_spo2, step=0.5, format="%.1f", key="input_spo2")
        with v_sub2:
            hr_input = st.number_input("Heart Rate (BPM) *", min_value=30, max_value=250, value=st.session_state.form_hr, step=1, key="input_hr")

        v_sub3, v_sub4 = st.columns(2)
        with v_sub3:
            sbp_input = st.number_input("Systolic BP (mmHg) *", min_value=40, max_value=260, value=st.session_state.form_sbp, step=2, key="input_sbp")
        with v_sub4:
            dbp_input = st.number_input("Diastolic BP (mmHg) *", min_value=20, max_value=160, value=st.session_state.form_dbp, step=2, key="input_dbp")

        temp_input = st.number_input("Core Temperature (°C) *", min_value=32.0, max_value=43.0, value=st.session_state.form_temp, step=0.1, format="%.1f", key="input_temp")

        # Dynamic Vitals Summary Pill
        v_hypoxia = "CRITICAL HYPOXIA" if spo2_input < 90 else ("Mild Hypoxia" if spo2_input < 95 else "SpO2 Normal")
        v_bp = "Hypotension" if sbp_input < 90 else ("Hypertensive" if sbp_input > 140 else "BP Optimal")
        v_pulse = "Tachycardia" if hr_input > 100 else ("Bradycardia" if hr_input < 60 else "HR Normal")
        st.markdown(
            f'<div style="background: #1e293b; border-radius: 8px; padding: 10px; border: 1px solid #334155; margin-top: 10px;">'
            f'<span style="font-size: 0.78rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Sensor Triage Preview:</span><br/>'
            f'<span style="color: {"#f87171" if spo2_input < 90 else "#fbbf24" if spo2_input < 95 else "#4ade80"}; font-weight: 700; font-size: 0.85rem;">● {v_hypoxia}</span> &nbsp;|&nbsp; '
            f'<span style="color: {"#f87171" if hr_input > 120 or hr_input < 50 else "#fbbf24" if hr_input > 100 else "#4ade80"}; font-weight: 700; font-size: 0.85rem;">● {v_pulse}</span> &nbsp;|&nbsp; '
            f'<span style="color: {"#f87171" if sbp_input < 90 else "#fbbf24" if sbp_input > 140 else "#4ade80"}; font-weight: 700; font-size: 0.85rem;">● {v_bp}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with intake_col3:
        st.markdown(
            '<div class="intake-card">'
            '<div class="intake-title">📍 Dispatch Origin & Notes</div>',
            unsafe_allow_html=True
        )
        location_input = st.text_input("Dispatch / Origin Address *", value=st.session_state.form_location, key="input_location")
        notes_input = st.text_area("Emergency Notes (Optional)", value=st.session_state.form_notes, height=135, key="input_notes", placeholder="Paramedic observations, on-scene treatments, allergies...")
        
        st.markdown(
            '<div style="background: #1e293b; border-radius: 8px; padding: 10px; border: 1px solid #334155; margin-top: 12px;">'
            '<span style="font-size: 0.78rem; font-weight: 700; color: #94a3b8;">SYSTEM READINESS:</span><br/>'
            '<span style="color: #4ade80; font-weight: 700; font-size: 0.85rem;">● 5 Candidate Hospitals Active</span><br/>'
            '<span style="color: #38bdf8; font-weight: 700; font-size: 0.85rem;">● Gemini AI Clinical Engine Ready</span>'
            '</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Prominent Activation Button
    st.markdown('<div style="height: 6px;"></div>', unsafe_allow_html=True)
    activate_mission = st.button("🚑 ACTIVATE EMERGENCY MISSION", type="primary", use_container_width=True)

    if activate_mission:
        # 1. Validation
        validation_errors = []
        if not amb_id_input.strip():
            validation_errors.append("Ambulance ID is required.")
        if not pat_id_input.strip():
            validation_errors.append("Patient ID is required.")
        if not pat_name_input.strip():
            validation_errors.append("Patient Name is required.")
        if not pat_complaint_input.strip():
            validation_errors.append("Chief Complaint description is required.")
        if not location_input.strip():
            validation_errors.append("Dispatch Location is required.")

        if validation_errors:
            for err in validation_errors:
                st.error(f"⚠️ Validation Error: {err}")
        else:
            with st.spinner("AI evaluating patient vitals & computing traffic-aware travel times..."):
                try:
                    # Construct models
                    p_info = PatientInfo(
                        patient_id=pat_id_input.strip(),
                        name=pat_name_input.strip(),
                        age=int(pat_age_input),
                        gender=pat_gender_input,
                        chief_complaint=pat_complaint_input.strip()
                    )
                    p_vitals = PatientVitals(
                        spo2=float(spo2_input),
                        heart_rate=int(hr_input),
                        systolic_bp=int(sbp_input),
                        diastolic_bp=int(dbp_input),
                        temperature=float(temp_input)
                    )
                    p_location = GeoPoint(
                        latitude=DEFAULT_START_LOCATION.latitude,
                        longitude=DEFAULT_START_LOCATION.longitude,
                        address=location_input.strip()
                    )

                    payload = {
                        "ambulance_id": amb_id_input.strip(),
                        "patient_info": p_info.model_dump(),
                        "vitals": p_vitals.model_dump(),
                        "location": p_location.model_dump()
                    }

                    res = requests.post(f"{BACKEND_URL}/api/dispatch", json=payload, timeout=8)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.dispatch_data = data

                        # Update simulator with the entered data and destination
                        sim.ambulance_id = amb_id_input.strip()
                        sim.patient_info = p_info
                        sim.current_vitals = p_vitals
                        sim.start_location = p_location
                        sim.current_location = p_location.model_copy(deep=True)

                        selected = data["selection"]["selected_hospital"]
                        route = data["selection"]["selected_route"]
                        ack = data["acknowledgment"]

                        # Send the complete dispatch packet to the selected hospital control room.
                        hospital_request = {
                            "ambulance_id": sim.ambulance_id,
                            "patient_id": p_info.patient_id,
                            "patient_name": p_info.name,
                            "age": p_info.age,
                            "gender": p_info.gender,
                            "chief_complaint": p_info.chief_complaint,
                            "spo2": p_vitals.spo2,
                            "heart_rate": p_vitals.heart_rate,
                            "systolic_bp": p_vitals.systolic_bp,
                            "diastolic_bp": p_vitals.diastolic_bp,
                            "temperature": p_vitals.temperature,
                            "dispatch_origin": p_location.address or "Ambulance dispatch origin",
                            "ambulance_latitude": p_location.latitude,
                            "ambulance_longitude": p_location.longitude,
                            "selected_hospital_id": HOSPITAL_ID_MAP.get(selected["id"], selected["id"]),
                            "selected_hospital_name": selected["name"],
                            "eta_minutes": route["eta_minutes"],
                            "distance_km": route["distance_km"],
                            "triage_level": data["selection"]["gemini_analysis"]["urgency"],
                            "triage_summary": data["selection"]["gemini_analysis"]["summary"],
                            "required_infrastructure": data["selection"]["gemini_analysis"].get("required_infrastructure", []),
                            "priority_code": {"CRITICAL": "P1", "HIGH": "P2", "MODERATE": "P3", "LOW": "P4"}.get(
                                data["selection"]["gemini_analysis"]["urgency"], "P3"
                            ),
                            "acknowledgment_id": ack["acknowledgment_id"],
                            "acknowledgment_status": "ACCEPTED" if ack["acknowledged"] else "PENDING",
                            "assigned_bay": ack["assigned_bay"],
                            "team_ready": ack["team_ready"],
                        }
                        try:
                            hospital_res = requests.post(
                                f"{HOSPITAL_BACKEND_URL}/emergency/incoming",
                                json=hospital_request,
                                timeout=3,
                            )
                            if hospital_res.status_code != 200:
                                st.warning(
                                    f"Ambulance dispatch succeeded, but the hospital notification was not accepted "
                                    f"({hospital_res.status_code}). Start the hospital backend on port 8001."
                                )
                        except requests.RequestException:
                            st.warning(
                                "Ambulance dispatch succeeded, but the hospital control room could not be reached. "
                                "Start the hospital backend on port 8001 to receive the emergency alert."
                            )

                        sim.set_destination(
                            hospital_id=selected["id"],
                            hospital_name=selected["name"],
                            destination_location=GeoPoint(
                                latitude=selected["location"]["latitude"],
                                longitude=selected["location"]["longitude"],
                                address=selected["location"].get("address")
                            ),
                            eta_minutes=route["eta_minutes"],
                            acknowledgment=HospitalAcknowledgment(**ack)
                        )
                        st.toast(f"Mission activated! Fastest hospital {selected['name']} locked & acknowledged.", icon="🚑")
                        st.rerun()
                    else:
                        st.error(f"API Error ({res.status_code}): {res.text}")
                except Exception as exc:
                    st.error(f"Failed to connect to backend: {exc}")

# ==========================================
# POST-ACTIVATION: LIVE ACTIVE MISSION VIEW
# ==========================================
else:
    data = st.session_state.dispatch_data
    selection = data["selection"]
    gemini = selection["gemini_analysis"]
    evaluations = selection["all_evaluations"]
    selected_hosp = selection["selected_hospital"]
    selected_route = selection["selected_route"]
    ack = data["acknowledgment"]

    # Active Mission Top Bar
    bar_col1, bar_col2, bar_col3, bar_col4 = st.columns([1.4, 2.0, 1.8, 1.8])

    with bar_col1:
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Active Ambulance</div>'
            f'<div class="telemetry-value" style="color: #38bdf8;">{sim.ambulance_id}</div>'
            f'<div class="telemetry-sub sub-normal">● IoT Sensor Connected</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with bar_col2:
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Patient Profile</div>'
            f'<div class="telemetry-value" style="font-size: 1.15rem;">{sim.patient_info.name} ({sim.patient_info.age}y)</div>'
            f'<div class="telemetry-sub" style="color: #cbd5e1;">ID: {sim.patient_info.patient_id} | {sim.patient_info.gender}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with bar_col3:
        status_class = "sub-normal" if sim.status == "ARRIVED" else "sub-warning"
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Mission Telemetry State</div>'
            f'<div class="telemetry-value" style="font-size: 1.15rem;">{sim.status}</div>'
            f'<div class="telemetry-sub {status_class}">Progress: {int(sim.progress_ratio * 100)}% to Goal</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with bar_col4:
        st.markdown('<div style="height: 4px;"></div>', unsafe_allow_html=True)
        if st.button("✏️ Edit Intake / New Mission", use_container_width=True):
            st.session_state.dispatch_data = None
            st.session_state.auto_sim = False
            sim.reset()
            st.rerun()

    # ----------------------------------------------------
    # LIVE PATIENT TELEMETRY & IOT STREAM CARDS
    # ----------------------------------------------------
    st.markdown("#### 📡 Real-Time Patient IoT Sensor Readings")

    v_col1, v_col2, v_col3, v_col4, v_col5 = st.columns(5)

    with v_col1:
        spo2_val = sim.current_vitals.spo2
        spo2_status = "CRITICAL HYPOXIA" if spo2_val < 90 else ("Mild Hypoxia" if spo2_val < 95 else "Optimal")
        spo2_class = "sub-critical" if spo2_val < 90 else ("sub-warning" if spo2_val < 95 else "sub-normal")
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Oxygen Saturation (SpO2)</div>'
            f'<div class="telemetry-value">{spo2_val:.1f}%</div>'
            f'<div class="telemetry-sub {spo2_class}">● {spo2_status}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with v_col2:
        hr_val = sim.current_vitals.heart_rate
        hr_status = "Tachycardia" if hr_val > 100 else ("Bradycardia" if hr_val < 60 else "Normal Sinus")
        hr_class = "sub-critical" if hr_val > 120 else ("sub-warning" if hr_val > 100 else "sub-normal")
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Heart Rate (Pulse)</div>'
            f'<div class="telemetry-value">{hr_val} <span style="font-size: 0.85rem; font-weight: 500;">BPM</span></div>'
            f'<div class="telemetry-sub {hr_class}">● {hr_status}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with v_col3:
        sbp_val = sim.current_vitals.systolic_bp
        dbp_val = sim.current_vitals.diastolic_bp
        bp_status = "Hypotension / Shock" if sbp_val < 90 else ("Hypertensive" if sbp_val > 140 else "Normotensive")
        bp_class = "sub-critical" if sbp_val < 90 else ("sub-warning" if sbp_val > 140 else "sub-normal")
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Blood Pressure (NIBP)</div>'
            f'<div class="telemetry-value">{sbp_val}/{dbp_val} <span style="font-size: 0.8rem; font-weight: 500;">mmHg</span></div>'
            f'<div class="telemetry-sub {bp_class}">● {bp_status}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with v_col4:
        temp_val = sim.current_vitals.temperature
        temp_status = "High Pyrexia / Fever" if temp_val >= 38.5 else ("Elevated Temp" if temp_val >= 37.8 else "Normothermia")
        temp_class = "sub-critical" if temp_val >= 38.5 else ("sub-warning" if temp_val >= 37.8 else "sub-normal")
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Core Temperature</div>'
            f'<div class="telemetry-value">{temp_val:.1f} <span style="font-size: 0.85rem; font-weight: 500;">°C</span></div>'
            f'<div class="telemetry-sub {temp_class}">● {temp_status}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with v_col5:
        st.markdown(
            f'<div class="telemetry-card">'
            f'<div class="telemetry-label">Chief Complaint</div>'
            f'<div class="telemetry-value" style="font-size: 0.95rem; font-weight: 700; height: 32px; overflow: hidden;">{sim.patient_info.chief_complaint[:32]}...</div>'
            f'<div class="telemetry-sub" style="color: #94a3b8;">Recorded: {sim.current_vitals.recorded_at[11:19]} UTC</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ----------------------------------------------------
    # LIVE AMBULANCE TRANSIT SIMULATION CONTROL PANEL
    # ----------------------------------------------------
    st.markdown("---")
    st.markdown("#### 🛰️ Live Ambulance Transit & Movement Simulator")
    
    status_badge_class = "badge-status-arrived" if sim.status == "ARRIVED" else ("badge-status-enroute" if sim.status == "EN_ROUTE" else "badge-status-dispatched")
    
    p_col1, p_col2, p_col3, p_col4 = st.columns([1.4, 2.6, 1.6, 1.4])
    with p_col1:
        st.markdown(f'<div style="margin-top: 6px;"><strong>Status:</strong> <span class="badge {status_badge_class}">{sim.status}</span></div>', unsafe_allow_html=True)
    with p_col2:
        st.progress(sim.progress_ratio, text=f"Route Progress: {int(sim.progress_ratio * 100)}% ({sim.current_location.address})")
    with p_col3:
        st.markdown(f'<div style="background: #1e293b; border-radius: 8px; padding: 6px 12px; border: 1px solid #334155; text-align: center;"><span style="font-size: 0.78rem; color: #94a3b8; font-weight: 700;">REMAINING ETA:</span> <strong style="color: #38bdf8; font-size: 1.15rem;">{sim.current_eta_minutes} min</strong></div>', unsafe_allow_html=True)
    with p_col4:
        st.markdown(f'<div style="margin-top: 6px; font-size: 0.8rem; color: #94a3b8;">🕒 <code>{sim.current_vitals.recorded_at[11:19]} UTC</code></div>', unsafe_allow_html=True)

    # Simulation Action Buttons
    sim_b1, sim_b2, sim_b3, sim_b4 = st.columns([1.5, 1.5, 1.5, 1.5])
    
    with sim_b1:
        if st.session_state.auto_sim:
            if st.button("⏹ Stop Live Stream", use_container_width=True, type="secondary"):
                st.session_state.auto_sim = False
                st.rerun()
        else:
            if st.button("▶ Start Live Simulation Stream", use_container_width=True, type="primary"):
                st.session_state.auto_sim = True
                st.rerun()

    with sim_b2:
        if st.button("⏭ Step Movement (+10%)", use_container_width=True):
            sim.step_simulation(step_fraction=0.10, backend_url=BACKEND_URL)
            st.rerun()

    with sim_b3:
        if st.button("🔄 Fluctuate Vitals Only", use_container_width=True):
            sim.generate_next_vitals()
            sim.send_telemetry_to_backend(backend_url=BACKEND_URL)
            st.rerun()

    with sim_b4:
        if st.button("⏮ Reset Mission", use_container_width=True):
            sim.reset()
            st.session_state.auto_sim = False
            sim.send_telemetry_to_backend(backend_url=BACKEND_URL)
            st.rerun()

    # ----------------------------------------------------
    # AI CLINICAL DECISION & FASTEST ROUTING DISPLAY
    # ----------------------------------------------------
    st.markdown("---")
    
    # 1. Gemini Clinical Assessment Banner (Prominent Headline Feature)
    urgency_class = gemini['urgency'].lower()
    border_left_color = '#ef4444' if urgency_class == 'critical' else ('#f97316' if urgency_class == 'high' else '#eab308')
    infra_tags = ''.join([f'<span class="tag-pill">🏥 {infra}</span>' for infra in gemini['required_infrastructure']])
    
    gemini_banner_html = (
        f'<div style="background: #0f172a; border-radius: 10px; border-left: 6px solid {border_left_color}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; padding: 16px 20px; margin-bottom: 22px;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
        f'<div style="font-size: 1.15rem; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;">🧠 Gemini Clinical Decision-Support Analysis</div>'
        f'<span class="badge badge-{urgency_class}">URGENCY: {gemini["urgency"]}</span>'
        f'</div>'
        f'<div style="font-size: 1.05rem; color: #e2e8f0; font-weight: 500; margin-bottom: 10px; line-height: 1.4;">{gemini["summary"]}</div>'
        f'<div style="border-top: 1px solid #1e293b; padding-top: 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">'
        f'<div><span style="font-size: 0.8rem; font-weight: 700; color: #94a3b8; margin-right: 8px; text-transform: uppercase;">Mandatory Capabilities:</span>{infra_tags}</div>'
        f'<span style="font-size: 0.78rem; color: #64748b; font-style: italic;">[Decision Engine: {gemini["source"]}]</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(gemini_banner_html, unsafe_allow_html=True)

    # 2. Multi-Hospital Suitability & Traffic Matrix
    st.markdown("#### 🏥 Multi-Hospital Suitability & Traffic Matrix")
    st.caption("The backend checks mandatory infrastructure eligibility first, then optimizes for lowest Estimated Travel Time (ETA):")

    cols_matrix = st.columns(len(evaluations))
    for idx, ev in enumerate(evaluations):
        with cols_matrix[idx]:
            is_winner = (selected_hosp and ev["hospital_id"] == selected_hosp["id"])
            border_style = "3px solid #22c55e" if is_winner else ("1.5px solid #3b82f6" if ev["is_infrastructure_eligible"] else "1.5px solid #64748b")
            card_bg = "#14291e" if is_winner else "#1e293b"
            
            traffic_badge = "badge-traffic-heavy" if ev["traffic_condition"] == "HEAVY" else ("badge-traffic-mod" if ev["traffic_condition"] == "MODERATE" else "badge-traffic-low")
            
            infra_match_html = (
                '<span style="color: #4ade80; font-weight: 700; font-size: 0.82rem;">✅ Infrastructure Match</span>'
                if ev['is_infrastructure_eligible']
                else f'<span style="color: #f87171; font-weight: 700; font-size: 0.82rem;">❌ Missing: {", ".join(ev["missing_infrastructure"])}</span>'
            )
            
            winner_badge_html = (
                '<div style="background: #16a34a; color: white; padding: 4px 8px; border-radius: 6px; font-weight: 800; font-size: 0.82rem; margin-top: 8px;">🏆 FASTEST SUITABLE</div>'
                if is_winner
                else (
                    '<div style="background: #1e3a8a; color: #bfdbfe; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.78rem; margin-top: 8px;">Feasible (Slower)</div>'
                    if ev['is_infrastructure_eligible']
                    else '<div style="background: #3f1d1d; color: #fca5a5; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 0.78rem; margin-top: 8px;">Lacks Capacity</div>'
                )
            )

            card_html = (
                f'<div style="background: {card_bg}; border-radius: 10px; padding: 14px; border: {border_style}; min-height: 290px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">'
                f'<div>'
                f'<div style="font-weight: 800; font-size: 0.98rem; color: #f8fafc; margin-bottom: 2px;">{ev["hospital_name"]}</div>'
                f'<div style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 8px;">ID: {ev["hospital_id"]}</div>'
                f'<div style="margin-bottom: 8px;"><span class="badge {traffic_badge}">Traffic: {ev["traffic_condition"]}</span></div>'
                f'<div style="font-size: 1.45rem; font-weight: 850; color: #38bdf8; margin: 4px 0;">⏱️ {ev["eta_minutes"]} min</div>'
                f'<div style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 8px;">📍 Distance: <strong>{ev["distance_km"]} km</strong></div>'
                f'</div>'
                f'<div>'
                f'<div style="border-top: 1px solid #334155; padding-top: 8px; margin-top: 4px;">{infra_match_html}</div>'
                f'<div style="text-align: center;">{winner_badge_html}</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

    # 3. Selected Hospital Details & Hospital Acknowledgment Box
    st.markdown("---")
    res_col1, res_col2 = st.columns([1.15, 1.0])

    with res_col1:
        st.markdown("#### 🎯 Optimal Routing Verdict")
        st.info(f"💡 **Decision Engine Rationale:** {selection['decision_summary']}")
        
        team_ready_text = "Ready on Standby ✅" if ack["team_ready"] else "Alerted"
        ack_box_html = (
            f'<div class="ack-box">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">'
            f'<div style="font-weight: 800; font-size: 1.05rem; color: #6ee7b7;">📋 Hospital Dispatch Handshake Acknowledgment</div>'
            f'<span style="background: #047857; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700;">{ack["acknowledgment_id"]}</span>'
            f'</div>'
            f'<div style="font-size: 0.92rem; margin-bottom: 4px;"><strong>Assigned Facility:</strong> {ack["hospital_name"]}</div>'
            f'<div style="font-size: 0.92rem; margin-bottom: 4px;"><strong>Reserved Trauma Bay:</strong> <span style="background: #047857; padding: 2px 8px; border-radius: 4px; font-weight: 700;">{ack["assigned_bay"]}</span></div>'
            f'<div style="font-size: 0.92rem; margin-bottom: 6px;"><strong>Clinical Emergency Team:</strong> {team_ready_text}</div>'
            f'<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #047857; font-style: italic; color: #a7f3d0; font-size: 0.88rem;">"{ack["message"]}"</div>'
            f'</div>'
        )
        st.markdown(ack_box_html, unsafe_allow_html=True)

    with res_col2:
        st.markdown("#### 🗺️ Live Emergency Routing Grid Map")
        amb_lat = sim.current_location.latitude
        amb_lon = sim.current_location.longitude
        
        m = folium.Map(location=[amb_lat, amb_lon], zoom_start=12, tiles="cartodbdark_matter")
        
        # Ambulance Marker
        folium.Marker(
            [amb_lat, amb_lon],
            popup=f"Ambulance {sim.ambulance_id} | Status: {sim.status} | ETA: {sim.current_eta_minutes}m",
            tooltip=f"🚑 Ambulance ({sim.status} - {int(sim.progress_ratio*100)}%)",
            icon=folium.Icon(color="red", icon="ambulance", prefix="fa")
        ).add_to(m)
        
        # Hospital Markers
        for ev in evaluations:
            h_match = next((h for h in requests.get(f"{BACKEND_URL}/api/hospitals").json() if h["id"] == ev["hospital_id"]), None)
            if h_match:
                h_lat = h_match["location"]["latitude"]
                h_lon = h_match["location"]["longitude"]
                is_sel = (selected_hosp and ev["hospital_id"] == selected_hosp["id"])
                
                pin_color = "green" if is_sel else ("blue" if ev["is_infrastructure_eligible"] else "gray")
                status_text = "SELECTED DESTINATION" if is_sel else ("Eligible" if ev["is_infrastructure_eligible"] else "Ineligible")
                
                folium.Marker(
                    [h_lat, h_lon],
                    popup=f"<b>{ev['hospital_name']}</b><br>ETA: {ev['eta_minutes']} min<br>Status: {status_text}",
                    tooltip=f"🏥 {ev['hospital_name']} ({ev['eta_minutes']}m)",
                    icon=folium.Icon(color=pin_color, icon="plus", prefix="fa")
                ).add_to(m)
                
                # Draw live route line to selected destination
                if is_sel:
                    folium.PolyLine(
                        locations=[[amb_lat, amb_lon], [h_lat, h_lon]],
                        color="#10b981",
                        weight=5,
                        opacity=0.85,
                        dash_array="10"
                    ).add_to(m)

        st_folium(m, height=360, width=540)

    # If auto-simulation is active, advance by 10% after 1.2 seconds and rerun
    if st.session_state.auto_sim:
        if sim.status != "ARRIVED":
            time.sleep(1.2)
            sim.step_simulation(step_fraction=0.10, backend_url=BACKEND_URL)
            st.rerun()
        else:
            st.session_state.auto_sim = False
            st.success("🎉 Ambulance has successfully arrived at the emergency bay!")
