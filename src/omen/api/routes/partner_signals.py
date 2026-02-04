"""
Partner Signals API - Pure Signal Engine.

This endpoint returns SIGNALS only, not risk decisions.
Risk decisions (SAFE/WARNING/CRITICAL) should be made by RiskCast.

OMEN provides:
- Raw metrics (price, volume, fundamentals)
- Evidence trail
- Confidence scores
- Market context

OMEN does NOT provide:
- Risk verdicts
- Risk status
- Overall risk assessment
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from omen.adapters.inbound.partner_risk import (
    LogisticsSignalMonitor,
    PartnerSignalResponse,
    PartnerSignalsListResponse,
    LOGISTICS_COMPANIES,
)
from omen.api.route_dependencies import require_partners_read, require_partners_write
from omen.infrastructure.security.unified_auth import AuthContext

router = APIRouter(
    prefix="/partner-signals",
    tags=["Partner Signals"],
)


@router.get(
    "/",
    response_model=PartnerSignalsListResponse,
    summary="Get signals for all monitored partners",
    description="""
    Returns raw signal metrics for logistics partners.
    
    **IMPORTANT**: This endpoint returns SIGNALS only, not risk decisions.
    
    RiskCast should use these signals to make risk assessments based on:
    - Order context
    - User risk appetite
    - Business rules
    
    **OMEN does NOT make risk decisions.**
    
    Response includes:
    - `signals`: Raw metrics (price, volume, fundamentals)
    - `evidence`: Evidence trail for audit
    - `confidence`: Data quality indicators
    - `omen_suggestion`: Optional suggestion (NOT a decision)
    
    Response does NOT include:
    - `risk_status`
    - `overall_risk`
    - `risk_breakdown`
    """,
    responses={
        200: {
            "description": "Signals retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "timestamp": "2026-02-01T10:30:00Z",
                        "total_partners": 5,
                        "partners": [
                            {
                                "symbol": "HAH",
                                "company_name": "Hai An Transport",
                                "signals": {
                                    "price_current": 42000,
                                    "price_change_percent": -3.5,
                                    "volume": 1234567,
                                    "pe_ratio": 12.5,
                                    "roe": 15.2,
                                },
                                "confidence": {
                                    "overall_confidence": 0.85,
                                    "data_completeness": 0.9,
                                },
                                "evidence": [],
                                "omen_suggestion": None,
                                "suggestion_disclaimer": "This is OMEN's signal-based suggestion only...",
                            }
                        ],
                        "aggregated_metrics": {"avg_volatility": 0.025, "avg_liquidity": 0.7},
                    }
                }
            },
        },
        503: {"description": "Data source unavailable"},
    },
)
async def get_all_partner_signals(
    symbols: Optional[str] = Query(
        default=None,
        description="Comma-separated list of symbols (default: GMD,HAH,VOS,VSC,PVT)",
        example="HAH,GMD,VOS",
    ),
    include_evidence: bool = Query(default=True, description="Include signal evidence in response"),
    include_market_context: bool = Query(
        default=False, description="Include market context (VNINDEX, sector)"
    ),
    auth: AuthContext = Depends(require_partners_read),  # RBAC: read:partners
) -> PartnerSignalsListResponse:
    """
    Get signals for all monitored partners.

    Returns raw signal metrics - NO risk verdict.
    """
    try:
        symbol_list = None
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]

        monitor = LogisticsSignalMonitor(symbols=symbol_list)
        response = monitor.get_all_signals()

        # Optionally strip evidence
        if not include_evidence:
            partners = []
            for p in response.partners:
                # Create new response without evidence
                partners.append(
                    PartnerSignalResponse(
                        symbol=p.symbol,
                        company_name=p.company_name,
                        sector=p.sector,
                        exchange=p.exchange,
                        signals=p.signals,
                        confidence=p.confidence,
                        evidence=[],  # Empty
                        market_context=p.market_context if include_market_context else None,
                        omen_suggestion=p.omen_suggestion,
                        suggestion_confidence=p.suggestion_confidence,
                        signal_id=p.signal_id,
                        timestamp=p.timestamp,
                    )
                )
            response = PartnerSignalsListResponse(
                timestamp=response.timestamp,
                total_partners=response.total_partners,
                market_context=response.market_context if include_market_context else {},
                partners=partners,
                aggregated_metrics=response.aggregated_metrics,
                data_quality=response.data_quality,
            )

        return response

    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "DATA_SOURCE_UNAVAILABLE",
                "message": f"vnstock library not available: {str(e)}",
                "suggestion": "Install vnstock with: pip install vnstock",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"error": "SIGNAL_FETCH_ERROR", "message": str(e)}
        )


@router.get(
    "/partners",
    summary="List all monitored logistics partners",
    description="Returns metadata about each partner company.",
)
async def list_partners(
    auth: AuthContext = Depends(require_partners_read),  # RBAC: read:partners
) -> dict:
    """List all monitored logistics partners."""
    return {
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
    "/{symbol}",
    response_model=PartnerSignalResponse,
    summary="Get signals for a specific partner",
    description="""
    Returns detailed signals for a single logistics partner.
    
    **IMPORTANT**: Returns SIGNALS only, not risk decisions.
    """,
)
async def get_partner_signal(
    symbol: str,
    include_evidence: bool = Query(default=True, description="Include signal evidence"),
    auth: AuthContext = Depends(require_partners_read),  # RBAC: read:partners
) -> PartnerSignalResponse:
    """
    Get detailed signals for one partner.

    Returns metrics, evidence, confidence - NO risk verdict.
    """
    symbol = symbol.upper()

    try:
        monitor = LogisticsSignalMonitor(symbols=[symbol])
        response = monitor.get_partner_signals(symbol)

        if not include_evidence:
            response = PartnerSignalResponse(
                symbol=response.symbol,
                company_name=response.company_name,
                sector=response.sector,
                exchange=response.exchange,
                signals=response.signals,
                confidence=response.confidence,
                evidence=[],
                market_context=response.market_context,
                omen_suggestion=response.omen_suggestion,
                suggestion_confidence=response.suggestion_confidence,
                signal_id=response.signal_id,
                timestamp=response.timestamp,
            )

        return response

    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "DATA_SOURCE_UNAVAILABLE",
                "message": f"vnstock library not available: {str(e)}",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SIGNAL_FETCH_ERROR",
                "message": f"Error fetching signals for {symbol}: {str(e)}",
            },
        )


@router.get(
    "/{symbol}/price",
    summary="Get raw price data for a partner",
    description="Returns real-time price data without any risk assessment.",
)
async def get_partner_price(
    symbol: str,
    auth: AuthContext = Depends(require_partners_read),  # RBAC: read:partners
) -> dict:
    """Get raw price data for a logistics partner."""
    symbol = symbol.upper()

    try:
        monitor = LogisticsSignalMonitor(symbols=[symbol])
        return monitor.fetch_price_data(symbol)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"vnstock library not available: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price for {symbol}: {str(e)}")


@router.get(
    "/{symbol}/fundamentals",
    summary="Get fundamental health indicators",
    description="Returns PE, ROE, and other fundamental metrics without risk classification.",
)
async def get_partner_fundamentals(
    symbol: str,
    auth: AuthContext = Depends(require_partners_read),  # RBAC: read:partners
) -> dict:
    """Get fundamental health indicators for a logistics partner."""
    symbol = symbol.upper()

    try:
        monitor = LogisticsSignalMonitor(symbols=[symbol])
        return monitor.fetch_health_indicators(symbol)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"vnstock library not available: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching fundamentals for {symbol}: {str(e)}"
        )
