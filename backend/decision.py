"""
Deterministic Hospital Eligibility and Traffic-Aware Selection Engine.
Combines Gemini AI clinical requirements with real-time hospital infrastructure
and traffic-aware ETA routing to identify the FASTEST SUITABLE hospital.
"""

import uuid
from typing import List, Optional, Tuple
from datetime import datetime

from backend.models import (
    GeoPoint,
    PatientVitals,
    PatientInfo,
    Hospital,
    RouteEvaluation,
    HospitalSelectionResponse,
    HospitalAcknowledgment,
    GeminiAnalysis
)
from backend.hospitals import get_all_hospitals
from backend.gemini_service import analyze_patient_vitals
from backend.routing import calculate_route


def check_hospital_eligibility(hospital: Hospital, required_infra: List[str]) -> Tuple[bool, List[str]]:
    """
    Deterministically checks whether a hospital possesses all infrastructure
    mandated by the clinical triage assessment.
    """
    missing: List[str] = []
    infra = hospital.infrastructure
    
    # Normalize required strings
    req_lower = [r.lower() for r in required_infra]
    
    if any("icu" in r for r in req_lower):
        if not infra.icu_available or infra.available_icu_beds <= 0:
            missing.append("ICU")
            
    if any("ventilator" in r for r in req_lower):
        if not infra.ventilator_available or infra.available_ventilators <= 0:
            missing.append("Ventilator")
            
    if any("bed" in r for r in req_lower) or any("emergency" in r for r in req_lower and "doctor" not in r):
        if not infra.emergency_bed_available or infra.available_emergency_beds <= 0:
            missing.append("Emergency Bed")
            
    if any("doctor" in r for r in req_lower):
        if not infra.emergency_doctor_available:
            missing.append("Emergency Doctor / Trauma Team")
            
    is_eligible = len(missing) == 0
    return is_eligible, missing


def evaluate_and_select_hospital(
    ambulance_location: GeoPoint,
    vitals: PatientVitals,
    patient_info: Optional[PatientInfo] = None,
    ambulance_id: str = "AMB-07"
) -> HospitalSelectionResponse:
    """
    Complete end-to-end decision workflow:
    1. Gemini analyzes patient vitals -> extracts required infrastructure.
    2. Backend checks infrastructure availability across all nearby hospitals.
    3. Traffic-aware routing computes distance and ETA for each hospital.
    4. Deterministic selector chooses the FASTEST eligible hospital.
    """
    # 1. AI Clinical Analysis
    gemini_result: GeminiAnalysis = analyze_patient_vitals(vitals, patient_info)
    
    # 2. Fetch active hospital registry
    all_hospitals = get_all_hospitals()
    
    evaluations: List[RouteEvaluation] = []
    eligible_evaluations: List[Tuple[Hospital, RouteEvaluation]] = []
    
    for hosp in all_hospitals:
        # Check infrastructure match
        is_eligible, missing = check_hospital_eligibility(hosp, gemini_result.required_infrastructure)
        
        # Calculate traffic-aware route
        route_data = calculate_route(ambulance_location, hosp.location, hospital_id=hosp.id)
        
        rejection_reason = None
        if not is_eligible:
            rejection_reason = f"Lacks required infrastructure: {', '.join(missing)}"
            
        evaluation = RouteEvaluation(
            hospital_id=hosp.id,
            hospital_name=hosp.name,
            distance_km=route_data["distance_km"],
            traffic_condition=route_data["traffic_condition"],
            eta_minutes=route_data["eta_minutes"],
            is_infrastructure_eligible=is_eligible,
            missing_infrastructure=missing,
            rejection_reason=rejection_reason,
            route_source=route_data.get("source", "MOCK_TRAFFIC_ENGINE")
        )
        evaluations.append(evaluation)
        
        if is_eligible:
            eligible_evaluations.append((hosp, evaluation))
            
    # 3. Sort evaluations for clear ranking: eligible first, then lowest ETA
    evaluations.sort(key=lambda ev: (not ev.is_infrastructure_eligible, ev.eta_minutes))
    
    # 4. Selection Logic: Fastest among eligible candidates
    if eligible_evaluations:
        # Sort eligible candidate pairs by ETA ascending
        eligible_evaluations.sort(key=lambda item: item[1].eta_minutes)
        selected_hospital, selected_route = eligible_evaluations[0]
        
        decision_summary = (
            f"Selected '{selected_hospital.name}' (ETA: {selected_route.eta_minutes} min, "
            f"Dist: {selected_route.distance_km} km, Traffic: {selected_route.traffic_condition}). "
            f"All required clinical capabilities ({', '.join(gemini_result.required_infrastructure)}) verified available."
        )
    else:
        # Extreme fallback if no single hospital meets 100% of requirements
        evaluations.sort(key=lambda ev: ev.eta_minutes)
        selected_route = evaluations[0] if evaluations else None
        selected_hospital = next((h for h in all_hospitals if h.id == selected_route.hospital_id), None) if selected_route else None
        decision_summary = (
            "WARNING: No candidate hospital met all infrastructure requirements. "
            f"Routing to fastest available facility '{selected_hospital.name if selected_hospital else 'N/A'}' with partial capability."
        )
        
    return HospitalSelectionResponse(
        selected_hospital=selected_hospital,
        selected_route=selected_route,
        gemini_analysis=gemini_result,
        all_evaluations=evaluations,
        decision_summary=decision_summary,
        timestamp=datetime.utcnow().isoformat()
    )


def create_hospital_acknowledgment(
    hospital: Hospital,
    ambulance_id: str,
    patient_id: str,
    required_infrastructure: List[str]
) -> HospitalAcknowledgment:
    """
    Generates a formal hospital acknowledgment and resource reservation confirmation.
    """
    assigned_bay = f"Emergency Trauma Bay #{abs(hash(hospital.id + patient_id)) % 6 + 1}"
    infra_str = ", ".join(required_infrastructure) if required_infrastructure else "Standard Bed"
    
    message = (
        f"{hospital.name} Central Emergency Control acknowledges inbound {ambulance_id}. "
        f"{assigned_bay} reserved. Emergency clinical team on standby with {infra_str} prepared."
    )
    
    return HospitalAcknowledgment(
        acknowledgment_id=f"ACK-{uuid.uuid4().hex[:8].upper()}",
        hospital_id=hospital.id,
        hospital_name=hospital.name,
        ambulance_id=ambulance_id,
        patient_id=patient_id,
        acknowledged=True,
        assigned_bay=assigned_bay,
        team_ready=True,
        message=message,
        timestamp=datetime.utcnow().isoformat()
    )
