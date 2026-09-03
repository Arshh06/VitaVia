"""System and simulation endpoints for the VITAVIA backend."""

import logging
from typing import Callable, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from app.data.hospitals import get_all_hospitals
from app.models.schemas import (
    EmergencyDecisionResponse,
    EmergencyHistoryDetail,
    EmergencyHistoryItem,
    EmergencySnapshot,
    Hospital,
    IncomingEmergencyRequest,
    IncomingEmergencyResponse,
    JourneyState,
    JourneyUpdateResponse,
    TriageResult,
    VitalSigns,
)
from app.services.gemini_service import is_gemini_configured
from app.services.journey_service import JourneyStartError, journey_service
from app.services.incoming_emergency_service import incoming_emergency_service
from app.services.persistence_service import PersistenceError, persistence_service
from app.services.routing_service import is_google_maps_configured
from app.services.selection_service import run_decision_pipeline
from app.services.simulation_service import simulation_service
from app.services.triage_service import analyze_vitals_assisted

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


def _ensure_persistence_session(snapshot: EmergencySnapshot) -> Optional[str]:
    """Create a history session lazily without making operational endpoints depend on SQLite."""
    try:
        return persistence_service.ensure_active_emergency(snapshot)
    except (PersistenceError, SQLAlchemyError):
        logger.warning("SQLite history is unavailable; continuing with in-memory simulation.")
        return None


def _persist_safely(operation: Callable, *args: object) -> None:
    """Save operational results best-effort without exposing database details to clients."""
    try:
        operation(*args)
    except (PersistenceError, SQLAlchemyError):
        logger.warning("SQLite history write failed; continuing with in-memory simulation.")


@router.get("/")
def root() -> dict[str, str]:
    """Provide a small welcome response for the backend root URL."""
    return {"message": "Welcome to VITAVIA"}


@router.get("/health")
def health_check() -> dict[str, str]:
    """Report whether the backend service is running."""
    return {"status": "ok", "service": "VITAVIA Backend"}


@router.get("/simulation/snapshot", response_model=EmergencySnapshot)
def get_simulation_snapshot() -> EmergencySnapshot:
    """Return the current simulated ambulance emergency state."""
    return simulation_service.get_current_snapshot()


@router.post("/simulation/update", response_model=EmergencySnapshot)
def update_simulation() -> EmergencySnapshot:
    """Advance simulated vitals and ambulance location by one small step."""
    simulation_service.update_vitals()
    simulation_service.update_location()
    snapshot = simulation_service.get_current_snapshot()
    emergency_id = _ensure_persistence_session(snapshot)
    if emergency_id is not None:
        _persist_safely(persistence_service.save_simulation_update, emergency_id, snapshot)
    return snapshot


@router.post("/simulation/vitals", response_model=EmergencySnapshot)
def set_simulation_vitals(vitals: VitalSigns) -> EmergencySnapshot:
    """Save manually entered prototype vitals without analyzing, routing, or moving GPS."""
    journey = journey_service.get_status()
    if journey.active or journey.status == "ARRIVED":
        raise HTTPException(
            status_code=409,
            detail="Manual vital updates are unavailable after a journey has started. Reset the emergency first.",
        )

    # Ensure a lazily created session retains the default initial reading before this manual update.
    emergency_id = _ensure_persistence_session(simulation_service.get_current_snapshot())
    simulation_service.set_vitals(vitals)
    snapshot = simulation_service.get_current_snapshot()
    if emergency_id is not None:
        _persist_safely(persistence_service.save_vitals, emergency_id, snapshot)
    return snapshot


@router.post("/simulation/reset", response_model=EmergencySnapshot)
def reset_simulation() -> EmergencySnapshot:
    """Restore the simulated emergency to its initial demo state."""
    snapshot = simulation_service.reset_simulation()
    journey_service.reset_journey()
    try:
        persistence_service.start_new_emergency(snapshot)
    except (PersistenceError, SQLAlchemyError):
        logger.warning("SQLite history reset failed; continuing with in-memory simulation.")
    return snapshot


@router.get("/hospitals", response_model=list[Hospital])
def list_hospitals() -> list[Hospital]:
    """Return all fictional simulated hospitals without filtering or selection."""
    return get_all_hospitals()


@router.post(
    "/analysis",
    response_model=TriageResult,
    description="Optional Gemini-assisted triage with deterministic fallback for this prototype.",
)
def analyze_current_emergency() -> TriageResult:
    """Analyze current simulated vitals without performing hospital selection."""
    snapshot = simulation_service.get_current_snapshot()
    triage = analyze_vitals_assisted(
        snapshot.vitals, emergency_type=snapshot.patient.emergency_type
    )
    emergency_id = _ensure_persistence_session(snapshot)
    if emergency_id is not None:
        _persist_safely(persistence_service.save_triage, emergency_id, triage)
    return triage


@router.get("/ai/status")
def get_ai_status() -> dict[str, object]:
    """Report the safe AI-analysis mode without exposing any credentials."""
    gemini_configured = is_gemini_configured()
    return {
        "gemini_configured": gemini_configured,
        "mode": (
            "gemini_with_deterministic_guard"
            if gemini_configured
            else "deterministic_fallback"
        ),
    }


