"""Test-wide safeguards that prevent external AI and routing API calls."""

import pytest

from app.db import database
from app.services import gemini_service, routing_service
from app.services.incoming_emergency_service import incoming_emergency_service
from app.services.persistence_service import persistence_service


@pytest.fixture(autouse=True)
def disable_external_api_keys(monkeypatch):
    """Force unit tests offline unless an individual test installs a local fake client."""
    monkeypatch.setattr(gemini_service.settings, "gemini_api_key", None)
    monkeypatch.setattr(routing_service.settings, "google_maps_api_key", None)


@pytest.fixture(autouse=True)
def isolate_sqlite_history(tmp_path):
    """Give every backend test a temporary SQLite audit database and clean active-session ID."""
    original_url = database.configured_database_url
    test_url = f"sqlite:///{tmp_path / 'vitavia-test.db'}"
    database.configure_database(test_url)
    database.init_db()
    persistence_service.clear_active_emergency()
    incoming_emergency_service.clear()
    yield
    persistence_service.clear_active_emergency()
    incoming_emergency_service.clear()
    database.configure_database(original_url)
