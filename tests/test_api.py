"""
FastAPI Endpoints Automated Test.
Tests all REST API endpoints using TestClient.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_api_endpoints():
    print("Testing GET / ...")
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "OPERATIONAL"

    print("Testing GET /api/hospitals ...")
    r = client.get("/api/hospitals")
    assert r.status_code == 200
    hospitals = r.json()
    assert len(hospitals) >= 3

    print("Testing POST /api/analyze-vitals ...")
    r = client.post(
        "/api/analyze-vitals",
        json={
            "vitals": {
                "spo2": 88.0,
                "heart_rate": 125,
                "systolic_bp": 90,
                "diastolic_bp": 60,
                "temperature": 38.2
            }
        }
    )
    assert r.status_code == 200
    res_ai = r.json()
    assert "urgency" in res_ai
    assert "required_infrastructure" in res_ai

    print("Testing POST /api/dispatch ...")
    dispatch_payload = {
        "ambulance_id": "AMB-07",
        "patient_info": {
            "patient_id": "PAT-99",
            "name": "Alex Mercer",
            "age": 45,
            "gender": "Male",
            "chief_complaint": "Severe respiratory distress"
        },
        "vitals": {
            "spo2": 88.0,
            "heart_rate": 125,
            "systolic_bp": 90,
            "diastolic_bp": 60,
            "temperature": 38.2
        },
        "location": {
            "latitude": 12.9700,
            "longitude": 77.6000,
            "address": "Trinity Junction"
        }
    }
    r = client.post("/api/dispatch", json=dispatch_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ["DISPATCHED", "DISPATCHED_TO_HOSPITAL"]
    assert data["selection"]["selected_hospital"]["id"] == "HOSP-B"
    assert data["acknowledgment"]["acknowledged"] is True

    print("Testing GET /api/telemetry ...")
    r = client.get("/api/telemetry")
    assert r.status_code == 200
    telemetry = r.json()
    assert telemetry["ambulance_id"] == "AMB-07"
    assert telemetry["destination_hospital_id"] == "HOSP-B"

    print("ALL API ENDPOINTS TESTED SUCCESSFULLY!")


if __name__ == "__main__":
    test_api_endpoints()
