"""
VitaVia Pydantic Models & Data Schemas
Defines structured objects for Telemetry, Vitals, Gemini Clinical Analysis,
Hospital Infrastructure, Traffic Routing, and System Acknowledgment.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class GeoPoint(BaseModel):
    """Geographic coordinate representation."""
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    address: Optional[str] = Field(None, description="Human readable address/landmark")


class PatientVitals(BaseModel):
    """Simulated IoT Patient Vital Signs."""
    spo2: float = Field(..., ge=0, le=100, description="Blood oxygen saturation percentage (%)")
    heart_rate: int = Field(..., ge=0, le=300, description="Heart rate in beats per minute (BPM)")
    systolic_bp: int = Field(..., ge=0, le=300, description="Systolic blood pressure (mmHg)")
    diastolic_bp: int = Field(..., ge=0, le=200, description="Diastolic blood pressure (mmHg)")
    temperature: float = Field(..., ge=30.0, le=45.0, description="Body temperature in Celsius (°C)")
    recorded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PatientInfo(BaseModel):
    """Patient emergency profile."""
    patient_id: str = Field(default="PAT-101")
    name: str = Field(default="Emergency Patient")
    age: int = Field(default=45)
    gender: str = Field(default="Unknown")
    chief_complaint: str = Field(default="Acute respiratory distress & chest tightness")


class GeminiAnalysis(BaseModel):
    """Clinical decision-support output from Gemini AI or heuristic fallback."""
    urgency: str = Field(..., description="Urgency category: CRITICAL, HIGH, MODERATE, LOW")
    required_infrastructure: List[str] = Field(
        default_factory=list,
        description="Required hospital resources, e.g. ['ICU', 'Ventilator', 'Emergency Bed', 'Emergency Doctor']"
    )
    summary: str = Field(..., description="Concise clinical condition summary")
    clinical_notes: Optional[str] = Field(default="", description="Detailed clinical assessment rationale")
    source: str = Field(default="GEMINI_API", description="Source of analysis: 'GEMINI_API' or 'HEURISTIC_FALLBACK'")


class HospitalInfrastructure(BaseModel):
    """Live resource availability at a hospital."""
    emergency_bed_available: bool = Field(default=True)
    icu_available: bool = Field(default=True)
    ventilator_available: bool = Field(default=True)
    emergency_doctor_available: bool = Field(default=True)
    
    total_emergency_beds: int = Field(default=20)
    available_emergency_beds: int = Field(default=4)
    total_icu_beds: int = Field(default=10)
    available_icu_beds: int = Field(default=2)
    total_ventilators: int = Field(default=8)
    available_ventilators: int = Field(default=2)


class Hospital(BaseModel):
    """Hospital facility details and real-time infrastructure."""
    id: str
    name: str
    location: GeoPoint
    infrastructure: HospitalInfrastructure
    contact_number: str = "108"
    trauma_level: str = "Level 1 Trauma Center"


class RouteEvaluation(BaseModel):
    """Evaluation metrics for a candidate hospital."""
    hospital_id: str
    hospital_name: str
    distance_km: float
    traffic_condition: str = Field(..., description="LOW, MODERATE, HEAVY, SEVERE")
    eta_minutes: float
    is_infrastructure_eligible: bool
    missing_infrastructure: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    route_source: str = Field(default="MOCK_TRAFFIC_ENGINE", description="'GOOGLE_ROUTES_API' or 'MOCK_TRAFFIC_ENGINE'")


class HospitalSelectionResponse(BaseModel):
    """Optimal fastest-suitable hospital selection response."""
    selected_hospital: Optional[Hospital] = None
    selected_route: Optional[RouteEvaluation] = None
    gemini_analysis: GeminiAnalysis
    all_evaluations: List[RouteEvaluation] = Field(default_factory=list)
    decision_summary: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HospitalAcknowledgment(BaseModel):
    """Hospital handshake & resource reservation acknowledgment."""
    acknowledgment_id: str
    hospital_id: str
    hospital_name: str
    ambulance_id: str
    patient_id: str
    acknowledged: bool
    assigned_bay: str
    team_ready: bool
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AmbulanceTelemetry(BaseModel):
    """Live state broadcasted by the connected ambulance."""
    ambulance_id: str = "AMB-07"
    patient_info: PatientInfo = Field(default_factory=PatientInfo)
    current_vitals: PatientVitals
    current_location: GeoPoint
    status: str = Field(
        default="DISPATCHED",
        description="DISPATCHED, EN_ROUTE, ARRIVED"
    )
    destination_hospital_id: Optional[str] = None
    destination_hospital_name: Optional[str] = None
    current_eta_minutes: Optional[float] = None
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Transit progress percentage (0-100%)")
    acknowledgment: Optional[HospitalAcknowledgment] = None
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
