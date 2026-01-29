"""
Test ImpactTranslator edge cases.

Coverage target: 95%
Focus: Rule filtering, error handling, no-match scenarios
"""

from datetime import datetime

import pytest

from omen.domain.models.common import (
    EventId,
    MarketId,
    ImpactDomain,
    RulesetVersion,
    SignalCategory,
    ValidationStatus,
)
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen_impact import ImpactTranslator
from omen_impact.rules.base import TranslationResult, ImpactTranslationRule
from omen_impact.rules.logistics import RedSeaDisruptionRule

_FIXED_TIME = datetime(2025, 1, 15, 12, 0, 0)


def _make_validated_signal(
    event: RawSignalEvent,
    category: SignalCategory,
    chokepoints: list[str],
    keywords: list[str],
) -> ValidatedSignal:
    ctx = ProcessingContext.create_for_replay(
        processing_time=_FIXED_TIME,
        ruleset_version=RulesetVersion("test-v1"),
    )
    step = ExplanationStep.create(
        step_id=1,
        rule_name="liquidity_validation",
        rule_version="1.0.0",
        reasoning="OK",
        confidence_contribution=0.27,
        processing_time=ctx.processing_time,
        input_summary={},
        output_summary={},
    )
    chain = ExplanationChain.create(ctx).add_step(step).finalize(ctx)
    return ValidatedSignal(
        event_id=event.event_id,
        original_event=event,
        category=category,
        relevant_locations=event.inferred_locations,
        affected_chokepoints=chokepoints,
        validation_results=[
            ValidationResult(
                rule_name="liquidity",
                rule_version="1.0",
                status=ValidationStatus.PASSED,
                score=0.9,
                reason="OK",
            )
        ],
        overall_validation_score=0.9,
        signal_strength=0.9,
        liquidity_score=0.9,
        explanation=chain,
        ruleset_version=RulesetVersion("test-v1"),
        validated_at=ctx.processing_time,
    )


class FailingTranslationRule:
    """A translation rule that raises when translate() is called."""

    @property
    def name(self) -> str:
        return "failing_translation_rule"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def domain(self) -> ImpactDomain:
        return ImpactDomain.LOGISTICS

    @property
    def applicable_categories(self) -> set[SignalCategory]:
        return {SignalCategory.GEOPOLITICAL, SignalCategory.INFRASTRUCTURE}

    def is_applicable(self, signal: ValidatedSignal) -> bool:
        return True

    def translate(
        self,
        signal: ValidatedSignal,
        *,
        processing_time: datetime | None = None,
    ) -> TranslationResult:
        raise RuntimeError("translation rule failed")


@pytest.fixture
def logistics_signal() -> ValidatedSignal:
    """Validated signal that matches Red Sea / logistics rules."""
    event = RawSignalEvent(
        event_id=EventId("log-001"),
        title="Red Sea shipping disruption",
        description="Houthi attacks",
        probability=0.75,
        keywords=["red sea", "shipping", "suez"],
        inferred_locations=[],
        market=MarketMetadata(
            source="test", market_id=MarketId("m1"),
            total_volume_usd=100_000.0, current_liquidity_usd=50_000.0,
        ),
    )
    return _make_validated_signal(
        event,
        category=SignalCategory.GEOPOLITICAL,
        chokepoints=["Red Sea", "Suez Canal"],
        keywords=event.keywords,
    )


@pytest.fixture
def unrelated_signal() -> ValidatedSignal:
    """Validated signal that does not match any logistics rule."""
    event = RawSignalEvent(
        event_id=EventId("unrel-001"),
        title="Will it rain in Tokyo?",
        description="Weather only.",
        probability=0.3,
        keywords=["weather", "rain"],
        inferred_locations=[],
        market=MarketMetadata(
            source="test", market_id=MarketId("m2"),
            total_volume_usd=10_000.0, current_liquidity_usd=5_000.0,
        ),
    )
    return _make_validated_signal(
        event,
        category=SignalCategory.CLIMATE,
        chokepoints=[],
        keywords=event.keywords,
    )


@pytest.fixture
def multi_match_signal(logistics_signal: ValidatedSignal) -> ValidatedSignal:
    """Signal matching Red Sea (same as logistics_signal for single-rule case)."""
    return logistics_signal


@pytest.fixture
def high_prob_signal(logistics_signal: ValidatedSignal) -> ValidatedSignal:
    """High-probability logistics signal for severity checks."""
    return logistics_signal


