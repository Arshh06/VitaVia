"""Fixed-step in-memory ambulance journey simulation for VITAVIA."""

from typing import Optional

from app.data.hospitals import get_all_hospitals
from app.models.schemas import (
    Acknowledgement,
    EmergencySnapshot,
    GPSLocation,
    HospitalDecision,
    JourneyState,
)
from app.services.simulation_service import simulation_service


TOTAL_JOURNEY_STEPS = 10


class JourneyStartError(Exception):
    """Raised when the backend has no accepted decision from which to start a journey."""


class JourneyService:
    """Maintain one fixed-destination journey without recalculating clinical or route decisions."""

    def __init__(self) -> None:
        self._journey: Optional[JourneyState] = None

    def get_status(self) -> JourneyState:
        """Return current journey state, including the safe normal no-journey state."""
        if self._journey is not None:
            return self._journey.model_copy(deep=True)
        snapshot = simulation_service.get_current_snapshot()
        return JourneyState(
            active=False,
            ambulance_id=snapshot.ambulance.ambulance_id,
            patient_id=snapshot.patient.patient_id,
            start_location=snapshot.ambulance.location,
            current_location=snapshot.ambulance.location,
            progress_percent=0.0,
            status="NOT_STARTED",
            step_number=0,
            acknowledgement_status="NOT_REQUESTED",
        )

    def start_journey(
        self,
        snapshot: EmergencySnapshot,
        selected_hospital: Optional[HospitalDecision],
        acknowledgement: Acknowledgement,
    ) -> JourneyState:
        """Fix a journey destination from an already selected and accepted backend decision."""
        if self._journey is not None and self._journey.active:
            raise JourneyStartError("An ambulance journey is already active.")
        if selected_hospital is None or acknowledgement.status != "ACCEPTED":
            raise JourneyStartError("No accepted hospital decision is available for this journey.")
        if selected_hospital.eta_minutes is None or selected_hospital.eta_minutes <= 0:
            raise JourneyStartError("The selected hospital does not have a usable route ETA.")

        destination = _find_hospital_location(selected_hospital.hospital_id)
        start_location = snapshot.ambulance.location.model_copy(deep=True)
        self._journey = JourneyState(
            active=True,
            ambulance_id=snapshot.ambulance.ambulance_id,
            patient_id=snapshot.patient.patient_id,
            selected_hospital_id=selected_hospital.hospital_id,
            selected_hospital_name=selected_hospital.name,
            start_location=start_location,
            current_location=start_location.model_copy(deep=True),
            destination_location=destination,
            initial_eta_minutes=selected_hospital.eta_minutes,
            remaining_eta_minutes=selected_hospital.eta_minutes,
            progress_percent=0.0,
            status="EN_ROUTE",
            step_number=0,
            acknowledgement_status=acknowledgement.status,
            routing_source=selected_hospital.routing_source,
        )
        simulation_service.set_ambulance_status("EN_ROUTE")
        return self.get_status()

    def advance_journey(self) -> JourneyState:
        """Advance one deterministic visual journey step and synchronize shared GPS and vitals."""
        if self._journey is None or not self._journey.active:
            return self.get_status()

        next_step = min(self._journey.step_number + 1, TOTAL_JOURNEY_STEPS)
        fraction = next_step / TOTAL_JOURNEY_STEPS
        destination = self._journey.destination_location
        if destination is None:
            raise JourneyStartError("Active journey is missing a destination.")

        if next_step == TOTAL_JOURNEY_STEPS:
            current_location = destination.model_copy(deep=True)
        else:
            current_location = _interpolate_location(
                self._journey.start_location, destination, fraction
            )
        progress_percent = round(fraction * 100, 1)
        remaining_eta = round(
            max(self._journey.initial_eta_minutes * (1 - fraction), 0.0), 2
        )
        status = "ARRIVED" if next_step == TOTAL_JOURNEY_STEPS else (
            "ARRIVING" if progress_percent >= 80 else "EN_ROUTE"
        )
        active = status != "ARRIVED"

        self._journey = self._journey.model_copy(
            update={
                "active": active,
                "current_location": current_location,
                "remaining_eta_minutes": remaining_eta,
                "progress_percent": progress_percent,
                "status": status,
                "step_number": next_step,
            }
        )
        simulation_service.set_location(current_location)
        simulation_service.set_ambulance_status(
            "ARRIVED_AT_HOSPITAL" if status == "ARRIVED" else status
        )
        simulation_service.update_vitals()
        return self.get_status()

    def reset_journey(self) -> JourneyState:
        """Clear journey state after the simulation is reset or a new demo begins."""
        self._journey = None
        return self.get_status()


def _find_hospital_location(hospital_id: str) -> GPSLocation:
    """Find a fictional destination location using only static simulated hospital data."""
    for hospital in get_all_hospitals():
        if hospital.hospital_id == hospital_id:
            return hospital.location.model_copy(deep=True)
    raise JourneyStartError("The selected simulated hospital no longer exists.")


def _interpolate_location(
    start: GPSLocation, destination: GPSLocation, fraction: float
) -> GPSLocation:
    """Prototype linear GPS interpolation only — not actual road geometry."""
    return GPSLocation(
        latitude=round(start.latitude + (destination.latitude - start.latitude) * fraction, 7),
        longitude=round(start.longitude + (destination.longitude - start.longitude) * fraction, 7),
    )


journey_service = JourneyService()
