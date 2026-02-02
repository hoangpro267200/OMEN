"""
Structured JSON Logging with Trace Context

Features:
- JSON formatted logs for ELK/Datadog/CloudWatch
- Request-scoped trace_id injection
- Automatic exception formatting
- Sensitive data redaction
"""

import asyncio
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# Context Variables (request-scoped)
# ═══════════════════════════════════════════════════════════════════════════════

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_signal_id: ContextVar[str | None] = ContextVar("signal_id", default=None)
_partition: ContextVar[str | None] = ContextVar("partition", default=None)


def set_trace_context(
    trace_id: str | None = None,
    request_id: str | None = None,
    signal_id: str | None = None,
    partition: str | None = None,
) -> None:
    """Set trace context for current async context."""
    if trace_id is not None:
        _trace_id.set(trace_id)
    if request_id is not None:
        _request_id.set(request_id)
    if signal_id is not None:
        _signal_id.set(signal_id)
    if partition is not None:
        _partition.set(partition)


def clear_trace_context() -> None:
    """Clear trace context."""
    _trace_id.set(None)
    _request_id.set(None)
    _signal_id.set(None)
    _partition.set(None)


def get_trace_context() -> dict[str, Any]:
    """Get current trace context as dict."""
    ctx: dict[str, Any] = {}
    if trace_id := _trace_id.get():
        ctx["trace_id"] = trace_id
    if request_id := _request_id.get():
        ctx["request_id"] = request_id
    if signal_id := _signal_id.get():
        ctx["signal_id"] = signal_id
    if partition := _partition.get():
        ctx["partition"] = partition
    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# JSON Formatter
# ═══════════════════════════════════════════════════════════════════════════════


class StructuredJsonFormatter(logging.Formatter):
    """
    JSON formatter with trace context injection.

    Output format:
    {
        "timestamp": "2024-01-29T10:00:00.000Z",
        "level": "INFO",
        "logger": "omen.emitter",
        "message": "Signal emitted",
        "trace_id": "abc123",
        "signal_id": "OMEN-123",
        "module": "signal_emitter",
        "function": "emit",
        "line": 42
    }
    """

    RESERVED_ATTRS = frozenset(
        {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "message",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        log_data.update(get_trace_context())
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS:
                log_data[key] = value
        return json.dumps(log_data, default=str, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════════
# Pretty Formatter (for development)
# ═══════════════════════════════════════════════════════════════════════════════


class PrettyFormatter(logging.Formatter):
    """Pretty formatter for development with colors."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ctx = get_trace_context()
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        level = f"{color}{record.levelname:8}{self.RESET}"
        msg = f"{timestamp} | {level} | {record.name} | {record.getMessage()}"
        if ctx_str:
            msg += f" | {ctx_str}"
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        return msg


# ═══════════════════════════════════════════════════════════════════════════════
# Setup Functions
# ═══════════════════════════════════════════════════════════════════════════════


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    service_name: str = "omen",
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format (True for production, False for dev)
        service_name: Service name for log context
    """
    from omen.infrastructure.security.redaction import RedactingWrapperFormatter

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        base_formatter: logging.Formatter = StructuredJsonFormatter()
    else:
        base_formatter = PrettyFormatter()
    handler.setFormatter(RedactingWrapperFormatter(base_formatter))
    root_logger.addHandler(handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logger = logging.getLogger(service_name)
    logger.info(
        "Logging configured",
        extra={"format": "json" if json_format else "pretty", "level": level},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Logging Decorators
# ═══════════════════════════════════════════════════════════════════════════════


def log_function_call(logger: logging.Logger):
    """Decorator to log function entry and exit."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.debug("Entering %s", func.__name__)
            try:
                result = await func(*args, **kwargs)
                logger.debug("Exiting %s", func.__name__)
                return result
            except Exception as e:
                logger.error("Error in %s: %s", func.__name__, e, exc_info=True)
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.debug("Entering %s", func.__name__)
            try:
                result = func(*args, **kwargs)
                logger.debug("Exiting %s", func.__name__)
                return result
            except Exception as e:
                logger.error("Error in %s: %s", func.__name__, e, exc_info=True)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
