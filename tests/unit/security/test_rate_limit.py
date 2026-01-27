"""Tests for rate limiting."""

import pytest

from omen.infrastructure.security.rate_limit import (
    TokenBucketRateLimiter,
    RateLimitState,
)


def test_rate_limit_state_dataclass():
    """RateLimitState has tokens and last_update."""
    from datetime import datetime
    s = RateLimitState(tokens=5.0, last_update=datetime.utcnow())
    assert s.tokens == 5.0


@pytest.mark.asyncio
async def test_limiter_allows_under_limit():
    """Limiter allows requests under the burst."""
    limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_size=2)
    allowed, headers = await limiter.check("client-a")
    assert allowed is True
    assert "X-RateLimit-Remaining" in headers


@pytest.mark.asyncio
async def test_limiter_consumes_tokens():
    """Each request consumes one token; burst_size=2 allows two then denies."""
    limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_size=2)
    allowed1, _ = await limiter.check("client-b")
    assert allowed1 is True
    allowed2, _ = await limiter.check("client-b")
    assert allowed2 is True
    allowed3, h3 = await limiter.check("client-b")
    assert allowed3 is False
    assert "Retry-After" in h3


@pytest.mark.asyncio
async def test_limiter_per_client():
    """Limits are per client_id."""
    limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_size=1)
    a1, _ = await limiter.check("c1")
    a2, _ = await limiter.check("c2")
    assert a1 is True and a2 is True
    b1, _ = await limiter.check("c1")
    assert b1 is False
