"""Centralized SQLite history writes for VITAVIA's simulated events.

Live simulation, triage, routing, and selection remain in memory. This service only
observes their completed results for prototype history and audit demonstrations.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import delete, select

from app.db import database
from app.db.models import (
    AmbulanceLocationRecord,
    EmergencyRecord,
    HospitalEvaluationRecord,
    VitalReadingRecord,
)
from app.models.schemas import (
    Acknowledgement,
    EmergencySnapshot,
    HospitalDecision,
    JourneyState,
    TriageResult,
)


class PersistenceError(Exception):
    """Raised when an expected simulated emergency record cannot be found."""


def _utc_now() -> datetime:
    """Return one timezone-aware timestamp for a simulated audit event."""
    return datetime.now(timezone.utc)


class PersistenceService:
    """Track the active in-memory session ID and save completed operation results."""

    def __init__(self) -> None:
        self._current_emergency_id: Optional[str] = None

    @property
    def current_emergency_id(self) -> Optional[str]:
        """Expose the non-persistent association for API orchestration only."""
        return self._current_emergency_id

    def clear_active_emergency(self) -> None:
        """Forget only the in-memory active-session association (useful for tests/restarts)."""
        self._current_emergency_id = None

    def ensure_active_emergency(self, snapshot: EmergencySnapshot) -> str:
        """Lazily create an audit record when an operational endpoint first needs one."""
        if self._current_emergency_id is not None:
            with database.session_scope() as session:
                record = session.scalar(
                    select(EmergencyRecord).where(
                        EmergencyRecord.emergency_id == self._current_emergency_id
                    )
                )
                if record is not None:
                    return record.emergency_id
            self._current_emergency_id = None
        return self.create_emergency(snapshot)

    def start_new_emergency(self, snapshot: EmergencySnapshot) -> str:
        """Close an unfinished audit session on reset, then create the next simulated session."""
        if self._current_emergency_id is not None:
            with database.session_scope() as session:
                record = _require_emergency(session, self._current_emergency_id)
                if record.status != "ARRIVED" and record.completed_at is None:
                    record.status = "RESET"
                    record.completed_at = _utc_now()
        self._current_emergency_id = None
        return self.create_emergency(snapshot)

    def create_emergency(self, snapshot: EmergencySnapshot) -> str:
        """Create a unique simulated emergency record with its initial vital and GPS readings."""
        emergency_id = _new_emergency_id()
        recorded_at = _utc_now()
        with database.session_scope() as session:
            session.add(
                EmergencyRecord(
                    emergency_id=emergency_id,
                    ambulance_id=snapshot.ambulance.ambulance_id,
                    patient_id=snapshot.patient.patient_id,
                    emergency_type=snapshot.patient.emergency_type,
                    status="ACTIVE",
                    started_at=recorded_at,
                )
            )
            _add_vital_reading(session, emergency_id, snapshot, recorded_at)
            _add_location_reading(session, emergency_id, snapshot, None, recorded_at)
        self._current_emergency_id = emergency_id
        return emergency_id

    def save_triage(self, emergency_id: str, triage: TriageResult) -> None:
        """Update the compact triage summary for an already-created emergency."""
        with database.session_scope() as session:
            record = _require_emergency(session, emergency_id)
            record.triage_severity = triage.severity
            record.triage_source = triage.source
            record.required_infrastructure = list(triage.required_infrastructure)
            record.triage_explanation = triage.explanation

    def save_decision(
        self,
        emergency_id: str,
        triage: TriageResult,
        decisions: list[HospitalDecision],
        selected_hospital: Optional[HospitalDecision],
        acknowledgement: Acknowledgement,
    ) -> None:
        """Replace the current evaluation snapshot so repeated decisions do not create duplicates."""
        with database.session_scope() as session:
            record = _require_emergency(session, emergency_id)
            _apply_triage(record, triage)
            record.selected_hospital_id = (
                selected_hospital.hospital_id if selected_hospital else None
            )
            record.selected_hospital_name = selected_hospital.name if selected_hospital else None
            record.acknowledgement_status = acknowledgement.status
            record.routing_source = selected_hospital.routing_source if selected_hospital else None
            record.initial_eta_minutes = selected_hospital.eta_minutes if selected_hospital else None
            if record.status not in {"EN_ROUTE", "ARRIVING", "ARRIVED"}:
                record.status = "DECIDED"

            session.execute(
                delete(HospitalEvaluationRecord).where(
                    HospitalEvaluationRecord.emergency_id == emergency_id
                )
            )
            for decision in decisions:
                session.add(
                    HospitalEvaluationRecord(
                        emergency_id=emergency_id,
                        hospital_id=decision.hospital_id,
                        hospital_name=decision.name,
                        eligible=decision.eligible,
                        missing_infrastructure=list(decision.missing_infrastructure),
                        distance_km=decision.distance_km,
                        traffic_condition=decision.traffic_condition,
                        eta_minutes=decision.eta_minutes,
                        routing_source=decision.routing_source,
                        selected=decision.selected,
                        acknowledgement_status=decision.acknowledgement_status,
                    )
                )

    def save_simulation_update(self, emergency_id: str, snapshot: EmergencySnapshot) -> None:
        """Append ordinary simulated vital and location changes to the audit timeline."""
        self._save_snapshot(emergency_id, snapshot, None)

    def save_vitals(self, emergency_id: str, snapshot: EmergencySnapshot) -> None:
        """Append a manual patient-vital reading without creating a duplicate GPS event."""
        recorded_at = _utc_now()
        with database.session_scope() as session:
            _require_emergency(session, emergency_id)
            _add_vital_reading(session, emergency_id, snapshot, recorded_at)

    def save_journey_start(
        self, emergency_id: str, snapshot: EmergencySnapshot, journey: JourneyState
    ) -> None:
        """Record a fixed accepted destination and its step-zero timeline state."""
        recorded_at = _utc_now()
        with database.session_scope() as session:
            record = _require_emergency(session, emergency_id)
            record.status = journey.status
            record.selected_hospital_id = journey.selected_hospital_id
            record.selected_hospital_name = journey.selected_hospital_name
            record.acknowledgement_status = journey.acknowledgement_status
            record.routing_source = journey.routing_source
            record.initial_eta_minutes = journey.initial_eta_minutes
            _add_vital_reading(session, emergency_id, snapshot, recorded_at)
            _add_location_reading(session, emergency_id, snapshot, journey, recorded_at)

    def save_journey_update(
        self, emergency_id: str, snapshot: EmergencySnapshot, journey: JourneyState
    ) -> None:
        """Append one active journey step; arrival marks its simulated emergency complete."""
        recorded_at = _utc_now()
        with database.session_scope() as session:
            record = _require_emergency(session, emergency_id)
            record.status = journey.status
            if journey.status == "ARRIVED" and record.completed_at is None:
                record.completed_at = recorded_at
            _add_vital_reading(session, emergency_id, snapshot, recorded_at)
            _add_location_reading(session, emergency_id, snapshot, journey, recorded_at)

    def get_emergency_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return newest simulated emergency summaries first, without integer database IDs."""
        safe_limit = min(max(limit, 1), 100)
        with database.session_scope() as session:
            records = session.scalars(
                select(EmergencyRecord)
                .order_by(EmergencyRecord.started_at.desc())
                .limit(safe_limit)
            ).all()
            return [_history_summary(record) for record in records]

    def get_emergency_details(self, emergency_id: str) -> Optional[dict[str, Any]]:
        """Return the stored simulation timeline and latest candidate-evaluation snapshot."""
        with database.session_scope() as session:
            record = session.scalar(
                select(EmergencyRecord).where(EmergencyRecord.emergency_id == emergency_id)
            )
            if record is None:
                return None
            evaluations = session.scalars(
                select(HospitalEvaluationRecord)
                .where(HospitalEvaluationRecord.emergency_id == emergency_id)
                .order_by(HospitalEvaluationRecord.hospital_id)
            ).all()
            vitals = session.scalars(
                select(VitalReadingRecord)
                .where(VitalReadingRecord.emergency_id == emergency_id)
                .order_by(VitalReadingRecord.id)
            ).all()
            locations = session.scalars(
                select(AmbulanceLocationRecord)
                .where(AmbulanceLocationRecord.emergency_id == emergency_id)
                .order_by(AmbulanceLocationRecord.id)
            ).all()
            return {
                "emergency": _history_summary(record),
                "required_infrastructure": record.required_infrastructure or [],
                "triage_explanation": record.triage_explanation,
                "hospital_evaluations": [_evaluation_item(item) for item in evaluations],
                "vital_history": [_vital_item(item) for item in vitals],
                "location_history": [_location_item(item) for item in locations],
            }

    def _save_snapshot(
        self,
        emergency_id: str,
        snapshot: EmergencySnapshot,
        journey: Optional[JourneyState],
    ) -> None:
        """Append matching vital and GPS entries in one short database transaction."""
        recorded_at = _utc_now()
        with database.session_scope() as session:
            _require_emergency(session, emergency_id)
            _add_vital_reading(session, emergency_id, snapshot, recorded_at)
            _add_location_reading(session, emergency_id, snapshot, journey, recorded_at)


