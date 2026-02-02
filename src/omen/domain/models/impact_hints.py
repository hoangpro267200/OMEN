"""
Impact Hints: Routing Metadata

⚠️ CRITICAL: This is NOT impact assessment.

ImpactHints provides:
✅ Which domains should ROUTE this signal to
✅ Semantic polarity (positive/negative sentiment)
✅ What asset types are MENTIONED

ImpactHints does NOT provide:
❌ Severity scores
❌ Delay estimates
❌ Cost calculations
❌ Risk quantification
❌ Recommendations
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from .enums import AffectedDomain, ImpactDirection


class ImpactHints(BaseModel):
    """
    Routing metadata for downstream systems.
    NOT impact assessment.
    """

    model_config = ConfigDict(frozen=True)

    domains: list[AffectedDomain] = Field(
        default_factory=list, description="Domains to route this signal. NOT impact scope."
    )

    direction: ImpactDirection = Field(
        default=ImpactDirection.UNKNOWN, description="Semantic polarity. NOT severity."
    )

    affected_asset_types: list[str] = Field(
        default_factory=list, description="Asset types mentioned. NOT impact targets."
    )

    keywords: list[str] = Field(default_factory=list, description="Extracted keywords for context.")

    # ⛔ DO NOT ADD:
    # - severity: float
    # - delay_days: float
    # - cost_estimate: float
    # - risk_score: float
    # - priority: str
    # - recommended_action: str
