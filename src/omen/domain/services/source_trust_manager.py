"""
Source Trust Management System.

Manages trust scores for different data sources based on:
- Historical accuracy
- Data freshness
- Response reliability
- Conflict resolution outcomes

Trust scores are used to:
1. Weight signals during aggregation
2. Resolve conflicts (higher trust source wins)
3. Adjust confidence based on source reliability
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from omen.application.ports.time_provider import utc_now


class TrustLevel(str, Enum):
    """Trust classification for data sources."""

    UNTRUSTED = "untrusted"      # New or problematic source
    LOW = "low"                  # Known issues
    MEDIUM = "medium"           # Standard reliability
    HIGH = "high"               # Proven accuracy
    AUTHORITATIVE = "authoritative"  # Primary/official source


class SourceTrustScore(BaseModel):
    """Trust score for a data source."""

    source_id: str = Field(..., description="Unique source identifier")
    trust_level: TrustLevel = Field(default=TrustLevel.MEDIUM)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Accuracy metrics
    accuracy_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    total_signals: int = Field(default=0, ge=0)
    accurate_signals: int = Field(default=0, ge=0)
    
    # Reliability metrics
    uptime_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_latency_ms: float = Field(default=0.0, ge=0.0)
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Freshness metrics
    avg_data_age_seconds: float = Field(default=0.0, ge=0.0)
    last_successful_fetch: Optional[datetime] = None
    
    # History
    last_updated: datetime = Field(default_factory=utc_now)
    trust_history: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"frozen": False}  # Mutable for updates

    def update_accuracy(self, was_accurate: bool) -> None:
        """Update accuracy metrics after signal validation."""
        self.total_signals += 1
        if was_accurate:
            self.accurate_signals += 1
        
        if self.total_signals > 0:
            self.accuracy_rate = self.accurate_signals / self.total_signals
        
        self._recalculate_trust()

    def update_reliability(
        self,
        success: bool,
        latency_ms: float = 0.0,
    ) -> None:
        """Update reliability metrics after API call."""
        # Exponential moving average for latency
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            alpha = 0.1
            self.avg_latency_ms = alpha * latency_ms + (1 - alpha) * self.avg_latency_ms

        # Update error rate (EMA)
        error_value = 0.0 if success else 1.0
        alpha = 0.05
        self.error_rate = alpha * error_value + (1 - alpha) * self.error_rate

        if success:
            self.last_successful_fetch = utc_now()
        
        self._recalculate_trust()

    def update_freshness(self, data_age_seconds: float) -> None:
        """Update freshness metrics."""
        if self.avg_data_age_seconds == 0:
            self.avg_data_age_seconds = data_age_seconds
        else:
            alpha = 0.1
            self.avg_data_age_seconds = (
                alpha * data_age_seconds + (1 - alpha) * self.avg_data_age_seconds
            )
        
        self._recalculate_trust()

    def _recalculate_trust(self) -> None:
        """Recalculate overall trust score."""
        # Weight factors
        accuracy_weight = 0.4
        reliability_weight = 0.3
        freshness_weight = 0.3

        # Accuracy score (higher is better)
        accuracy_score = self.accuracy_rate

        # Reliability score (lower error rate and latency is better)
        reliability_score = max(0, 1.0 - self.error_rate)
        if self.avg_latency_ms > 5000:  # More than 5s is bad
            reliability_score *= 0.5

        # Freshness score (lower age is better)
        if self.avg_data_age_seconds < 60:  # Less than 1 min
            freshness_score = 1.0
        elif self.avg_data_age_seconds < 300:  # Less than 5 min
            freshness_score = 0.8
        elif self.avg_data_age_seconds < 900:  # Less than 15 min
            freshness_score = 0.6
        else:
            freshness_score = 0.3

        # Combined score
        self.trust_score = (
            accuracy_weight * accuracy_score +
            reliability_weight * reliability_score +
            freshness_weight * freshness_score
        )

        # Update trust level
        if self.trust_score >= 0.9:
            self.trust_level = TrustLevel.AUTHORITATIVE
        elif self.trust_score >= 0.7:
            self.trust_level = TrustLevel.HIGH
        elif self.trust_score >= 0.5:
            self.trust_level = TrustLevel.MEDIUM
        elif self.trust_score >= 0.3:
            self.trust_level = TrustLevel.LOW
        else:
            self.trust_level = TrustLevel.UNTRUSTED

        self.last_updated = utc_now()


class SourceTrustManager:
    """
    Manages trust scores for all data sources.

    Thread-safe singleton pattern for consistent trust management.
    """

    # Default trust scores for known sources
    DEFAULT_TRUST_SCORES: dict[str, float] = {
        # Market data sources (generally reliable)
        "polymarket": 0.75,
        "stock": 0.85,
        "commodity": 0.80,
        
        # Physical data sources
        "ais": 0.70,
        "weather": 0.85,
        "freight": 0.75,
        
        # News sources (variable quality)
        "news": 0.60,
        
        # Partner data
        "partner_risk": 0.65,
    }

    def __init__(self):
        self._trust_scores: dict[str, SourceTrustScore] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize with default trust scores."""
        for source_id, score in self.DEFAULT_TRUST_SCORES.items():
            self._trust_scores[source_id] = SourceTrustScore(
                source_id=source_id,
                trust_score=score,
                trust_level=TrustLevel.from_score(score) if hasattr(TrustLevel, 'from_score') else TrustLevel.MEDIUM,
            )

    def get_trust_score(self, source_id: str) -> SourceTrustScore:
        """Get trust score for a source."""
        if source_id not in self._trust_scores:
            # Create new entry with default medium trust
            self._trust_scores[source_id] = SourceTrustScore(
                source_id=source_id,
                trust_score=0.5,
                trust_level=TrustLevel.MEDIUM,
            )
        return self._trust_scores[source_id]

    def get_trust_weight(self, source_id: str) -> float:
        """Get normalized weight for source (0.0 - 1.0)."""
        score = self.get_trust_score(source_id)
        return score.trust_score

    def record_signal_accuracy(
        self,
        source_id: str,
        was_accurate: bool,
    ) -> None:
        """Record whether a signal from source was accurate."""
        score = self.get_trust_score(source_id)
        score.update_accuracy(was_accurate)

    def record_api_call(
        self,
        source_id: str,
        success: bool,
        latency_ms: float = 0.0,
    ) -> None:
        """Record API call result."""
        score = self.get_trust_score(source_id)
        score.update_reliability(success, latency_ms)

    def record_data_freshness(
        self,
        source_id: str,
        data_age_seconds: float,
    ) -> None:
        """Record data freshness."""
        score = self.get_trust_score(source_id)
        score.update_freshness(data_age_seconds)

    def resolve_conflict(
        self,
        source_a: str,
        source_b: str,
        value_a: Any,
        value_b: Any,
    ) -> tuple[str, Any, float]:
        """
        Resolve conflict between two sources by trust score.

        Returns:
            (winning_source, winning_value, confidence)
        """
        trust_a = self.get_trust_weight(source_a)
        trust_b = self.get_trust_weight(source_b)

        if trust_a >= trust_b:
            # Source A wins
            confidence = trust_a / (trust_a + trust_b) if (trust_a + trust_b) > 0 else 0.5
            return source_a, value_a, confidence
        else:
            # Source B wins
            confidence = trust_b / (trust_a + trust_b) if (trust_a + trust_b) > 0 else 0.5
            return source_b, value_b, confidence

    def weighted_average(
        self,
        values: dict[str, float],
    ) -> tuple[float, float]:
        """
        Calculate trust-weighted average of values.

        Args:
            values: Dict of source_id -> value

        Returns:
            (weighted_average, total_weight)
        """
        if not values:
            return 0.0, 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for source_id, value in values.items():
            weight = self.get_trust_weight(source_id)
            weighted_sum += value * weight
            total_weight += weight

        if total_weight == 0:
            return sum(values.values()) / len(values), 1.0

        return weighted_sum / total_weight, total_weight

    def get_all_trust_scores(self) -> dict[str, SourceTrustScore]:
        """Get all current trust scores."""
        return dict(self._trust_scores)

    def get_trust_summary(self) -> dict[str, Any]:
        """Get summary of all source trust levels."""
        summary = {
            "total_sources": len(self._trust_scores),
            "by_level": {},
            "sources": {},
        }

        for level in TrustLevel:
            summary["by_level"][level.value] = 0

        for source_id, score in self._trust_scores.items():
            summary["by_level"][score.trust_level.value] += 1
            summary["sources"][source_id] = {
                "trust_score": round(score.trust_score, 3),
                "trust_level": score.trust_level.value,
                "accuracy_rate": round(score.accuracy_rate, 3),
                "error_rate": round(score.error_rate, 3),
            }

        return summary


# Singleton instance
_trust_manager: Optional[SourceTrustManager] = None


def get_trust_manager() -> SourceTrustManager:
    """Get the singleton trust manager instance."""
    global _trust_manager
    if _trust_manager is None:
        _trust_manager = SourceTrustManager()
    return _trust_manager
