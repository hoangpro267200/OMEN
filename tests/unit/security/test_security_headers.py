"""Tests that all responses include required security headers."""

import pytest
from fastapi.testclient import TestClient

from omen.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


REQUIRED_HEADERS = [
    "X-Content-Type-Options",
    "X-Frame-Options",
    "X-XSS-Protection",
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "Referrer-Policy",
]


def test_security_headers_on_root(client: TestClient):
    """Root response includes required security headers."""
    response = client.get("/")
    assert response.status_code == 200
    for name in REQUIRED_HEADERS:
        assert name in response.headers, f"Missing header: {name}"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_security_headers_on_health(client: TestClient):
    """Health endpoint response includes security headers."""
    response = client.get("/health/ready")
    for name in REQUIRED_HEADERS:
        assert name in response.headers, f"Missing header: {name}"
