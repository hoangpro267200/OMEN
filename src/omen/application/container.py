"""
Dependency injection container for OMEN.

Composition root where all components are wired together.
"""

from dataclasses import dataclass
from functools import lru_cache

from omen.adapters.outbound.console_publisher import ConsolePublisher
from omen.adapters.outbound.webhook_publisher import WebhookPublisher
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.application.ports.output_publisher import OutputPublisher
from omen.application.ports.signal_repository import SignalRepository
from omen.config import OmenConfig, get_config
from omen.domain.rules.translation.logistics.red_sea_disruption import (
    RedSeaDisruptionRule,
)
from omen.domain.rules.translation.logistics.port_closure import PortClosureRule
from omen.domain.rules.translation.logistics.strike_impact import StrikeImpactRule
from omen.domain.rules.validation.anomaly_detection_rule import AnomalyDetectionRule
from omen.domain.rules.validation.geographic_relevance_rule import (
    GeographicRelevanceRule,
)
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.validation.semantic_relevance_rule import (
    SemanticRelevanceRule,
)
from omen.domain.services.impact_translator import ImpactTranslator
from omen.domain.services.signal_validator import SignalValidator
from omen.infrastructure.dead_letter import DeadLetterQueue


@dataclass
class Container:
    """
    Application container holding all composed components.

    Use create_default() for production-style wiring,
    or create_for_testing() for tests (no external I/O).
    """

    config: OmenConfig
    validator: SignalValidator
    translator: ImpactTranslator
    repository: SignalRepository
    publisher: OutputPublisher
    pipeline: OmenPipeline
    dlq: DeadLetterQueue

    @classmethod
    def create_default(cls) -> "Container":
        """Create container with default production configuration."""
        config = get_config()
        validator = SignalValidator(
            rules=[
                LiquidityValidationRule(min_liquidity_usd=config.min_liquidity_usd),
                AnomalyDetectionRule(),
                SemanticRelevanceRule(),
                GeographicRelevanceRule(),
            ]
        )
        translator = ImpactTranslator(
            rules=[
                RedSeaDisruptionRule(),
                PortClosureRule(),
                StrikeImpactRule(),
            ]
        )
        repository = InMemorySignalRepository()
        if config.webhook_url:
            publisher = WebhookPublisher(
                url=config.webhook_url,
                secret=config.webhook_secret,
                timeout=config.webhook_timeout_seconds,
                max_retries=config.webhook_retry_attempts,
            )
        else:
            publisher = ConsolePublisher()
        dlq = DeadLetterQueue()
        pipeline_config = PipelineConfig(
            ruleset_version=config.parsed_ruleset_version,
            target_domains=config.parsed_target_domains,
            min_confidence_for_output=config.min_confidence_for_output,
        )
        pipeline = OmenPipeline(
            validator=validator,
            translator=translator,
            repository=repository,
            publisher=publisher,
            dead_letter_queue=dlq,
            config=pipeline_config,
        )
        return cls(
            config=config,
            validator=validator,
            translator=translator,
            repository=repository,
            publisher=publisher,
            pipeline=pipeline,
            dlq=dlq,
        )

    @classmethod
    def create_for_testing(cls) -> "Container":
        """Create container for tests (no external dependencies)."""
        config = OmenConfig(
            ruleset_version="test-v1.0.0",
            min_liquidity_usd=100.0,
        )
        validator = SignalValidator(
            rules=[LiquidityValidationRule(min_liquidity_usd=100.0)]
        )
        translator = ImpactTranslator(rules=[RedSeaDisruptionRule()])
        repository = InMemorySignalRepository()
        publisher = ConsolePublisher()
        dlq = DeadLetterQueue()
        pipeline = OmenPipeline(
            validator=validator,
            translator=translator,
            repository=repository,
            publisher=publisher,
            dead_letter_queue=dlq,
            config=PipelineConfig(
                ruleset_version=config.parsed_ruleset_version,
                target_domains=config.parsed_target_domains,
                enable_dry_run=True,
            ),
        )
        return cls(
            config=config,
            validator=validator,
            translator=translator,
            repository=repository,
            publisher=publisher,
            pipeline=pipeline,
            dlq=dlq,
        )


@lru_cache
def get_container() -> Container:
    """Return the global container instance (cached)."""
    return Container.create_default()
