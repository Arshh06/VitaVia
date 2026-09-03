"""Offline tests for the frontend's FastAPI HTTP client."""

import json

import httpx
import pytest

from api_client import ApiClientError, VitaviaApiClient


def test_successful_health_response() -> None:
    """A healthy backend response is returned as a validated dictionary."""
    client = _client_with_handler(
        lambda request: httpx.Response(200, json={"status": "ok", "service": "VITAVIA Backend"})
    )

    assert client.get_health()["status"] == "ok"


def test_connection_failure_becomes_clean_frontend_error() -> None:
    """A stopped backend never leaks a transport traceback into the dashboard layer."""
    class FailingHttpClient:
        def request(self, method, url):
            raise httpx.ConnectError("simulated connection failure")

    client = VitaviaApiClient(http_client=FailingHttpClient())

    with pytest.raises(ApiClientError, match="backend is unavailable"):
        client.get_health()


def test_successful_decision_response_parsing() -> None:
    """A complete decision payload remains available for the display-only dashboard."""
    expected_payload = {
        "ambulance": {"ambulance_id": "AMB001"},
        "patient": {"patient_id": "PAT001"},
        "vitals": {"spo2": 89.0},
        "triage": {"severity": "HIGH"},
        "hospitals": [],
        "selected_hospital": {"hospital_id": "HOSP002"},
        "acknowledgement": {"status": "ACCEPTED"},
    }
    client = _client_with_handler(lambda request: httpx.Response(200, json=expected_payload))

    decision = client.get_decision()

    assert decision["selected_hospital"]["hospital_id"] == "HOSP002"
    assert decision["acknowledgement"]["status"] == "ACCEPTED"


def test_submit_vitals_posts_a_manual_vital_payload() -> None:
    """Manual dashboard input is sent to FastAPI instead of being analyzed in Streamlit."""
    submitted = {
        "spo2": 95.0,
        "heart_rate": 105,
        "systolic_bp": 110,
        "diastolic_bp": 70,
        "temperature": 37.5,
    }
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(200, json={"vitals": submitted})

    client = _client_with_handler(handler)

    assert client.submit_vitals(submitted)["vitals"] == submitted
    assert seen_request is not None
    assert seen_request.method == "POST"
    assert seen_request.url.path == "/simulation/vitals"
    assert json.loads(seen_request.content) == submitted


def test_submit_vitals_validation_error_becomes_clean_frontend_error() -> None:
    """FastAPI validation failures remain safe messages for the Streamlit layer."""
    client = _client_with_handler(
        lambda request: httpx.Response(422, json={"detail": "invalid prototype vitals"})
    )

    with pytest.raises(ApiClientError, match="backend is unavailable"):
        client.submit_vitals({"spo2": 120.0})


def test_journey_client_methods_use_backend_endpoints() -> None:
    """Journey state stays backend-owned while the client exposes its three API calls."""
    expected_paths = ["/journey/status", "/journey/start", "/journey/update"]
    responses = [
        {"active": False, "status": "NOT_STARTED", "progress_percent": 0},
        {"active": True, "status": "EN_ROUTE", "selected_hospital_id": "HOSP002"},
        {
            "journey": {"active": True, "status": "EN_ROUTE", "step_number": 1},
            "snapshot": {"ambulance": {"ambulance_id": "AMB001"}, "vitals": {"spo2": 89.0}},
        },
    ]
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(200, json=responses[len(seen_paths) - 1])

    client = _client_with_handler(handler)

    assert client.get_journey_status()["status"] == "NOT_STARTED"
    assert client.start_journey()["selected_hospital_id"] == "HOSP002"
    assert client.update_journey()["journey"]["step_number"] == 1
    assert seen_paths == expected_paths


def test_incoming_emergency_client_scopes_polling_to_hospital_id() -> None:
    """The hospital console polls FastAPI rather than storing ambulance data locally."""
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "exists": True,
                "has_active_request": True,
                "selected_hospital_id": "HOSP002",
                "incoming_request": {"ambulance_id": "AMB-07"},
            },
        )

    client = _client_with_handler(handler)

    response = client.get_incoming_emergency("HOSP002")

    assert response["incoming_request"]["ambulance_id"] == "AMB-07"
    assert seen_request is not None
    assert seen_request.url.path == "/emergency/incoming"
    assert seen_request.url.params["hospital_id"] == "HOSP002"


def test_history_client_methods_use_fastapi_history_endpoints() -> None:
    """History remains a backend API concern; the Streamlit client never opens SQLite."""
    responses = [
        [
            {
                "emergency_id": "EMG-ABC12345",
                "status": "ARRIVED",
                "selected_hospital_name": "Metro Emergency Institute",
            }
        ],
        {
            "emergency": {"emergency_id": "EMG-ABC12345", "status": "ARRIVED"},
            "hospital_evaluations": [],
            "vital_history": [],
            "location_history": [],
        },
        {"database": "sqlite", "configured": True, "status": "ready"},
    ]
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json=responses[len(seen_requests) - 1])

    client = _client_with_handler(handler)

    assert client.get_emergency_history(limit=5)[0]["emergency_id"] == "EMG-ABC12345"
    assert client.get_emergency_detail("EMG-ABC12345")["emergency"]["status"] == "ARRIVED"
    assert client.get_database_status()["status"] == "ready"
    assert seen_requests[0].url.path == "/history/emergencies"
    assert seen_requests[0].url.params["limit"] == "5"
    assert seen_requests[1].url.path == "/history/emergencies/EMG-ABC12345"
    assert seen_requests[2].url.path == "/database/status"


def test_timeout_becomes_clean_frontend_error() -> None:
    """A timeout is safe and understandable to the dashboard caller."""
    class TimeoutHttpClient:
        def request(self, method, url):
            raise httpx.TimeoutException("simulated timeout")

    client = VitaviaApiClient(http_client=TimeoutHttpClient())

    with pytest.raises(ApiClientError, match="timed out"):
        client.get_snapshot()


def test_history_timeout_becomes_clean_frontend_error() -> None:
    """A history outage stays separate from and safe for the live dashboard workflow."""
    class TimeoutHttpClient:
        def request(self, method, url):
            raise httpx.TimeoutException("simulated timeout")

    client = VitaviaApiClient(http_client=TimeoutHttpClient())

    with pytest.raises(ApiClientError, match="timed out"):
        client.get_emergency_history()


def test_malformed_json_becomes_clean_frontend_error() -> None:
    """Invalid backend JSON cannot crash the Streamlit page."""
    client = _client_with_handler(lambda request: httpx.Response(200, content=b"not json"))

    with pytest.raises(ApiClientError, match="invalid response"):
        client.get_health()


def _client_with_handler(handler) -> VitaviaApiClient:
    """Build an API client backed by an in-memory HTTP transport."""
    return VitaviaApiClient(
        base_url="http://testserver",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
