"""
Tests for OMEN Python SDK.

Covers:
- Client initialization
- Partner signals operations
- Async client operations
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import httpx


class TestOmenClientInitialization:
    """Test OmenClient initialization and configuration."""
    
    def test_client_initialization_with_api_key(self):
        """Test client initializes correctly with API key."""
        from omen_client import OmenClient
        
        client = OmenClient(api_key="test_key")
        
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.omen.io"
        
        client.close()
    
    def test_client_custom_base_url(self):
        """Test client with custom base URL."""
        from omen_client import OmenClient
        
        client = OmenClient(
            api_key="test_key",
            base_url="http://localhost:8002",
        )
        
        assert client.base_url == "http://localhost:8002"
        
        client.close()
    
    def test_client_requires_api_key(self):
        """Test client raises error without API key."""
        from omen_client import OmenClient
        
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                OmenClient(api_key=None)
    
    def test_client_headers(self):
        """Test client sets correct headers."""
        from omen_client import OmenClient
        
        client = OmenClient(api_key="test_key")
        
        assert client._client.headers["X-API-Key"] == "test_key"
        assert "omen-python-sdk" in client._client.headers["User-Agent"]
        assert client._client.headers["Accept"] == "application/json"
        
        client.close()
    
    def test_client_context_manager(self):
        """Test client works as context manager."""
        from omen_client import OmenClient
        
        with OmenClient(api_key="test_key") as client:
            assert client.api_key == "test_key"


class TestPartnerSignals:
    """Test partner signals operations."""
    
    @pytest.fixture
    def mock_partner_response(self) -> dict:
        """Mock API response for partner signals."""
        return {
            "timestamp": "2026-02-01T10:00:00Z",
            "total_partners": 2,
            "partners": [
                {
                    "symbol": "GMD",
                    "company_name": "Gemadept Corporation",
                    "sector": "logistics",
                    "exchange": "HOSE",
                    "signals": {
                        "price_current": 68.5,
                        "price_close_previous": 67.9,
                        "price_change_percent": 0.88,
                        "volume": 1901300,
                        "volume_avg_20d": 1500000,
                        "volatility_20d": 0.023,
                        "liquidity_score": 0.85,
                    },
                    "confidence": {
                        "overall_confidence": 0.85,
                        "data_completeness": 0.9,
                        "data_freshness_seconds": 120,
                        "price_data_confidence": 1.0,
                        "fundamental_data_confidence": 0.0,
                        "volume_data_confidence": 1.0,
                        "missing_fields": [],
                        "data_source": "vnstock",
                        "data_source_reliability": 0.95,
                    },
                    "evidence": [],
                    "signal_id": "gmd-signal-001",
                    "timestamp": "2026-02-01T10:00:00Z",
                },
                {
                    "symbol": "HAH",
                    "company_name": "Hai An Transport",
                    "sector": "logistics",
                    "exchange": "HOSE",
                    "signals": {
                        "price_current": 34.2,
                        "price_close_previous": 34.0,
                        "price_change_percent": 0.59,
                        "volume": 500000,
                        "volume_avg_20d": 450000,
                        "volatility_20d": 0.018,
                        "liquidity_score": 0.72,
                    },
                    "confidence": {
                        "overall_confidence": 0.82,
                        "data_completeness": 0.85,
                        "data_freshness_seconds": 180,
                        "price_data_confidence": 1.0,
                        "fundamental_data_confidence": 0.0,
                        "volume_data_confidence": 1.0,
                        "missing_fields": ["market_cap"],
                        "data_source": "vnstock",
                        "data_source_reliability": 0.95,
                    },
                    "evidence": [],
                    "signal_id": "hah-signal-001",
                    "timestamp": "2026-02-01T10:00:00Z",
                },
            ],
        }
    
    def test_list_partner_signals(self, mock_partner_response):
        """Test listing partner signals."""
        from omen_client import OmenClient, PartnerSignalsListResponse
        
        client = OmenClient(api_key="test_key", base_url="http://test")
        
        with patch.object(client._client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_partner_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            
            result = client.partner_signals.list()
            
            assert isinstance(result, PartnerSignalsListResponse)
            assert result.total_partners == 2
            assert result.partners[0].symbol == "GMD"
            assert result.partners[1].symbol == "HAH"
        
        client.close()
    
    def test_list_partner_signals_with_filter(self, mock_partner_response):
        """Test listing partner signals with symbol filter."""
        from omen_client import OmenClient
        
        client = OmenClient(api_key="test_key", base_url="http://test")
        
        # Filter response to just GMD
        filtered_response = mock_partner_response.copy()
        filtered_response["partners"] = [mock_partner_response["partners"][0]]
        filtered_response["total_partners"] = 1
        
        with patch.object(client._client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = filtered_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            
            result = client.partner_signals.list(symbols=["GMD"])
            
            assert result.total_partners == 1
            assert result.partners[0].symbol == "GMD"
            
            # Verify the request was made with correct params
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args
            assert "symbols" in str(call_kwargs)
        
        client.close()
    
    def test_get_partner_signal(self, mock_partner_response):
        """Test getting single partner signal."""
        from omen_client import OmenClient, PartnerSignalResponse
        
        client = OmenClient(api_key="test_key", base_url="http://test")
        
        single_response = mock_partner_response["partners"][0]
        
        with patch.object(client._client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = single_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            
            result = client.partner_signals.get("GMD")
            
            assert isinstance(result, PartnerSignalResponse)
            assert result.symbol == "GMD"
            assert result.signals.price_current == 68.5
            assert result.confidence.overall_confidence == 0.85
        
        client.close()


class TestAsyncClient:
    """Test async client operations."""
    
    @pytest.mark.asyncio
    async def test_async_client_initialization(self):
        """Test async client initializes correctly."""
        from omen_client import AsyncOmenClient
        
        client = AsyncOmenClient(api_key="test_key", base_url="http://test")
        
        assert client.api_key == "test_key"
        assert client.base_url == "http://test"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async client works as context manager."""
        from omen_client import AsyncOmenClient
        
        async with AsyncOmenClient(api_key="test_key", base_url="http://test") as client:
            assert client.api_key == "test_key"
    
    @pytest.mark.asyncio
    async def test_async_list_signals(self):
        """Test async signal listing."""
        from omen_client import AsyncOmenClient
        
        client = AsyncOmenClient(api_key="test_key", base_url="http://test")
        
        mock_response = {
            "items": [
                {
                    "signal_id": "test-signal-1",
                    "signal_type": "stock",
                    "title": "Test Signal",
                    "confidence_score": 0.85,
                    "created_at": "2026-02-01T10:00:00Z",
                }
            ],
            "has_more": False,
        }
        
        # Create async mock
        async_client = AsyncMock()
        async_response = MagicMock()
        async_response.status_code = 200
        async_response.json.return_value = mock_response
        async_response.raise_for_status = MagicMock()
        async_client.get.return_value = async_response
        
        client._client = async_client
        
        result = await client.signals.list()
        
        assert len(result) == 1
        assert result[0].signal_id == "test-signal-1"
        
        await client.close()


