"""
Debug endpoints for pipeline visibility.

Security: Requires DEBUG scope (admin-level access).
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from omen.api.route_dependencies import require_debug
from omen.api.dependencies import get_signal_only_pipeline
from omen.application.signal_pipeline import SignalOnlyPipeline
from omen.infrastructure.debug.rejection_tracker import get_rejection_tracker
from omen.infrastructure.security.unified_auth import AuthContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/rejections")
async def get_rejections(
    auth: AuthContext = Depends(require_debug),  # RBAC: debug
    limit: int = Query(default=50, le=200),
    stage: Optional[
        Literal["ingestion", "mapping", "validation", "translation", "generation"]
    ] = None,
):
    """
    Get recent rejected events with reasons.

    Use this to understand WHY events are being filtered out.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    return {
        "rejections": tracker.get_recent_rejections(limit=limit, stage=stage),
        "statistics": tracker.get_statistics(),
    }


@router.get("/passed")
async def get_passed(
    auth: AuthContext = Depends(require_debug),  # RBAC: debug
    limit: int = Query(default=50, le=200),
):
    """
    Get recently passed/generated signals.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    return {
        "passed": tracker.get_recent_passed(limit=limit),
        "total_passed": tracker.get_passed_count(),
    }


@router.get("/statistics")
async def get_pipeline_statistics(
    auth: AuthContext = Depends(require_debug),  # RBAC: debug
):
    """
    Get overall pipeline statistics.

    Shows pass/rejection rates and breakdown by stage.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    return tracker.get_statistics()


@router.delete("/data")
async def clear_debug_data(
    auth: AuthContext = Depends(require_debug),  # RBAC: debug
):
    """
    Clear all debug records.

    **Requires scope:** `debug`
    """
    tracker = get_rejection_tracker()
    tracker.clear()
    return {"status": "cleared"}


@router.get("/validator-config")
async def get_validator_config(
    auth: AuthContext = Depends(require_debug),  # RBAC: debug
    pipeline: SignalOnlyPipeline = Depends(get_signal_only_pipeline),
):
    """
    Get current validator configuration.

    Returns the list of validation rules active on the API endpoint.
    Use this to verify that the FULL validator (12 rules) is in use.

    **Requires scope:** `debug`
    """
    validator = pipeline._validator
    rules = validator.rules
    
    rule_info = []
    for rule in rules:
        rule_info.append({
            "name": rule.name,
            "version": rule.version,
            "class": type(rule).__name__,
        })
    
    # Determine profile based on rule count
    rule_count = len(rules)
    if rule_count >= 12:
        profile = "FULL"
    elif rule_count >= 6:
        profile = "DEFAULT"
    else:
        profile = "MINIMAL"
    
    logger.info(
        "Validator config requested: profile=%s, rule_count=%d, rules=%s",
        profile, rule_count, [r["class"] for r in rule_info]
    )
    
    return {
        "profile": profile,
        "rule_count": rule_count,
        "expected_full_count": 12,
        "is_full": rule_count >= 12,
        "rules": rule_info,
        "missing_rules_if_default": [
            "NewsQualityGateRule",
            "CommodityContextRule",
            "PortCongestionValidationRule",
            "ChokePointDelayValidationRule",
            "AISDataFreshnessRule",
            "AISDataQualityRule",
        ] if rule_count < 12 else [],
    }