def _new_emergency_id() -> str:
    """Create a user-independent ID distinct from reusable ambulance and patient identifiers."""
    return f"EMG-{uuid4().hex[:8].upper()}"


def _require_emergency(session, emergency_id: str) -> EmergencyRecord:
    """Load a record inside an existing transaction or fail with a safe service error."""
    record = session.scalar(
        select(EmergencyRecord).where(EmergencyRecord.emergency_id == emergency_id)
    )
    if record is None:
        raise PersistenceError("The simulated emergency history record was not found.")
    return record


def _apply_triage(record: EmergencyRecord, triage: TriageResult) -> None:
    """Copy normalized triage fields into the compact emergency summary."""
    record.triage_severity = triage.severity
    record.triage_source = triage.source
    record.required_infrastructure = list(triage.required_infrastructure)
    record.triage_explanation = triage.explanation


def _add_vital_reading(session, emergency_id: str, snapshot: EmergencySnapshot, recorded_at: datetime) -> None:
    """Append one simulated vital-sign event using only current in-memory snapshot values."""
    vitals = snapshot.vitals
    session.add(
        VitalReadingRecord(
            emergency_id=emergency_id,
            recorded_at=recorded_at,
            spo2=vitals.spo2,
            heart_rate=vitals.heart_rate,
            systolic_bp=vitals.systolic_bp,
            diastolic_bp=vitals.diastolic_bp,
            temperature=vitals.temperature,
        )
    )


