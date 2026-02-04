"""
API endpoints for methodology documentation.

Provides transparency into OMEN's validation calculations.
Impact assessment is handled by downstream consumers (e.g., RiskCast service).
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from omen.api.errors import not_found
from omen.api.route_dependencies import require_methodology_read
from omen.domain.methodology import VALIDATION_METHODOLOGIES
from omen.infrastructure.security.unified_auth import AuthContext

router = APIRouter(prefix="/methodology", tags=["Methodology"])


class MethodologySummary(BaseModel):
    """Summary of a methodology."""

    name: str
    version: str
    description: str
    validation_status: str
    primary_source: Optional[str] = None


class MethodologyDetail(BaseModel):
    """Full methodology details."""

    name: str
    version: str
    description: str
    formula: str
    formula_latex: Optional[str] = None
    inputs: dict[str, str] = {}
    outputs: dict[str, str] = {}
    parameters: dict[str, dict[str, Any]] = {}
    primary_source: Optional[dict] = None
    supporting_sources: list[dict] = []
    assumptions: list[str] = []
    limitations: list[str] = []
    validation: dict = {}
    version_info: dict = {}


@router.get("", response_model=dict[str, list[MethodologySummary]])
async def list_methodologies(
    auth: AuthContext = Depends(require_methodology_read),  # RBAC: read:methodology
) -> dict[str, list[MethodologySummary]]:
    """
    List documented validation methodologies.

    Impact assessment methodologies are handled by downstream consumers.
    """
    return {
        "validation": [
            MethodologySummary(
                name=m.name,
                version=m.version,
                description=m.description,
                validation_status=m.validation_status.value,
                primary_source=m.primary_source.to_string() if m.primary_source else None,
            )
            for m in VALIDATION_METHODOLOGIES.values()
        ],
    }


@router.get("/for-metric/{metric_name}", response_model=MethodologyDetail)
async def get_methodology_for_metric(
    metric_name: str,
    auth: AuthContext = Depends(require_methodology_read),  # RBAC: read:methodology
) -> MethodologyDetail:
    """
    Get the methodology for a validation metric (e.g. liquidity, geographic).

    Impact assessment is handled by downstream consumers.
    """
    methodology = VALIDATION_METHODOLOGIES.get(metric_name.lower())
    if not methodology:
        raise not_found("Methodology", metric_name)
    return MethodologyDetail(**methodology.to_dict())


@router.get("/{category}/{name}", response_model=MethodologyDetail)
async def get_methodology_detail(
    category: str,
    name: str,
    auth: AuthContext = Depends(require_methodology_read),  # RBAC: read:methodology
) -> MethodologyDetail:
    """
    Get full details of a validation methodology.

    category must be 'validation'. Impact assessment is downstream.
    """
    if category != "validation":
        raise not_found("Category", category)
    methodology = VALIDATION_METHODOLOGIES.get(name)
    if not methodology:
        raise not_found("Methodology", name)
    return MethodologyDetail(**methodology.to_dict())
