"""
⚠️ DEPRECATED - Partner Risk API endpoints.

This module is DEPRECATED. OMEN is a Signal Engine, not a Decision Engine.

Migration:
- Use /api/v1/partner-signals/ instead
- Risk decisions (SAFE/WARNING/CRITICAL) should be made by RiskCast

See: https://docs.omen.io/migration/v2-signals
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Literal

router = APIRouter(tags=["Partner Risk (DEPRECATED)"])


DEPRECATION_RESPONSE = {
    "error": "ENDPOINT_DEPRECATED",
    "message": "This endpoint has been deprecated. OMEN is a Signal Engine, not a Decision Engine.",
    "migration": {
        "new_endpoint": "/api/v1/partner-signals/",
        "documentation": "https://docs.omen.io/migration/v2-signals",
        "reason": "Risk decisions (SAFE/WARNING/CRITICAL) should be made by RiskCast based on order context and user risk appetite.",
    },
    "example_migration": {
        "old": "GET /api/v1/partner-risk/partners/{symbol}",
        "new": "GET /api/v1/partner-signals/{symbol}",
        "note": "New endpoint returns signals/metrics instead of risk verdicts",
    },
}


@router.get(
    "/partners",
    deprecated=True,
    summary="⚠️ DEPRECATED - Use /api/v1/partner-signals/partners",
    description="""
    **⚠️ This endpoint is DEPRECATED.**
    
    OMEN is a Signal Engine, not a Decision Engine.
    
    **Migration:**
    - Use `GET /api/v1/partner-signals/partners` instead
    - The new endpoint returns the same partner list
    """,
)
async def list_partners() -> dict:
    """
    ⚠️ DEPRECATED - List all monitored logistics partners.

    Use GET /api/v1/partner-signals/partners instead.
    """
    # Still functional but with deprecation warning
    from omen.adapters.inbound.partner_risk.monitor import LOGISTICS_COMPANIES

    return {
        "_deprecated": True,
        "_migration": "Use GET /api/v1/partner-signals/partners instead",
        "partners": [
            {
                "symbol": symbol,
                **info,
            }
            for symbol, info in LOGISTICS_COMPANIES.items()
        ],
        "total": len(LOGISTICS_COMPANIES),
    }


@router.get(
    "/partners/{symbol}",
    deprecated=True,
    summary="⚠️ DEPRECATED - Use /api/v1/partner-signals/{symbol}",
)
async def get_partner_risk(symbol: str) -> dict:
    """
    ⚠️ DEPRECATED - Get risk assessment for a specific partner.

    This endpoint violates Signal Engine principles by returning risk verdicts.

    **Migration:**
    - Use `GET /api/v1/partner-signals/{symbol}` instead
    - The new endpoint returns signals/metrics
    - RiskCast should make risk decisions
    """
    raise HTTPException(status_code=410, detail=DEPRECATION_RESPONSE)


@router.get(
    "/partners/{symbol}/price",
    deprecated=True,
    summary="⚠️ DEPRECATED - Use /api/v1/partner-signals/{symbol}/price",
)
async def get_partner_price(symbol: str) -> dict:
    """
    ⚠️ DEPRECATED - Use /api/v1/partner-signals/{symbol}/price instead.
    """
    raise HTTPException(
        status_code=410,
        detail={**DEPRECATION_RESPONSE, "new_endpoint": f"/api/v1/partner-signals/{symbol}/price"},
    )


@router.get(
    "/partners/{symbol}/health",
    deprecated=True,
    summary="⚠️ DEPRECATED - Use /api/v1/partner-signals/{symbol}/fundamentals",
)
async def get_partner_health(symbol: str) -> dict:
    """
    ⚠️ DEPRECATED - Use /api/v1/partner-signals/{symbol}/fundamentals instead.
    """
    raise HTTPException(
        status_code=410,
        detail={
            **DEPRECATION_RESPONSE,
            "new_endpoint": f"/api/v1/partner-signals/{symbol}/fundamentals",
        },
    )


@router.get(
    "/portfolio",
    deprecated=True,
    summary="⚠️ DEPRECATED - Use /api/v1/partner-signals/",
)
async def get_portfolio_summary(
    symbols: str | None = Query(default=None),
) -> dict:
    """
    ⚠️ DEPRECATED - This endpoint returns risk verdicts which violates Signal Engine principles.

    **Migration:**
    - Use `GET /api/v1/partner-signals/` instead
    - The new endpoint returns signals/metrics without risk verdicts
    - RiskCast should compute portfolio risk from signals
    """
    raise HTTPException(
        status_code=410,
        detail={
            **DEPRECATION_RESPONSE,
            "reason": "Portfolio risk summary with overall_risk violates Signal Engine principles. "
            "RiskCast should compute portfolio-level risk from individual signals.",
        },
    )


@router.get(
    "/alerts",
    deprecated=True,
    summary="⚠️ DEPRECATED - Signal Engine does not emit alerts",
)
async def get_risk_alerts(
    min_level: Literal["CAUTION", "WARNING", "CRITICAL"] = Query(default="WARNING"),
) -> dict:
    """
    ⚠️ DEPRECATED - OMEN is a Signal Engine, not an Alert Engine.

    **Migration:**
    - Use `GET /api/v1/partner-signals/` to get signals
    - RiskCast should evaluate signals and generate alerts based on business rules
    """
    raise HTTPException(
        status_code=410,
        detail={
            **DEPRECATION_RESPONSE,
            "reason": "OMEN is a Signal Engine. Alert generation based on risk levels "
            "should be implemented in RiskCast, not OMEN.",
        },
    )


@router.post(
    "/webhook/clawbot",
    deprecated=True,
    summary="⚠️ DEPRECATED - Clawbot integration moved to RiskCast",
)
async def trigger_clawbot_notification() -> dict:
    """
    ⚠️ DEPRECATED - Clawbot notification should be triggered by RiskCast, not OMEN.

    **Migration:**
    - RiskCast should consume signals from OMEN
    - RiskCast evaluates risk and triggers Clawbot notifications
    - OMEN only provides signals, not notifications
    """
    raise HTTPException(
        status_code=410,
        detail={
            **DEPRECATION_RESPONSE,
            "reason": "Clawbot notification is a risk-based action. "
            "RiskCast should evaluate signals and trigger notifications.",
        },
    )
