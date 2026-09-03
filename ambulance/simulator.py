"""
VitaVia Ambulance & IoT Vital Signs Telemetry Simulator.
Simulates connected medical devices, continuous patient vital stream variations,
emergency clinical scenarios, GPS route movement, state transitions
(DISPATCHED -> EN_ROUTE -> ARRIVED), and telemetry transmission to FastAPI backend.
"""

import time
import random
import os
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from backend.models import (
    PatientVitals,
    PatientInfo,
    GeoPoint,
    AmbulanceTelemetry,
    HospitalAcknowledgment
)

# Realistic clinical demo scenarios
PRESET_SCENARIOS = {
    "1. Acute Respiratory Distress & Hypoxia (Critical)": {
        "description": "Patient experiencing severe dyspnea, falling oxygen levels, and tachycardia. Requires ICU + Ventilator.",
        "patient": PatientInfo(
            patient_id="PAT-8812",
            name="Sarah Jenkins",
            age=58,
            gender="Female",
            chief_complaint="Severe shortness of breath, acute cyanosis, wheezing"
        ),
        "vitals": PatientVitals(
            spo2=87.5,
            heart_rate=128,
            systolic_bp=92,
            diastolic_bp=58,
            temperature=38.4
        )
    },
    "2. Acute Coronary Syndrome / Cardiogenic Stress (High)": {
        "description": "Crushing retrosternal chest pain with diaphoresis and hypotension. Requires ICU + Emergency Doctor.",
        "patient": PatientInfo(
            patient_id="PAT-4029",
            name="Robert Chen",
            age=63,
            gender="Male",
            chief_complaint="Crushing retrosternal chest pain radiating to left arm"
        ),
        "vitals": PatientVitals(
            spo2=91.0,
            heart_rate=118,
            systolic_bp=88,
            diastolic_bp=54,
            temperature=37.2
        )
    },
    "3. Moderate Trauma / Extremity Injury (Moderate)": {
        "description": "Closed tibia fracture with moderate pain. Vitals stable. Standard Emergency Bed required.",
        "patient": PatientInfo(
            patient_id="PAT-1194",
            name="David Kumar",
            age=29,
            gender="Male",
            chief_complaint="Right lower leg trauma following bike collision"
        ),
        "vitals": PatientVitals(
            spo2=98.0,
            heart_rate=84,
            systolic_bp=124,
            diastolic_bp=78,
            temperature=36.8
        )
    },
    "4. Severe Sepsis / High Grade Pyrexia (Critical)": {
        "description": "Septic shock presentation with hyperthermia and severe tachycardia. Requires ICU + Emergency Bed.",
        "patient": PatientInfo(
            patient_id="PAT-7731",
            name="Maria Rodriguez",
            age=71,
            gender="Female",
            chief_complaint="High fever, altered mental status, suspected septic shock"
        ),
        "vitals": PatientVitals(
            spo2=89.5,
            heart_rate=136,
            systolic_bp=82,
            diastolic_bp=48,
            temperature=40.2
        )
    }
}

DEFAULT_START_LOCATION = GeoPoint(
    latitude=12.9700,
    longitude=77.6000,
    address="Trinity Junction Central (Dispatch Origin)"
)