@router.get("/routing/status")
def get_routing_status() -> dict[str, object]:
    """Report the active routing mode without exposing the Maps API key."""
    google_maps_configured = is_google_maps_configured()
    return {
        "google_maps_configured": google_maps_configured,
        "active_mode": (
            "google_maps_with_mock_fallback" if google_maps_configured else "mock"
        ),
    }


@router.get("/database/status")
def get_database_status() -> dict[str, object]:
    """Report local SQLite readiness without disclosing a filesystem path or credentials."""
    try:
        from app.db.database import init_db

        init_db()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="SQLite history is unavailable.")
    return {"database": "sqlite", "configured": True, "status": "ready"}


@router.get("/journey/status", response_model=JourneyState)
def get_journey_status() -> JourneyState:
    """Return current journey state without treating no journey as an error."""
    return journey_service.get_status()


@router.post("/journey/start", response_model=JourneyState)
def start_journey() -> JourneyState:
    """Start a fixed journey from the backend's own current accepted decision."""
    snapshot = simulation_service.get_current_snapshot()
    emergency_id = _ensure_persistence_session(snapshot)
    triage, decisions, selected_hospital, acknowledgement = run_decision_pipeline(
        snapshot, get_all_hospitals()
    )
    if emergency_id is not None:
        _persist_safely(
            persistence_service.save_decision,
            emergency_id,
            triage,
            decisions,
            selected_hospital,
            acknowledgement,
        )
    try:
        journey = journey_service.start_journey(snapshot, selected_hospital, acknowledgement)
    except JourneyStartError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if emergency_id is not None:
        _persist_safely(
            persistence_service.save_journey_start,
            emergency_id,
            simulation_service.get_current_snapshot(),
            journey,
        )
    return journey


@router.post("/journey/update", response_model=JourneyUpdateResponse)
def update_journey() -> JourneyUpdateResponse:
    """Advance one journey step, then return journey and synchronized snapshot state."""
    was_active = journey_service.get_status().active
    try:
        journey = journey_service.advance_journey()
    except JourneyStartError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    snapshot = simulation_service.get_current_snapshot()
    if was_active:
        emergency_id = _ensure_persistence_session(snapshot)
        if emergency_id is not None:
            _persist_safely(persistence_service.save_journey_update, emergency_id, snapshot, journey)
    return JourneyUpdateResponse(
        journey=journey,
        snapshot=snapshot,
    )


@router.post(
    "/emergency/decision",
    response_model=EmergencyDecisionResponse,
    description="Prototype simulation only — not intended for real medical decision-making.",
)
def make_emergency_decision() -> EmergencyDecisionResponse:
    """Run deterministic triage, eligibility filtering, mock routing, and selection."""
    snapshot = simulation_service.get_current_snapshot()
    triage, hospitals, selected_hospital, acknowledgement = run_decision_pipeline(
        snapshot, get_all_hospitals()
    )
    emergency_id = _ensure_persistence_session(snapshot)
    if emergency_id is not None:
        _persist_safely(
            persistence_service.save_decision,
            emergency_id,
            triage,
            hospitals,
            selected_hospital,
            acknowledgement,
        )
    return EmergencyDecisionResponse(
        ambulance=snapshot.ambulance,
        patient=snapshot.patient,
        vitals=snapshot.vitals,
        triage=triage,
        hospitals=hospitals,
        selected_hospital=selected_hospital,
        acknowledgement=acknowledgement,
    )


@router.post(
    "/emergency/incoming",
    response_model=IncomingEmergencyResponse,
    description="Receive the latest validated ambulance request without running triage or selection.",
)
def receive_incoming_emergency(
    request: IncomingEmergencyRequest,
) -> IncomingEmergencyResponse:
    """Store the latest ambulance-provided request as a communication event only."""
    return incoming_emergency_service.receive(request)


@router.get("/emergency/incoming", response_model=IncomingEmergencyResponse)
def get_incoming_emergency(
    hospital_id: Optional[str] = Query(default=None),
) -> IncomingEmergencyResponse:
    """Return the latest request and optionally hide its data from non-selected hospitals."""
    return incoming_emergency_service.get_latest(hospital_id=hospital_id)


@router.get("/history/emergencies", response_model=list[EmergencyHistoryItem])
def get_emergency_history(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, object]]:
    """Return recent simulated emergency audit summaries, newest first."""
    try:
        return persistence_service.get_emergency_history(limit=limit)
    except (PersistenceError, SQLAlchemyError):
        logger.warning("SQLite history read failed.")
        raise HTTPException(status_code=500, detail="Emergency history is unavailable.")


@router.get("/history/emergencies/{emergency_id}", response_model=EmergencyHistoryDetail)
def get_emergency_history_detail(emergency_id: str) -> dict[str, object]:
    """Return one simulated emergency's persisted triage, decisions, and journey timeline."""
    try:
        details = persistence_service.get_emergency_details(emergency_id)
    except (PersistenceError, SQLAlchemyError):
        logger.warning("SQLite history detail read failed.")
        raise HTTPException(status_code=500, detail="Emergency history is unavailable.")
    if details is None:
        raise HTTPException(status_code=404, detail="Emergency history record was not found.")
    return details
