"""
Test pipeline edge cases and error handling.

Coverage target: 90%
Focus: DLQ, dry-run, error paths, boundary conditions
DO NOT: Test internal state, mock domain services deeply
"""

from unittest.mock import MagicMock

import pytest

from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.domain.models.common import EventId, ImpactDomain, RulesetVersion
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.impact_translator import ImpactTranslator
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.translation.logistics.red_sea_disruption import (
    RedSeaDisruptionRule,
)
from omen.domain.errors import (
    ValidationRuleError,
    TranslationRuleError,
    PersistenceError,
    PublishError,
    OmenError,
)
from omen.infrastructure.dead_letter import DeadLetterQueue
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository


@pytest.fixture
def pipeline_with_dlq():
    """Pipeline with DLQ for testing error handling."""
    dlq = DeadLetterQueue()
    pipeline = OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)]
        ),
        translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
        repository=InMemorySignalRepository(),
        publisher=None,
        dead_letter_queue=dlq,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            enable_dlq=True,
        ),
    )
    return pipeline, dlq


@pytest.fixture
def dry_run_pipeline():
    """Pipeline in dry-run mode with mocked repository and publisher."""
    repo = MagicMock()
    pub = MagicMock()
    return OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
        repository=repo,
        publisher=pub,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            enable_dry_run=True,
        ),
    )


@pytest.fixture
def pipeline_high_threshold():
    """Pipeline with min_confidence_for_output=0.9 (filters more)."""
    return OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
        repository=InMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            min_confidence_for_output=0.9,
        ),
    )


@pytest.fixture
def pipeline_low_threshold():
    """Pipeline with min_confidence_for_output=0.1 (passes more)."""
    return OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
        repository=InMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            min_confidence_for_output=0.1,
        ),
    )


@pytest.fixture
def pipeline_no_rules():
    """Pipeline with no translation rules."""
    return OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        translator=ImpactTranslator(rules=[]),
        repository=InMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
        ),
    )


@pytest.fixture
def pipeline_wrong_domain():
    """Pipeline targeting ENERGY only (Red Sea event won't match)."""
    return OmenPipeline(
        validator=SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        ),
        translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
        repository=InMemorySignalRepository(),
        publisher=None,
        config=PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.ENERGY}),
        ),
    )


class TestErrorHandling:
    """Error handling paths."""

    def test_validation_error_adds_to_dlq(
        self, pipeline_with_dlq, high_quality_event
    ) -> None:
        """ValidationRuleError → event in DLQ."""
        pipeline, dlq = pipeline_with_dlq
        pipeline._validator = MagicMock()
        pipeline._validator.validate = MagicMock(
            side_effect=ValidationRuleError("rule blew up", rule_name="test_rule")
        )
        result = pipeline.process_single(high_quality_event)
        assert result.success is False
        assert dlq.size() == 1
        entry = dlq.peek(1)[0]
        assert entry.event.event_id == high_quality_event.event_id
        assert "rule blew up" in entry.error.message or "test_rule" in entry.error.message

    def test_translation_error_adds_to_dlq(
        self, pipeline_with_dlq, high_quality_event
    ) -> None:
        """TranslationRuleError → event in DLQ."""
        pipeline, dlq = pipeline_with_dlq
        pipeline._validator = SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        )
        pipeline._translator = MagicMock()
        pipeline._translator.translate = MagicMock(
            side_effect=TranslationRuleError(
                "translate failed", rule_name="r", domain="LOGISTICS"
            )
        )
        result = pipeline.process_single(high_quality_event)
        assert result.success is False
        assert dlq.size() == 1

    def test_unexpected_error_adds_to_dlq(
        self, pipeline_with_dlq, high_quality_event
    ) -> None:
        """RuntimeError → event in DLQ with wrapped OmenError."""
        pipeline, dlq = pipeline_with_dlq
        pipeline._validator = MagicMock()
        pipeline._validator.validate = MagicMock(side_effect=RuntimeError("oops"))
        result = pipeline.process_single(high_quality_event)
        assert result.success is False
        assert dlq.size() == 1
        entry = dlq.peek(1)[0]
        assert isinstance(entry.error, OmenError)

    def test_repository_error_logs_but_continues(
        self, high_quality_event
    ) -> None:
        """Repository save failure → logged, signal still returned."""
        repo = MagicMock()
        repo.find_by_hash = MagicMock(return_value=None)
        repo.save = MagicMock(side_effect=PersistenceError("db down"))
        pipeline = OmenPipeline(
            validator=SignalValidator(
                rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
            ),
            translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
            repository=repo,
            publisher=None,
            config=PipelineConfig(
                ruleset_version=RulesetVersion("test"),
                target_domains=frozenset({ImpactDomain.LOGISTICS}),
            ),
        )
        result = pipeline.process_single(high_quality_event)
        assert result.success is True
        assert len(result.signals) >= 1
        repo.save.assert_called()

    def test_publisher_error_continues_when_configured(
        self, high_quality_event
    ) -> None:
        """fail_on_publish_error=False → continues on publish error."""
        repo = InMemorySignalRepository()
        pub = MagicMock()
        pub.publish = MagicMock(side_effect=PublishError("broker down"))
        pipeline = OmenPipeline(
            validator=SignalValidator(
                rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
            ),
            translator=ImpactTranslator(rules=[RedSeaDisruptionRule()]),
            repository=repo,
            publisher=pub,
            config=PipelineConfig(
                ruleset_version=RulesetVersion("test"),
                target_domains=frozenset({ImpactDomain.LOGISTICS}),
                fail_on_publish_error=False,
            ),
        )
        result = pipeline.process_single(high_quality_event)
        assert result.success is True
        assert len(result.signals) >= 1

    def test_publisher_error_fails_when_configured(
        self, pipeline_with_dlq, high_quality_event
    ) -> None:
        """fail_on_publish_error=True → raises on publish error, DLQ gets event."""
        pipeline, dlq = pipeline_with_dlq
        pipeline._publisher = MagicMock()
        pipeline._publisher.publish = MagicMock(
            side_effect=PublishError("broker down")
        )
        pipeline._config = PipelineConfig(
            ruleset_version=RulesetVersion("test"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            fail_on_publish_error=True,
        )
        result = pipeline.process_single(high_quality_event)
        assert result.success is False
        assert dlq.size() == 1


class TestDLQReprocessing:
    """Dead letter queue reprocessing."""

    def test_reprocess_empty_dlq_returns_empty(self, pipeline_with_dlq) -> None:
        """Empty DLQ → empty results list."""
        pipeline, dlq = pipeline_with_dlq
        results = pipeline.reprocess_dlq()
        assert results == []

    def test_reprocess_returns_results(
        self, pipeline_with_dlq, high_quality_event
    ) -> None:
        """DLQ with items → list of PipelineResult."""
        pipeline, dlq = pipeline_with_dlq
        pipeline._validator = MagicMock()
        pipeline._validator.validate = MagicMock(
            side_effect=ValidationRuleError("x", rule_name="r")
        )
        pipeline.process_single(high_quality_event)
        assert dlq.size() == 1
        pipeline._validator = SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        )
        results = pipeline.reprocess_dlq()
        assert len(results) == 1
        assert isinstance(results[0].success, bool)

    def test_reprocess_respects_max_items(
        self, pipeline_with_dlq, high_quality_event
    ) -> None:
        """max_items=2 with 5 items → processes only 2."""
        pipeline, dlq = pipeline_with_dlq
        pipeline._validator = MagicMock()
        pipeline._validator.validate = MagicMock(
            side_effect=ValidationRuleError("x", rule_name="r")
        )
        for i in range(5):
            evt = high_quality_event.model_copy(
                update={"event_id": EventId(f"evt-{i}")}
            )
            pipeline.process_single(evt)
        pipeline._validator = SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        )
        n_before = dlq.size()
        results = pipeline.reprocess_dlq(max_items=2)
        assert len(results) == 2
        assert dlq.size() == n_before - 2

    def test_reprocess_removes_from_dlq(
        self, pipeline_with_dlq, high_quality_event
    ) -> None:
        """Reprocessed items removed from DLQ."""
        pipeline, dlq = pipeline_with_dlq
        pipeline._validator = MagicMock()
        pipeline._validator.validate = MagicMock(
            side_effect=ValidationRuleError("x", rule_name="r")
        )
        pipeline.process_single(high_quality_event)
        assert dlq.size() == 1
        pipeline._validator = SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        )
        pipeline.reprocess_dlq(max_items=10)
        assert dlq.size() == 0


