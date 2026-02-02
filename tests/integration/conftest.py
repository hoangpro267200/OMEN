"""Fixtures for integration tests."""

import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT SETUP (MUST BE BEFORE OTHER IMPORTS)
# ═══════════════════════════════════════════════════════════════════════════════

# Add src to path BEFORE any imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set test API key before any omen import (comma-separated, NOT JSON)
os.environ["OMEN_ENV"] = "test"
os.environ["OMEN_SECURITY_API_KEYS"] = "test-key-integration,test-admin-key"
os.environ["OMEN_SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["OMEN_SECURITY_JWT_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

# Clear security config cache before importing main
from omen.infrastructure.security.config import get_security_config
get_security_config.cache_clear()

from omen.main import create_app

TEST_API_KEY = "test-key-integration"


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI test client for integration tests.

    Uses the real app; live/process may return empty or 503 if Polymarket is unavailable.
    """
    # Clear config cache to pick up test environment
    get_security_config.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def api_headers() -> dict:
    """Headers with valid API key for protected routes."""
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def admin_api_headers() -> dict:
    """Headers with admin API key."""
    return {"X-API-Key": "test-admin-key"}
