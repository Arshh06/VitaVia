"""Minimal in-memory ambulance-to-hospital request exchange for the prototype."""

from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from app.models.schemas import IncomingEmergencyRequest, IncomingEmergencyResponse


class IncomingEmergencyService:
    """Keep only the latest ambulance request without influencing operational decisions."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._request: Optional[IncomingEmergencyRequest] = None
        self._received_at: Optional[datetime] = None

    def receive(self, request: IncomingEmergencyRequest) -> IncomingEmergencyResponse:
        """Store a validated request exactly as supplied by the ambulance application."""
        with self._lock:
            self._request = request.model_copy(deep=True)
            self._received_at = datetime.now(timezone.utc)
        return self.get_latest()

    def get_latest(
        self, hospital_id: Optional[str] = None
    ) -> IncomingEmergencyResponse:
        """Return the latest request, optionally exposing it only to its selected hospital."""
        with self._lock:
            request = self._request.model_copy(deep=True) if self._request else None
            received_at = self._received_at

        if request is None:
            return IncomingEmergencyResponse(exists=False, has_active_request=False)

        matches_hospital = hospital_id is None or request.selected_hospital_id == hospital_id
        return IncomingEmergencyResponse(
            exists=matches_hospital,
            has_active_request=True,
            selected_hospital_id=request.selected_hospital_id,
            incoming_request=request if matches_hospital else None,
            received_at=received_at,
        )

    def clear(self) -> None:
        """Clear test-only/in-memory request state without touching SQLite or simulation state."""
        with self._lock:
            self._request = None
            self._received_at = None


incoming_emergency_service = IncomingEmergencyService()
