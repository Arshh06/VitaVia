"""Offline tests for Google Routes normalization and per-hospital mock fallback."""

import httpx

from fastapi.testclient import TestClient

from app.data.hospitals import get_all_hospitals
from app.main import app
from app.services import routing_service
from app.services.simulation_service import simulation_service


client = TestClient(app)


def test_no_maps_key_uses_mock_route_and_keeps_default_selection() -> None:
    """No Maps key must retain the original deterministic mock scenario."""
    origin = simulation_service.reset_simulation().ambulance.location
    hospital = _hospital_by_id("HOSP002")

    route = routing_service.calculate_route(origin, hospital)
    client.post("/simulation/reset")
    decision = client.post("/emergency/decision").json()

    assert route.routing_source == "mock"
    assert route.eta_minutes == 10.0
    assert decision["selected_hospital"]["hospital_id"] == "HOSP002"
    assert all(hospital["routing_source"] == "mock" for hospital in decision["hospitals"])


def test_valid_google_response_is_normalized(monkeypatch) -> None:
    """Google distance and duration become the shared RouteResult contract."""
    captured_request = {}
    _configure_maps_key(monkeypatch)

    def fake_post(url, headers, json, timeout):
        captured_request.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse({"routes": [{"distanceMeters": 8000, "duration": "600s"}]})

    monkeypatch.setattr(routing_service.httpx, "post", fake_post)
    route = routing_service.calculate_route(
        simulation_service.reset_simulation().ambulance.location,
        _hospital_by_id("HOSP002"),
    )

    assert route.distance_km == 8.0
    assert route.eta_minutes == 10.0
    assert route.routing_source == "google_maps"
    assert route.traffic_condition in {"LOW", "MODERATE", "HEAVY"}
    assert captured_request["url"] == routing_service.GOOGLE_ROUTES_URL
    assert captured_request["timeout"] == routing_service.GOOGLE_ROUTES_TIMEOUT_SECONDS
    assert captured_request["headers"]["X-Goog-FieldMask"] == "routes.duration,routes.distanceMeters"
    assert captured_request["json"]["travelMode"] == "DRIVE"
    assert captured_request["json"]["routingPreference"] == "TRAFFIC_AWARE"


def test_google_timeout_falls_back_to_mock_route(monkeypatch) -> None:
    """A request timeout affects only the attempted hospital route."""
    _configure_maps_key(monkeypatch)

    def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("simulated timeout")

    monkeypatch.setattr(routing_service.httpx, "post", raise_timeout)
    route = routing_service.calculate_route(
        simulation_service.reset_simulation().ambulance.location,
        _hospital_by_id("HOSP002"),
    )

    assert route.routing_source == "mock"
    assert route.eta_minutes == 10.0


def test_google_http_failure_falls_back_to_mock_route(monkeypatch) -> None:
    """A representative Google API rejection must not fail the decision pipeline."""
    _configure_maps_key(monkeypatch)

    def fail_status():
        request = httpx.Request("POST", routing_service.GOOGLE_ROUTES_URL)
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError("simulated API rejection", request=request, response=response)

    monkeypatch.setattr(
        routing_service.httpx,
        "post",
        lambda *args, **kwargs: _FakeResponse({}, raise_for_status=fail_status),
    )
    route = routing_service.calculate_route(
        simulation_service.reset_simulation().ambulance.location,
        _hospital_by_id("HOSP002"),
    )

    assert route.routing_source == "mock"


def test_malformed_google_response_falls_back_to_mock_route(monkeypatch) -> None:
    """An empty route list or invalid route content cannot crash routing."""
    _configure_maps_key(monkeypatch)
    monkeypatch.setattr(
        routing_service.httpx,
        "post",
        lambda *args, **kwargs: _FakeResponse({"routes": []}),
    )
    route = routing_service.calculate_route(
        simulation_service.reset_simulation().ambulance.location,
        _hospital_by_id("HOSP002"),
    )

    assert route.routing_source == "mock"
    assert route.distance_km == 8.0


