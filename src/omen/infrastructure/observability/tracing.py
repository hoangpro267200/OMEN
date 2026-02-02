"""
Distributed Tracing with OpenTelemetry.

Provides end-to-end request tracing across OMEN services.
Integrates with Jaeger, Zipkin, or any OTLP-compatible collector.

Environment Variables:
    OTLP_ENDPOINT: OpenTelemetry collector endpoint (e.g., http://jaeger:4317)
    OMEN_SERVICE_NAME: Service name for tracing (default: omen)
    OMEN_TRACING_ENABLED: Enable/disable tracing (default: true in production)
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])

# Global tracer
_tracer: Optional[Any] = None
_tracing_enabled: bool = False


def setup_tracing(
    service_name: str = "omen",
    otlp_endpoint: Optional[str] = None,
    sample_rate: float = 1.0,
) -> Optional[Any]:
    """
    Configure distributed tracing with OpenTelemetry.
    
    Args:
        service_name: Name to identify this service in traces
        otlp_endpoint: OTLP collector endpoint (e.g., http://jaeger:4317)
        sample_rate: Fraction of requests to trace (0.0-1.0)
    
    Returns:
        Tracer instance if configured, None otherwise
    """
    global _tracer, _tracing_enabled
    
    # Get configuration from environment
    otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")
    service_name = os.getenv("OMEN_SERVICE_NAME", service_name)
    tracing_enabled = os.getenv("OMEN_TRACING_ENABLED", "true").lower() == "true"
    
    if not tracing_enabled:
        logger.info("Tracing disabled via OMEN_TRACING_ENABLED")
        _tracing_enabled = False
        return None
    
    if not otlp_endpoint:
        logger.info("OTLP_ENDPOINT not configured, tracing disabled")
        _tracing_enabled = False
        return None
    
    try:
        # Import OpenTelemetry
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        
        # Create resource with service info
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv("OMEN_VERSION", "2.0.0"),
            "deployment.environment": os.getenv("OMEN_ENV", "development"),
        })
        
        # Create sampler
        sampler = TraceIdRatioBased(sample_rate)
        
        # Create provider
        provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )
        
        # Add OTLP exporter
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        
        # Set as global provider
        trace.set_tracer_provider(provider)
        
        # Get tracer
        _tracer = trace.get_tracer(service_name)
        _tracing_enabled = True
        
        logger.info(
            "Tracing enabled: service=%s, endpoint=%s, sample_rate=%.2f",
            service_name, otlp_endpoint, sample_rate
        )
        
        return _tracer
        
    except ImportError as e:
        logger.warning(
            "OpenTelemetry not installed, tracing disabled: %s. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-exporter-otlp", e
        )
        _tracing_enabled = False
        return None
    except Exception as e:
        logger.error("Failed to setup tracing: %s", e)
        _tracing_enabled = False
        return None


def setup_fastapi_instrumentation(app) -> None:
    """
    Instrument FastAPI application for automatic tracing.
    
    Args:
        app: FastAPI application instance
    """
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    except ImportError:
        logger.debug("FastAPI instrumentation not available")
    except Exception as e:
        logger.warning("Failed to instrument FastAPI: %s", e)


def setup_httpx_instrumentation() -> None:
    """Instrument HTTPX for automatic outbound request tracing."""
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
    except ImportError:
        logger.debug("HTTPX instrumentation not available")
    except Exception as e:
        logger.warning("Failed to instrument HTTPX: %s", e)


def setup_asyncpg_instrumentation() -> None:
    """Instrument asyncpg for automatic database tracing."""
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
        AsyncPGInstrumentor().instrument()
        logger.info("AsyncPG instrumentation enabled")
    except ImportError:
        logger.debug("AsyncPG instrumentation not available")
    except Exception as e:
        logger.warning("Failed to instrument AsyncPG: %s", e)


def setup_redis_instrumentation() -> None:
    """Instrument Redis for automatic cache tracing."""
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
    except ImportError:
        logger.debug("Redis instrumentation not available")
    except Exception as e:
        logger.warning("Failed to instrument Redis: %s", e)


def setup_all_instrumentations(app=None) -> None:
    """
    Setup all available instrumentations.
    
    Args:
        app: Optional FastAPI application instance
    """
    if app:
        setup_fastapi_instrumentation(app)
    setup_httpx_instrumentation()
    setup_asyncpg_instrumentation()
    setup_redis_instrumentation()


def get_tracer() -> Optional[Any]:
    """Get the global tracer instance."""
    return _tracer


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    return _tracing_enabled


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[dict] = None,
    kind: Optional[str] = None,
):
    """
    Context manager for creating trace spans.
    
    Usage:
        with trace_span("process_signal", {"signal_id": signal.id}):
            # ... processing code ...
    
    Args:
        name: Span name
        attributes: Optional span attributes
        kind: Span kind (internal, server, client, producer, consumer)
    """
    if not _tracing_enabled or _tracer is None:
        yield None
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanKind
        
        # Map kind string to SpanKind
        span_kind = SpanKind.INTERNAL
        if kind:
            kind_map = {
                "internal": SpanKind.INTERNAL,
                "server": SpanKind.SERVER,
                "client": SpanKind.CLIENT,
                "producer": SpanKind.PRODUCER,
                "consumer": SpanKind.CONSUMER,
            }
            span_kind = kind_map.get(kind.lower(), SpanKind.INTERNAL)
        
        with _tracer.start_as_current_span(name, kind=span_kind) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span
            
    except Exception as e:
        logger.debug("Tracing error: %s", e)
        yield None


def traced(
    name: Optional[str] = None,
    attributes: Optional[dict] = None,
) -> Callable[[F], F]:
    """
    Decorator for tracing functions.
    
    Usage:
        @traced("process_signal")
        def process_signal(signal: OmenSignal) -> None:
            # ... processing code ...
    
        @traced(attributes={"component": "pipeline"})
        async def run_pipeline() -> None:
            # ... pipeline code ...
    """
    def decorator(func: F) -> F:
        span_name = name or func.__name__
        
        if _is_async(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with trace_span(span_name, attributes):
                    return await func(*args, **kwargs)
            return async_wrapper  # type: ignore
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with trace_span(span_name, attributes):
                    return func(*args, **kwargs)
            return sync_wrapper  # type: ignore
    
    return decorator


def _is_async(func: Callable) -> bool:
    """Check if function is async."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


def add_span_attribute(key: str, value: Any) -> None:
    """
    Add attribute to current span.
    
    Args:
        key: Attribute key
        value: Attribute value
    """
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span:
            span.set_attribute(key, value)
    except Exception:
        pass


def add_span_event(
    name: str,
    attributes: Optional[dict] = None,
) -> None:
    """
    Add event to current span.
    
    Args:
        name: Event name
        attributes: Optional event attributes
    """
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span:
            span.add_event(name, attributes=attributes)
    except Exception:
        pass


def record_exception(exception: Exception) -> None:
    """
    Record exception in current span.
    
    Args:
        exception: Exception to record
    """
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span:
            span.record_exception(exception)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
    except Exception:
        pass


def get_trace_context() -> dict:
    """
    Get current trace context for propagation.
    
    Returns:
        Dict with trace_id and span_id
    """
    if not _tracing_enabled:
        return {}
    
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
    except Exception:
        pass
    
    return {}
