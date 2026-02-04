"""
LIVE Mode Status API.

Provides backend-authoritative LIVE mode validation for the frontend.
This is the SINGLE SOURCE OF TRUTH for whether LIVE mode is allowed.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, List

from omen.infrastructure.data_integrity import (
    get_source_registry,
    validate_live_mode,
    SourceType,
)
from omen.api.route_dependencies import require_live_mode_read, require_live_mode_write
from omen.infrastructure.security.unified_auth import AuthContext

router = APIRouter(prefix="/live-mode", tags=["Live Mode"])


class SourceStatus(BaseModel):
    """Status of a single data source."""
    name: str
    source_type: str  # "real", "mock", "disabled"
    provider_name: str
    enabled: bool
    health: str
    reason: str


class LiveModeStatus(BaseModel):
    """
    Backend-authoritative LIVE mode status.
    
    The frontend MUST use this to determine if LIVE mode can be shown.
    """
    can_go_live: bool
    blockers: List[str]
    sources: Dict[str, SourceStatus]
    summary: Dict[str, int]
    checked_at: str
    
    # Clear instructions for the frontend
    live_allowed: bool
    demo_required: bool
    message: str


@router.get("/status", response_model=LiveModeStatus)
async def get_live_mode_status(
    auth: AuthContext = Depends(require_live_mode_read),  # RBAC: read:live-mode
) -> LiveModeStatus:
    """
    Get LIVE mode status.
    
    This endpoint is the SINGLE SOURCE OF TRUTH for LIVE mode validation.
    
    **Frontend MUST:**
    - Call this before showing LIVE toggle
    - Disable LIVE toggle if `can_go_live` is false
    - Show blockers to user if LIVE is not allowed
    - NEVER claim LIVE if this returns `can_go_live: false`
    """
    registry = get_source_registry()
    status = registry.get_live_mode_status()
    
    can_go_live = status["can_go_live"]
    blockers = status["blockers"]
    
    # Convert sources to response format
    sources = {}
    for name, info in status["sources"].items():
        sources[name] = SourceStatus(
            name=info["name"],
            source_type=info["source_type"],
            provider_name=info["provider_name"],
            enabled=info["enabled"],
            health=info["health"],
            reason=info["reason"],
        )
    
    # Generate user-friendly message
    if can_go_live:
        message = "All data sources are configured for LIVE mode."
    else:
        mock_count = status["summary"]["mock_count"]
        message = f"LIVE mode blocked: {mock_count} source(s) using mock data."
    
    return LiveModeStatus(
        can_go_live=can_go_live,
        blockers=blockers,
        sources=sources,
        summary=status["summary"],
        checked_at=status["checked_at"],
        live_allowed=can_go_live,
        demo_required=not can_go_live,
        message=message,
    )


@router.get("/sources")
async def list_sources(
    auth: AuthContext = Depends(require_live_mode_read),  # RBAC: read:live-mode
) -> dict:
    """
    List all data sources and their configurations.
    
    Returns detailed information about each source including:
    - Provider type (real/mock/disabled)
    - Configuration status
    - Health status
    """
    registry = get_source_registry()
    sources = registry.get_all_sources()
    
    return {
        "sources": [s.to_dict() for s in sources],
        "total": len(sources),
        "real_count": len([s for s in sources if s.source_type == SourceType.REAL]),
        "mock_count": len([s for s in sources if s.source_type == SourceType.MOCK]),
    }


@router.get("/blockers")
async def get_blockers(
    auth: AuthContext = Depends(require_live_mode_read),  # RBAC: read:live-mode
) -> dict:
    """
    Get list of blockers preventing LIVE mode.
    
    Returns an empty list if LIVE mode is allowed.
    """
    can_go_live, blockers = validate_live_mode()
    
    return {
        "can_go_live": can_go_live,
        "blockers": blockers,
        "count": len(blockers),
    }


@router.get("/production-readiness")
async def get_production_readiness(
    auth: AuthContext = Depends(require_live_mode_read),  # RBAC: read:live-mode
) -> dict:
    """
    Get production readiness assessment.
    
    This endpoint is designed for enterprise due diligence.
    Returns a comprehensive assessment of system data integrity.
    """
    import os
    from datetime import datetime, timezone
    
    registry = get_source_registry()
    can_go_live, blockers = validate_live_mode()
    
    sources = registry.get_all_sources()
    real_sources = [s for s in sources if s.source_type == SourceType.REAL]
    mock_sources = [s for s in sources if s.source_type == SourceType.MOCK]
    
    # Production readiness score
    total_sources = len(sources)
    real_count = len(real_sources)
    score = (real_count / total_sources * 100) if total_sources > 0 else 0
    
    # Determine readiness level
    if score == 100 and can_go_live:
        readiness_level = "PRODUCTION_READY"
        readiness_message = "All data sources are real. System is ready for production LIVE mode."
    elif score >= 50:
        readiness_level = "PARTIAL"
        readiness_message = f"{len(mock_sources)} sources using mock data. LIVE mode blocked until resolved."
    else:
        readiness_level = "DEMO_ONLY"
        readiness_message = "Majority of sources are mock. System is suitable for demonstrations only."
    
    return {
        "readiness_level": readiness_level,
        "readiness_message": readiness_message,
        "data_integrity_score": round(score, 1),
        "can_go_live": can_go_live,
        "blockers": blockers,
        "sources": {
            "total": total_sources,
            "real": real_count,
            "mock": len(mock_sources),
            "real_sources": [s.name for s in real_sources],
            "mock_sources": [s.name for s in mock_sources],
        },
        "environment": os.getenv("OMEN_ENV", "development"),
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "enterprise_safe": can_go_live and score == 100,
        "sellable_statement": (
            "OMEN is safe to sell - all data sources verified as real." 
            if can_go_live and score == 100 
            else f"NOT SAFE TO SELL - {len(mock_sources)} mock sources must be replaced with real providers."
        ),
    }
