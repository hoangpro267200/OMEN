"""
API endpoints for methodology documentation.

Provides transparency into OMEN's calculations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from omen.domain.methodology import (
    RED_SEA_METHODOLOGIES,
    VALIDATION_METHODOLOGIES,
    get_methodology,
)

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
    List all documented methodologies.

    Returns methodologies grouped by category:
    - impact: Red Sea impact calculations
    - validation: Signal validation rules
    """
    return {
        "impact": [
            MethodologySummary(
                name=m.name,
                version=m.version,
                description=m.description,
                validation_status=m.validation_status.value,
                primary_source=m.primary_source.to_string() if m.primary_source else None,
            )
            for m in RED_SEA_METHODOLOGIES.values()
        ],
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
    Get the methodology used to calculate a specific metric.

    Args:
        metric_name: Name of the metric (e.g., 'transit_time_increase', 'fuel_cost_increase')

    Returns:
        Methodology used for that metric, or 404 if not found.
    """
    metric_mapping = {
        "transit_time_increase": "transit_time",
        "transit_time": "transit_time",
        "fuel_consumption_increase": "fuel_cost",
        "fuel_cost_increase": "fuel_cost",
        "fuel_cost": "fuel_cost",
        "freight_rate_pressure": "freight_rate",
        "freight_rate_increase": "freight_rate",
        "freight_rate": "freight_rate",
        "insurance_premium_increase": "insurance",
        "insurance": "insurance",
    }
    methodology_name = metric_mapping.get(metric_name.lower())
    if not methodology_name:
        raise HTTPException(
            status_code=404,
            detail=f"No methodology found for metric: {metric_name}",
        )
    methodology = RED_SEA_METHODOLOGIES.get(methodology_name)
    if not methodology:
        raise HTTPException(status_code=404, detail="Methodology not found")
    return MethodologyDetail(**methodology.to_dict())


@router.get("/{category}/{name}", response_model=MethodologyDetail)
async def get_methodology_detail(category: str, name: str):
    """
    Get full details of a specific methodology.

    Args:
        category: 'impact' or 'validation'
        name: Methodology name (e.g., 'transit_time', 'liquidity')

    Returns:
        Complete methodology documentation.
    """
    if category == "impact":
        methodology = RED_SEA_METHODOLOGIES.get(name)
    elif category == "validation":
        methodology = VALIDATION_METHODOLOGIES.get(name)
    else:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    if not methodology:
        raise HTTPException(status_code=404, detail=f"Methodology not found: {name}")

    return MethodologyDetail(**methodology.to_dict())
