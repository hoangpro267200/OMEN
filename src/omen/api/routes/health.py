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


async def _check_ledger_writable() -> tuple[bool, str]:
    """
    Check if ledger directory is writable.
    
    Performs an actual write test to verify file system permissions.
    """
    config = get_config()
    ledger_path = Path(config.ledger_base_path) if hasattr(config, 'ledger_base_path') else Path(".demo/ledger")
    
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
