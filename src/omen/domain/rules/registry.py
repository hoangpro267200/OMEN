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
    Global registry of all rule parameters.

    Usage:
        registry = RuleParameterRegistry.default()
        transit_days = registry.get("red_sea_disruption_logistics", "reroute_transit_increase_days")
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

        registry.register(
            RuleConfig(
                rule_name="red_sea_disruption_logistics",
                rule_version="2.0.0",
                parameters={
                    "reroute_transit_increase_days": RuleParameter(
                        name="reroute_transit_increase_days",
                        value=10,
                        unit="days",
                        description="Transit time increase via Cape of Good Hope",
                        source="Drewry Maritime Research Q1 2024",
                        source_date=date(2024, 2, 1),
                        min_value=5,
                        max_value=20,
                    ),
                    "fuel_consumption_increase_pct": RuleParameter(
                        name="fuel_consumption_increase_pct",
                        value=30,
                        unit="percent",
                        description="Fuel consumption increase on longer route",
                        source="Lloyd's List Intelligence, Jan 2024",
                        source_date=date(2024, 1, 20),
                    ),
                    "freight_rate_increase_pct_base": RuleParameter(
                        name="freight_rate_increase_pct_base",
                        value=15,
                        unit="percent",
                        description="Minimum freight rate increase",
                        source="Freightos Baltic Index",
                        source_date=date(2024, 1, 25),
                    ),
                    "freight_rate_increase_pct_crisis": RuleParameter(
                        name="freight_rate_increase_pct_crisis",
                        value=100,
                        unit="percent",
                        description="Peak freight rate increase during crisis",
                        source="Freightos Baltic Index Dec 2023-Jan 2024",
                        source_date=date(2024, 1, 30),
                    ),
                },
            )
        )

        return registry


_registry: RuleParameterRegistry | None = None


def get_rule_registry() -> RuleParameterRegistry:
    """Return the global rule parameter registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = RuleParameterRegistry.default()
    return _registry
