"""Validation rules for OMEN signal processing.

✅ ACTIVATED: All 12 validation rules are now exported and available.

Core Rules (6):
- LiquidityValidationRule
- GeographicRelevanceRule  
- SemanticRelevanceRule
- AnomalyDetectionRule
- CrossSourceValidationRule
- SourceDiversityRule

News & Commodity (2):
- NewsQualityGateRule
- CommodityContextRule

AIS/Maritime (4):
- PortCongestionValidationRule
- ChokePointDelayValidationRule
- AISDataFreshnessRule
- AISDataQualityRule
"""

from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.validation.geographic_relevance_rule import GeographicRelevanceRule
from omen.domain.rules.validation.semantic_relevance_rule import SemanticRelevanceRule
from omen.domain.rules.validation.anomaly_detection_rule import AnomalyDetectionRule
from omen.domain.rules.validation.news_quality_rule import NewsQualityGateRule
from omen.domain.rules.validation.commodity_context_rule import CommodityContextRule
from omen.domain.rules.validation.cross_source_validation import (
    CrossSourceValidationRule,
    SourceDiversityRule,
)
# ✅ NEW: AIS/Maritime validation rules
from omen.domain.rules.validation.ais_validation import (
    PortCongestionValidationRule,
    ChokePointDelayValidationRule,
    AISDataFreshnessRule,
    AISDataQualityRule,
)

__all__ = [
    # Core validation
    "LiquidityValidationRule",
    "GeographicRelevanceRule",
    "SemanticRelevanceRule",
    "AnomalyDetectionRule",
    # Cross-source
    "CrossSourceValidationRule",
    "SourceDiversityRule",
    # News & Commodity
    "NewsQualityGateRule",
    "CommodityContextRule",
    # AIS/Maritime
    "PortCongestionValidationRule",
    "ChokePointDelayValidationRule",
    "AISDataFreshnessRule",
    "AISDataQualityRule",
]
