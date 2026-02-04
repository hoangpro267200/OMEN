"""Health check endpoints."""

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Query, Response

from omen.infrastructure.middleware.request_tracking import (
    get_active_request_count,
    is_shutting_down,
)
from omen.infrastructure.health.source_health_aggregator import (
    SourceHealthSummary,
    get_health_aggregator,
)
from omen.application.ports.health_checkable import HealthCheckResult
from omen.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def health_check(response: Response):
    """
    Basic health check.
    Returns 503 during shutdown so load balancers stop sending traffic.
    """
    if is_shutting_down():
        response.status_code = 503
        return {
            "status": "shutting_down",
            "message": "Service is shutting down, not accepting new requests",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    return {
        "status": "healthy",
        "service": "omen",
        "active_requests": get_active_request_count(),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.get("/ready")
async def readiness_check(response: Response):
    """
    Readiness check (e.g. Kubernetes).
    Returns 503 if not ready to serve traffic (e.g. shutting down).
    """
    if is_shutting_down():
        response.status_code = 503
        return {
            "ready": False,
            "reason": "shutting_down",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    checks: dict[str, bool] = {}
    check_details: dict[str, str] = {}

    try:
        checks["ledger"], check_details["ledger"] = await _check_ledger_writable()
    except Exception as e:
        checks["ledger"] = False
        check_details["ledger"] = f"Error: {str(e)}"

    try:
        checks["riskcast"], check_details["riskcast"] = await _check_riskcast_reachable()
    except Exception as e:
        checks["riskcast"] = False
        check_details["riskcast"] = f"Error: {str(e)}"

    try:
        checks["redis"], check_details["redis"] = await _check_redis_connection()
    except Exception as e:
        checks["redis"] = False
        check_details["redis"] = f"Error: {str(e)}"

    try:
        checks["database"], check_details["database"] = await _check_database_connection()
    except Exception as e:
        checks["database"] = False
        check_details["database"] = f"Error: {str(e)}"

    all_ready = all(checks.values()) if checks else True
    if not all_ready:
        response.status_code = 503

    return {
        "ready": all_ready,
        "checks": checks,
        "details": check_details,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.get("/live")
async def liveness_check():
    """Liveness check."""
    return {"status": "alive"}


@router.get("/auth")
async def auth_health():
    """
    Authentication system health check.
    
    Returns:
    - Auth configuration status
    - Rate limiter statistics
    - Any configuration issues (especially for production)
    """
    from omen.infrastructure.security.unified_auth import get_auth_health
    return get_auth_health()


@router.get("/redis")
async def redis_health():
    """
    Redis state manager health check.
    
    Returns:
    - Connection status
    - Latency
    - Memory usage
    - Fallback mode indicator
    """
    from omen.infrastructure.redis import get_redis_state_manager
    
    manager = get_redis_state_manager()
    return await manager.health_check()


async def _check_ledger_writable() -> tuple[bool, str]:
    """
    Check if ledger directory is writable.

    Performs an actual write test to verify file system permissions.
    """
    config = get_config()
    ledger_path = (
        Path(config.ledger_base_path)
        if hasattr(config, "ledger_base_path")
        else Path(".demo/ledger")
    )

    try:
        # Ensure directory exists
        ledger_path.mkdir(parents=True, exist_ok=True)

        # Try to write a test file
        test_file = ledger_path / ".health_check"
        test_content = f"health_check_{datetime.now(timezone.utc).isoformat()}"

        # Write and read back
        test_file.write_text(test_content)
        read_back = test_file.read_text()

        # Clean up
        test_file.unlink(missing_ok=True)

        if read_back == test_content:
            return True, f"Ledger writable at {ledger_path}"
        else:
            return False, "Ledger write verification failed"

    except PermissionError as e:
        logger.warning(f"Ledger permission error: {e}")
        return False, f"Permission denied: {ledger_path}"
    except OSError as e:
        logger.warning(f"Ledger OS error: {e}")
        return False, f"OS error: {str(e)}"
    except Exception as e:
        logger.warning(f"Ledger check error: {e}")
        return False, f"Unknown error: {str(e)}"


async def _check_riskcast_reachable() -> tuple[bool, str]:
    """
    Check if RiskCast API is reachable.

    Attempts to connect to RiskCast health endpoint.
    """
    riskcast_url = os.getenv("RISKCAST_URL", "http://localhost:8001")
    health_endpoint = f"{riskcast_url}/health"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_endpoint)

            if response.status_code == 200:
                return True, f"RiskCast healthy at {riskcast_url}"
            else:
                return False, f"RiskCast returned {response.status_code}"

    except httpx.ConnectError:
        # RiskCast not running is OK in development
        env = os.getenv("OMEN_ENV", "development")
        if env != "production":
            return True, f"RiskCast not running (acceptable in {env})"
        return False, f"Cannot connect to RiskCast at {riskcast_url}"
    except httpx.TimeoutException:
        return False, f"RiskCast timeout at {riskcast_url}"
    except Exception as e:
        logger.warning(f"RiskCast check error: {e}")
        return False, f"Error: {str(e)}"


async def _check_redis_connection() -> tuple[bool, str]:
    """
    Check if Redis is reachable.
    
    Returns (True, message) if connected or Redis is not configured.
    Returns (False, message) if configured but unreachable.
    """
    redis_url = os.getenv("REDIS_URL")
    
    if not redis_url:
        return True, "Redis not configured (using in-memory fallback)"
    
    try:
        from omen.infrastructure.redis.state_manager import get_redis_state_manager
        
        manager = get_redis_state_manager()
        health = await manager.health_check()
        
        if health.get("status") == "healthy":
            latency = health.get("latency_ms", 0)
            return True, f"Redis healthy (latency: {latency:.1f}ms)"
        elif health.get("status") == "fallback":
            return True, "Redis using in-memory fallback"
        else:
            return False, health.get("error", "Redis unhealthy")
            
    except ImportError:
        return True, "Redis package not installed (using in-memory)"
    except Exception as e:
        env = os.getenv("OMEN_ENV", "development")
        if env != "production":
            return True, f"Redis error (acceptable in {env}): {e}"
        return False, f"Redis error: {e}"


async def _check_database_connection() -> tuple[bool, str]:
    """
    Check if PostgreSQL database is reachable.
    
    Returns (True, message) if connected or database is not configured.
    Returns (False, message) if configured but unreachable.
    """
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        return True, "Database not configured (using in-memory)"
    
    try:
        import asyncpg
        
        # Quick connection test
        conn = await asyncpg.connect(db_url, timeout=5)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            return True, "PostgreSQL connected"
        else:
            return False, "PostgreSQL query failed"
            
    except ImportError:
        return True, "asyncpg not installed (using in-memory)"
    except Exception as e:
        env = os.getenv("OMEN_ENV", "development")
        if env != "production":
            return True, f"Database error (acceptable in {env}): {e}"
        return False, f"Database error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA SOURCE HEALTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/sources",
    response_model=SourceHealthSummary,
    summary="Check all data sources health",
    description="Returns health status for all registered data sources.",
)
async def check_all_sources_health(
    force: bool = Query(False, description="Bypass cache and force fresh checks"),
) -> SourceHealthSummary:
    """
    Check health of all registered data sources.

    Returns aggregated health information including:
    - Overall system status
    - Per-source status
    - Response latencies
    - Error messages for unhealthy sources

    Results are cached for 30 seconds by default. Use `force=true` to bypass.
    """
    aggregator = get_health_aggregator()
    return await aggregator.check_all(force=force)


@router.get(
    "/sources/{source_name}",
    response_model=HealthCheckResult,
    summary="Check specific source health",
    description="Returns health status for a specific data source.",
)
async def check_source_health(
    source_name: str,
) -> HealthCheckResult:
    """
    Check health of a specific data source.

    Available sources (when registered):
    - polymarket: Polymarket prediction market API
    - stock: Stock price data (yfinance + vnstock)
    - news: News article API (NewsAPI)
    - commodity: Commodity prices (Alpha Vantage)
    - weather: Weather alerts (OpenWeatherMap)
    - ais: Maritime AIS data
    - freight: Freight rates data
    """
    aggregator = get_health_aggregator()
    return await aggregator.check_source(source_name)


@router.get(
    "/sources/list",
    summary="List registered sources",
    description="Returns list of all registered data sources.",
)
async def list_registered_sources() -> dict:
    """
    List all registered data sources for health monitoring.
    """
    aggregator = get_health_aggregator()
    return {
        "sources": aggregator.registered_sources,
        "count": len(aggregator.registered_sources),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/circuit-breakers",
    summary="Get all circuit breaker states",
    description="Returns status of all registered circuit breakers.",
)
async def get_circuit_breakers() -> dict:
    """
    Get status of all circuit breakers.
    
    Returns:
    - State (CLOSED/OPEN/HALF_OPEN)
    - Failure counts
    - Last failure time
    - Statistics
    """
    from omen.infrastructure.resilience.circuit_breaker import _circuit_breakers
    
    breakers = {}
    for name, cb in _circuit_breakers.items():
        stats = cb.stats
        breakers[name] = {
            "state": stats.state.value,
            "failure_count": stats.consecutive_failures,
            "success_count": stats.consecutive_successes,
            "total_calls": stats.total_calls,
            "total_failures": stats.total_failures,
            "total_successes": stats.total_successes,
            "total_rejected": stats.total_rejected,
            "last_failure": stats.last_failure_time.isoformat() if stats.last_failure_time else None,
            "last_success": stats.last_success_time.isoformat() if stats.last_success_time else None,
            "last_state_change": stats.last_state_change.isoformat() if stats.last_state_change else None,
        }
    
    # Summary
    open_count = sum(1 for b in breakers.values() if b["state"] == "open")
    half_open_count = sum(1 for b in breakers.values() if b["state"] == "half_open")
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "total": len(breakers),
            "closed": len(breakers) - open_count - half_open_count,
            "open": open_count,
            "half_open": half_open_count,
            "healthy": open_count == 0,
        },
        "breakers": breakers,
    }


