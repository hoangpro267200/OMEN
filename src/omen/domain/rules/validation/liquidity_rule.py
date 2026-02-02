"""Liquidity Validation Rule.

OMEN assumes: If there is no liquidity, there is no information.
"""

from datetime import datetime, timezone

from ...models.explanation import ExplanationStep, ParameterReference
from ...models.raw_signal import RawSignalEvent
from ...models.validated_signal import ValidationResult
from ...models.common import ValidationStatus
from ..base import Rule
from ..registry import get_rule_registry


class LiquidityValidationRule(Rule[RawSignalEvent, ValidationResult]):
    """
    Validates that a signal has sufficient market liquidity.
    
    Markets with low liquidity are susceptible to manipulation
    and do not represent genuine collective belief.
    """
    
    def __init__(self, min_liquidity_usd: float = 1000.0):
        """
        Args:
            min_liquidity_usd: Minimum liquidity threshold in USD
        """
        self._min_liquidity = min_liquidity_usd
    
    @property
    def name(self) -> str:
        return "liquidity_validation"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def apply(self, input_data: RawSignalEvent) -> ValidationResult:
        """Check if the event has sufficient liquidity."""
        liquidity = input_data.market.current_liquidity_usd
        
        if liquidity >= self._min_liquidity:
            # Calculate score: higher liquidity = higher score (with diminishing returns)
            score = min(1.0, liquidity / (self._min_liquidity * 10))
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=score,
                reason=f"Sufficient liquidity: ${liquidity:,.0f} >= ${self._min_liquidity:,.0f} threshold"
            )
        else:
            score = liquidity / self._min_liquidity  # Partial score
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_LOW_LIQUIDITY,
                score=score,
                reason=f"Insufficient liquidity: ${liquidity:,.0f} below ${self._min_liquidity:,.0f} threshold"
            )
    
    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation for this validation."""
        ts = processing_time or datetime.now(timezone.utc)
        parameters_used: list[ParameterReference] = []
        try:
            cfg = get_rule_registry().get_config("liquidity_validation")
            params_dict = cfg._get_params_dict()
            p = params_dict.get("min_liquidity_usd")
            if p:
                _, src = cfg.get_with_source("min_liquidity_usd")
                parameters_used = [
                    ParameterReference(name=p.name, value=p.value, unit=p.unit, source=src)
                ]
            else:
                raise KeyError("min_liquidity_usd not found")
        except (KeyError, AttributeError):
            parameters_used = [
                ParameterReference(
                    name="min_liquidity_usd",
                    value=self._min_liquidity,
                    unit="USD",
                    source=None,
                )
            ]
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={
                "current_liquidity_usd": input_data.market.current_liquidity_usd,
                "total_volume_usd": input_data.market.total_volume_usd,
                "threshold_usd": self._min_liquidity,
            },
            output_summary={
                "status": output_data.status.value,
                "score": output_data.score,
            },
            parameters_used=parameters_used,
            reasoning=output_data.reason,
            confidence_contribution=output_data.score * 0.3,
            timestamp=ts,
        )