def test_ineligible_fastest_google_route_is_rejected(monkeypatch) -> None:
    """HOSP003 cannot win with a five-minute route because it has no ICU."""
    _configure_maps_key(monkeypatch)
    _configure_google_routes(monkeypatch, {"HOSP001": 14, "HOSP002": 9, "HOSP003": 5, "HOSP004": 8})
    client.post("/simulation/reset")

    response = client.post("/emergency/decision")
    payload = response.json()
    hospitals = _decisions_by_id(payload)

    assert response.status_code == 200
    assert hospitals["HOSP003"]["eta_minutes"] == 5.0
    assert hospitals["HOSP003"]["eligible"] is False
    assert hospitals["HOSP003"]["selected"] is False
    assert hospitals["HOSP004"]["eligible"] is False
    assert payload["selected_hospital"]["hospital_id"] == "HOSP002"
    assert hospitals["HOSP002"]["eta_minutes"] == 9.0


def test_eligible_selection_changes_with_google_eta(monkeypatch) -> None:
    """Google route ETAs can select HOSP001 when it is the faster eligible option."""
    _configure_maps_key(monkeypatch)
    _configure_google_routes(monkeypatch, {"HOSP001": 8, "HOSP002": 11, "HOSP003": 5, "HOSP004": 8})
    client.post("/simulation/reset")

    payload = client.post("/emergency/decision").json()
    hospitals = _decisions_by_id(payload)

    assert hospitals["HOSP001"]["eligible"] is True
    assert hospitals["HOSP001"]["eta_minutes"] == 8.0
    assert hospitals["HOSP002"]["eta_minutes"] == 11.0
    assert payload["selected_hospital"]["hospital_id"] == "HOSP001"


def test_each_hospital_can_fall_back_independently(monkeypatch) -> None:
    """A Google failure for one destination does not discard other successful routes."""
    _configure_maps_key(monkeypatch)
    locations = {hospital.location.latitude: hospital.hospital_id for hospital in get_all_hospitals()}

    def mixed_post(url, headers, json, timeout):
        hospital_id = locations[json["destination"]["location"]["latLng"]["latitude"]]
        if hospital_id in {"HOSP002", "HOSP004"}:
            raise httpx.TimeoutException("simulated timeout")
        eta_minutes = {"HOSP001": 14, "HOSP003": 5}[hospital_id]
        return _FakeResponse(
            {"routes": [{"distanceMeters": 6000, "duration": f"{eta_minutes * 60}s"}]}
        )

    monkeypatch.setattr(routing_service.httpx, "post", mixed_post)
    client.post("/simulation/reset")
    payload = client.post("/emergency/decision").json()
    hospitals = _decisions_by_id(payload)

    assert hospitals["HOSP001"]["routing_source"] == "google_maps"
    assert hospitals["HOSP002"]["routing_source"] == "mock"
    assert hospitals["HOSP003"]["routing_source"] == "google_maps"
    assert hospitals["HOSP004"]["routing_source"] == "mock"
    assert payload["selected_hospital"]["hospital_id"] == "HOSP002"


class _FakeResponse:
    """A small response double for offline Routes API tests."""

    def __init__(self, payload: dict, raise_for_status=None) -> None:
        self._payload = payload
        self._raise_for_status = raise_for_status

    def raise_for_status(self) -> None:
        if self._raise_for_status is not None:
            self._raise_for_status()

    def json(self) -> dict:
        return self._payload


def _configure_maps_key(monkeypatch) -> None:
    """Enable the routing branch with a non-secret local test value."""
    monkeypatch.setattr(routing_service.settings, "google_maps_api_key", "test-key")


def _configure_google_routes(monkeypatch, eta_by_hospital_id: dict) -> None:
    """Map each fictional destination coordinate to a deterministic fake API route."""
    location_to_hospital_id = {
        hospital.location.latitude: hospital.hospital_id for hospital in get_all_hospitals()
    }

    def fake_post(url, headers, json, timeout):
        hospital_id = location_to_hospital_id[
            json["destination"]["location"]["latLng"]["latitude"]
        ]
        eta_minutes = eta_by_hospital_id[hospital_id]
        return _FakeResponse(
            {
                "routes": [
                    {
                        "distanceMeters": 8000,
                        "duration": f"{eta_minutes * 60}s",
                    }
                ]
            }
        )

    monkeypatch.setattr(routing_service.httpx, "post", fake_post)


def _hospital_by_id(hospital_id: str):
    """Get one fictional hospital by ID for direct routing tests."""
    return next(hospital for hospital in get_all_hospitals() if hospital.hospital_id == hospital_id)


def _decisions_by_id(payload: dict) -> dict:
    """Index a decision response's hospitals for readable assertions."""
    return {hospital["hospital_id"]: hospital for hospital in payload["hospitals"]}
