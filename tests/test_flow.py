"""
Automated Integration & Scenario Smoke Tests for VitaVia.
Validates:
1. Gemini clinical triage analysis (with heuristic fallback).
2. Traffic-aware route calculation.
3. Deterministic hospital infrastructure filtering (e.g. rejecting Hospital C when ICU is needed).
4. Fastest suitable hospital selection (selecting Hospital B over Hospital A despite greater distance).
5. Hospital acknowledgment creation.
"""

import sys
import os

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models import (
    PatientVitals,
    PatientInfo,
    GeoPoint,
    HospitalSelectionResponse
)
from backend.gemini_service import analyze_patient_vitals
from backend.hospitals import get_all_hospitals, get_hospital_by_id
from backend.routing import calculate_route
from backend.decision import evaluate_and_select_hospital, create_hospital_acknowledgment


def test_gemini_analysis_fallback():
    print("[TEST 1] Testing Gemini Decision-Support Service...")
    critical_vitals = PatientVitals(
        spo2=87.0,
        heart_rate=128,
        systolic_bp=90,
        diastolic_bp=55,
        temperature=38.4
    )
    result = analyze_patient_vitals(critical_vitals)
    assert result.urgency in ["CRITICAL", "HIGH"], f"Expected CRITICAL/HIGH, got {result.urgency}"
    assert "ICU" in result.required_infrastructure, "ICU should be required for severe hypoxia/shock"
    assert "Ventilator" in result.required_infrastructure, "Ventilator should be required for severe hypoxia"
    print(f" -> PASSED (Urgency: {result.urgency}, Infra: {result.required_infrastructure}, Source: {result.source})")


def test_routing_engine():
    print("[TEST 2] Testing Traffic-Aware Routing Engine...")
    origin = GeoPoint(latitude=12.9700, longitude=77.6000)
    hosp_a = get_hospital_by_id("HOSP-A")
    hosp_b = get_hospital_by_id("HOSP-B")
    
    route_a = calculate_route(origin, hosp_a.location, hospital_id="HOSP-A")
    route_b = calculate_route(origin, hosp_b.location, hospital_id="HOSP-B")
    
    assert route_a["traffic_condition"] == "HEAVY"
    assert route_b["traffic_condition"] == "LOW"
    # Hospital B should have lower ETA than Hospital A despite distance
    print(f" -> Hospital A: Dist={route_a['distance_km']}km, Traffic={route_a['traffic_condition']}, ETA={route_a['eta_minutes']}min")
    print(f" -> Hospital B: Dist={route_b['distance_km']}km, Traffic={route_b['traffic_condition']}, ETA={route_b['eta_minutes']}min")
    assert route_b["eta_minutes"] < route_a["eta_minutes"], "Hospital B on expressway should have lower ETA than congested Hospital A"
    print(" -> PASSED")


def test_deterministic_hospital_selection():
    print("[TEST 3] Testing Deterministic Fastest Suitable Hospital Selection...")
    amb_location = GeoPoint(latitude=12.9700, longitude=77.6000)
    
    # Scenario: Critical Patient requiring ICU + Ventilator
    vitals = PatientVitals(
        spo2=88.0,
        heart_rate=124,
        systolic_bp=90,
        diastolic_bp=60,
        temperature=38.2
    )
    patient = PatientInfo(patient_id="PAT-TEST", name="Test Patient", age=50)
    
    response: HospitalSelectionResponse = evaluate_and_select_hospital(
        ambulance_location=amb_location,
        vitals=vitals,
        patient_info=patient
    )
    
    # Check Hospital C rejection (No ICU/Ventilator)
    hosp_c_eval = next(e for e in response.all_evaluations if e.hospital_id == "HOSP-C")
    assert not hosp_c_eval.is_infrastructure_eligible, "Hospital C should be marked ineligible due to missing ICU/Ventilator"
    assert "ICU" in hosp_c_eval.missing_infrastructure, "Hospital C should report missing ICU"
    
    # Check Winning Hospital: Must be Hospital B (Fastest eligible)
    selected_hosp = response.selected_hospital
    assert selected_hosp is not None
    assert selected_hosp.id == "HOSP-B", f"Expected HOSP-B to win as fastest suitable, but got {selected_hosp.id}"
    print(f" -> Winner: {selected_hosp.name} (ID: {selected_hosp.id})")
    print(f" -> Decision Rationale: {response.decision_summary}")
    print(" -> PASSED")


def test_hospital_acknowledgment():
    print("[TEST 4] Testing Hospital Acknowledgment Handshake...")
    hosp = get_hospital_by_id("HOSP-B")
    ack = create_hospital_acknowledgment(
        hospital=hosp,
        ambulance_id="AMB-07",
        patient_id="PAT-99",
        required_infrastructure=["ICU", "Ventilator"]
    )
    assert ack.acknowledged is True
    assert "reserved" in ack.message.lower()
    print(f" -> Ack: {ack.acknowledgment_id} | Bay: {ack.assigned_bay} | Message: {ack.message}")
    print(" -> PASSED")


if __name__ == "__main__":
    print("========================================")
    print("RUNNING VITAVIA INTEGRATION TEST SUITE")
    print("========================================")
    test_gemini_analysis_fallback()
    test_routing_engine()
    test_deterministic_hospital_selection()
    test_hospital_acknowledgment()
    print("========================================")
    print("ALL TESTS PASSED SUCCESSFULLY! (4/4)")
    print("========================================")
