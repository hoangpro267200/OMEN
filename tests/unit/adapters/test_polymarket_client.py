"""
Test Polymarket API client with mocked HTTP.

Coverage target: 90%
Focus: Error handling, circuit breaker, retry behavior
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from omen.adapters.inbound.polymarket.client import PolymarketClient
from omen.domain.errors import SourceRateLimitedError, SourceUnavailableError


@pytest.fixture
def client() -> PolymarketClient:
    return PolymarketClient(api_url="https://api.polymarket.com", api_key="test-key")


@pytest.fixture
def mock_httpx_success():
    """Mock successful HTTP response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b'[{"id": "1", "question": "Q?"}]'
    resp.json.return_value = [{"id": "1", "question": "Q?"}]
    resp.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = resp
    mock_client_class = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client_instance
    mock_client_class.return_value.__exit__.return_value = False

    with patch(
        "omen.adapters.inbound.polymarket.client.httpx.Client",
        mock_client_class,
    ):
        yield mock_client_class


@pytest.fixture
def mock_httpx_timeout():
    """Mock HTTP timeout."""
    mock_client_instance = MagicMock()
    mock_client_instance.get.side_effect = httpx.TimeoutException("timeout")
    mock_client_class = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client_instance
    mock_client_class.return_value.__exit__.return_value = False

    with patch(
        "omen.adapters.inbound.polymarket.client.httpx.Client",
        mock_client_class,
    ):
        yield


@pytest.fixture
def mock_httpx_429():
    """Mock rate limit response."""
    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {"Retry-After": "60"}
    req = MagicMock()
    err = httpx.HTTPStatusError("429", request=req, response=resp)
    mock_client_instance = MagicMock()
    mock_client_instance.get.side_effect = err
    mock_client_class = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client_instance
    mock_client_class.return_value.__exit__.return_value = False

    with patch(
        "omen.adapters.inbound.polymarket.client.httpx.Client",
        mock_client_class,
    ):
        yield


@pytest.fixture
def mock_httpx_500():
    """Mock server error."""
    resp = MagicMock()
    resp.status_code = 500
    req = MagicMock()
    err = httpx.HTTPStatusError("500", request=req, response=resp)
    mock_client_instance = MagicMock()
    mock_client_instance.get.side_effect = err
    mock_client_class = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client_instance
    mock_client_class.return_value.__exit__.return_value = False

    with patch(
        "omen.adapters.inbound.polymarket.client.httpx.Client",
        mock_client_class,
    ):
        yield


@pytest.fixture
def mock_httpx_503():
    """Mock service unavailable."""
    resp = MagicMock()
    resp.status_code = 503
    req = MagicMock()
    err = httpx.HTTPStatusError("503", request=req, response=resp)
    mock_client_instance = MagicMock()
    mock_client_instance.get.side_effect = err
    mock_client_class = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client_instance
    mock_client_class.return_value.__exit__.return_value = False

    with patch(
        "omen.adapters.inbound.polymarket.client.httpx.Client",
        mock_client_class,
    ):
        yield


class TestFetchMarkets:
    """Main API call behavior."""

    def test_returns_list_on_success(self, client: PolymarketClient, mock_httpx_success) -> None:
        result = client.fetch_markets(limit=10)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0].get("id") == "1"

    def test_passes_limit_parameter(self, client: PolymarketClient, mock_httpx_success) -> None:
        client.fetch_markets(limit=25)
        ctx = mock_httpx_success.return_value.__enter__.return_value
        ctx.get.assert_called_once()
        call_kw = ctx.get.call_args[1]
        assert call_kw["params"]["limit"] == 25

    def test_includes_auth_header(self, client: PolymarketClient, mock_httpx_success) -> None:
        client.fetch_markets(limit=5)
        mock_httpx_success.assert_called_once()
        call_kw = mock_httpx_success.call_args[1]
        assert "Authorization" in call_kw["headers"]
        assert "Bearer test-key" in call_kw["headers"]["Authorization"]

    def test_raises_unavailable_on_timeout(
        self, client: PolymarketClient, mock_httpx_timeout
    ) -> None:
        with pytest.raises(SourceUnavailableError) as exc_info:
            client.fetch_markets(limit=10)
        assert (
            "timeout" in str(exc_info.value).lower() or "unavailable" in str(exc_info.value).lower()
        )

    def test_raises_rate_limited_on_429(self, client: PolymarketClient, mock_httpx_429) -> None:
        with pytest.raises(SourceRateLimitedError) as exc_info:
            client.fetch_markets(limit=10)
        assert exc_info.value.retry_after_seconds == 60

    def test_raises_unavailable_on_500(self, client: PolymarketClient, mock_httpx_500) -> None:
        with pytest.raises(SourceUnavailableError):
            client.fetch_markets(limit=10)

    def test_raises_unavailable_on_503(self, client: PolymarketClient, mock_httpx_503) -> None:
        with pytest.raises(SourceUnavailableError):
            client.fetch_markets(limit=10)


class TestCircuitBreaker:
    """Circuit breaker integration."""

    def test_records_success_on_good_response(self, mock_httpx_success) -> None:
        with patch("omen.adapters.inbound.polymarket.client.create_source_circuit_breaker") as p_cb:
            mock_cb = MagicMock()
            mock_cb.is_available.return_value = True
            p_cb.return_value = mock_cb
            c = PolymarketClient(api_url="https://api.example.com", api_key="k")
            c.fetch_markets(limit=5)
            mock_cb.record_success.assert_called_once()

    def test_raises_immediately_when_circuit_open(self) -> None:
        with patch("omen.adapters.inbound.polymarket.client.create_source_circuit_breaker") as p_cb:
            mock_cb = MagicMock()
            mock_cb.is_available.return_value = False
            p_cb.return_value = mock_cb
            client = PolymarketClient(api_url="https://api.example.com", api_key="k")
            with patch("omen.adapters.inbound.polymarket.client.httpx.Client") as MockClient:
                with pytest.raises(SourceUnavailableError) as exc_info:
                    client.fetch_markets(limit=1)
                assert (
                    "circuit" in str(exc_info.value).lower()
                    or "open" in str(exc_info.value).lower()
                )
                MockClient.assert_not_called()
