"""Schemas for VITAVIA's simulated emergency and decision-pipeline data."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VitalSigns(BaseModel):
    """Simulated patient vital signs within prototype input boundaries only."""

    spo2: float = Field(ge=75.0, le=100.0)
    heart_rate: int = Field(ge=40, le=180)
    systolic_bp: int = Field(ge=70, le=180)
    diastolic_bp: int = Field(ge=40, le=120)
    temperature: float = Field(ge=34.0, le=42.0)


class GPSLocation(BaseModel):
    """A latitude and longitude pair used only for this prototype simulation."""

    latitude: float
    longitude: float


class Patient(BaseModel):
    """Simulated patient details for one active emergency."""

    patient_id: str
    age: int
    gender: str
    emergency_type: str


class Ambulance(BaseModel):
    """Simulated ambulance details and its current position."""

    ambulance_id: str
    status: str
    location: GPSLocation


class HospitalAvailability(BaseModel):
    """Current simulated infrastructure availability at a hospital."""

    emergency_bed: bool
    icu: bool
    ventilator: bool
    emergency_team: bool


class Hospital(BaseModel):
    """A fictional hospital and its simulated infrastructure."""

    hospital_id: str
    name: str
    location: GPSLocation
    availability: HospitalAvailability


class EmergencySnapshot(BaseModel):
    """The complete current simulated state of one emergency."""

    ambulance: Ambulance
    patient: Patient
    vitals: VitalSigns


class TriageResult(BaseModel):
    """A deterministic prototype assessment derived from simulated vitals."""

    severity: str
    required_infrastructure: list[str]
    explanation: str
    source: str


class HospitalEvaluation(BaseModel):
    """Infrastructure eligibility of one hospital for a set of requirements."""

    hospital_id: str
    name: str
    eligible: bool
    missing_infrastructure: list[str]


class RouteResult(BaseModel):
    """A traffic and ETA result returned by the Stage 3 mock router."""

    hospital_id: str
    distance_km: float
    traffic_condition: str
    eta_minutes: float
    routing_source: str


class HospitalDecision(BaseModel):
    """Eligibility, route context, and selection state for one hospital."""

    hospital_id: str
    name: str
    eligible: bool
    missing_infrastructure: list[str]
    distance_km: Optional[float] = None
    traffic_condition: Optional[str] = None
    eta_minutes: Optional[float] = None
    routing_source: Optional[str] = None
    selected: bool
    acknowledgement_status: str


class Acknowledgement(BaseModel):
    """The simulated response from the selected destination hospital."""

    status: str
    hospital_id: Optional[str] = None
    message: str


class JourneyState(BaseModel):
    """Current in-memory ambulance journey state for the VITAVIA prototype."""

    active: bool
    ambulance_id: str
    patient_id: str
    selected_hospital_id: Optional[str] = None
    selected_hospital_name: Optional[str] = None
    start_location: GPSLocation
    current_location: GPSLocation
    destination_location: Optional[GPSLocation] = None
    initial_eta_minutes: Optional[float] = None
    remaining_eta_minutes: Optional[float] = None
    progress_percent: float
    status: str
    step_number: int
    acknowledgement_status: str
    routing_source: Optional[str] = None


class JourneyUpdateResponse(BaseModel):
    """A journey advancement paired with the synchronized emergency snapshot."""

    journey: JourneyState
    snapshot: EmergencySnapshot


class EmergencyHistoryItem(BaseModel):
    """Summary of one persisted, simulated emergency for the history API."""

    emergency_id: str
    ambulance_id: str
    patient_id: str
    emergency_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    selected_hospital_id: Optional[str] = None
    selected_hospital_name: Optional[str] = None
    acknowledgement_status: Optional[str] = None
    triage_severity: Optional[str] = None
    triage_source: Optional[str] = None
    routing_source: Optional[str] = None
    initial_eta_minutes: Optional[float] = None


class VitalHistoryItem(BaseModel):
    """One persisted simulated vital-sign reading."""

    recorded_at: datetime
    spo2: float
    heart_rate: int
    systolic_bp: int
    diastolic_bp: int
    temperature: float


class LocationHistoryItem(BaseModel):
    """One persisted simulated ambulance location and journey-state reading."""

    recorded_at: datetime
    latitude: float
    longitude: float
    ambulance_status: str
    journey_status: Optional[str] = None
    progress_percent: Optional[float] = None
    remaining_eta_minutes: Optional[float] = None


class HospitalEvaluationHistoryItem(BaseModel):
    """One persisted deterministic hospital evaluation."""

    hospital_id: str
    hospital_name: str
    eligible: bool
    missing_infrastructure: list[str]
    distance_km: Optional[float] = None
    traffic_condition: Optional[str] = None
    eta_minutes: Optional[float] = None
    routing_source: Optional[str] = None
    selected: bool
    acknowledgement_status: str


class EmergencyHistoryDetail(BaseModel):
    """Full audit detail for one simulated emergency session."""

    emergency: EmergencyHistoryItem
    required_infrastructure: list[str]
    triage_explanation: Optional[str] = None
    hospital_evaluations: list[HospitalEvaluationHistoryItem]
    vital_history: list[VitalHistoryItem]
    location_history: list[LocationHistoryItem]


class EmergencyDecisionResponse(BaseModel):
    """The complete deterministic Stage 3 emergency decision response."""

    ambulance: Ambulance
    patient: Patient
    vitals: VitalSigns
    triage: TriageResult
    hospitals: list[HospitalDecision]
    selected_hospital: Optional[HospitalDecision] = None
    acknowledgement: Acknowledgement


class IncomingEmergencyRequest(BaseModel):
    """Latest ambulance-to-hospital request payload; it does not trigger clinical logic."""

    ambulance_id: str = Field(min_length=1)
    patient_id: str = Field(min_length=1)
    patient_name: str = Field(min_length=1)
    age: int = Field(ge=0, le=130)
    gender: str = Field(min_length=1)
    chief_complaint: str = Field(min_length=1)
    spo2: float = Field(ge=75.0, le=100.0)
    heart_rate: int = Field(ge=40, le=180)
    systolic_bp: int = Field(ge=70, le=180)
    diastolic_bp: int = Field(ge=40, le=120)
    temperature: float = Field(ge=34.0, le=42.0)
    dispatch_origin: str = Field(min_length=1)
    selected_hospital_id: str = Field(min_length=1)
    eta_minutes: float = Field(ge=0)
    distance_km: float = Field(ge=0)
    triage_level: str = Field(min_length=1)


class IncomingEmergencyResponse(BaseModel):
    """Latest incoming request visibility for one hospital control-room client."""

    exists: bool
    has_active_request: bool
    selected_hospital_id: Optional[str] = None
    incoming_request: Optional[IncomingEmergencyRequest] = None
    received_at: Optional[datetime] = None
