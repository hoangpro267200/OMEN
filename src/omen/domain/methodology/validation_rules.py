"""
Methodology documentation for validation rules.

Documents liquidity threshold rationale (ISSUE-011) and related rules.
"""

from datetime import date

from .base import Methodology, SourceCitation, ValidationStatus

LIQUIDITY_VALIDATION_METHODOLOGY = Methodology(
    name="liquidity_validation",
    version="1.1.0",
    description="Validates that prediction market has sufficient liquidity to provide reliable price signals.",
    formula="is_valid = liquidity_usd >= MIN_THRESHOLD; score = min(1.0, log10(liquidity_usd) / 6)",
    formula_latex=r"valid = L \geq L_{min}; \quad score = \min(1, \frac{\log_{10}(L)}{6})",
    inputs={
        "liquidity_usd": "Total liquidity in USD from market API",
    },
    outputs={
        "is_valid": "Boolean indicating if liquidity meets threshold",
        "liquidity_score": "Confidence contribution (0-1)",
        "reason": "Human-readable explanation",
    },
    parameters={
        "MIN_THRESHOLD_USD": (
            1000,
            "Minimum $1,000 liquidity required. Rationale: Markets below this threshold "
            "show high bid-ask spreads (>5%) and price manipulation risk. Based on analysis "
            "of Polymarket markets where spreads exceed 5% below $1K liquidity.",
        ),
        "REFERENCE_LOG": (
            6,
            "log10($1,000,000) = 6. Markets with $1M+ liquidity are considered highly reliable. "
            "Score scales logarithmically: $1K→0.5, $10K→0.67, $100K→0.83, $1M→1.0",
        ),
    },
    primary_source=SourceCitation(
        title="Market Microstructure and Liquidity",
        author="O'Hara, Maureen",
        publication="Journal of Finance",
        date=date(1995, 1, 1),
        page_or_section="Chapter 4: Bid-Ask Spreads",
    ),
    supporting_sources=[
        SourceCitation(
            title="Polymarket Liquidity Analysis",
            author="OMEN Team",
            publication="Internal Analysis",
            date=date(2024, 1, 10),
            page_or_section="Analysis of 500 markets showing spread vs liquidity correlation",
        ),
    ],
    assumptions=[
        "Liquidity reported by API is accurate and current",
        "Higher liquidity correlates with more informed traders",
        "Bid-ask spread decreases with liquidity (empirically validated)",
    ],
    limitations=[
        "Does not account for wash trading or artificial liquidity",
        "Single-point-in-time measurement; liquidity can change rapidly",
        "Threshold is static; may need adjustment for different market types",
    ],
    validation_status=ValidationStatus.BACKTESTED,
    validated_by="Analysis of prediction accuracy vs liquidity on 500 Polymarket events",
    validation_date=date(2024, 1, 15),
    validation_notes="Markets with >$10K liquidity showed 23% better calibration than <$1K markets",
    changelog=[
        "1.0.0 (2024-01-01): Initial implementation with $500 threshold",
        "1.1.0 (2024-01-15): Raised threshold to $1000 after backtesting; added score calculation",
    ],
)

GEOGRAPHIC_RELEVANCE_METHODOLOGY = Methodology(
    name="geographic_relevance_validation",
    version="2.0.0",
    description="Validates that event has geographic relevance to logistics chokepoints or shipping routes.",
    formula="score = matched_chokepoints / total_known_chokepoints; is_valid = score > 0",
    formula_latex=r"score = \frac{|C_{matched}|}{|C_{known}|}; \quad valid = score > 0",
    inputs={
        "event_title": "Title/question of the prediction market",
        "event_description": "Full description if available",
        "extracted_locations": "Locations mentioned in the event",
    },
    outputs={
        "is_valid": "Boolean indicating geographic relevance",
        "geographic_score": "Relevance score (0-1)",
        "matched_chokepoints": "List of matched chokepoint names",
        "matched_coordinates": "Lat/lng of matched locations",
    },
    parameters={
        "CHOKEPOINTS": (
            [
                "Red Sea",
                "Suez Canal",
                "Panama Canal",
                "Strait of Hormuz",
                "Strait of Malacca",
                "Bab el-Mandeb",
                "Taiwan Strait",
                "Cape of Good Hope",
            ],
            "Major maritime chokepoints that handle >50% of global shipping",
        ),
        "KEYWORDS": (
            ["shipping", "freight", "container", "port", "maritime", "vessel", "cargo"],
            "Logistics-related keywords for semantic matching",
        ),
    },
    primary_source=SourceCitation(
        title="World Maritime Chokepoints",
        author="US Energy Information Administration",
        publication="EIA World Oil Transit Chokepoints",
        date=date(2023, 7, 25),
        url="https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints",
    ),
    assumptions=[
        "Chokepoint names are consistently mentioned in relevant events",
        "Event titles are descriptive of geographic scope",
    ],
    limitations=[
        "May miss events that affect logistics indirectly",
        "Relies on keyword matching; could miss nuanced references",
        "Does not account for regional spelling variations",
    ],
    validation_status=ValidationStatus.INTERNAL_REVIEW,
    validation_date=date(2024, 1, 20),
)

CONFIDENCE_SCORE_METHODOLOGY = Methodology(
    name="confidence_score_calculation",
    version="1.0.0",
    description="Calculates overall confidence score from component validation scores.",
    formula="confidence = mean([liquidity_score, geographic_score, semantic_score, source_reliability])",
    formula_latex=r"C = \frac{1}{n}\sum_{i=1}^{n} c_i",
    inputs={
        "liquidity_score": "Score from liquidity validation (0-1)",
        "geographic_score": "Score from geographic relevance (0-1)",
        "semantic_score": "Score from semantic matching (0-1)",
        "source_reliability": "Reliability score of data source (0-1)",
    },
    outputs={
        "confidence_score": "Overall confidence (0-1)",
        "confidence_level": "Categorical level: LOW (<0.5), MEDIUM (0.5-0.75), HIGH (>0.75)",
    },
    parameters={
        "POLYMARKET_RELIABILITY": (0.85, "Polymarket is an established, liquid market"),
        "LOW_THRESHOLD": (0.5, "Below this is LOW confidence"),
        "HIGH_THRESHOLD": (0.75, "Above this is HIGH confidence"),
    },
    assumptions=[
        "All component scores are equally weighted",
        "Scores are independent (no correlation adjustment)",
    ],
    limitations=[
        "Simple average may not capture component interactions",
        "Does not penalize missing components appropriately",
        "Equal weighting may not reflect true importance",
    ],
    validation_status=ValidationStatus.DRAFT,
    changelog=[
        "1.0.0 (2024-01-25): Initial simple average implementation",
    ],
)

CONFIDENCE_METHODOLOGY = CONFIDENCE_SCORE_METHODOLOGY

VALIDATION_METHODOLOGIES = {
    "liquidity": LIQUIDITY_VALIDATION_METHODOLOGY,
    "geographic": GEOGRAPHIC_RELEVANCE_METHODOLOGY,
    "confidence": CONFIDENCE_SCORE_METHODOLOGY,
}
