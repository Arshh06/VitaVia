"""Deterministic in-memory simulation for one VITAVIA emergency."""

from app.models.schemas import Ambulance, EmergencySnapshot, GPSLocation, Patient, VitalSigns


INITIAL_LOCATION = GPSLocation(latitude=12.9716, longitude=77.5946)
INITIAL_VITALS = VitalSigns(
    spo2=89.0,
    heart_rate=122,
    systolic_bp=90,
    diastolic_bp=60,
    temperature=38.1,
)

VITAL_UPDATE_CYCLE = (
    {"spo2": 1.0, "heart_rate": 2, "systolic_bp": 1, "diastolic_bp": 1, "temperature": 0.1},
    {"spo2": -1.0, "heart_rate": -3, "systolic_bp": -2, "diastolic_bp": -1, "temperature": -0.1},
    {"spo2": 0.0, "heart_rate": 1, "systolic_bp": 2, "diastolic_bp": 0, "temperature": 0.0},
    {"spo2": -1.0, "heart_rate": 0, "systolic_bp": -1, "diastolic_bp": -1, "temperature": 0.1},
)


class SimulationService:
    """Maintain deterministic simulated ambulance, patient, and vital-sign state."""

    def __init__(self) -> None:
        self.reset_simulation()

    def get_current_snapshot(self) -> EmergencySnapshot:
        """Return a copy of the current simulated emergency state."""
        return EmergencySnapshot(
            ambulance=self._ambulance.model_copy(deep=True),
            patient=self._patient.model_copy(deep=True),
            vitals=self._vitals.model_copy(deep=True),
        )

    def update_vitals(self) -> VitalSigns:
        """Advance vitals by one small, bounded, deterministic simulation step."""
        change = VITAL_UPDATE_CYCLE[self._vital_update_index % len(VITAL_UPDATE_CYCLE)]
        self._vital_update_index += 1

        self._vitals = VitalSigns(
            spo2=self._clamp(self._vitals.spo2 + change["spo2"], 75.0, 100.0),
            heart_rate=int(self._clamp(self._vitals.heart_rate + change["heart_rate"], 40, 180)),
            systolic_bp=int(self._clamp(self._vitals.systolic_bp + change["systolic_bp"], 70, 180)),
            diastolic_bp=int(self._clamp(self._vitals.diastolic_bp + change["diastolic_bp"], 40, 120)),
            temperature=round(self._clamp(self._vitals.temperature + change["temperature"], 34.0, 42.0), 1),
        )
        return self._vitals.model_copy(deep=True)

    def set_vitals(self, vitals: VitalSigns) -> VitalSigns:
        """Replace current vital signs from the prototype's manual dashboard input."""
        self._vitals = vitals.model_copy(deep=True)
        return self._vitals.model_copy(deep=True)

    def update_location(self) -> GPSLocation:
        """Move the simulated ambulance by a small fixed coordinate increment."""
        self._ambulance.location = GPSLocation(
            latitude=round(self._ambulance.location.latitude + 0.0002, 7),
            longitude=round(self._ambulance.location.longitude + 0.0002, 7),
        )
        return self._ambulance.location.model_copy(deep=True)

    def set_location(self, location: GPSLocation) -> GPSLocation:
        """Set the shared simulated ambulance GPS position from a journey update."""
        self._ambulance.location = location.model_copy(deep=True)
        return self._ambulance.location.model_copy(deep=True)

    def set_ambulance_status(self, status: str) -> Ambulance:
        """Set the shared ambulance status from a controlled simulation transition."""
        self._ambulance.status = status
        return self._ambulance.model_copy(deep=True)

    def reset_simulation(self) -> EmergencySnapshot:
        """Restore the one emergency simulation to its initial demo values."""
        self._ambulance = Ambulance(
            ambulance_id="AMB001",
            status="PATIENT_ONBOARD",
            location=INITIAL_LOCATION.model_copy(deep=True),
        )
        self._patient = Patient(
            patient_id="PAT001",
            age=45,
            gender="Male",
            emergency_type="Respiratory distress",
        )
        self._vitals = INITIAL_VITALS.model_copy(deep=True)
        self._vital_update_index = 0
        return self.get_current_snapshot()

    @staticmethod
    def _clamp(value: float, lower_bound: float, upper_bound: float) -> float:
        """Keep prototype values inside their defined simulation boundaries."""
        return max(lower_bound, min(value, upper_bound))


simulation_service = SimulationService()
