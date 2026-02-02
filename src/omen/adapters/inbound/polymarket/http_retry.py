"""
HTTP retry with exponential backoff for Polymarket clients.

Retries on: timeout, connect errors, 429, 5xx.
Uses POLYMARKET_RETRY_* and respects Retry-After header.
"""

import logging
import random
import time
from typing import Callable, TypeVar

import httpx

from omen.domain.errors import SourceRateLimitedError, SourceUnavailableError
from omen.polymarket_settings import PolymarketSettings, get_polymarket_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _backoff(attempt: int, base_s: float, cap_s: float = 60.0) -> float:
    """Exponential backoff with small jitter. Cap at cap_s."""
    wait = base_s * (2**attempt) + random.uniform(0, 0.5)
    return min(wait, cap_s)


def _log_connection_error(exc: Exception) -> None:
    """Classify and log connection refused / network unreachable."""
    msg = str(exc)
    if "10061" in msg or "Connection refused" in msg or "actively refused" in msg:
        logger.warning(
            "Polymarket connection refused (network unreachable or blocked). "
            "Check firewall/proxy or run scripts/polymarket_doctor.py",
            exc_info=False,
        )
    else:
        logger.warning("Polymarket request failed: %s", exc, exc_info=False)


def run_with_retry(
    request_fn: Callable[[], httpx.Response],
    settings: PolymarketSettings | None = None,
) -> httpx.Response:
    """
    Execute request_fn() with retry on timeout, connect errors, 429, 5xx.

    - Exponential backoff: base * 2^attempt + jitter; cap 60s.
    - If response has Retry-After, use it (capped) for 429.
    - After max attempts, raises SourceUnavailableError or SourceRateLimitedError.
    """
    s = settings or get_polymarket_settings()
    last_exc: Exception | None = None

    for attempt in range(s.retry_max + 1):
        try:
            response = request_fn()

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                wait = min(retry_after, 60)
                if attempt == s.retry_max:
                    raise SourceRateLimitedError(
                        "Polymarket rate limited",
                        retry_after_seconds=retry_after,
                        context={"status_code": 429},
                    )
                logger.warning("Polymarket 429, retrying after %ss (attempt %s)", wait, attempt + 1)
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                if attempt == s.retry_max:
                    response.raise_for_status()
                wait = _backoff(attempt, s.retry_backoff_s)
                logger.warning(
                    "Polymarket %s, retrying in %.1fs (attempt %s)",
                    response.status_code,
                    wait,
                    attempt + 1,
                )
                time.sleep(wait)
                continue

            return response

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_exc = e
            _log_connection_error(e)
            if attempt == s.retry_max:
                raise SourceUnavailableError(
                    f"Polymarket unreachable after {s.retry_max + 1} attempts: {e}",
                    context={
                        "event": (
                            "timeout" if isinstance(e, httpx.TimeoutException) else "connect_error"
                        ),
                        "attempts": attempt + 1,
                    },
                ) from e
            wait = _backoff(attempt, s.retry_backoff_s)
            time.sleep(wait)

    if last_exc:
        raise SourceUnavailableError(
            f"Polymarket error: {last_exc}",
            context={"exception_type": type(last_exc).__name__},
        ) from last_exc
    raise RuntimeError("unreachable")
