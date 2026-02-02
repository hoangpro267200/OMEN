"""
Redis-backed Rate Limiter.

Enables distributed rate limiting across multiple instances.
Uses sliding window algorithm for accurate rate limiting.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis.
    
    Uses sliding window counter algorithm for accurate, distributed rate limiting.
    Supports multiple OMEN instances sharing rate limit state.
    
    Requires:
    - redis library: pip install redis
    - Redis server
    """
    
    def __init__(
        self,
        redis_url: str,
        requests_per_minute: int = 600,
        burst_size: int = 50,
        key_prefix: str = "omen:ratelimit:",
    ):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            requests_per_minute: Maximum requests per minute per key
            burst_size: Maximum burst allowance
            key_prefix: Prefix for Redis keys
        """
        self.redis_url = redis_url
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.key_prefix = key_prefix
        self.window_seconds = 60
        self._redis = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError(
                "redis library is required for distributed rate limiting. "
                "Install with: pip install redis"
            )
        
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        
        # Test connection
        try:
            await self._redis.ping()
            self._initialized = True
            logger.info("Redis rate limiter initialized: %s", self.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise
    
    def _ensure_initialized(self) -> None:
        """Ensure limiter is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "Redis rate limiter not initialized. Call await initialize() first."
            )
    
    async def is_allowed(self, client_key: str) -> tuple[bool, dict[str, str]]:
        """
        Check if request is allowed under rate limit.
        
        Uses sliding window counter:
        1. Remove expired entries from sorted set
        2. Count current entries
        3. If under limit, add current timestamp
        4. Return rate limit headers
        
        Args:
            client_key: Unique identifier for client (API key or IP)
            
        Returns:
            (allowed: bool, headers: dict with X-RateLimit-* headers)
        """
        self._ensure_initialized()
        
        key = f"{self.key_prefix}{client_key}"
        now = time.time()
        window_start = now - self.window_seconds
        
        pipe = self._redis.pipeline()
        
        # Remove entries outside window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current entries
        pipe.zcard(key)
        
        # Add current request (optimistic - will be there for next check)
        pipe.zadd(key, {str(now): now})
        
        # Set expiry to window size (cleanup)
        pipe.expire(key, self.window_seconds + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        # Check if allowed
        allowed = current_count < self.requests_per_minute
        
        # If not allowed, remove the optimistically added entry
        if not allowed:
            await self._redis.zrem(key, str(now))
        
        remaining = max(0, self.requests_per_minute - current_count - (1 if allowed else 0))
        reset_time = int(now + self.window_seconds)
        
        headers = {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }
        
        if not allowed:
            headers["Retry-After"] = str(self.window_seconds)
        
        return allowed, headers
    
    async def get_usage(self, client_key: str) -> dict:
        """
        Get current rate limit usage for a client.
        
        Returns:
            dict with current usage stats
        """
        self._ensure_initialized()
        
        key = f"{self.key_prefix}{client_key}"
        now = time.time()
        window_start = now - self.window_seconds
        
        # Count entries in current window
        count = await self._redis.zcount(key, window_start, now)
        
        return {
            "client_key": client_key,
            "current_requests": count,
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - count),
            "window_seconds": self.window_seconds,
            "reset_at": datetime.fromtimestamp(now + self.window_seconds, tz=timezone.utc).isoformat(),
        }
    
    async def reset(self, client_key: str) -> None:
        """Reset rate limit for a client (admin use)."""
        self._ensure_initialized()
        
        key = f"{self.key_prefix}{client_key}"
        await self._redis.delete(key)
        logger.info("Rate limit reset for client: %s", client_key)
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis rate limiter connection closed")


class RedisRateLimitMiddleware:
    """
    FastAPI middleware for Redis-based rate limiting.
    
    Drop-in replacement for the in-memory rate limiter.
    """
    
    def __init__(self, limiter: RedisRateLimiter):
        self.limiter = limiter
    
    async def __call__(self, request, call_next):
        """Process request with rate limiting."""
        from fastapi import Response
        from starlette.responses import JSONResponse
        
        # Get client identifier (API key or IP)
        client_key = request.headers.get("X-API-Key")
        if not client_key:
            client_key = request.client.host if request.client else "unknown"
        
        allowed, headers = await self.limiter.is_allowed(client_key)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers=headers,
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# Factory function
async def create_redis_rate_limiter(
    redis_url: str,
    requests_per_minute: int = 600,
    burst_size: int = 50,
) -> RedisRateLimiter:
    """Create and initialize a Redis rate limiter."""
    limiter = RedisRateLimiter(
        redis_url=redis_url,
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
    )
    await limiter.initialize()
    return limiter
