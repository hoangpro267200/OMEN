"""
Impact Translation Rule Interface.

Translation rules convert belief into consequence.
Lives in omen_impact; uses omen.domain for ValidatedSignal, Rule, etc.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable

from omen.domain.models.common import ImpactDomain, SignalCategory
from omen.domain.models.validated_signal import ValidatedSignal
from omen.domain.models.explanation import ExplanationStep
from omen.domain.rules.base import Rule

from omen_impact.assessment import (
    ImpactMetric,
    AffectedRoute,
    AffectedSystem,
)


class TranslationResult:
    """
    Result of applying a translation rule.

    A rule may produce partial results that are combined
    by the translator service.
    """
    def __init__(
        self,
        applicable: bool,
        metrics: list[ImpactMetric] | None = None,
        affected_routes: list[AffectedRoute] | None = None,
        affected_systems: list[AffectedSystem] | None = None,
        severity_contribution: float = 0.0,
        assumptions: list[str] | None = None,
        explanation: ExplanationStep | None = None,
    ):
        self.applicable = applicable
        self.metrics = metrics or []
        self.affected_routes = affected_routes or []
        self.affected_systems = affected_systems or []
        self.severity_contribution = severity_contribution
        self.assumptions = assumptions or []
        self.explanation = explanation

    @classmethod
    def not_applicable(cls) -> "TranslationResult":
        """Factory for non-applicable results."""
        return cls(applicable=False)


@runtime_checkable
class ImpactTranslationRule(Protocol):
    """
    Protocol for impact translation rules.

    To add a new domain:
    1. Create a new module in omen_impact/rules/{domain}/
    2. Implement classes that satisfy this protocol
    3. Register them with the ImpactTranslator service
    """

    @property
    def name(self) -> str:
        """Unique rule identifier."""
        ...

    @property
    def version(self) -> str:
        """Rule version."""
        ...

    @property
    def domain(self) -> ImpactDomain:
        """Target domain for this rule."""
        ...

    @property
    def applicable_categories(self) -> set[SignalCategory]:
        """Signal categories this rule can process."""
        ...

    def is_applicable(self, signal: ValidatedSignal) -> bool:
        """Check if this rule applies to the given signal."""
        ...

    def translate(
        self,
        signal: ValidatedSignal,
        *,
        processing_time: datetime | None = None,
    ) -> TranslationResult:
        """Perform the translation."""
        ...


class BaseTranslationRule(Rule[ValidatedSignal, TranslationResult]):
    """
    Abstract base class providing common functionality for translation rules.
    """

    @property
    @abstractmethod
    def domain(self) -> ImpactDomain:
        ...

    @property
    @abstractmethod
    def applicable_categories(self) -> set[SignalCategory]:
        ...

    @property
    def applicable_keywords(self) -> set[str]:
        """Keywords that trigger this rule. Override in subclasses."""
        return set()

    @property
    def applicable_chokepoints(self) -> set[str]:
        """Chokepoints that trigger this rule. Override in subclasses."""
        return set()

    def is_applicable(self, signal: ValidatedSignal) -> bool:
        if signal.category not in self.applicable_categories:
            return False

        signal_keywords = set(signal.original_event.keywords)
        if self.applicable_keywords & signal_keywords:
            return True

        signal_chokepoints = set(signal.affected_chokepoints)
        if self.applicable_chokepoints & signal_chokepoints:
            return True

        return self._custom_applicability_check(signal)

    def _custom_applicability_check(self, signal: ValidatedSignal) -> bool:
        """Override for custom applicability logic."""
        return False

    def apply(self, input_data: ValidatedSignal) -> TranslationResult:
        """Apply rule with applicability check."""
        if not self.is_applicable(input_data):
            return TranslationResult.not_applicable()
        return self.translate(input_data)

    @abstractmethod
    def translate(
        self,
        signal: ValidatedSignal,
        *,
        processing_time: datetime | None = None,
    ) -> TranslationResult:
        """Implement the actual translation logic."""
        ...

    def explain(
        self,
        input_data: ValidatedSignal,
        output_data: TranslationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation (required by base class)."""
        if output_data.explanation:
            return output_data.explanation
        ts = processing_time if processing_time is not None else datetime.utcnow()
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={},
            output_summary={},
            reasoning="No explanation available",
            confidence_contribution=0.0,
            timestamp=ts,
        )