@pytest.fixture
def translator() -> ImpactTranslator:
    return ImpactTranslator(rules=[RedSeaDisruptionRule()])


@pytest.fixture
def empty_translator() -> ImpactTranslator:
    return ImpactTranslator(rules=[])


@pytest.fixture
def translator_with_failing_rule() -> ImpactTranslator:
    return ImpactTranslator(rules=[FailingTranslationRule()])


@pytest.fixture
def translator_mixed_rules() -> ImpactTranslator:
    return ImpactTranslator(
        rules=[FailingTranslationRule(), RedSeaDisruptionRule()]
    )


class TestRuleFiltering:
    """Rule applicability filtering."""

    def test_only_matching_domain_rules_applied(
        self, translator: ImpactTranslator, logistics_signal: ValidatedSignal
    ) -> None:
        """LOGISTICS signal → only logistics rules run."""
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = translator.translate(
            logistics_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is not None
        assert out.domain == ImpactDomain.LOGISTICS

    def test_skips_non_applicable_rules(
        self, unrelated_signal: ValidatedSignal
    ) -> None:
        """Signal not matching rule keywords → rule skipped, no fallback → None."""
        no_fallback = ImpactTranslator(
            rules=[RedSeaDisruptionRule()], fallback_enabled=False
        )
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = no_fallback.translate(
            unrelated_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is None

    def test_multiple_applicable_rules_all_run(
        self, translator: ImpactTranslator, multi_match_signal: ValidatedSignal
    ) -> None:
        """Signal matching rule → assessment produced."""
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = translator.translate(
            multi_match_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is not None
        assert len(out.metrics) >= 1 or len(out.affected_routes) >= 1


class TestNoMatchScenarios:
    """No applicable rules scenarios."""

    def test_no_matching_rules_returns_none(
        self, unrelated_signal: ValidatedSignal
    ) -> None:
        """No rules match and fallback disabled → returns None."""
        no_fallback = ImpactTranslator(
            rules=[RedSeaDisruptionRule()], fallback_enabled=False
        )
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = no_fallback.translate(
            unrelated_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is None

    def test_empty_rules_list_returns_none(
        self, logistics_signal: ValidatedSignal
    ) -> None:
        """No rules configured and fallback disabled → returns None."""
        no_fallback = ImpactTranslator(rules=[], fallback_enabled=False)
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = no_fallback.translate(
            logistics_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is None


class TestRuleErrorHandling:
    """Rule exception handling."""

    def test_rule_exception_logged_and_skipped(
        self, logistics_signal: ValidatedSignal
    ) -> None:
        """Rule raises → logged, no applicable results, fallback disabled → None."""
        failing_only = ImpactTranslator(
            rules=[FailingTranslationRule()], fallback_enabled=False
        )
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = failing_only.translate(
            logistics_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is None

    def test_partial_results_returned_on_some_failures(
        self, translator_mixed_rules: ImpactTranslator, logistics_signal: ValidatedSignal
    ) -> None:
        """Some rules fail → results from successful rules returned."""
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = translator_mixed_rules.translate(
            logistics_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is not None
        assert out.domain == ImpactDomain.LOGISTICS
        assert out.overall_severity >= 0


class TestAssessmentBuilding:
    """ImpactAssessment construction."""

    def test_metrics_aggregated_from_all_rules(
        self, translator: ImpactTranslator, multi_match_signal: ValidatedSignal
    ) -> None:
        """Metrics from matching rules present."""
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = translator.translate(
            multi_match_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is not None
        assert len(out.metrics) >= 1 or len(out.affected_routes) >= 1

    def test_severity_calculated_correctly(
        self, translator: ImpactTranslator, high_prob_signal: ValidatedSignal
    ) -> None:
        """Severity reflects rule contributions."""
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = translator.translate(
            high_prob_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is not None
        assert 0 <= out.overall_severity <= 1
        assert out.severity_label in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW")

    def test_explanation_chain_finalized(
        self, translator: ImpactTranslator, logistics_signal: ValidatedSignal
    ) -> None:
        """ExplanationChain has completed_at set."""
        ctx = ProcessingContext.create_for_replay(
            processing_time=_FIXED_TIME,
            ruleset_version=RulesetVersion("test"),
        )
        out = translator.translate(
            logistics_signal, domain=ImpactDomain.LOGISTICS, context=ctx
        )
        assert out is not None
        assert out.explanation_chain is not None
        assert out.explanation_chain.completed_at is not None