class TestErrorHandling:
    """Test error handling."""
    
    def test_authentication_error(self):
        """Test handling of authentication errors."""
        from omen_client import OmenClient
        
        client = OmenClient(api_key="invalid_key", base_url="http://test")
        
        with patch.object(client._client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": "UNAUTHORIZED",
                "message": "Invalid API key",
            }
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401", request=MagicMock(), response=mock_response
            )
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception):
                client.partner_signals.list()
        
        client.close()
    
    def test_rate_limit_error(self):
        """Test handling of rate limit errors."""
        from omen_client import OmenClient
        
        client = OmenClient(api_key="test_key", base_url="http://test")
        
        with patch.object(client._client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.json.return_value = {
                "error": "RATE_LIMITED",
                "message": "Rate limit exceeded",
            }
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429", request=MagicMock(), response=mock_response
            )
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception):
                client.partner_signals.list()
        
        client.close()
    
    def test_not_found_error(self):
        """Test handling of not found errors."""
        from omen_client import OmenClient
        
        client = OmenClient(api_key="test_key", base_url="http://test")
        
        with patch.object(client._client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {
                "error": "NOT_FOUND",
                "message": "Partner 'INVALID' not found",
            }
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=mock_response
            )
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception):
                client.partner_signals.get("INVALID")
        
        client.close()


class TestHealthCheck:
    """Test health check functionality."""
    
    def test_health_check(self):
        """Test health endpoint."""
        from omen_client import OmenClient
        
        client = OmenClient(api_key="test_key", base_url="http://test")
        
        with patch.object(client._client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "service": "omen",
            }
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            
            result = client.health()
            
            assert result["status"] == "healthy"
        
        client.close()
