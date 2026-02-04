"""
Multi-Source Conflict Detection.

Identifies when different sources provide conflicting signals about
the same event or topic. Conflicts reduce signal confidence.

Key Conflict Types:
1. Probability Disagreement: Sources report significantly different probabilities
2. Sentiment Conflict: Sources have opposing sentiment (positive vs negative)
3. Geographic Conflict: Sources disagree on affected locations

NOTE: No logging in domain layer - maintain purity for determinism.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from omen.application.ports.time_provider import utc_now
from omen.domain.models.raw_signal import RawSignalEvent


class ConflictSeverity(str, Enum):
    """Severity of detected conflict."""

    NONE = "none"  # No conflict detected
    LOW = "low"  # Minor disagreement (10-20% probability diff)
    MEDIUM = "medium"  # Moderate disagreement (20-30% probability diff)
    HIGH = "high"  # Significant disagreement (>30% probability diff)


class ConflictResult(BaseModel):
    """Result of conflict detection analysis."""

    has_conflict: bool = Field(..., description="Whether a conflict was detected")
    severity: ConflictSeverity = Field(default=ConflictSeverity.NONE)
    conflicting_sources: list[str] = Field(default_factory=list)
    description: str = Field(..., description="Human-readable conflict description")
    confidence_adjustment: float = Field(
        0.0,
        description="How much to adjust confidence (negative = reduce)",
    )
    details: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(
        default_factory=lambda: utc_now(),
        description="When the conflict was detected (timezone-aware UTC)",
    )

    @classmethod
    def no_conflict(cls) -> "ConflictResult":
        """Factory for no conflict detected."""
        return cls(
            has_conflict=False,
            severity=ConflictSeverity.NONE,
            description="No conflicts detected",
            confidence_adjustment=0.0,
        )


class SignalConflictDetector:
    """
    Detects conflicts between signals from different sources.

    Conflicts occur when:
    - Same event/topic, different probabilities (>20% diff)
    - Contradicting sentiment (positive vs negative)
    - Inconsistent geographic data

    Usage:
        detector = SignalConflictDetector()

        conflicts = detector.detect_conflicts(signals)

        for conflict in conflicts:
            if conflict.has_conflict:
                print(f"Conflict: {conflict.description}")
                print(f"Adjust confidence by: {conflict.confidence_adjustment}")
    """

    # Configuration thresholds
    PROBABILITY_DIFF_LOW = 0.10  # 10% = low severity
    PROBABILITY_DIFF_MEDIUM = 0.20  # 20% = medium severity
    PROBABILITY_DIFF_HIGH = 0.30  # 30% = high severity

    SENTIMENT_CONFLICT_THRESHOLD = 0.30  # Opposite ends of sentiment scale

    # Confidence adjustments by severity
    CONFIDENCE_ADJUSTMENTS = {
        ConflictSeverity.NONE: 0.0,
        ConflictSeverity.LOW: -0.05,
        ConflictSeverity.MEDIUM: -0.15,
        ConflictSeverity.HIGH: -0.25,
    }

    def detect_conflicts(
        self,
        signals: list[RawSignalEvent],
    ) -> list[ConflictResult]:
        """
        Detect conflicts in a list of signals.

        Signals are grouped by similarity (event_id, keywords, locations).

        Args:
            signals: List of signals to analyze

        Returns:
            List of ConflictResult for each detected conflict
        """
        if len(signals) < 2:
            return []

        conflicts = []

        # Group signals by similarity
        groups = self._group_similar_signals(signals)

        for group_key, group_signals in groups.items():
            if len(group_signals) < 2:
                continue

            # Check for probability conflicts
            prob_conflict = self._check_probability_conflict(group_signals)
            if prob_conflict and prob_conflict.has_conflict:
                conflicts.append(prob_conflict)

            # Check for sentiment conflicts
            sentiment_conflict = self._check_sentiment_conflict(group_signals)
            if sentiment_conflict and sentiment_conflict.has_conflict:
                conflicts.append(sentiment_conflict)

            # Check for geographic conflicts
            geo_conflict = self._check_geographic_conflict(group_signals)
            if geo_conflict and geo_conflict.has_conflict:
                conflicts.append(geo_conflict)

        return conflicts

    def _group_similar_signals(
        self,
        signals: list[RawSignalEvent],
    ) -> dict[str, list[RawSignalEvent]]:
        """
        Group signals by similarity.

        Signals are considered similar if they share:
        - Common keywords
        - Similar locations
        - Related event IDs
        """
        groups: dict[str, list[RawSignalEvent]] = defaultdict(list)

        for signal in signals:
            key = self._get_group_key(signal)
            groups[key].append(signal)

        return dict(groups)

    def _get_group_key(self, signal: RawSignalEvent) -> str:
        """Generate grouping key for signal based on keywords and locations."""
        # Use top keywords for grouping
        keywords = sorted(signal.keywords[:3]) if signal.keywords else []

        # Include location names
        locations = []
        if signal.inferred_locations:
            locations = sorted([loc.name for loc in signal.inferred_locations[:2]])

        # Combine into key
        key_parts = keywords + locations

        if not key_parts:
            # Fallback to event_id prefix
            return signal.event_id[:10] if signal.event_id else "unknown"

        return "|".join(key_parts)

    def _check_probability_conflict(
        self,
        signals: list[RawSignalEvent],
    ) -> Optional[ConflictResult]:
        """Check for probability disagreement between sources."""
        probabilities = [
            (s.market.source if s.market else "unknown", s.probability)
            for s in signals
            if s.probability is not None
        ]

        if len(probabilities) < 2:
            return None

        # Find min and max probabilities
        min_source, min_prob = min(probabilities, key=lambda x: x[1])
        max_source, max_prob = max(probabilities, key=lambda x: x[1])

        diff = max_prob - min_prob

        # Determine severity
        if diff < self.PROBABILITY_DIFF_LOW:
            return ConflictResult.no_conflict()
        elif diff < self.PROBABILITY_DIFF_MEDIUM:
            severity = ConflictSeverity.LOW
        elif diff < self.PROBABILITY_DIFF_HIGH:
            severity = ConflictSeverity.MEDIUM
        else:
            severity = ConflictSeverity.HIGH

        sources = list(set(s[0] for s in probabilities))

        return ConflictResult(
            has_conflict=True,
            severity=severity,
            conflicting_sources=sources,
            description=(
                f"Probability disagreement: {min_source} reports {min_prob:.0%} "
                f"vs {max_source} reports {max_prob:.0%} (diff: {diff:.0%})"
            ),
            confidence_adjustment=self.CONFIDENCE_ADJUSTMENTS[severity],
            details={
                "min_probability": min_prob,
                "max_probability": max_prob,
                "difference": diff,
                "min_source": min_source,
                "max_source": max_source,
                "all_probabilities": dict(probabilities),
            },
        )

    def _check_sentiment_conflict(
        self,
        signals: list[RawSignalEvent],
    ) -> Optional[ConflictResult]:
        """Check for sentiment disagreement between sources."""
        sentiments = []

        for signal in signals:
            if not signal.source_metrics:
                continue

            sentiment = signal.source_metrics.get("sentiment")
            if sentiment is not None:
                source = signal.market.source if signal.market else "unknown"
                sentiments.append((source, sentiment))

        if len(sentiments) < 2:
            return None

        # Check for opposing sentiments
        values = [s[1] for s in sentiments]
        has_positive = any(v > self.SENTIMENT_CONFLICT_THRESHOLD for v in values)
        has_negative = any(v < -self.SENTIMENT_CONFLICT_THRESHOLD for v in values)

        if not (has_positive and has_negative):
            return ConflictResult.no_conflict()

        # Find the most extreme sources
        positive_source = max(sentiments, key=lambda x: x[1])
        negative_source = min(sentiments, key=lambda x: x[1])

        return ConflictResult(
            has_conflict=True,
            severity=ConflictSeverity.MEDIUM,
            conflicting_sources=[positive_source[0], negative_source[0]],
            description=(
                f"Sentiment conflict: {positive_source[0]} is positive ({positive_source[1]:.2f}) "
                f"while {negative_source[0]} is negative ({negative_source[1]:.2f})"
            ),
            confidence_adjustment=self.CONFIDENCE_ADJUSTMENTS[ConflictSeverity.MEDIUM],
            details={
                "sentiments": dict(sentiments),
                "positive_source": positive_source[0],
                "negative_source": negative_source[0],
            },
        )

    def _check_geographic_conflict(
        self,
        signals: list[RawSignalEvent],
    ) -> Optional[ConflictResult]:
        """Check for geographic disagreement between sources."""
        location_sets = []

        for signal in signals:
            if signal.inferred_locations:
                source = signal.market.source if signal.market else "unknown"
                locations = frozenset(loc.name for loc in signal.inferred_locations)
                location_sets.append((source, locations))

        if len(location_sets) < 2:
            return None

        # Check for non-overlapping location sets
        all_locations = set()
        for _, locs in location_sets:
            all_locations.update(locs)

        # Count how many sources mention each location
        location_counts: dict[str, int] = defaultdict(int)
        for _, locs in location_sets:
            for loc in locs:
                location_counts[loc] += 1

        # Find locations mentioned by only one source
        exclusive_locations = [loc for loc, count in location_counts.items() if count == 1]

        # If more than half of locations are exclusive, there's a conflict
        if len(exclusive_locations) > len(all_locations) / 2:
            return ConflictResult(
                has_conflict=True,
                severity=ConflictSeverity.LOW,
                conflicting_sources=[s[0] for s in location_sets],
                description=(
                    f"Geographic disagreement: Sources report different affected locations "
                    f"({len(exclusive_locations)} locations mentioned by only one source)"
                ),
                confidence_adjustment=self.CONFIDENCE_ADJUSTMENTS[ConflictSeverity.LOW],
                details={
                    "all_locations": list(all_locations),
                    "exclusive_locations": exclusive_locations,
                    "location_counts": dict(location_counts),
                },
            )

        return ConflictResult.no_conflict()

    def adjust_confidence(
        self,
        base_confidence: float,
        conflicts: list[ConflictResult],
    ) -> tuple[float, list[str]]:
        """
        Adjust confidence score based on detected conflicts.

        Args:
            base_confidence: Original confidence score
            conflicts: List of detected conflicts

        Returns:
            (adjusted_confidence, list of adjustment reasons)
        """
        adjusted = base_confidence
        reasons = []

        for conflict in conflicts:
            if conflict.has_conflict:
                adjusted += conflict.confidence_adjustment
                reasons.append(f"{conflict.severity.value}: {conflict.description}")

        # Clamp to valid range [0.1, 1.0]
        adjusted = max(0.1, min(1.0, adjusted))

        return adjusted, reasons

    def get_conflict_summary(
        self,
        conflicts: list[ConflictResult],
    ) -> dict[str, Any]:
        """
        Get summary of all detected conflicts.

        Returns:
            Summary dict with counts and details
        """
        if not conflicts:
            return {
                "total_conflicts": 0,
                "has_conflicts": False,
                "severity_counts": {},
                "total_confidence_impact": 0.0,
            }

        severity_counts: dict[str, int] = defaultdict(int)
        total_impact = 0.0

        for conflict in conflicts:
            if conflict.has_conflict:
                severity_counts[conflict.severity.value] += 1
                total_impact += conflict.confidence_adjustment

        return {
            "total_conflicts": sum(1 for c in conflicts if c.has_conflict),
            "has_conflicts": any(c.has_conflict for c in conflicts),
            "severity_counts": dict(severity_counts),
            "total_confidence_impact": total_impact,
            "conflicts": [c.model_dump() for c in conflicts if c.has_conflict],
        }
