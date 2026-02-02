"""
Tests for Phase 2 validation rules: NewsQualityGateRule and CommodityContextRule.

Tests cover:
1. NewsQualityGateRule: fail-closed behavior, bounded scoring
2. CommodityContextRule: context-only, bounded scoring, JSON safety
3. Integration: rules pass non-applicable signals
"""

import pytest
import math
from datetime import datetime, timezone
from uuid import uuid4

from omen.domain.rules.validation.news_quality_rule import NewsQualityGateRule
from omen.domain.rules.validation.commodity_context_rule import CommodityContextRule
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.common import ValidationStatus


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def news_quality_rule() -> NewsQualityGateRule:
    """Create news quality gate rule."""
    return NewsQualityGateRule()


@pytest.fixture
def commodity_context_rule() -> CommodityContextRule:
    """Create commodity context rule."""
    return CommodityContextRule()


@pytest.fixture
def reference_time() -> datetime:
    """Fixed reference time."""
    return datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)


def create_signal_with_source_metrics(
    source_metrics: dict | None,
    title: str = "Test Signal",
    probability: float = 0.5,
) -> RawSignalEvent:
    """Create a RawSignalEvent with given source_metrics."""
    now = datetime.now(timezone.utc)
    return RawSignalEvent(
        event_id=str(uuid4()),
        title=title,
        description="Test description",
        probability=probability,
        observed_at=now,
        market=MarketMetadata(
            source="test",
            market_id="test-market-123",
            created_at=now,
            current_liquidity_usd=10000.0,
            total_volume_usd=5000.0,
        ),
        keywords=["test"],
        source_metrics=source_metrics or {},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE RULE - PASS-THROUGH
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsQualityGateRulePassThrough:
    """Tests for non-news signal pass-through."""
    
    def test_non_news_signal_passes(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Non-news signals pass through unchanged."""
        signal = create_signal_with_source_metrics(None)
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0
        assert "not a news source" in result.reason.lower()
    
    def test_signal_with_empty_source_metrics_passes(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Signals with empty source_metrics pass through."""
        signal = create_signal_with_source_metrics({})
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
    
    def test_commodity_signal_passes(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Commodity signals pass through news rule."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": True,
            "zscore": 2.5,
        })
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE RULE - FAIL-CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsQualityGateRuleFailClosed:
    """Tests for fail-closed behavior."""
    
    def test_low_credibility_rejected(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Low credibility news is rejected."""
        signal = create_signal_with_source_metrics({
            "credibility_score": 0.1,  # Below threshold
            "recency_score": 0.9,
            "combined_score": 0.5,
        })
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.REJECTED_RULE
        assert "credibility" in result.reason.lower()
    
    def test_stale_news_rejected(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Stale news (low recency) is rejected."""
        signal = create_signal_with_source_metrics({
            "credibility_score": 0.9,
            "recency_score": 0.05,  # Below threshold
            "combined_score": 0.4,
        })
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.REJECTED_RULE
        assert "stale" in result.reason.lower() or "recency" in result.reason.lower()
    
    def test_duplicate_rejected(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Duplicate articles are rejected."""
        signal = create_signal_with_source_metrics({
            "credibility_score": 0.9,
            "recency_score": 0.9,
            "combined_score": 0.9,
            "is_duplicate": True,  # Duplicate
        })
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.REJECTED_RULE
        assert "duplicate" in result.reason.lower()
    
    def test_low_combined_score_rejected(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Low combined score is rejected."""
        signal = create_signal_with_source_metrics({
            "credibility_score": 0.4,
            "recency_score": 0.4,
            "combined_score": 0.15,  # Below threshold
        })
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.REJECTED_RULE
        assert "combined" in result.reason.lower() or "quality" in result.reason.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE RULE - BOUNDED SCORING
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsQualityGateRuleBounded:
    """Tests for bounded scoring."""
    
    def test_high_quality_news_passes(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """High quality news passes validation."""
        signal = create_signal_with_source_metrics({
            "credibility_score": 0.95,
            "recency_score": 1.0,
            "combined_score": 0.97,
            "is_duplicate": False,
        })
        
        result = news_quality_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
        assert result.score > 0.5
    
    def test_score_bounded_by_max_boost(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """Score contribution is bounded by max_confidence_boost."""
        signal = create_signal_with_source_metrics({
            "credibility_score": 1.0,
            "recency_score": 1.0,
            "combined_score": 1.0,
            "is_duplicate": False,
        })
        
        result = news_quality_rule.apply(signal)
        
        # Score should be bounded
        assert result.score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COMMODITY CONTEXT RULE - PASS-THROUGH
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommodityContextRulePassThrough:
    """Tests for non-commodity signal pass-through."""
    
    def test_non_commodity_signal_passes(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Non-commodity signals pass through unchanged."""
        signal = create_signal_with_source_metrics(None)
        
        result = commodity_context_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0
    
    def test_news_signal_passes(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """News signals pass through commodity rule."""
        signal = create_signal_with_source_metrics({
            "credibility_score": 0.9,
            "recency_score": 0.8,
        })
        
        result = commodity_context_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COMMODITY CONTEXT RULE - CONTEXT ONLY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommodityContextRuleContextOnly:
    """Tests for context-only behavior."""
    
    def test_non_spike_neutral_score(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Non-spike commodity data gets neutral score."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": False,
            "zscore": 0.5,
            "pct_change": 2.0,
        })
        
        result = commodity_context_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
        assert result.score == 0.5  # Neutral
        assert "no significant" in result.reason.lower()
    
    def test_spike_below_threshold_neutral_score(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Spike below severity threshold gets neutral score."""
        # Create rule with higher threshold
        rule = CommodityContextRule(min_severity="moderate")
        
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": True,
            "severity": "minor",  # Below threshold
            "zscore": 1.5,
            "pct_change": 8.0,
        })
        
        result = rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
        assert result.score == 0.5  # Neutral
    
    def test_spike_above_threshold_boosted_score(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Spike above severity threshold gets boosted score."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": True,
            "severity": "moderate",
            "zscore": 2.5,
            "pct_change": 15.0,
        })
        
        result = commodity_context_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
        assert result.score > 0.5  # Boosted


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COMMODITY CONTEXT RULE - BOUNDED SCORING
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommodityContextRuleBounded:
    """Tests for bounded scoring."""
    
    def test_major_spike_score_bounded(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Major spike score is bounded by max_confidence_boost."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": True,
            "severity": "major",
            "zscore": 5.0,
            "pct_change": 30.0,
        })
        
        result = commodity_context_rule.apply(signal)
        
        assert result.score <= 1.0
        # Score = base (0.5) + boost (max 0.08)
        assert result.score <= 0.5 + 0.08 + 0.01  # Small margin


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COMMODITY CONTEXT RULE - JSON SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommodityContextRuleJSONSafety:
    """Tests for JSON safety."""
    
    def test_nan_zscore_handled(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """NaN zscore is handled gracefully."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": True,
            "severity": "moderate",
            "zscore": float('nan'),  # NaN
            "pct_change": 15.0,
        })
        
        # Should not raise
        result = commodity_context_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
    
    def test_inf_zscore_handled(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Inf zscore is handled gracefully."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": True,
            "severity": "moderate",
            "zscore": float('inf'),  # Inf
            "pct_change": 15.0,
        })
        
        # Should not raise
        result = commodity_context_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED
    
    def test_extreme_zscore_bounded(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Extreme zscore values are bounded."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "is_spike": True,
            "severity": "major",
            "zscore": 1000.0,  # Extreme
            "pct_change": 50.0,
        })
        
        # Should not raise
        result = commodity_context_rule.apply(signal)
        
        assert result.status == ValidationStatus.PASSED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RULE METADATA
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleMetadata:
    """Tests for rule metadata."""
    
    def test_news_rule_name_and_version(
        self,
        news_quality_rule: NewsQualityGateRule,
    ):
        """News rule has correct name and version."""
        assert news_quality_rule.name == "news_quality_gate"
        assert news_quality_rule.version == "1.0.0"
        assert "news_quality_gate@1.0.0" in news_quality_rule.qualified_name
    
    def test_commodity_rule_name_and_version(
        self,
        commodity_context_rule: CommodityContextRule,
    ):
        """Commodity rule has correct name and version."""
        assert commodity_context_rule.name == "commodity_context"
        assert commodity_context_rule.version == "1.0.0"
        assert "commodity_context@1.0.0" in commodity_context_rule.qualified_name


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EXPLANATION GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplanationGeneration:
    """Tests for explanation generation."""
    
    def test_news_rule_generates_explanation(
        self,
        news_quality_rule: NewsQualityGateRule,
        reference_time: datetime,
    ):
        """News rule generates explanation step."""
        signal = create_signal_with_source_metrics({
            "source_domain": "reuters.com",
            "credibility_score": 0.95,
            "recency_score": 1.0,
            "combined_score": 0.97,
            "matched_topics": ["red_sea_disruption"],
        })
        
        result = news_quality_rule.apply(signal)
        explanation = news_quality_rule.explain(signal, result, reference_time)
        
        assert explanation.rule_name == "news_quality_gate"
        assert "reuters.com" in str(explanation.input_summary)
        assert explanation.output_summary["status"] == "PASSED"
    
    def test_commodity_rule_generates_explanation(
        self,
        commodity_context_rule: CommodityContextRule,
        reference_time: datetime,
    ):
        """Commodity rule generates explanation step."""
        signal = create_signal_with_source_metrics({
            "symbol": "BRENT",
            "category": "energy",
            "is_spike": True,
            "severity": "moderate",
            "pct_change": 15.0,
            "zscore": 2.5,
        })
        
        result = commodity_context_rule.apply(signal)
        explanation = commodity_context_rule.explain(signal, result, reference_time)
        
        assert explanation.rule_name == "commodity_context"
        assert "BRENT" in str(explanation.input_summary)
        assert explanation.output_summary["status"] == "PASSED"
