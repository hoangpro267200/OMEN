"""
Test SignalValidator edge cases.

Coverage target: 95%
Focus: Rule error handling, multiple rules, edge cases
"""

from datetime import datetime

import pytest

from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.validated_signal import ValidationResult
from omen.domain.models.common import (
    EventId,
    MarketId,
    ValidationStatus,
    RulesetVersion,
)
from omen.domain.models.context import ProcessingContext
from omen.domain.models.explanation import ExplanationStep
from omen.domain.services.signal_validator import SignalValidator, ValidationOutcome
from omen.domain.rules.base import Rule
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule


def _make_event(liquidity: float = 10_000.0) -> RawSignalEvent:
    return RawSignalEvent(
        event_id=EventId("validator-edge-001"),
        title="Red Sea shipping",
        probability=0.7,
        market=MarketMetadata(
            source="test",
            market_id=MarketId("m1"),
            total_volume_usd=liquidity * 2,
            current_liquidity_usd=liquidity,
        ),
    )


class FailingRule(Rule[RawSignalEvent, ValidationResult]):
    """A validation rule that raises when apply() is called."""

    @property
    def name(self) -> str:
        return "failing_rule"

    @property
    def version(self) -> str:
        return "1.0.0"

    def apply(self, input_data: RawSignalEvent) -> ValidationResult:
        raise RuntimeError("rule blew up")

    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        return ExplanationStep.create(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            reasoning="N/A",
            confidence_contribution=0.0,
            processing_time=processing_time or datetime.utcnow(),
        )


class PassThenFailRule(Rule[RawSignalEvent, ValidationResult]):
    """First call passes, second (by order) would fail; used for multiple-rule ordering."""

    def __init__(self, pass_first: bool = True):
        self._pass_first = pass_first

    @property
    def name(self) -> str:
        return "pass_then_fail"

    @property
    def version(self) -> str:
        return "1.0.0"

    def apply(self, input_data: RawSignalEvent) -> ValidationResult:
        if self._pass_first:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=0.9,
                reason="OK",
            )
        raise RuntimeError("failed")

    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        return ExplanationStep.create(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            reasoning="N/A",
            confidence_contribution=0.0,
            processing_time=processing_time or datetime.utcnow(),
        )


@pytest.fixture
def validator():
    """Default validator with one passing rule."""
    return SignalValidator(rules=[LiquidityValidationRule(min_liquidity_usd=100.0)])


@pytest.fixture
def valid_event():
    return _make_event(50_000.0)


@pytest.fixture
def validator_with_failing_rule():
    return SignalValidator(
        rules=[FailingRule()],
        fail_on_rule_error=True,
    )


@pytest.fixture
def validator_continue_on_error():
    return SignalValidator(
        rules=[FailingRule(), LiquidityValidationRule(min_liquidity_usd=100.0)],
        fail_on_rule_error=False,
    )


@pytest.fixture
def validator_fail_on_error():
    return SignalValidator(
        rules=[FailingRule()],
        fail_on_rule_error=True,
    )


@pytest.fixture
def validator_multiple_rules():
    return SignalValidator(
        rules=[
            LiquidityValidationRule(min_liquidity_usd=100.0),
            PassThenFailRule(pass_first=False),
        ],
        fail_on_rule_error=True,
    )


class TestRuleErrorHandling:
    """Handling of rule exceptions."""

    def test_rule_exception_creates_error_result(
        self, validator_with_failing_rule, valid_event
    ) -> None:
        """Rule raises → ValidationOutcome with REJECTED_RULE_ERROR in results."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator_with_failing_rule.validate(valid_event, context=ctx)
        assert outcome.passed is False
        assert outcome.signal is None
        assert outcome.results is not None
        assert len(outcome.results) >= 1
        err_result = outcome.results[-1]
        assert err_result.status == ValidationStatus.REJECTED_RULE_ERROR
        assert "rule blew up" in err_result.reason or "Rule error" in err_result.reason

    def test_continues_after_rule_error_when_configured(
        self, validator_continue_on_error, valid_event
    ) -> None:
        """fail_on_rule_error=False → continues to next rule; both rule results present."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator_continue_on_error.validate(valid_event, context=ctx)
        assert outcome.results is not None
        assert any(r.status == ValidationStatus.REJECTED_RULE_ERROR for r in outcome.results)
        assert any(r.rule_name == "liquidity_validation" for r in outcome.results)
        assert len(outcome.results) >= 2
        # When continue-on-error: first rule errored, second passed → overall passed
        assert outcome.passed is True
        assert outcome.signal is not None

    def test_stops_after_rule_error_when_configured(
        self, validator_fail_on_error, valid_event
    ) -> None:
        """fail_on_rule_error=True → stops and returns failure."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator_fail_on_error.validate(valid_event, context=ctx)
        assert outcome.passed is False
        assert outcome.rejection_reason is not None
        assert "failing_rule" in outcome.rejection_reason or "errored" in outcome.rejection_reason


class TestMultipleRules:
    """Multiple rule behavior."""

    def test_all_rules_applied_in_order(self, validator_multiple_rules, valid_event) -> None:
        """Each rule in list is applied until one fails."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator_multiple_rules.validate(valid_event, context=ctx)
        assert outcome.passed is False
        assert outcome.results is not None
        assert len(outcome.results) >= 2
        names = [r.rule_name for r in outcome.results]
        assert "liquidity_validation" in names
        assert "pass_then_fail" in names

    def test_stops_on_first_rejection(self, validator_multiple_rules, valid_event) -> None:
        """First rejecting/erring rule → stops, returns that outcome."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator_multiple_rules.validate(valid_event, context=ctx)
        assert outcome.passed is False
        assert outcome.rejection_reason is not None

    def test_all_passed_returns_validated_signal(self, validator, valid_event) -> None:
        """All rules pass → ValidatedSignal returned."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator.validate(valid_event, context=ctx)
        assert outcome.passed is True
        assert outcome.signal is not None
        assert outcome.signal.event_id == valid_event.event_id


class TestExplanationChain:
    """Explanation building."""

    def test_explanation_contains_all_passing_rules(self, validator, valid_event) -> None:
        """Each passing rule adds ExplanationStep."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator.validate(valid_event, context=ctx)
        assert outcome.passed and outcome.signal is not None
        chain = outcome.signal.explanation
        assert chain.steps is not None
        assert len(chain.steps) >= 1
        assert any(s.rule_name == "liquidity_validation" for s in chain.steps)

    def test_explanation_step_has_required_fields(self, validator, valid_event) -> None:
        """rule_name, rule_version, reasoning populated."""
        ctx = ProcessingContext.create(RulesetVersion("test"))
        outcome = validator.validate(valid_event, context=ctx)
        assert outcome.passed and outcome.signal is not None
        for step in outcome.signal.explanation.steps or []:
            assert step.rule_name
            assert step.rule_version
            assert step.reasoning is not None
