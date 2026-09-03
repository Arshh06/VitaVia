"""Google Routes integration with deterministic mock fallback for VITAVIA."""

import logging
import re

import httpx

from app.core.config import settings
from app.models.schemas import GPSLocation, Hospital, RouteResult


logger = logging.getLogger(__name__)

GOOGLE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_ROUTES_TIMEOUT_SECONDS = 5.0
GOOGLE_ROUTES_FIELD_MASK = "routes.duration,routes.distanceMeters"
PROTOTYPE_BASELINE_SPEED_KMH = 35.0

MOCK_ROUTE_DATA = {
    "HOSP001": {"distance_km": 6.5, "traffic_condition": "HEAVY", "eta_minutes": 17.0},
    "HOSP002": {"distance_km": 8.0, "traffic_condition": "LOW", "eta_minutes": 10.0},
    "HOSP003": {"distance_km": 4.0, "traffic_condition": "LOW", "eta_minutes": 7.0},
    "HOSP004": {"distance_km": 5.0, "traffic_condition": "MODERATE", "eta_minutes": 11.0},
}


def is_google_maps_configured() -> bool:
    """Return whether a Maps key is available without exposing its value."""
    return bool(settings.google_maps_api_key and settings.google_maps_api_key.strip())


def calculate_route(origin: GPSLocation, hospital: Hospital) -> RouteResult:
    """Prefer Google traffic-aware routing, falling back to mock data for this hospital only."""
    if not is_google_maps_configured():
        return calculate_mock_route(origin, hospital)

    try:
        return calculate_google_route(origin, hospital)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        logger.warning("Google Routes unavailable for %s; using mock route.", hospital.hospital_id)
        return calculate_mock_route(origin, hospital)


def calculate_google_route(origin: GPSLocation, hospital: Hospital) -> RouteResult:
    """Call Google Compute Routes for one fictional hospital using traffic-aware driving mode."""
    response = httpx.post(
        GOOGLE_ROUTES_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.google_maps_api_key or "",
            "X-Goog-FieldMask": GOOGLE_ROUTES_FIELD_MASK,
        },
        json={
            "origin": _to_google_waypoint(origin),
            "destination": _to_google_waypoint(hospital.location),
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
        },
        timeout=GOOGLE_ROUTES_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    route_data = _extract_google_route(response.json())

    distance_meters = route_data["distanceMeters"]
    duration_seconds = _parse_duration_seconds(route_data["duration"])
    if (
        isinstance(distance_meters, bool)
        or not isinstance(distance_meters, (int, float))
        or distance_meters <= 0
    ):
        raise ValueError("Google Routes response has an invalid distance.")

    distance_km = float(distance_meters) / 1000
    eta_minutes = duration_seconds / 60
    return RouteResult(
        hospital_id=hospital.hospital_id,
        distance_km=round(distance_km, 3),
        traffic_condition=_derive_traffic_condition(distance_km, eta_minutes),
        eta_minutes=round(eta_minutes, 2),
        routing_source="google_maps",
    )


def calculate_mock_route(origin: GPSLocation, hospital: Hospital) -> RouteResult:
    """Return fixed demonstration route data; no external routing API is called."""
    _ = origin  # A later stage will use the ambulance position with a real routing provider.
    route_data = MOCK_ROUTE_DATA[hospital.hospital_id]
    return RouteResult(
        hospital_id=hospital.hospital_id,
        distance_km=route_data["distance_km"],
        traffic_condition=route_data["traffic_condition"],
        eta_minutes=route_data["eta_minutes"],
        routing_source="mock",
    )


def _to_google_waypoint(location: GPSLocation) -> dict:
    """Format a fictional simulation coordinate as a Compute Routes waypoint."""
    return {
        "location": {
            "latLng": {
                "latitude": location.latitude,
                "longitude": location.longitude,
            }
        }
    }


def _extract_google_route(response_data: object) -> dict:
    """Extract the single primary route and reject malformed Google response bodies."""
    if not isinstance(response_data, dict):
        raise ValueError("Google Routes response must be an object.")
    routes = response_data.get("routes")
    if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
        raise ValueError("Google Routes response contains no usable route.")
    return routes[0]


def _parse_duration_seconds(duration: object) -> float:
    """Safely parse a Google duration such as '653s' or '653.5s'."""
    if not isinstance(duration, str):
        raise ValueError("Google Routes response has no duration string.")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)s", duration)
    if match is None:
        raise ValueError("Google Routes response has an invalid duration format.")
    seconds = float(match.group(1))
    if seconds <= 0:
        raise ValueError("Google Routes response duration must be positive.")
    return seconds


def _derive_traffic_condition(distance_km: float, eta_minutes: float) -> str:
    """Map ETA to a prototype display label; this is not a Google traffic-severity label."""
    baseline_minutes = distance_km / PROTOTYPE_BASELINE_SPEED_KMH * 60
    if baseline_minutes <= 0:
        raise ValueError("Route baseline duration must be positive.")
    ratio = eta_minutes / baseline_minutes
    if ratio <= 1.2:
        return "LOW"
    if ratio <= 1.6:
        return "MODERATE"
    return "HEAVY"