def _add_location_reading(
    session,
    emergency_id: str,
    snapshot: EmergencySnapshot,
    journey: Optional[JourneyState],
    recorded_at: datetime,
) -> None:
    """Append one simulated ambulance GPS event, optionally carrying journey progress."""
    location = snapshot.ambulance.location
    session.add(
        AmbulanceLocationRecord(
            emergency_id=emergency_id,
            recorded_at=recorded_at,
            latitude=location.latitude,
            longitude=location.longitude,
            ambulance_status=snapshot.ambulance.status,
            journey_status=journey.status if journey else None,
            progress_percent=journey.progress_percent if journey else None,
            remaining_eta_minutes=journey.remaining_eta_minutes if journey else None,
        )
    )


def _history_summary(record: EmergencyRecord) -> dict[str, Any]:
    """Serialize only explicit, safe public history fields."""
    return {
        "emergency_id": record.emergency_id,
        "ambulance_id": record.ambulance_id,
        "patient_id": record.patient_id,
        "emergency_type": record.emergency_type,
        "status": record.status,
        "started_at": _as_utc(record.started_at),
        "completed_at": _as_utc(record.completed_at),
        "selected_hospital_id": record.selected_hospital_id,
        "selected_hospital_name": record.selected_hospital_name,
        "acknowledgement_status": record.acknowledgement_status,
        "triage_severity": record.triage_severity,
        "triage_source": record.triage_source,
        "routing_source": record.routing_source,
        "initial_eta_minutes": record.initial_eta_minutes,
    }


def _evaluation_item(record: HospitalEvaluationRecord) -> dict[str, Any]:
    """Serialize a latest evaluation row without leaking its internal integer ID."""
    return {
        "hospital_id": record.hospital_id,
        "hospital_name": record.hospital_name,
        "eligible": record.eligible,
        "missing_infrastructure": record.missing_infrastructure or [],
        "distance_km": record.distance_km,
        "traffic_condition": record.traffic_condition,
        "eta_minutes": record.eta_minutes,
        "routing_source": record.routing_source,
        "selected": record.selected,
        "acknowledgement_status": record.acknowledgement_status,
    }


def _vital_item(record: VitalReadingRecord) -> dict[str, Any]:
    """Serialize one simulated vital reading."""
    return {
        "recorded_at": _as_utc(record.recorded_at),
        "spo2": record.spo2,
        "heart_rate": record.heart_rate,
        "systolic_bp": record.systolic_bp,
        "diastolic_bp": record.diastolic_bp,
        "temperature": record.temperature,
    }


def _location_item(record: AmbulanceLocationRecord) -> dict[str, Any]:
    """Serialize one simulated GPS/journey reading."""
    return {
        "recorded_at": _as_utc(record.recorded_at),
        "latitude": record.latitude,
        "longitude": record.longitude,
        "ambulance_status": record.ambulance_status,
        "journey_status": record.journey_status,
        "progress_percent": record.progress_percent,
        "remaining_eta_minutes": record.remaining_eta_minutes,
    }


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Restore explicit UTC metadata after SQLite's timezone-less datetime storage."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


persistence_service = PersistenceService()
