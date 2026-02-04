"""
Cross-source validation rule.

Validates signals by correlating multiple data sources for higher confidence.
This is the "killer feature" that makes OMEN multi-source intelligence powerful.
"""

from typing import Any
from collections import defaultdict

from omen.domain.rules.base import Rule
from omen.domain.models.raw_signal import RawSignalEvent


class CrossSourceValidationRule(Rule):
    """
    Validate signals by correlating multiple sources.

    Example scenarios:

    1. Port congestion confirmed:
       - AIS: Port SGSIN has 45 ships waiting
       - Freight: SHA-SG rates spiked 30%
       → HIGH CONFIDENCE: Real congestion

    2. Storm impact validation:
       - Weather: Category 4 typhoon approaching Philippines
       - AIS: 50 ships re-routed from Manila
       → HIGH CONFIDENCE: Storm causing disruption

    3. False positive filter:
       - AIS: Congestion detected
       - No other sources confirm
       → MEDIUM CONFIDENCE: Could be data error or localized issue
    """

    rule_type = "validation"
    name = "cross_source_validation"
    version = "1.0.0"
    description = "Validates signals by cross-referencing multiple data sources"
    category = "multi_source"
    applicable_signal_types = ["disruption", "opportunity", "risk"]

    def __init__(
        self,
        min_sources_for_boost: int = 2,
        base_boost_2_sources: float = 0.2,
        base_boost_3_sources: float = 0.3,
        keyword_overlap_bonus: float = 0.1,
        max_boost: float = 0.4,
    ):
        """
        Initialize cross-source validation.

        Args:
            min_sources_for_boost: Minimum sources needed for confidence boost
            base_boost_2_sources: Confidence boost for 2 source confirmation
            base_boost_3_sources: Confidence boost for 3+ source confirmation
            keyword_overlap_bonus: Extra boost for keyword/topic alignment
            max_boost: Maximum total confidence boost
        """
        self.min_sources_for_boost = min_sources_for_boost
        self.base_boost_2_sources = base_boost_2_sources
        self.base_boost_3_sources = base_boost_3_sources
        self.keyword_overlap_bonus = keyword_overlap_bonus
        self.max_boost = max_boost

    @property
    def name(self) -> str:
        return "cross_source_validation"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def apply(self, input_data: RawSignalEvent) -> "ValidationResult":
        """
        Apply cross-source validation to single event.
        
        For batch validation with multiple events, use evaluate_batch.
        """
        from omen.domain.models.validated_signal import ValidationResult
        from omen.domain.models.common import ValidationStatus
        
        result = self.evaluate(input_data)
        return ValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            status=ValidationStatus.PASSED,
            score=result.get("score", 0.0),
            reason=result.get("reason", "Single event - no cross-validation"),
        )
    
    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: "ValidationResult",
        processing_time=None,
    ) -> "ExplanationStep":
        """Generate explanation for this rule."""
        from omen.domain.models.explanation import ExplanationStep
        from omen.application.ports.time_provider import utc_now
        
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={"source": input_data.market.source},
            output_summary={"status": output_data.status.value, "score": output_data.score},
            reasoning=output_data.reason or "Cross-source validation",
            confidence_contribution=output_data.score,
            timestamp=processing_time or utc_now(),
        )

    def evaluate(
        self, event: RawSignalEvent, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Evaluate single event (no cross-validation possible).

        For batch validation with multiple events, use evaluate_batch.
        """
        # Single event can't be cross-validated
        return {
            "passed": True,
            "score": 0.0,
            "reason": "Single event - no cross-validation",
            "metadata": {
                "cross_validation_available": False,
            },
        }

    def evaluate_batch(self, events: list[RawSignalEvent]) -> list[dict[str, Any]]:
        """
        Evaluate batch of events for cross-source validation.

        Groups events by location and checks for multi-source confirmation.

        Returns:
            List of validation results, one per event
        """
        if len(events) < self.min_sources_for_boost:
            # Not enough events for cross-validation
            return [
                {
                    "passed": True,
                    "score": 0.0,
                    "reason": f"Need {self.min_sources_for_boost}+ events for cross-validation",
                    "metadata": {"cross_validation_available": False},
                }
                for _ in events
            ]

        # Group events by location
        location_groups = self._group_by_location(events)

        # Build results
        results = []
        event_to_result: dict[str, dict[str, Any]] = {}

        for location, group in location_groups.items():
            sources = {e.market.source for e in group}
            n_sources = len(sources)

            if n_sources >= self.min_sources_for_boost:
                # Multi-source confirmation - calculate boost
                confidence_boost = self._calculate_confidence_boost(group)

                for event in group:
                    cross_refs = [e.event_id for e in group if e.event_id != event.event_id]
                    event_to_result[event.event_id] = {
                        "passed": True,
                        "score": confidence_boost,
                        "reason": f"Confirmed by {n_sources} sources: {', '.join(sorted(sources))}",
                        "metadata": {
                            "cross_validation_available": True,
                            "cross_source_refs": cross_refs,
                            "sources": list(sources),
                            "location": location,
                            "confidence_boost": confidence_boost,
                        },
                    }
            else:
                # Single source - no boost
                for event in group:
                    if event.event_id not in event_to_result:
                        event_to_result[event.event_id] = {
                            "passed": True,
                            "score": 0.0,
                            "reason": "Single source - no cross-validation boost",
                            "metadata": {
                                "cross_validation_available": True,
                                "sources": list(sources),
                                "location": location,
                            },
                        }

        # Return results in same order as input
        for event in events:
            if event.event_id in event_to_result:
                results.append(event_to_result[event.event_id])
            else:
                results.append(
                    {
                        "passed": True,
                        "score": 0.0,
                        "reason": "No location match for cross-validation",
                        "metadata": {"cross_validation_available": False},
                    }
                )

        return results

    def _group_by_location(self, events: list[RawSignalEvent]) -> dict[str, list[RawSignalEvent]]:
        """
        Group events by geographic location.

        Uses primary inferred_location for grouping.
        Also groups by region if locations are related.
        """
        groups: dict[str, list[RawSignalEvent]] = defaultdict(list)

        for event in events:
            # Get all locations
            locations = event.inferred_locations or []

            if not locations:
                groups["unknown"].append(event)
                continue

            # Add to primary location group
            primary = locations[0]
            groups[primary].append(event)

            # Also add to region groups for broader matching
            for loc in locations[1:]:
                # Check if it's a region
                if loc in ["Southeast Asia", "East Asia", "North America", "Europe", "Middle East"]:
                    groups[loc].append(event)

        return dict(groups)

    def _calculate_confidence_boost(self, events: list[RawSignalEvent]) -> float:
        """
        Calculate confidence boost from cross-source confirmation.

        Logic:
        - 2 sources: base_boost_2_sources (default 0.2)
        - 3+ sources: base_boost_3_sources (default 0.3)
        - High keyword overlap: +keyword_overlap_bonus (default 0.1)
        """
        n_sources = len({e.market.source for e in events})

        if n_sources < 2:
            return 0.0

        # Base boost
        if n_sources == 2:
            boost = self.base_boost_2_sources
        else:
            boost = self.base_boost_3_sources

        # Keyword overlap bonus
        overlap = self._calculate_keyword_overlap(events)
        if overlap > 0.3:  # Significant overlap
            boost += self.keyword_overlap_bonus

        # Cap at max
        return min(boost, self.max_boost)

    def _calculate_keyword_overlap(self, events: list[RawSignalEvent]) -> float:
        """
        Calculate keyword overlap ratio between events.

        Returns Jaccard similarity of keywords.
        """
        if len(events) < 2:
            return 0.0

        keyword_sets = [set(e.keywords or []) for e in events]

        # Filter empty sets
        keyword_sets = [ks for ks in keyword_sets if ks]

        if len(keyword_sets) < 2:
            return 0.0

        # Jaccard similarity: intersection / union
        intersection = set.intersection(*keyword_sets)
        union = set.union(*keyword_sets)

        if not union:
            return 0.0

        return len(intersection) / len(union)


class SourceDiversityRule(Rule):
    """
    Rewards signals that have diverse source types.

    Higher scores for signals confirmed by fundamentally different data types:
    - Market data (Polymarket, stock prices)
    - Physical data (AIS, weather)
    - Economic data (freight rates, commodity prices)
    """

    rule_type = "validation"
    description = "Rewards signals confirmed by diverse data source types"
    category = "multi_source"

    # Source type classification
    SOURCE_TYPES = {
        "polymarket": "market",
        "stock": "market",
        "ais": "physical",
        "weather": "physical",
        "freight": "economic",
        "commodity": "economic",
        "news": "media",
    }

    @property
    def name(self) -> str:
        return "source_diversity"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def apply(self, input_data: RawSignalEvent) -> "ValidationResult":
        """Apply source diversity check to single event."""
        from omen.domain.models.validated_signal import ValidationResult
        from omen.domain.models.common import ValidationStatus
        
        result = self.evaluate(input_data)
        return ValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            status=ValidationStatus.PASSED,
            score=result.get("score", 0.0),
            reason=result.get("reason", "Single source - no diversity"),
        )
    
    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: "ValidationResult",
        processing_time=None,
    ) -> "ExplanationStep":
        """Generate explanation for this rule."""
        from omen.domain.models.explanation import ExplanationStep
        from omen.application.ports.time_provider import utc_now
        
        source = input_data.market.source
        source_type = self.SOURCE_TYPES.get(source, "unknown")
        
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={"source": source, "source_type": source_type},
            output_summary={"status": output_data.status.value, "score": output_data.score},
            reasoning=output_data.reason or f"Source type: {source_type}",
            confidence_contribution=output_data.score,
            timestamp=processing_time or utc_now(),
        )

    def evaluate(
        self, event: RawSignalEvent, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Evaluate source diversity for single event."""
        source = event.market.source
        source_type = self.SOURCE_TYPES.get(source, "unknown")

        return {
            "passed": True,
            "score": 0.0,  # Single source can't have diversity
            "reason": f"Source type: {source_type}",
            "metadata": {
                "source": source,
                "source_type": source_type,
            },
        }

    def evaluate_batch(self, events: list[RawSignalEvent]) -> list[dict[str, Any]]:
        """Evaluate source diversity across batch."""
        # Get unique source types
        sources = [e.market.source for e in events]
        source_types = {self.SOURCE_TYPES.get(s, "unknown") for s in sources}

        # Diversity score based on number of different types
        n_types = len(source_types - {"unknown"})

        if n_types <= 1:
            diversity_score = 0.0
        elif n_types == 2:
            diversity_score = 0.5
        else:
            diversity_score = 1.0

        return [
            {
                "passed": True,
                "score": diversity_score,
                "reason": f"Source diversity: {n_types} types ({', '.join(sorted(source_types))})",
                "metadata": {
                    "source_types": list(source_types),
                    "n_types": n_types,
                },
            }
            for _ in events
        ]
