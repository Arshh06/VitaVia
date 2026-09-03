"""HTTP-only client for the VITAVIA FastAPI backend."""

import os
from typing import Any, Mapping, Optional, Type
from urllib.parse import quote

import httpx


DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 5.0


class ApiClientError(Exception):
    """A concise, user-safe backend communication error."""


class VitaviaApiClient:
    """Wrap VITAVIA backend endpoints without exposing transport details to the UI."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("VITAVIA_API_URL", DEFAULT_API_URL)).rstrip("/")
        self._http_client = http_client or httpx.Client(timeout=timeout_seconds)

    def get_health(self) -> dict[str, Any]:
        """Fetch the backend health status."""
        return self._request("GET", "/health", dict)

    def get_snapshot(self) -> dict[str, Any]:
        """Fetch the current simulated emergency snapshot."""
        return self._request("GET", "/simulation/snapshot", dict)

    def update_simulation(self) -> dict[str, Any]:
        """Advance simulated vitals and ambulance location."""
        return self._request("POST", "/simulation/update", dict)

    def submit_vitals(self, vitals: Mapping[str, Any]) -> dict[str, Any]:
        """Send manually entered prototype vital signs to the current backend simulation."""
        return self._request("POST", "/simulation/vitals", dict, json_body=dict(vitals))

    def reset_simulation(self) -> dict[str, Any]:
        """Reset the simulated emergency to its default values."""
        return self._request("POST", "/simulation/reset", dict)

    def get_hospitals(self) -> list[dict[str, Any]]:
        """Fetch the fictional hospitals without making a decision."""
        return self._request("GET", "/hospitals", list)

    def get_analysis(self) -> dict[str, Any]:
        """Request the current backend triage analysis."""
        return self._request("POST", "/analysis", dict)

    def get_decision(self) -> dict[str, Any]:
        """Run and return the full backend emergency-decision pipeline."""
        return self._request("POST", "/emergency/decision", dict)

    def get_ai_status(self) -> dict[str, Any]:
        """Fetch safe AI-mode status without receiving credentials."""
        return self._request("GET", "/ai/status", dict)

    def get_routing_status(self) -> dict[str, Any]:
        """Fetch safe routing-mode status without receiving credentials."""
        return self._request("GET", "/routing/status", dict)

    def start_journey(self) -> dict[str, Any]:
        """Ask the backend to start a journey using its own trusted decision."""
        return self._request("POST", "/journey/start", dict)

    def update_journey(self) -> dict[str, Any]:
        """Advance one backend-controlled journey-simulation step."""
        return self._request("POST", "/journey/update", dict)

    def get_journey_status(self) -> dict[str, Any]:
        """Fetch the current backend-owned journey state."""
        return self._request("GET", "/journey/status", dict)

    def get_incoming_emergency(
        self, hospital_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Fetch the latest ambulance request, optionally scoped to one hospital ID."""
        path = "/emergency/incoming"
        if hospital_id:
            path += f"?hospital_id={quote(hospital_id, safe='')}"
        return self._request("GET", path, dict)

    def get_emergency_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch stored emergency audit summaries through FastAPI, never SQLite directly."""
        safe_limit = min(max(int(limit), 1), 100)
        return self._request("GET", f"/history/emergencies?limit={safe_limit}", list)

    def get_emergency_detail(self, emergency_id: str) -> dict[str, Any]:
        """Fetch one stored emergency audit trail through the backend history API."""
        safe_emergency_id = quote(emergency_id, safe="")
        return self._request("GET", f"/history/emergencies/{safe_emergency_id}", dict)

    def get_database_status(self) -> dict[str, Any]:
        """Fetch a safe, user-facing database readiness indication."""
        return self._request("GET", "/database/status", dict)

    def _request(
        self,
        method: str,
        path: str,
        expected_type: Type[Any],
        *,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Make one request and turn transport/response issues into a clean UI error."""
        try:
            request_kwargs = {"json": json_body} if json_body is not None else {}
            response = self._http_client.request(
                method, f"{self.base_url}{path}", **request_kwargs
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise ApiClientError("The backend request timed out. Please try again.") from error
        except httpx.HTTPError as error:
            raise ApiClientError("The VITAVIA backend is unavailable or returned an error.") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise ApiClientError("The backend returned an invalid response.") from error
        if not isinstance(payload, expected_type):
            raise ApiClientError("The backend returned an unexpected response.")
        return payload
