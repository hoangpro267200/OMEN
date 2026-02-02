"""Integration tests for API contract validation (B08)."""

import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from riskcast.api.app import app as riskcast_app


@pytest.mark.anyio
async def test_invalid_payload_returns_400() -> None:
    """POST invalid JSON should return HTTP 400 (B08)."""
    transport = ASGITransport(app=riskcast_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/signals/ingest", json={"foo": "bar"})
    assert resp.status_code == 400, resp.text
