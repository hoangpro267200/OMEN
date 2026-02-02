"""
OMEN Python Client.

Official Python client for the OMEN Signal Intelligence API.

Example:
    >>> from omen_client import OmenClient
    >>> 
    >>> # Sync client
    >>> client = OmenClient(api_key="your-api-key")
    >>> signals = client.partner_signals.list()
    >>> for partner in signals.partners:
    ...     print(f"{partner.symbol}: volatility={partner.signals.volatility_20d}")
    >>>
    >>> # Async client
    >>> async with AsyncOmenClient(api_key="your-api-key") as client:
    ...     signals = await client.partner_signals.list()
    ...     async for signal in client.signals.stream():
    ...         process(signal)
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Iterator, Optional

import httpx

from .models import (
    PartnerSignalResponse,
    PartnerSignalsListResponse,
    OmenSignal,
)
from .exceptions import raise_for_status, OmenError

logger = logging.getLogger(__name__)


class PartnerSignalsClient:
    """Partner signals operations (sync)."""
    
    def __init__(self, client: "OmenClient"):
        self._client = client
    
    def list(
        self,
        symbols: Optional[list[str]] = None,
        include_evidence: bool = True,
        include_market_context: bool = True,
    ) -> PartnerSignalsListResponse:
        """
        List partner signals.
        
        Args:
            symbols: Filter by symbols (e.g., ["GMD", "HAH"])
            include_evidence: Include signal evidence
            include_market_context: Include market context
        
        Returns:
            PartnerSignalsListResponse with all partner signals
        
        Example:
            >>> signals = client.partner_signals.list(symbols=["HAH", "GMD"])
            >>> for partner in signals.partners:
            ...     print(f"{partner.symbol}: {partner.signals.price_change_percent}%")
        """
        params = {
            "include_evidence": include_evidence,
            "include_market_context": include_market_context,
        }
        if symbols:
            params["symbols"] = ",".join(symbols)
        
        data = self._client._get("/api/v1/partner-signals/", params=params)
        return PartnerSignalsListResponse.model_validate(data)
    
    def get(
        self,
        symbol: str,
        include_evidence: bool = True,
        include_history: bool = False,
        history_days: int = 30,
    ) -> PartnerSignalResponse:
        """
        Get signals for a specific partner.
        
        Args:
            symbol: Partner symbol (e.g., "HAH")
            include_evidence: Include signal evidence
            include_history: Include historical data
            history_days: Days of history (max 90)
        
        Returns:
            PartnerSignalResponse for the partner
        
        Example:
            >>> signal = client.partner_signals.get("HAH")
            >>> print(f"Price: {signal.signals.price_current}")
            >>> print(f"Confidence: {signal.confidence.overall_confidence}")
        """
        params = {
            "include_evidence": include_evidence,
            "include_history": include_history,
            "history_days": min(history_days, 90),
        }
        
        data = self._client._get(f"/api/v1/partner-signals/{symbol}", params=params)
        return PartnerSignalResponse.model_validate(data)


class SignalsClient:
    """General signals operations (sync)."""
    
    def __init__(self, client: "OmenClient"):
        self._client = client
    
    def list(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> list[OmenSignal]:
        """
        List recent signals.
        
        Args:
            limit: Number of signals to return (max 100)
            cursor: Pagination cursor
            signal_type: Filter by signal type
        
        Returns:
            List of OmenSignal objects
        """
        params = {"limit": min(limit, 100)}
        if cursor:
            params["cursor"] = cursor
        if signal_type:
            params["signal_type"] = signal_type
        
        data = self._client._get("/api/v1/signals/", params=params)
        return [OmenSignal.model_validate(s) for s in data.get("items", [])]
    
    def get(self, signal_id: str) -> OmenSignal:
        """
        Get a specific signal by ID.
        
        Args:
            signal_id: Signal identifier
        
        Returns:
            OmenSignal object
        """
        data = self._client._get(f"/api/v1/signals/{signal_id}")
        return OmenSignal.model_validate(data)


class AsyncPartnerSignalsClient:
    """Partner signals operations (async)."""
    
    def __init__(self, client: "AsyncOmenClient"):
        self._client = client
    
    async def list(
        self,
        symbols: Optional[list[str]] = None,
        include_evidence: bool = True,
        include_market_context: bool = True,
    ) -> PartnerSignalsListResponse:
        """List partner signals (async)."""
        params = {
            "include_evidence": include_evidence,
            "include_market_context": include_market_context,
        }
        if symbols:
            params["symbols"] = ",".join(symbols)
        
        data = await self._client._get("/api/v1/partner-signals/", params=params)
        return PartnerSignalsListResponse.model_validate(data)
    
    async def get(
        self,
        symbol: str,
        include_evidence: bool = True,
    ) -> PartnerSignalResponse:
        """Get signals for a specific partner (async)."""
        params = {"include_evidence": include_evidence}
        data = await self._client._get(f"/api/v1/partner-signals/{symbol}", params=params)
        return PartnerSignalResponse.model_validate(data)


class AsyncSignalsClient:
    """General signals operations (async)."""
    
    def __init__(self, client: "AsyncOmenClient"):
        self._client = client
    
    async def list(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> list[OmenSignal]:
        """List recent signals (async)."""
        params = {"limit": min(limit, 100)}
        if cursor:
            params["cursor"] = cursor
        if signal_type:
            params["signal_type"] = signal_type
        
        data = await self._client._get("/api/v1/signals/", params=params)
        return [OmenSignal.model_validate(s) for s in data.get("items", [])]
    
    async def get(self, signal_id: str) -> OmenSignal:
        """Get a specific signal by ID (async)."""
        data = await self._client._get(f"/api/v1/signals/{signal_id}")
        return OmenSignal.model_validate(data)
    
    async def stream(self) -> AsyncIterator[OmenSignal]:
        """
        Stream real-time signals via SSE.
        
        Yields:
            OmenSignal objects as they arrive
        
        Example:
            >>> async for signal in client.signals.stream():
            ...     print(f"New signal: {signal.signal_id}")
            ...     process_signal(signal)
        """
        async with httpx.AsyncClient() as http:
            async with http.stream(
                "GET",
                f"{self._client.base_url}/api/v1/signals/stream",
                headers={"X-API-Key": self._client.api_key},
                timeout=None,  # SSE streams indefinitely
            ) as response:
                raise_for_status(response)
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            yield OmenSignal.model_validate(data)
                        except Exception as e:
                            logger.warning("Failed to parse SSE data: %s", e)


class OmenClient:
    """
    Official OMEN Python Client (synchronous).
    
    Example:
        >>> client = OmenClient(api_key="your-api-key")
        >>> 
        >>> # Get partner signals
        >>> signals = client.partner_signals.list()
        >>> for partner in signals.partners:
        ...     print(f"{partner.symbol}: {partner.signals.price_change_percent}%")
        >>> 
        >>> # Get specific partner
        >>> hah = client.partner_signals.get("HAH")
        >>> print(f"Volatility: {hah.signals.volatility_20d}")
        >>> print(f"Confidence: {hah.confidence.overall_confidence}")
    
    Environment Variables:
        OMEN_API_KEY: Default API key (if not provided in constructor)
        OMEN_BASE_URL: Default base URL (default: https://api.omen.io)
    """
    
    DEFAULT_BASE_URL = "https://api.omen.io"
    DEFAULT_TIMEOUT = 30.0
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize OMEN client.
        
        Args:
            api_key: OMEN API key (or set OMEN_API_KEY env var)
            base_url: API base URL (default: https://api.omen.io)
            timeout: Request timeout in seconds
        """
        import os
        
        self.api_key = api_key or os.getenv("OMEN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key is required. Pass api_key parameter or set OMEN_API_KEY env var."
            )
        
        self.base_url = base_url or os.getenv("OMEN_BASE_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout
        
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-API-Key": self.api_key,
                "User-Agent": "omen-python-sdk/2.0.0",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
        
        # Sub-clients
        self.partner_signals = PartnerSignalsClient(self)
        self.signals = SignalsClient(self)
    
    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make GET request."""
        response = self._client.get(path, params=params)
        raise_for_status(response)
        return response.json()
    
    def _post(self, path: str, data: Optional[dict] = None) -> dict:
        """Make POST request."""
        response = self._client.post(path, json=data)
        raise_for_status(response)
        return response.json()
    
    def health(self) -> dict:
        """
        Check API health.
        
        Returns:
            Health status dict
        """
        return self._get("/health")
    
    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self) -> "OmenClient":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()


class AsyncOmenClient:
    """
    Official OMEN Python Client (asynchronous).
    
    Example:
        >>> async with AsyncOmenClient(api_key="your-api-key") as client:
        ...     # Get partner signals
        ...     signals = await client.partner_signals.list()
        ...     
        ...     # Stream real-time signals
        ...     async for signal in client.signals.stream():
        ...         print(f"New signal: {signal.signal_id}")
    """
    
    DEFAULT_BASE_URL = "https://api.omen.io"
    DEFAULT_TIMEOUT = 30.0
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize async OMEN client.
        
        Args:
            api_key: OMEN API key (or set OMEN_API_KEY env var)
            base_url: API base URL (default: https://api.omen.io)
            timeout: Request timeout in seconds
        """
        import os
        
        self.api_key = api_key or os.getenv("OMEN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key is required. Pass api_key parameter or set OMEN_API_KEY env var."
            )
        
        self.base_url = base_url or os.getenv("OMEN_BASE_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout
        
        self._client: Optional[httpx.AsyncClient] = None
        
        # Sub-clients
        self.partner_signals = AsyncPartnerSignalsClient(self)
        self.signals = AsyncSignalsClient(self)
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure async client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "X-API-Key": self.api_key,
                    "User-Agent": "omen-python-sdk/2.0.0",
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client
    
    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make async GET request."""
        client = await self._ensure_client()
        response = await client.get(path, params=params)
        raise_for_status(response)
        return response.json()
    
    async def _post(self, path: str, data: Optional[dict] = None) -> dict:
        """Make async POST request."""
        client = await self._ensure_client()
        response = await client.post(path, json=data)
        raise_for_status(response)
        return response.json()
    
    async def health(self) -> dict:
        """Check API health (async)."""
        return await self._get("/health")
    
    async def close(self) -> None:
        """Close the async HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self) -> "AsyncOmenClient":
        await self._ensure_client()
        return self
    
    async def __aexit__(self, *args) -> None:
        await self.close()
