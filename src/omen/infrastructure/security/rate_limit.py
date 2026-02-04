"""
Rate limiting for OMEN API.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Awaitable

from fastapi import Request, status
from fastapi.responses import JSONResponse

from omen.infrastructure.security.config import get_security_config


@dataclass
class RateLimitState:
    """State for a single client."""

    tokens: float
    last_update: datetime


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.

    Each client gets a bucket of tokens that refills over time.
    Each request consumes one token.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        self._rate = requests_per_minute / 60.0
        self._burst = burst_size
        self._buckets: dict[str, RateLimitState] = {}
        self._lock = asyncio.Lock()

    async def check(self, client_id: str) -> tuple[bool, dict[str, str]]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (allowed, headers_dict)
        """
        async with self._lock:
            now = datetime.now(timezone.utc)

            if client_id not in self._buckets:
                self._buckets[client_id] = RateLimitState(
                    tokens=float(self._burst),
                    last_update=now,
                )

            state = self._buckets[client_id]

            elapsed = (now - state.last_update).total_seconds()
            state.tokens = min(
                self._burst,
                state.tokens + elapsed * self._rate,
            )
            state.last_update = now

            headers = {
                "X-RateLimit-Limit": str(int(self._rate * 60)),
                "X-RateLimit-Remaining": str(int(state.tokens)),
                "X-RateLimit-Reset": str(int(self._burst / self._rate)),
            }

            if state.tokens >= 1:
                state.tokens -= 1
                return True, headers
            else:
                headers["Retry-After"] = str(int(max(1, (1 - state.tokens) / self._rate)))
                return False, headers


import os
import logging

logger = logging.getLogger(__name__)

_rate_limiter: TokenBucketRateLimiter | None = None
_redis_rate_limiter = None
_use_redis = False


def get_rate_limiter() -> TokenBucketRateLimiter:
    """Return the global rate limiter instance (in-memory fallback)."""
    global _rate_limiter
    if _rate_limiter is None:
        config = get_security_config()
        _rate_limiter = TokenBucketRateLimiter(
            requests_per_minute=config.rate_limit_requests_per_minute,
            burst_size=config.rate_limit_burst,
        )
    return _rate_limiter


async def _init_redis_rate_limiter():
    """Initialize Redis rate limiter if REDIS_URL is available."""
    global _redis_rate_limiter, _use_redis
    
    if _redis_rate_limiter is not None:
        return _redis_rate_limiter
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    
    try:
        from omen.infrastructure.security.redis_rate_limit import RedisRateLimiter
        
        config = get_security_config()
        _redis_rate_limiter = RedisRateLimiter(
            redis_url=redis_url,
            requests_per_minute=config.rate_limit_requests_per_minute,
            burst_size=config.rate_limit_burst,
        )
        await _redis_rate_limiter.initialize()
        _use_redis = True
        logger.info("✅ Using Redis-based rate limiting (distributed)")
        return _redis_rate_limiter
    except Exception as e:
        logger.warning(f"Redis rate limiter unavailable, using in-memory: {e}")
        return None


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    """FastAPI middleware for rate limiting.
    
    ✅ ACTIVATED: Uses Redis for distributed rate limiting when REDIS_URL is set.
    Falls back to in-memory rate limiting otherwise.
    """
    config = get_security_config()

    if not config.rate_limit_enabled:
        return await call_next(request)

    client_id = request.headers.get("X-API-Key") or (
        request.client.host if request.client else "unknown"
    )

    # ✅ Try Redis rate limiter first (distributed)
    redis_limiter = await _init_redis_rate_limiter()
    
    if redis_limiter and _use_redis:
        try:
            allowed, headers = await redis_limiter.is_allowed(client_id)
        except Exception as e:
            logger.warning(f"Redis rate limit check failed, using in-memory: {e}")
            limiter = get_rate_limiter()
            allowed, headers = await limiter.check(client_id)
    else:
        # In-memory fallback
        limiter = get_rate_limiter()
        allowed, headers = await limiter.check(client_id)

    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"},
            headers=headers,
        )

    response = await call_next(request)
    for key, value in headers.items():
        response.headers[key] = value
    return response
