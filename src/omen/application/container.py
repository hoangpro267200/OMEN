"""
Dependency injection container for OMEN.

Composition root where all components are wired together.

IMPORTANT: For production deployments:
- Set OMEN_ENV=production
- Set DATABASE_URL for PostgreSQL persistence
- Set REDIS_URL for distributed rate limiting (optional)

In production, signals are persisted to PostgreSQL for horizontal scaling.
In development (default), signals use in-memory storage.
"""

import logging
import os
from dataclasses import dataclass
from functools import lru_cache

from omen.adapters.outbound.console_publisher import ConsolePublisher
from omen.adapters.outbound.webhook_publisher import WebhookPublisher
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.application.ports.output_publisher import OutputPublisher
from omen.application.ports.signal_repository import SignalRepository
from omen.config import OmenConfig, get_config
from omen.domain.rules.validation.anomaly_detection_rule import AnomalyDetectionRule
from omen.domain.rules.validation.geographic_relevance_rule import (
    GeographicRelevanceRule,
)
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.validation.semantic_relevance_rule import (
    SemanticRelevanceRule,
)
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.services.signal_validator import SignalValidator
from omen.infrastructure.dead_letter import DeadLetterQueue

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """
    Application container holding all composed components.

    Use create_default() for production-style wiring,
    or create_for_testing() for tests (no external I/O).
    Impact/legacy pipeline: use the omen_impact package (LegacyPipeline, ImpactTranslator).
    """

    config: OmenConfig
    validator: SignalValidator
    enricher: SignalEnricher
    repository: SignalRepository
    publisher: OutputPublisher
    pipeline: OmenPipeline
    dlq: DeadLetterQueue

    @classmethod
    def create_default(cls) -> "Container":
        """
        Create container with default configuration.

        In production (OMEN_ENV=production):
        - Uses PostgreSQL for signal persistence (requires DATABASE_URL)
        - Falls back to in-memory if DATABASE_URL not set (with warning)

        In development (default):
        - Uses in-memory repository
        """
        config = get_config()
        env = os.getenv("OMEN_ENV", "development")

        validator = SignalValidator(
            rules=[
                LiquidityValidationRule(min_liquidity_usd=config.min_liquidity_usd),
                AnomalyDetectionRule(),
                SemanticRelevanceRule(),
                GeographicRelevanceRule(),
            ]
        )
        enricher = SignalEnricher()

        # Repository selection based on environment
        repository: SignalRepository
        if env == "production":
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                try:
                    # Import PostgreSQL repository lazily (may not be installed)
                    from omen.adapters.persistence.postgres_repository import (
                        PostgresSignalRepository,
                    )

                    repository = PostgresSignalRepository(dsn=database_url)
                    logger.info("Using PostgreSQL repository for production")
                except ImportError:
                    logger.warning(
                        "PostgreSQL adapter not available. Install with: pip install asyncpg. "
                        "Falling back to in-memory repository (DATA WILL BE LOST ON RESTART)"
                    )
                    repository = InMemorySignalRepository()
                except Exception as e:
                    logger.error(
                        "Failed to initialize PostgreSQL repository: %s. "
                        "Falling back to in-memory (DATA WILL BE LOST ON RESTART)",
                        e,
                    )
                    repository = InMemorySignalRepository()
            else:
                logger.warning(
                    "PRODUCTION MODE but DATABASE_URL not set! "
                    "Using in-memory repository (DATA WILL BE LOST ON RESTART). "
                    "Set DATABASE_URL for persistent storage."
                )
                repository = InMemorySignalRepository()
        else:
            repository = InMemorySignalRepository()
            logger.debug("Using in-memory repository (development mode)")

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
            enricher=enricher,
            repository=repository,
            publisher=publisher,
            dead_letter_queue=dlq,
            config=pipeline_config,
        )
        return cls(
            config=config,
            validator=validator,
            enricher=enricher,
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
        validator = SignalValidator(rules=[LiquidityValidationRule(min_liquidity_usd=100.0)])
        enricher = SignalEnricher()
        repository = InMemorySignalRepository()
        publisher = ConsolePublisher()
        dlq = DeadLetterQueue()
        pipeline = OmenPipeline(
            validator=validator,
            enricher=enricher,
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
            enricher=enricher,
            repository=repository,
            publisher=publisher,
            pipeline=pipeline,
            dlq=dlq,
        )


# Thread-safe container instance management
# Using a simple module-level variable instead of @lru_cache to allow testing flexibility
_container_instance: Container | None = None
_container_lock = __import__("threading").Lock()


def get_container() -> Container:
    """
    Return the container instance.

    Thread-safe singleton pattern that allows:
    - Testing: call reset_container() between tests
    - Production: efficient reuse of single instance
    """
    global _container_instance
    if _container_instance is None:
        with _container_lock:
            # Double-check locking pattern
            if _container_instance is None:
                _container_instance = Container.create_default()
    return _container_instance


def reset_container() -> None:
    """
    Reset the container instance.

    Use in tests to ensure clean state between test cases.
    NOT for production use.
    """
    global _container_instance
    with _container_lock:
        _container_instance = None


def set_container(container: Container) -> None:
    """
    Set a custom container instance.

    Use in tests to inject mock dependencies.
    NOT for production use.
    """
    global _container_instance
    with _container_lock:
        _container_instance = container