class AmbulanceSimulator:
    """
    Simulates an IoT connected emergency ambulance with live telemetry,
    physiologic vital variations, progressive GPS transit movement,
    and automatic backend synchronization.
    """
    
    def __init__(
        self,
        ambulance_id: str = "AMB-07",
        initial_location: Optional[GeoPoint] = None,
        scenario_key: str = "1. Acute Respiratory Distress & Hypoxia (Critical)"
    ):
        self.ambulance_id = ambulance_id
        self.start_location = (initial_location or DEFAULT_START_LOCATION).model_copy(deep=True)
        self.current_location = self.start_location.model_copy(deep=True)
        
        self.scenario_key = scenario_key
        self.scenario = PRESET_SCENARIOS.get(scenario_key, list(PRESET_SCENARIOS.values())[0])
        self.patient_info = self.scenario["patient"].model_copy(deep=True)
        self.current_vitals = self.scenario["vitals"].model_copy(deep=True)
        
        # Transit & Routing State
        self.destination_hospital_id: Optional[str] = None
        self.destination_hospital_name: Optional[str] = None
        self.destination_location: Optional[GeoPoint] = None
        self.initial_eta_minutes: float = 10.0
        self.current_eta_minutes: float = 10.0
        self.acknowledgment: Optional[HospitalAcknowledgment] = None
        
        # State Machine: DISPATCHED -> EN_ROUTE -> ARRIVED
        self.status: str = "DISPATCHED"
        self.progress_ratio: float = 0.0
        self.step_count: int = 0

    def set_scenario(self, scenario_key: str):
        """Switch to a specific preset patient scenario."""
        if scenario_key in PRESET_SCENARIOS:
            self.scenario_key = scenario_key
            self.scenario = PRESET_SCENARIOS[scenario_key]
            self.patient_info = self.scenario["patient"].model_copy(deep=True)
            self.current_vitals = self.scenario["vitals"].model_copy(deep=True)
            self.reset()

    def set_destination(
        self,
        hospital_id: str,
        hospital_name: str,
        destination_location: GeoPoint,
        eta_minutes: float,
        acknowledgment: Optional[HospitalAcknowledgment] = None
    ):
        """Configure the destination hospital after decision-engine selection."""
        self.destination_hospital_id = hospital_id
        self.destination_hospital_name = hospital_name
        self.destination_location = destination_location.model_copy(deep=True)
        self.initial_eta_minutes = max(0.5, float(eta_minutes))
        self.current_eta_minutes = self.initial_eta_minutes
        self.acknowledgment = acknowledgment
        
        self.start_location = self.current_location.model_copy(deep=True)
        self.progress_ratio = 0.0
        self.status = "DISPATCHED"
        self.step_count = 0

    def generate_next_vitals(self, trend: str = "fluctuate") -> PatientVitals:
        """
        Simulates subtle live IoT sensor noise and physiologic vital drift.
        """
        v = self.current_vitals
        
        if trend == "fluctuate":
            # Realistic physiological micro-variations
            spo2_delta = random.choice([-0.3, -0.1, 0.0, 0.1, 0.2])
            hr_delta = random.randint(-2, 2)
            sbp_delta = random.randint(-2, 2)
            dbp_delta = random.randint(-1, 1)
            temp_delta = round(random.choice([-0.05, 0.0, 0.05]), 2)
        elif trend == "deteriorate":
            spo2_delta = -0.5
            hr_delta = random.randint(1, 3)
            sbp_delta = -random.randint(1, 3)
            dbp_delta = -random.randint(1, 2)
            temp_delta = 0.1
        else:  # "improve"
            spo2_delta = 0.4
            hr_delta = -random.randint(1, 3)
            sbp_delta = random.randint(1, 2)
            dbp_delta = random.randint(1, 2)
            temp_delta = -0.05

        new_spo2 = max(65.0, min(100.0, round(v.spo2 + spo2_delta, 1)))
        new_hr = max(40, min(220, v.heart_rate + hr_delta))
        new_sbp = max(55, min(240, v.systolic_bp + sbp_delta))
        new_dbp = max(35, min(140, v.diastolic_bp + dbp_delta))
        new_temp = max(35.0, min(42.0, round(v.temperature + temp_delta, 1)))

        self.current_vitals = PatientVitals(
            spo2=new_spo2,
            heart_rate=new_hr,
            systolic_bp=new_sbp,
            diastolic_bp=new_dbp,
            temperature=new_temp,
            recorded_at=datetime.utcnow().isoformat()
        )
        return self.current_vitals

    def step_simulation(
        self,
        step_fraction: float = 0.10,
        trend: str = "fluctuate",
        backend_url: Optional[str] = None
    ) -> AmbulanceTelemetry:
        """
        Advances the simulation by one telemetry step:
        1. Slightly updates vital signs.
        2. Interpolates GPS coordinates toward destination hospital.
        3. Updates ETA and transit progress.
        4. Transitions state machine: DISPATCHED -> EN_ROUTE -> ARRIVED.
        5. Synchronizes telemetry with FastAPI backend if URL provided.
        """
        self.step_count += 1
        
        # 1. Update Vitals
        self.generate_next_vitals(trend=trend)
        
        # 2. Advance GPS coordinates and ETA if destination is set
        if self.destination_location is not None:
            self.progress_ratio = min(1.0, round(self.progress_ratio + step_fraction, 4))
            
            s_lat = self.start_location.latitude
            s_lon = self.start_location.longitude
            d_lat = self.destination_location.latitude
            d_lon = self.destination_location.longitude
            
            curr_lat = round(s_lat + (d_lat - s_lat) * self.progress_ratio, 5)
            curr_lon = round(s_lon + (d_lon - s_lon) * self.progress_ratio, 5)
            
            pct = int(self.progress_ratio * 100)
            
            if self.progress_ratio >= 1.0:
                self.status = "ARRIVED"
                self.current_eta_minutes = 0.0
                curr_address = f"ARRIVED at {self.destination_hospital_name or 'Hospital'}"
            else:
                self.status = "EN_ROUTE"
                self.current_eta_minutes = round(max(0.1, self.initial_eta_minutes * (1.0 - self.progress_ratio)), 1)
                curr_address = f"In Transit - {pct}% to {self.destination_hospital_name or 'Hospital'}"
                
            self.current_location = GeoPoint(
                latitude=curr_lat,
                longitude=curr_lon,
                address=curr_address
            )
        else:
            self.status = "DISPATCHED"
            self.current_eta_minutes = self.initial_eta_minutes

        # 3. Construct Telemetry Payload
        telemetry = AmbulanceTelemetry(
            ambulance_id=self.ambulance_id,
            patient_info=self.patient_info,
            current_vitals=self.current_vitals,
            current_location=self.current_location,
            status=self.status,
            destination_hospital_id=self.destination_hospital_id,
            destination_hospital_name=self.destination_hospital_name,
            current_eta_minutes=self.current_eta_minutes,
            progress_percentage=round(self.progress_ratio * 100.0, 1),
            acknowledgment=self.acknowledgment,
            last_updated=datetime.utcnow().isoformat()
        )
        
        # 4. Sync with Backend
        if backend_url:
            self.send_telemetry_to_backend(telemetry, backend_url)
            
        return telemetry

    def send_telemetry_to_backend(
        self,
        telemetry: Optional[AmbulanceTelemetry] = None,
        backend_url: str = "http://127.0.0.1:8000"
    ) -> bool:
        """Transmits current telemetry to POST /api/telemetry/update."""
        tel = telemetry or self.get_telemetry()
        try:
            url = f"{backend_url.rstrip('/')}/api/telemetry/update"
            resp = requests.post(url, json=tel.model_dump(), timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def get_telemetry(self) -> AmbulanceTelemetry:
        """Builds current telemetry snapshot."""
        return AmbulanceTelemetry(
            ambulance_id=self.ambulance_id,
            patient_info=self.patient_info,
            current_vitals=self.current_vitals,
            current_location=self.current_location,
            status=self.status,
            destination_hospital_id=self.destination_hospital_id,
            destination_hospital_name=self.destination_hospital_name,
            current_eta_minutes=self.current_eta_minutes,
            progress_percentage=round(self.progress_ratio * 100.0, 1),
            acknowledgment=self.acknowledgment,
            last_updated=datetime.utcnow().isoformat()
        )

    def reset(self):
        """Resets the simulator state back to initial dispatch baseline."""
        self.current_location = self.start_location.model_copy(deep=True)
        self.scenario = PRESET_SCENARIOS.get(self.scenario_key, list(PRESET_SCENARIOS.values())[0])
        self.patient_info = self.scenario["patient"].model_copy(deep=True)
        self.current_vitals = self.scenario["vitals"].model_copy(deep=True)
        self.progress_ratio = 0.0
        self.status = "DISPATCHED"
        self.step_count = 0
        if self.destination_location is not None:
            self.current_eta_minutes = self.initial_eta_minutes


def run_standalone_simulation(
    backend_url: str = "http://127.0.0.1:8000",
    interval_seconds: float = 2.0
):
    """
    Console loop for standalone ambulance transmitter testing with live movement.
    """
    sim = AmbulanceSimulator()
    print("=" * 70)
    print(f"VITAVIA AMBULANCE TELEMETRY SIMULATOR [{sim.ambulance_id}]")
    print(f"Connecting to Backend: {backend_url}")
    print("=" * 70)

    # 1. Trigger dispatch decision
    try:
        dispatch_payload = {
            "ambulance_id": sim.ambulance_id,
            "patient_info": sim.patient_info.model_dump(),
            "vitals": sim.current_vitals.model_dump(),
            "location": sim.current_location.model_dump()
        }
        res = requests.post(f"{backend_url}/api/dispatch", json=dispatch_payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            selected = data["selection"]["selected_hospital"]
            route = data["selection"]["selected_route"]
            ack = data["acknowledgment"]
            
            sim.set_destination(
                hospital_id=selected["id"],
                hospital_name=selected["name"],
                destination_location=GeoPoint(
                    latitude=selected["location"]["latitude"],
                    longitude=selected["location"]["longitude"]
                ),
                eta_minutes=route["eta_minutes"],
                acknowledgment=HospitalAcknowledgment(**ack)
            )
            print(f"[DISPATCH OK] Destination: {selected['name']} (ETA: {route['eta_minutes']} min)")
            print(f"[HANDSHAKE OK] {ack['message']}")
        else:
            print(f"[ERR] Dispatch API returned {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[ERR] Could not connect to backend: {e}")

    # 2. Continuous telemetry loop (Step until arrived)
    print("\nStarting live telemetry broadcasting loop...")
    while True:
        tel = sim.step_simulation(step_fraction=0.10, backend_url=backend_url)
        v = tel.current_vitals
        loc = tel.current_location
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Step {sim.step_count:02d} | "
            f"Status: {tel.status:10s} | "
            f"Progress: {tel.progress_percentage:5.1f}% | "
            f"ETA: {tel.current_eta_minutes:4.1f}m | "
            f"SpO2: {v.spo2:4.1f}% | HR: {v.heart_rate:3d} bpm | BP: {v.systolic_bp}/{v.diastolic_bp} | "
            f"GPS: ({loc.latitude:.4f}, {loc.longitude:.4f})"
        )
        if tel.status == "ARRIVED":
            print(f"\n[GOAL REACHED] Ambulance has arrived at {sim.destination_hospital_name}!")
            break
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_standalone_simulation()
