"""Tests for OMEN error hierarchy and pipeline error handling."""

import pytest

from omen.domain.errors import (
    OmenError,
    SourceRateLimitedError,
    ValidationRuleError,
    TranslationRuleError,
    SignalNotFoundError,
    PublishRetriesExhaustedError,
)
from omen.infrastructure.dead_letter import DeadLetterQueue
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.adapters.outbound.console_publisher import ConsolePublisher
from omen.domain.models.common import ImpactDomain, RulesetVersion


class TestOmenErrorHierarchy:
    """Error types carry context and serialize to dict."""

    def test_base_error_has_message_and_context(self):
        err = OmenError("test", context={"a": 1})
        assert err.message == "test"
        assert err.context == {"a": 1}
        assert "timestamp" in err.to_dict()
        assert err.to_dict()["error_type"] == "OmenError"

    def test_source_rate_limited_has_retry_after(self):
        err = SourceRateLimitedError("limited", retry_after_seconds=60)
        assert err.retry_after_seconds == 60

    def test_validation_rule_error_has_rule_name(self):
        err = ValidationRuleError("oops", rule_name="liquidity_validation")
        assert err.rule_name == "liquidity_validation"

    def test_translation_rule_error_has_domain(self):
        err = TranslationRuleError("oops", rule_name="r", domain="LOGISTICS")
        assert err.domain == "LOGISTICS"

    def test_signal_not_found_has_signal_id(self):
        err = SignalNotFoundError("sig-123")
        assert err.signal_id == "sig-123"
        assert "sig-123" in err.message

    def test_publish_retries_exhausted_has_attempts(self):
        err = PublishRetriesExhaustedError("failed", attempts=5, context={"x": 1})
        assert err.attempts == 5


class TestPipelineErrorHandling:
    """Pipeline sends failures to DLQ and returns structured results."""

    @pytest.fixture
    def dlq(self):
        return DeadLetterQueue(max_size=100)

    @pytest.fixture
    def pipeline_with_dlq(self, dlq):
        validator = SignalValidator(rules=[LiquidityValidationRule(min_liquidity_usd=1000.0)])
        enricher = SignalEnricher()
        repo = InMemorySignalRepository()
        pub = ConsolePublisher()
        config = PipelineConfig(
            ruleset_version=RulesetVersion("v1.0.0"),
            target_domains=frozenset({ImpactDomain.LOGISTICS}),
            enable_dlq=True,
        )
        return OmenPipeline(
            validator=validator,
            enricher=enricher,
            repository=repo,
            publisher=pub,
            dead_letter_queue=dlq,
            config=config,
        )

    def test_validation_rejection_returns_failures_not_exception(
        self, pipeline_with_dlq, low_liquidity_event
    ):
        result = pipeline_with_dlq.process_single(low_liquidity_event)
        assert result.success is True
        assert len(result.signals) == 0
        assert len(result.validation_failures) >= 1
        assert result.stats.events_rejected_validation >= 1

    def test_dlq_empty_when_validation_rejection(self, pipeline_with_dlq, dlq, low_liquidity_event):
        pipeline_with_dlq.process_single(low_liquidity_event)
        assert dlq.size() == 0

    def test_reprocess_dlq_empty_returns_empty_list(self, pipeline_with_dlq):
        results = pipeline_with_dlq.reprocess_dlq(max_items=10)
        assert results == []
