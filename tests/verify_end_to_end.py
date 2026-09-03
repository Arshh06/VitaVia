"""
Comprehensive End-to-End Live Workflow Verification for VitaVia.
Tests the exact sequence:
1. User requests ambulance
2. Simulated ambulance & patient vitals generated
3. Backend receives telemetry
4. Patient vitals analyzed (Gemini / Heuristic)
5. Required hospital infrastructure determined
6. Multiple candidate hospitals evaluated
7. Hospitals lacking infrastructure rejected
8. Traffic-aware travel times computed
9. Fastest suitable hospital selected
10. Hospital acknowledgment generated
11. Ambulance receives acknowledgment
12. Continuous telemetry update in transit
"""

import sys
import os
import requests

BACKEND_URL = "http://127.0.0.1:8000"

def verify_live_workflow():
    print("=" * 70)
    print("VITAVIA END-TO-END LIVE WORKFLOW VERIFICATION")
    print(f"Target Backend: {BACKEND_URL}")
    print("=" * 70)

    # Step 1: Health check
    print("\n[STEP 1] Checking Backend Health...")
    r = requests.get(f"{BACKEND_URL}/", timeout=3)
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print(f" -> OK: {r.json()}")

    # Step 2: Fetch Hospitals Registry
    print("\n[STEP 2] Fetching Candidate Hospitals Grid...")
    r = requests.get(f"{BACKEND_URL}/api/hospitals", timeout=3)
    assert r.status_code == 200, f"Failed to get hospitals: {r.status_code}"
    hospitals = r.json()
    print(f" -> OK: Loaded {len(hospitals)} hospitals")
    for h in hospitals:
        print(f"    - {h['id']}: {h['name']} | ICU: {h['infrastructure']['icu_available']} | Vent: {h['infrastructure']['ventilator_available']}")

    # Step 3: Simulate Patient Telemetry & Dispatch Request (Critical Case)
    print("\n[STEP 3 & 4] Simulating Patient Telemetry & Requesting Dispatch...")
    payload = {
        "ambulance_id": "AMB-07",
        "patient_info": {
            "patient_id": "PAT-8812",
            "name": "Sarah Jenkins",
            "age": 58,
            "gender": "Female",
            "chief_complaint": "Severe dyspnea, acute cyanosis, respiratory failure"
        },
        "vitals": {
            "spo2": 87.5,
            "heart_rate": 128,
            "systolic_bp": 92,
            "diastolic_bp": 58,
            "temperature": 38.4
        },
        "location": {
            "latitude": 12.9700,
            "longitude": 77.6000,
            "address": "Trinity Junction Central"
        }
    }

    r = requests.post(f"{BACKEND_URL}/api/dispatch", json=payload, timeout=8)
    assert r.status_code == 200, f"Dispatch failed: {r.status_code} - {r.text}"
    dispatch_res = r.json()
    
    # Step 5: Verify AI Analysis Results
    print("\n[STEP 5] Verifying AI Clinical Analysis...")
    selection = dispatch_res["selection"]
    gemini = selection["gemini_analysis"]
    print(f" -> Urgency: {gemini['urgency']}")
    print(f" -> Required Infrastructure: {gemini['required_infrastructure']}")
    print(f" -> Clinical Summary: {gemini['summary']}")
    print(f" -> Engine Source: {gemini['source']}")
    assert gemini["urgency"] in ["CRITICAL", "HIGH"]
    assert "ICU" in gemini["required_infrastructure"]
    assert "Ventilator" in gemini["required_infrastructure"]

    # Step 6 & 7: Verify Hospital Evaluation & Ineligible Rejections
    print("\n[STEP 6 & 7] Verifying Hospital Infrastructure Evaluation & Rejections...")
    evaluations = selection["all_evaluations"]
    for ev in evaluations:
        status = "ELIGIBLE" if ev["is_infrastructure_eligible"] else f"REJECTED ({ev['rejection_reason']})"
        print(f"    - {ev['hospital_id']} ({ev['hospital_name']}): Dist={ev['distance_km']}km, Traffic={ev['traffic_condition']}, ETA={ev['eta_minutes']}min -> {status}")

    hosp_c = next(e for e in evaluations if e["hospital_id"] == "HOSP-C")
    assert not hosp_c["is_infrastructure_eligible"], "Hospital C must be rejected due to lack of ICU/Ventilator"
    print(" -> OK: Hospital C properly rejected due to missing ICU.")

    # Step 8 & 9: Verify Fastest Suitable Selection (HOSP-B over HOSP-A)
    print("\n[STEP 8 & 9] Verifying Fastest-Suitable Hospital Selection...")
    selected_hosp = selection["selected_hospital"]
    selected_route = selection["selected_route"]
    print(f" -> Selected Hospital: {selected_hosp['name']} (ID: {selected_hosp['id']})")
    print(f" -> Winning Metrics: Distance={selected_route['distance_km']}km, Traffic={selected_route['traffic_condition']}, ETA={selected_route['eta_minutes']}min")
    assert selected_hosp["id"] == "HOSP-B", f"Expected HOSP-B, got {selected_hosp['id']}"
    print(" -> OK: HOSP-B selected as fastest feasible route despite longer geometric distance.")

    # Step 10 & 11: Verify Hospital Handshake Acknowledgment
    print("\n[STEP 10 & 11] Verifying Hospital Acknowledgment Handshake...")
    ack = dispatch_res["acknowledgment"]
    print(f" -> Ack ID: {ack['acknowledgment_id']}")
    print(f" -> Assigned Bay: {ack['assigned_bay']}")
    print(f" -> Team Ready: {ack['team_ready']}")
    print(f" -> Message: {ack['message']}")
    assert ack["acknowledged"] is True
    assert ack["hospital_id"] == "HOSP-B"

    # Step 12: Verify Continuous Transit Telemetry Update
    print("\n[STEP 12] Verifying Transit Telemetry Update...")
    updated_telemetry = dispatch_res["telemetry"]
    updated_telemetry["status"] = "ROUTING_TO_HOSPITAL"
    updated_telemetry["current_location"]["address"] = "In Transit - 40% to St. Jude"
    r = requests.post(f"{BACKEND_URL}/api/telemetry/update", json=updated_telemetry, timeout=3)
    assert r.status_code == 200
    
    r = requests.get(f"{BACKEND_URL}/api/telemetry", timeout=3)
    assert r.status_code == 200
    live_tel = r.json()
    print(f" -> Live Ambulance Status: {live_tel['status']}")
    print(f" -> Destination: {live_tel['destination_hospital_name']}")
    print(f" -> Position: {live_tel['current_location']['address']}")

    print("\n" + "=" * 70)
    print("SUCCESS: COMPLETE END-TO-END WORKFLOW VERIFIED WITHOUT ERRORS!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        verify_live_workflow()
    except Exception as e:
        print(f"\n[FAIL] Verification error: {e}")
        sys.exit(1)
