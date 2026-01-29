"""
API endpoints for methodology documentation.

Provides transparency into OMEN's validation calculations.
Impact methodologies live in the omen_impact package (consumer responsibility).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from omen.domain.methodology import VALIDATION_METHODOLOGIES

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


@router.get("", response_model=dict)
async def list_methodologies():
    """
    List documented validation methodologies.

    Impact methodologies (Red Sea, etc.) are in the omen_impact package.
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
async def get_methodology_for_metric(metric_name: str):
    """
    Get the methodology for a validation metric (e.g. liquidity, geographic).

    For impact metrics use the omen_impact package.
    """
    methodology = VALIDATION_METHODOLOGIES.get(metric_name.lower())
    if not methodology:
        raise HTTPException(
            status_code=404,
            detail=f"No validation methodology found for: {metric_name}. Impact metrics are in omen_impact.",
        )
    return MethodologyDetail(**methodology.to_dict())


@router.get("/{category}/{name}", response_model=MethodologyDetail)
async def get_methodology_detail(category: str, name: str):
    """
    Get full details of a validation methodology.

    category must be 'validation'. Impact methodologies are in omen_impact.
    """
    if category != "validation":
        raise HTTPException(
            status_code=404,
            detail=f"Unknown category: {category}. Only 'validation' is exposed. Impact methodologies are in omen_impact.",
        )
    methodology = VALIDATION_METHODOLOGIES.get(name)
    if not methodology:
        raise HTTPException(status_code=404, detail=f"Methodology not found: {name}")
    return MethodologyDetail(**methodology.to_dict())
