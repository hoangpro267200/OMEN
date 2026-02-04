"""
OMEN API - Basic Usage Example

This example shows how to:
1. Connect to OMEN API
2. Fetch signals
3. Handle responses
4. Work with async patterns

Prerequisites:
    pip install httpx
"""

import asyncio
import httpx
from datetime import datetime
from typing import Optional


class OmenClient:
    """Synchronous OMEN API client."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "your-api-key"
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=30.0
        )
    
    def health_check(self) -> dict:
        """Check API health status."""
        response = self._client.get("/health/ready")
        response.raise_for_status()
        return response.json()
    
    def get_signals(
        self,
        limit: int = 50,
        category: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> list[dict]:
        """
        Get signals from OMEN.
        
        Args:
            limit: Maximum number of signals to return
            category: Filter by category (e.g., "geopolitical", "weather")
            min_confidence: Minimum confidence score (0.0 - 1.0)
        """
        params = {"limit": limit}
        if category:
            params["category"] = category
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        
        response = self._client.get("/api/v1/signals", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("signals", data.get("data", []))
    
    def get_signal(self, signal_id: str) -> dict:
        """Get a specific signal by ID."""
        response = self._client.get(f"/api/v1/signals/{signal_id}")
        response.raise_for_status()
        return response.json()
    
    def get_explanation(self, signal_id: str) -> dict:
        """Get explanation for a signal."""
        response = self._client.get(f"/api/v1/explanations/{signal_id}")
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Close the client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


class OmenAsyncClient:
    """Asynchronous OMEN API client."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "your-api-key"
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=30.0
        )
    
    async def health_check(self) -> dict:
        """Check API health status."""
        response = await self._client.get("/health/ready")
        response.raise_for_status()
        return response.json()
    
    async def get_signals(
        self,
        limit: int = 50,
        category: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> list[dict]:
        """Get signals from OMEN."""
        params = {"limit": limit}
        if category:
            params["category"] = category
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        
        response = await self._client.get("/api/v1/signals", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("signals", data.get("data", []))
    
    async def get_signal(self, signal_id: str) -> dict:
        """Get a specific signal by ID."""
        response = await self._client.get(f"/api/v1/signals/{signal_id}")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()


# ═══════════════════════════════════════════════════════════════════════════
# EXAMPLE USAGE
# ═══════════════════════════════════════════════════════════════════════════

def sync_example():
    """Synchronous client usage example."""
    print("=== Sync Client Example ===\n")
    
    with OmenClient(api_key="demo-key") as client:
        # Health check
        health = client.health_check()
        print(f"API Status: {health.get('status', 'unknown')}")
        
        # Get signals
        signals = client.get_signals(limit=5)
        print(f"\nFound {len(signals)} signals:")
        
        for signal in signals:
            print(f"  - {signal.get('signal_id', 'N/A')}: "
                  f"{signal.get('title', 'N/A')[:50]}... "
                  f"(confidence: {signal.get('confidence_score', 0):.2%})")


async def async_example():
    """Asynchronous client usage example."""
    print("\n=== Async Client Example ===\n")
    
    async with OmenAsyncClient(api_key="demo-key") as client:
        # Parallel requests for multiple categories
        categories = ["geopolitical", "weather", "economic"]
        
        tasks = [
            client.get_signals(limit=2, category=cat)
            for cat in categories
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for category, result in zip(categories, results):
            if isinstance(result, Exception):
                print(f"  {category}: Error - {result}")
            else:
                print(f"  {category}: {len(result)} signals")


async def streaming_example():
    """WebSocket streaming example."""
    print("\n=== WebSocket Streaming Example ===\n")
    
    import websockets
    
    uri = "ws://localhost:8000/api/v1/realtime/ws"
    
    try:
        async with websockets.connect(uri) as ws:
            print("Connected to WebSocket")
            
            # Receive 5 messages
            for i in range(5):
                message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                print(f"  Message {i+1}: {message[:100]}...")
    except Exception as e:
        print(f"  WebSocket error: {e}")


if __name__ == "__main__":
    print("OMEN API Python Examples\n")
    print("=" * 60)
    
    # Run sync example
    try:
        sync_example()
    except Exception as e:
        print(f"Sync example error: {e}")
    
    # Run async example
    try:
        asyncio.run(async_example())
    except Exception as e:
        print(f"Async example error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples complete!")
