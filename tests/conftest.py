"""``pytest`` configuration."""

import os
from pathlib import Path
from typing import Dict, Optional, Any, Literal

from attrs import field
import pytest
from fastapi import Depends, Header
from starlette.testclient import TestClient

from titiler.openeo.auth import Auth, FakeBasicAuth, User

DATA_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

StoreType = Literal["local", "duckdb", "parquet"]

@pytest.fixture(params=["local", "duckdb", "parquet"])
def store_type(request) -> StoreType:
    """Parameterize the service store type."""
    return request.param

@pytest.fixture
def store_path(tmp_path, store_type: StoreType) -> Path:
    """Create a temporary store path based on store type."""
    if store_type == "local":
        path = tmp_path / "services.json"
        path.write_text("{}")
    elif store_type == "duckdb":
        path = tmp_path / "services.db"
    else:  # parquet
        path = tmp_path / "services.parquet"
    return path

@pytest.fixture(autouse=True)
def app(monkeypatch, store_path, store_type) -> TestClient:
    """Create App with temporary services store."""
    # Create fixtures directory if it doesn't exist
    Path(DATA_DIR).mkdir(exist_ok=True)
    
    monkeypatch.setenv("TITILER_OPENEO_STAC_API_URL", "https://stac.eoapi.dev")
    monkeypatch.setenv("TITILER_OPENEO_SERVICE_STORE_URL", f"{store_path}")
    
    from titiler.openeo.main import app, endpoints
    
    # Override the auth dependency with the mock auth
    mock_auth = MockAuth()
    app.dependency_overrides[endpoints.auth.validate] = mock_auth.validate

    return TestClient(app)


class MockAuth(Auth):
    """Mock authentication class for testing."""

    def login(self, authorization: str = Header(default=None)) -> Any:
        return {"access_token": "mock_token"}

    def validate(self, authorization: str = Header(default=None)) -> User:
        return User(user_id="test_user")


@pytest.fixture
def clean_services(app, store_path, store_type):
    """Ensure services are cleaned up after each test."""
    yield
    # Reset store to empty state
    if store_type == "local":
        store_path.write_text("{}")
    elif store_type == "duckdb":
        if store_path.exists():
            store_path.unlink()
    else:  # parquet
        if store_path.exists():
            store_path.unlink()
