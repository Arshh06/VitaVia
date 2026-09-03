"""
VitaVia FastAPI Server.
Exposes REST endpoints for live IoT telemetry ingestion, Gemini AI clinical analysis,
deterministic traffic-aware hospital selection, and hospital acknowledgment handshakes.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.models import (
    GeoPoint,
    PatientVitals,
    PatientInfo,
    Hospital,
    GeminiAnalysis,
    HospitalSelectionResponse,
    HospitalAcknowledgment,
    AmbulanceTelemetry
)
from backend.hospitals import (
    get_all_hospitals,
    get_hospital_by_id,
    update_hospital_infrastructure,
    reset_mock_hospitals
)
from backend.gemini_service import analyze_patient_vitals
from backend.decision import evaluate_and_select_hospital, create_hospital_acknowledgment

app = FastAPI(
    title="VitaVia Emergency Routing Engine",
    description="AI-Assisted Intelligent Connected Ambulance & Traffic-Aware Hospital Routing System",
    version="1.0.0"
)

# Enable CORS for local Streamlit & frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory telemetry state for the active demonstration mission
_active_telemetry = AmbulanceTelemetry(
    ambulance_id="AMB-07",
    patient_info=PatientInfo(
        patient_id="PAT-9021",
        name="Alex Mercer",
        age=52,
        gender="Male",
        chief_complaint="Acute severe chest tightness and dyspnea"
    ),
    current_vitals=PatientVitals(
        spo2=89.0,
        heart_rate=124,
        systolic_bp=90,
        diastolic_bp=60,
        temperature=38.2
    ),
    current_location=GeoPoint(latitude=12.9700, longitude=77.6000, address="Trinity Junction Central"),
    status="PATIENT_ONBOARD"
)


class DispatchRequest(BaseModel):
    ambulance_id: str = "AMB-07"
    patient_info: Optional[PatientInfo] = None
    vitals: PatientVitals
    location: GeoPoint


class InfrastructureUpdateRequest(BaseModel):
    emergency_bed_available: Optional[bool] = None
    icu_available: Optional[bool] = None
    ventilator_available: Optional[bool] = None
    emergency_doctor_available: Optional[bool] = None
    available_emergency_beds: Optional[int] = None
    available_icu_beds: Optional[int] = None
    available_ventilators: Optional[int] = None


@app.get("/")
def root():
    return {
        "system": "VitaVia Emergency Dispatch API",
        "status": "OPERATIONAL",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/api/hospitals", response_model=List[Hospital])
def list_hospitals():
    """Retrieve list of all hospitals and live infrastructure availability."""
    return get_all_hospitals()


@app.get("/api/hospitals/{hospital_id}", response_model=Hospital)
def get_hospital(hospital_id: str):
    """Retrieve details for a specific hospital."""
    hosp = get_hospital_by_id(hospital_id)
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hosp


@app.put("/api/hospitals/{hospital_id}", response_model=Hospital)
def update_hospital(hospital_id: str, update: InfrastructureUpdateRequest):
    """Dynamically modify hospital infrastructure for testing/demonstration."""
    hosp = update_hospital_infrastructure(
        hospital_id=hospital_id,
        emergency_bed=update.emergency_bed_available,
        icu=update.icu_available,
        ventilator=update.ventilator_available,
        doctor=update.emergency_doctor_available,
        available_emergency_beds=update.available_emergency_beds,
        available_icu_beds=update.available_icu_beds,
        available_ventilators=update.available_ventilators
    )
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hosp


@app.post("/api/hospitals/reset", response_model=List[Hospital])
def reset_hospitals():
    """Reset all hospital resource states to default baseline."""
    return reset_mock_hospitals()


class AnalyzeVitalsRequest(BaseModel):
    vitals: PatientVitals
    patient_info: Optional[PatientInfo] = None


@app.post("/api/analyze-vitals", response_model=GeminiAnalysis)
def analyze_vitals_endpoint(request: AnalyzeVitalsRequest):
    """Analyze vitals via Gemini AI clinical decision support."""
    return analyze_patient_vitals(request.vitals, request.patient_info)


@app.post("/api/recommend-hospital", response_model=HospitalSelectionResponse)
def recommend_hospital_endpoint(request: DispatchRequest):
    """
    Evaluates patient vitals with Gemini, tests hospital infrastructure,
    evaluates traffic-aware routes, and returns the fastest suitable hospital.
    """
    patient = request.patient_info or _active_telemetry.patient_info
    return evaluate_and_select_hospital(
        ambulance_location=request.location,
        vitals=request.vitals,
        patient_info=patient,
        ambulance_id=request.ambulance_id
    )


@app.post("/api/dispatch", response_model=Dict[str, Any])
def full_dispatch_pipeline(request: DispatchRequest):
    """
    Executes the full automated workflow:
    1. AI Clinical Analysis
    2. Deterministic fastest suitable hospital selection
    3. Formal hospital acknowledgment & bed reservation
    4. Mission telemetry state update
    """
    global _active_telemetry
    
    patient = request.patient_info or _active_telemetry.patient_info
    
    # 1 & 2. Run selection engine
    selection: HospitalSelectionResponse = evaluate_and_select_hospital(
        ambulance_location=request.location,
        vitals=request.vitals,
        patient_info=patient,
        ambulance_id=request.ambulance_id
    )
    
    if not selection.selected_hospital or not selection.selected_route:
        raise HTTPException(status_code=500, detail="Unable to route to any available medical facility")
        
    # 3. Create hospital acknowledgment
    ack: HospitalAcknowledgment = create_hospital_acknowledgment(
        hospital=selection.selected_hospital,
        ambulance_id=request.ambulance_id,
        patient_id=patient.patient_id,
        required_infrastructure=selection.gemini_analysis.required_infrastructure
    )
    
    # 4. Update active telemetry
    _active_telemetry.ambulance_id = request.ambulance_id
    _active_telemetry.patient_info = patient
    _active_telemetry.current_vitals = request.vitals
    _active_telemetry.current_location = request.location
    _active_telemetry.destination_hospital_id = selection.selected_hospital.id
    _active_telemetry.destination_hospital_name = selection.selected_hospital.name
    _active_telemetry.current_eta_minutes = selection.selected_route.eta_minutes
    _active_telemetry.progress_percentage = 0.0
    _active_telemetry.status = "DISPATCHED"
    _active_telemetry.acknowledgment = ack
    _active_telemetry.last_updated = datetime.utcnow().isoformat()
    
    return {
        "status": "DISPATCHED",
        "selection": selection,
        "acknowledgment": ack,
        "telemetry": _active_telemetry
    }


@app.post("/api/telemetry/update", response_model=AmbulanceTelemetry)
def update_telemetry(telemetry: AmbulanceTelemetry):
    """Update continuous ambulance telemetry (vitals, GPS, status) during transit."""
    global _active_telemetry
    _active_telemetry = telemetry
    _active_telemetry.last_updated = datetime.utcnow().isoformat()
    return _active_telemetry


@app.get("/api/telemetry", response_model=AmbulanceTelemetry)
def get_telemetry():
    """Fetch current live ambulance telemetry and mission status."""
    return _active_telemetry
