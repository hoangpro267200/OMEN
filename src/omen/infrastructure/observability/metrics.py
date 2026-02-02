"""
Prometheus Metrics

Exposes metrics for:
- Signal emission (count, duration, status)
- Ledger writes (count, size)
- Circuit breaker state
- Ingest requests
- Reconcile operations
"""

import logging
import time
from functools import wraps
from typing import Callable, TypeVar

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════════

REGISTRY = CollectorRegistry()

# ═══════════════════════════════════════════════════════════════════════════════
# OMEN Metrics
# ═══════════════════════════════════════════════════════════════════════════════

SIGNALS_EMITTED = Counter(
    "omen_signals_emitted_total",
    "Total number of signals emitted",
    ["status", "category"],
    registry=REGISTRY,
)

EMIT_DURATION = Histogram(
    "omen_emit_duration_seconds",
    "Time to emit a signal (ledger + hot path)",
    ["status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

LEDGER_WRITES = Counter(
    "omen_ledger_writes_total",
    "Total ledger write operations",
    ["partition", "result"],
    registry=REGISTRY,
)

LEDGER_WRITE_DURATION = Histogram(
    "omen_ledger_write_duration_seconds",
    "Time to write to ledger",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
    registry=REGISTRY,
)

LEDGER_SEGMENT_SIZE = Gauge(
    "omen_ledger_segment_size_bytes",
    "Current segment size in bytes",
    ["partition", "segment"],
    registry=REGISTRY,
)

LEDGER_PARTITION_RECORDS = Gauge(
    "omen_ledger_partition_records_total",
    "Total records in partition",
    ["partition"],
    registry=REGISTRY,
)

CIRCUIT_BREAKER_STATE = Gauge(
    "omen_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["name"],
    registry=REGISTRY,
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "omen_circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["name"],
    registry=REGISTRY,
)

# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Request Metrics (for p50, p95, p99 latency tracking)
# ═══════════════════════════════════════════════════════════════════════════════

HTTP_REQUEST_DURATION = Histogram(
    "omen_http_request_duration_seconds",
    "HTTP request latency by endpoint and method",
    ["method", "endpoint", "status_code"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
    registry=REGISTRY,
)

HTTP_REQUESTS_TOTAL = Counter(
    "omen_http_requests_total",
    "Total HTTP requests by endpoint, method, and status",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "omen_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=REGISTRY,
)

HTTP_REQUEST_SIZE_BYTES = Histogram(
    "omen_http_request_size_bytes",
    "HTTP request body size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
    registry=REGISTRY,
)

HTTP_RESPONSE_SIZE_BYTES = Histogram(
    "omen_http_response_size_bytes",
    "HTTP response body size in bytes",
    ["method", "endpoint", "status_code"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
    registry=REGISTRY,
)

# ═══════════════════════════════════════════════════════════════════════════════
# RiskCast Metrics
# ═══════════════════════════════════════════════════════════════════════════════

INGEST_REQUESTS = Counter(
    "riskcast_ingest_requests_total",
    "Total ingest requests received",
    ["status_code"],
    registry=REGISTRY,
)

INGEST_DURATION = Histogram(
    "riskcast_ingest_duration_seconds",
    "Time to process ingest request",
    ["status_code"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=REGISTRY,
)

RECONCILE_RUNS = Counter(
    "riskcast_reconcile_runs_total",
    "Total reconcile job runs",
    ["partition", "status"],
    registry=REGISTRY,
)

RECONCILE_REPLAYED = Counter(
    "riskcast_reconcile_replayed_total",
    "Total signals replayed by reconcile",
    ["partition"],
    registry=REGISTRY,
)

RECONCILE_DURATION = Histogram(
    "riskcast_reconcile_duration_seconds",
    "Time to reconcile a partition",
    ["status"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

PROCESSED_SIGNALS = Gauge(
    "riskcast_processed_signals_total",
    "Total signals in processed_signals table",
    ["partition"],
    registry=REGISTRY,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Decorators
# ═══════════════════════════════════════════════════════════════════════════════

T = TypeVar("T")


def timed(histogram: Histogram, labels: dict | None = None):
    """Decorator to measure function duration."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        import asyncio

        @wraps(func)
        async def async_wrapper(*args: object, **kwargs: object) -> T:
            start = time.perf_counter()
            status = "success"
            try:
                return await func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start
                label_values = {**(labels or {}), "status": status}
                if getattr(histogram, "_labelnames", ()):
                    histogram.labels(**label_values).observe(duration)
                else:
                    histogram.observe(duration)

        @wraps(func)
        def sync_wrapper(*args: object, **kwargs: object) -> T:
            start = time.perf_counter()
            status = "success"
            try:
                return func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start
                label_values = {**(labels or {}), "status": status}
                if getattr(histogram, "_labelnames", ()):
                    histogram.labels(**label_values).observe(duration)
                else:
                    histogram.observe(duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def counted(counter: Counter, labels: dict | None = None):
    """Decorator to count function calls."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        import asyncio

        @wraps(func)
        async def async_wrapper(*args: object, **kwargs: object) -> T:
            try:
                result = await func(*args, **kwargs)
                counter.labels(**(labels or {}), status="success").inc()
                return result
            except Exception:
                counter.labels(**(labels or {}), status="error").inc()
                raise

        @wraps(func)
        def sync_wrapper(*args: object, **kwargs: object) -> T:
            try:
                result = func(*args, **kwargs)
                counter.labels(**(labels or {}), status="success").inc()
                return result
            except Exception:
                counter.labels(**(labels or {}), status="error").inc()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def get_metrics() -> bytes:
    """Generate metrics in Prometheus format."""
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get content type for metrics response."""
    return CONTENT_TYPE_LATEST


def update_circuit_breaker_state(name: str, state: str) -> None:
    """Update circuit breaker state gauge."""
    state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, -1)
    CIRCUIT_BREAKER_STATE.labels(name=name).set(state_value)
