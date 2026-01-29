"""
Signal Enricher — Adds context to validated signals.

DOES:
- Add geographic context (regions, chokepoints)
- Add temporal context (event horizon) via extraction from event
- Add keyword/category classification
- Compile validation scores (pass-through from context)

DOES NOT:
- Calculate impact (delay, cost, severity)
- Make recommendations
- Assess time-horizon or relevance
"""

from __future__ import annotations

from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.rules.validation.keywords import (
    get_matched_keywords,
    get_keyword_categories,
    calculate_relevance_score,
)


# Geographic term lists for extraction (lowercase)
CHOKEPOINTS = [
    "red sea", "suez", "panama", "hormuz", "malacca",
    "bosphorus", "gibraltar", "taiwan strait", "bab el-mandeb",
]

REGIONS = [
    "asia", "europe", "america", "africa", "middle east",
    "pacific", "atlantic", "mediterranean", "china", "india",
]


class SignalEnricher:
    """
    Enriches validated signals with context.

    No impact calculations — just context and classification.
    """

    def __init__(
        self,
        chokepoints: list[str] | None = None,
        regions: list[str] | None = None,
    ):
        self._chokepoints = chokepoints if chokepoints is not None else CHOKEPOINTS
        self._regions = regions if regions is not None else REGIONS

    def enrich(
        self,
        event: RawSignalEvent,
        validation_context: dict,
    ) -> dict:
        """
        Enrich a validated event with additional context.

        validation_context may contain:
        - confidence_factors: dict (optional)
        - validation_results: list of ValidationResult (optional)

        Returns enrichment dict suitable for OmenSignal.from_validated_event.
        """
        text = f"{event.title} {event.description or ''}".lower()

        # Extract keywords via logistics keyword DB
        keywords = get_matched_keywords(text)
        keyword_categories = get_keyword_categories(keywords)

        # Geographic context from text
        matched_chokepoints = [
            cp for cp in self._chokepoints
            if cp in text
        ]
        matched_regions = [
            r for r in self._regions
            if r in text
        ]

        out: dict = {
            "matched_keywords": keywords,
            "keyword_categories": keyword_categories,
            "relevance_score": calculate_relevance_score(keywords),
            "matched_chokepoints": matched_chokepoints,
            "matched_regions": matched_regions,
        }

        # Carry forward validation context
        if "confidence_factors" in validation_context:
            out["confidence_factors"] = dict(validation_context["confidence_factors"])
        if "validation_results" in validation_context:
            out["validation_results"] = list(validation_context["validation_results"])

        return out
