"""Unit tests for graceful shutdown (B1 gating item)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from omen.infrastructure.ledger import LedgerWriter
from omen.infrastructure.middleware.request_tracking import (
    clear_shutdown,
    is_shutting_down,
    set_shutdown,
)
from omen.main import graceful_shutdown, register_emitter, register_writer


@pytest.mark.asyncio
async def test_graceful_shutdown_flushes_writers(tmp_path: Path):
    """Graceful shutdown calls flush_and_close on all registered writers."""
    flushed = []

    class MockWriter:
        async def flush_and_close(self):
            flushed.append(self)

    writer = MockWriter()
    register_writer(writer)
    await graceful_shutdown(timeout_seconds=2)
    assert len(flushed) == 1
    assert flushed[0] is writer


@pytest.mark.asyncio
async def test_graceful_shutdown_closes_emitters():
    """Graceful shutdown calls close on all registered emitters."""
    closed = []

    class MockEmitter:
        async def close(self):
            closed.append(self)

    emitter = MockEmitter()
    register_emitter(emitter)
    await graceful_shutdown(timeout_seconds=2)
    assert len(closed) == 1
    assert closed[0] is emitter


@pytest.mark.asyncio
async def test_graceful_shutdown_flushes_real_ledger_writer(tmp_path: Path):
    """Real LedgerWriter.flush_and_close runs without error."""
    writer = LedgerWriter(tmp_path)
    register_writer(writer)
    await graceful_shutdown(timeout_seconds=2)
    # LedgerWriter.flush_and_close is a no-op (logs only); no exception
    assert True


@pytest.mark.asyncio
async def test_health_returns_503_during_shutdown():
    """Health endpoint returns 503 when shutting down."""
    from fastapi.testclient import TestClient

    from omen.main import app

    clear_shutdown()
    client = TestClient(app)
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json().get("status") == "healthy"

    set_shutdown()
    try:
        response = client.get("/health/")
        assert response.status_code == 503
        assert response.json().get("status") == "shutting_down"
    finally:
        clear_shutdown()

    response = client.get("/health/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ready_returns_503_during_shutdown():
    """Ready endpoint returns 503 when shutting down.

    This test verifies the shutdown behavior of /health/ready endpoint.
    When the system is in shutdown state, it should return 503 regardless
    of other health check results.
    """
    from fastapi.testclient import TestClient

    from omen.main import app

    # Ensure clean state before test
    clear_shutdown()

    with TestClient(app) as client:
        # Set shutdown state and verify 503
        set_shutdown()
        try:
            response = client.get("/health/ready")
            assert (
                response.status_code == 503
            ), f"Expected 503, got {response.status_code}: {response.json()}"
            assert response.json().get("ready") is False
            assert response.json().get("reason") == "shutting_down"
        finally:
            clear_shutdown()

        # After clearing shutdown, endpoint should work
        # (may still return 503 due to other checks like ledger, but not due to shutdown)
        response = client.get("/health/ready")
        # Just verify we don't get shutdown reason anymore
        data = response.json()
        assert data.get("reason") != "shutting_down"


def test_is_shutting_down():
    """is_shutting_down reflects set_shutdown / clear_shutdown."""
    clear_shutdown()
    assert is_shutting_down() is False
    set_shutdown()
    assert is_shutting_down() is True
    clear_shutdown()
    assert is_shutting_down() is False
