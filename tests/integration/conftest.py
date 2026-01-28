"""Fixtures for integration tests."""

import pytest
from fastapi.testclient import TestClient

from omen.main import create_app


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI test client for integration tests.

    Uses the real app; live/process may return empty or 503 if Polymarket is unavailable.
    """
    return TestClient(create_app())