class TestDryRun:
    """Dry run mode behavior."""

    def test_dry_run_does_not_persist(
        self, dry_run_pipeline, high_quality_event
    ) -> None:
        """enable_dry_run=True → repository.save not called."""
        dry_run_pipeline.process_single(high_quality_event)
        dry_run_pipeline._repository.save.assert_not_called()

    def test_dry_run_does_not_publish(
        self, dry_run_pipeline, high_quality_event
    ) -> None:
        """enable_dry_run=True → publisher.publish not called."""
        dry_run_pipeline.process_single(high_quality_event)
        dry_run_pipeline._publisher.publish.assert_not_called()

    def test_dry_run_still_returns_signals(
        self, dry_run_pipeline, high_quality_event
    ) -> None:
        """Signals generated and returned, just not persisted."""
        result = dry_run_pipeline.process_single(high_quality_event)
        assert result.success is True
        assert len(result.signals) >= 1


class TestConfidenceFiltering:
    """Confidence threshold filtering."""

    def test_filters_below_threshold(
        self, pipeline_high_threshold, high_quality_event
    ) -> None:
        """min_confidence=0.9 → low confidence signals may be filtered."""
        result = pipeline_high_threshold.process_single(high_quality_event)
        assert result.success is True
        if result.signals:
            assert all(s.confidence_score >= 0.9 for s in result.signals)
        else:
            assert result.stats.events_no_impact >= 0 or len(result.signals) == 0

    def test_passes_above_threshold(
        self, pipeline_low_threshold, high_quality_event
    ) -> None:
        """min_confidence=0.1 → high confidence signals pass."""
        result = pipeline_low_threshold.process_single(high_quality_event)
        assert result.success is True
        assert len(result.signals) >= 1


class TestNoApplicableRules:
    """Events with no matching rules."""

    def test_no_translation_rules_returns_empty(
        self, pipeline_no_rules, high_quality_event
    ) -> None:
        """No translation rules → empty signals, events_no_impact=1."""
        result = pipeline_no_rules.process_single(high_quality_event)
        assert result.success is True
        assert len(result.signals) == 0
        assert result.stats.events_no_impact == 1

    def test_no_matching_domain_returns_empty(
        self, pipeline_wrong_domain, high_quality_event
    ) -> None:
        """Event domain doesn't match any rule → empty signals."""
        result = pipeline_wrong_domain.process_single(high_quality_event)
        assert result.success is True
        assert len(result.signals) == 0
        assert result.stats.events_no_impact == 1
