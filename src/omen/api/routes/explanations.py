"""
Explanation and audit endpoints.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from omen.api.dependencies import get_repository
from omen.application.ports.signal_repository import SignalRepository
from omen.domain.services.explanation_report import (
    generate_json_audit_report,
    generate_text_report,
)
from omen.infrastructure.security.auth import verify_api_key

router = APIRouter()


@router.get("/signals/{signal_id}/explanation", response_model=None)
async def get_signal_explanation(
    signal_id: str,
    format: str = "json",
    repository: SignalRepository = Depends(get_repository),
    _api_key: str = Depends(verify_api_key),
) -> dict[str, Any] | Response:
    """
    Get detailed explanation for a signal.

    Formats:
    - json: Machine-readable audit format
    - text: Human-readable report
    """
    signal = repository.find_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    if format == "text":
        report = generate_text_report(signal)
        return Response(content=report, media_type="text/plain")
    return generate_json_audit_report(signal)


@router.get("/parameters")
async def list_all_parameters(
    _api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """
    List all rule parameters used by OMEN.

    Useful for:
    - Documentation
    - Auditing assumptions
    - Parameter sensitivity analysis
    """
    from omen.domain.rules.registry import get_rule_registry

    registry = get_rule_registry()
    return registry.export_all_parameters()
