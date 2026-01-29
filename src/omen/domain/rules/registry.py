"""
Rule Parameter Registry.

Central configuration for all rule parameters.
Enables:
- Consistent parameter management
- Easy auditing of all assumptions
- Runtime configuration changes
- A/B testing of parameters
"""

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class RuleParameter:
    """A single rule parameter with metadata."""

    name: str
    value: Any
    unit: str
    description: str
    source: str | None = None
    source_date: date | None = None
    min_value: float | None = None
    max_value: float | None = None

    def validate(self) -> bool:
        """Check if value is within bounds (numeric only)."""
        if self.min_value is not None or self.max_value is not None:
            try:
                v = float(self.value)
            except (TypeError, ValueError):
                return True
            if self.min_value is not None and v < self.min_value:
                return False
            if self.max_value is not None and v > self.max_value:
                return False
        return True


@dataclass
class RuleConfig:
    """Configuration for a single rule."""

    rule_name: str
    rule_version: str
    parameters: dict[str, RuleParameter]

    def get(self, param_name: str) -> Any:
        """Get parameter value."""
        return self.parameters[param_name].value

    def get_with_source(self, param_name: str) -> tuple[Any, str | None]:
        """Get parameter value and source citation."""
        param = self.parameters[param_name]
        source = None
        if param.source:
            source = param.source
            if param.source_date:
                source += f" ({param.source_date})"
        return param.value, source


class RuleParameterRegistry:
    """
    Global registry of rule parameters used by the OMEN signal pipeline.

    Contains only signal-validation parameters (e.g. liquidity_validation).
    Impact-assessment parameters are not registered; downstream consumers
    (e.g. RiskCast) define their own impact parameters.

    Usage:
        registry = RuleParameterRegistry.default()
        min_liq = registry.get("liquidity_validation", "min_liquidity_usd")
    """

    def __init__(self) -> None:
        self._rules: dict[str, RuleConfig] = {}

    def register(self, config: RuleConfig) -> None:
        """Register a rule's configuration."""
        self._rules[config.rule_name] = config

    def get(self, rule_name: str, param_name: str) -> Any:
        """Get a parameter value."""
        return self._rules[rule_name].get(param_name)

    def get_config(self, rule_name: str) -> RuleConfig:
        """Get full rule configuration."""
        return self._rules[rule_name]

    def all_rules(self) -> list[str]:
        """List all registered rules."""
        return list(self._rules.keys())

    def export_all_parameters(self) -> dict:
        """Export all parameters for documentation."""
        result: dict = {}
        for rule_name, config in self._rules.items():
            result[rule_name] = {
                "version": config.rule_version,
                "parameters": {
                    name: {
                        "value": p.value,
                        "unit": p.unit,
                        "description": p.description,
                        "source": p.source,
                    }
                    for name, p in config.parameters.items()
                },
            }
        return result

    @classmethod
    def default(cls) -> "RuleParameterRegistry":
        """Create registry with all default rule configurations."""
        registry = cls()

        registry.register(
            RuleConfig(
                rule_name="liquidity_validation",
                rule_version="1.0.0",
                parameters={
                    "min_liquidity_usd": RuleParameter(
                        name="min_liquidity_usd",
                        value=1000.0,
                        unit="USD",
                        description="Minimum liquidity for signal validity",
                        min_value=0,
                        max_value=1_000_000,
                    ),
                    "high_liquidity_threshold": RuleParameter(
                        name="high_liquidity_threshold",
                        value=100_000.0,
                        unit="USD",
                        description="Threshold for high-confidence liquidity",
                    ),
                },
            )
        )

        # Impact-assessment parameters (freight, transit, fuel, etc.) are NOT
        # registered here. OMEN is a signal intelligence engine; impact
        # assessment is the responsibility of downstream consumers (e.g. RiskCast).

        return registry


_registry: RuleParameterRegistry | None = None


def get_rule_registry() -> RuleParameterRegistry:
    """Return the global rule parameter registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = RuleParameterRegistry.default()
    return _registry