@router.post(
    "/circuit-breakers/{name}/reset",
    summary="Reset a circuit breaker",
    description="Manually reset a circuit breaker to CLOSED state.",
)
async def reset_circuit_breaker(name: str) -> dict:
    """
    Manually reset a circuit breaker.
    
    Use this to force recovery after confirming a service is healthy.
    """
    from omen.infrastructure.resilience.circuit_breaker import get_circuit_breaker, _circuit_breakers
    
    cb = get_circuit_breaker(name)
    if cb is None:
        return {
            "success": False,
            "error": f"Circuit breaker '{name}' not found",
            "available": list(_circuit_breakers.keys()),
        }
    
    await cb.reset()
    return {
        "success": True,
        "name": name,
        "new_state": cb.state.value,
        "message": f"Circuit breaker '{name}' has been reset to CLOSED",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE SYSTEM HEALTH
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/system",
    summary="Comprehensive system health",
    description="Returns complete health status of all system components.",
)
async def system_health(response: Response) -> dict:
    """
    Comprehensive system health check.
    
    Aggregates:
    - Basic health status
    - Data sources
    - Circuit breakers
    - Authentication
    - Active requests
    """
    from omen.infrastructure.resilience.circuit_breaker import _circuit_breakers
    from omen.infrastructure.security.unified_auth import get_auth_health
    
    health_data = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "healthy",
        "components": {},
    }
    
    issues = []
    
    # 1. Basic health
    if is_shutting_down():
        health_data["status"] = "shutting_down"
        issues.append("Service is shutting down")
    
    health_data["components"]["requests"] = {
        "active": get_active_request_count(),
        "shutting_down": is_shutting_down(),
    }
    
    # 2. Authentication
    auth_health = get_auth_health()
    health_data["components"]["auth"] = {
        "status": auth_health.get("status", "unknown"),
        "api_keys_configured": auth_health.get("api_keys_configured", 0),
        "issues": auth_health.get("production_issues", []),
    }
    if auth_health.get("production_issues"):
        issues.extend(auth_health["production_issues"])
    
    # 3. Circuit breakers
    open_breakers = [name for name, cb in _circuit_breakers.items() if cb.state.value == "open"]
    health_data["components"]["circuit_breakers"] = {
        "total": len(_circuit_breakers),
        "open": len(open_breakers),
        "open_names": open_breakers,
    }
    if open_breakers:
        issues.append(f"Circuit breakers open: {', '.join(open_breakers)}")
    
    # 4. Data sources
    try:
        aggregator = get_health_aggregator()
        source_health = await aggregator.check_all(force=False)
        health_data["components"]["data_sources"] = {
            "status": source_health.status,
            "healthy_count": source_health.healthy_count,
            "unhealthy_count": source_health.unhealthy_count,
        }
        if source_health.status != "healthy":
            issues.append(f"Data sources unhealthy: {source_health.unhealthy_count}")
    except Exception as e:
        health_data["components"]["data_sources"] = {
            "status": "error",
            "error": str(e),
        }
        issues.append(f"Data source check failed: {e}")
    
    # Overall status
    if issues:
        health_data["status"] = "degraded" if health_data["status"] == "healthy" else health_data["status"]
        health_data["issues"] = issues
        response.status_code = 503 if "shutting_down" in health_data["status"] else 200
    
    return health_data
