"""Circuit breaker metrics endpoint for monitoring."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from omen.infrastructure.emitter.signal_emitter import CIRCUIT_NAME_RISKCAST
from omen.infrastructure.resilience.circuit_breaker import get_circuit_breaker

router = APIRouter(tags=["metrics"])


class CircuitBreakerUpdateRequest(BaseModel):
    """Request to update circuit breaker state."""

    state: str = Field(..., description="Target state: 'closed' to reset")


@router.get("/metrics/circuit-breakers")
async def get_circuit_breaker_stats() -> dict:
    """
    Get circuit breaker statistics for monitoring.

    Returns current state and metrics for registered circuit breakers.
    RiskCast hot path circuit is present when an emitter has been used.
    """
    cb = get_circuit_breaker(CIRCUIT_NAME_RISKCAST)
    if cb is None:
        return {
            "circuit_breakers": {},
            "message": "No circuit breakers registered (emitter not yet used)",
        }

    stats = cb.stats
    total = stats.total_calls
    failure_rate = (stats.total_failures / total) if total > 0 else 0.0

    return {
        "circuit_breakers": {
            CIRCUIT_NAME_RISKCAST: {
                "state": stats.state.value,
                "consecutive_failures": stats.consecutive_failures,
                "consecutive_successes": stats.consecutive_successes,
                "total_calls": stats.total_calls,
                "total_failures": stats.total_failures,
                "total_successes": stats.total_successes,
                "total_rejected": stats.total_rejected,
                "failure_rate": round(failure_rate, 4),
                "last_failure_time": (
                    stats.last_failure_time.isoformat() if stats.last_failure_time else None
                ),
                "last_success_time": (
                    stats.last_success_time.isoformat() if stats.last_success_time else None
                ),
                "last_state_change": stats.last_state_change.isoformat(),
            }
        }
    }


@router.patch("/metrics/circuit-breakers/{name}")
async def update_circuit_breaker(name: str, request: CircuitBreakerUpdateRequest) -> dict:
    """
    Update circuit breaker state.

    Set state='closed' to reset the circuit breaker.
    Use only when downstream service is confirmed healthy.
    """
    if name != CIRCUIT_NAME_RISKCAST:
        raise HTTPException(404, detail=f"Unknown circuit breaker: {name}")

    cb = get_circuit_breaker(name)
    if cb is None:
        raise HTTPException(404, detail="Circuit breaker not registered")

    if request.state.lower() == "closed":
        await cb.reset()
        return {"status": "reset", "circuit": name, "state": "closed"}
    else:
        raise HTTPException(400, detail=f"Invalid state: {request.state}. Use 'closed' to reset.")
