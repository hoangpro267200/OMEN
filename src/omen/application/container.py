"""
Dependency injection container for OMEN.

Composition root where all components are wired together.

IMPORTANT: For production deployments:
- Set OMEN_ENV=production
- Set DATABASE_URL for PostgreSQL persistence
- Set REDIS_URL for distributed rate limiting (optional)
- Set KAFKA_BOOTSTRAP_SERVERS for event streaming (optional)

In production, signals are persisted to PostgreSQL for horizontal scaling.
In development (default), signals use in-memory storage.

✅ ACTIVATED: All domain services and validation rules are now enabled.
✅ ACTIVATED: Kafka publisher support for event streaming (when KAFKA_BOOTSTRAP_SERVERS is set).
"""

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, List

from omen.adapters.outbound.console_publisher import ConsolePublisher
from omen.adapters.outbound.webhook_publisher import WebhookPublisher
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.application.ports.output_publisher import OutputPublisher
from omen.application.ports.signal_repository import SignalRepository
from omen.config import OmenConfig, get_config
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.services.signal_validator import SignalValidator
from omen.domain.services.signal_classifier import SignalClassifier
from omen.domain.services.confidence_calculator import (
    EnhancedConfidenceCalculator,
    get_confidence_calculator,
)
from omen.infrastructure.dead_letter import DeadLetterQueue

logger = logging.getLogger(__name__)


class CompositePublisher(OutputPublisher):
    """
    Publisher that sends signals to multiple destinations.
    
    Enables simultaneous publishing to:
    - Kafka (for event streaming)
    - Webhook (for real-time notifications)
    - Console (for debugging)
    """
    
    def __init__(self, publishers: List[OutputPublisher]):
        self._publishers = publishers
    
    def publish(self, signal) -> None:
        """Publish to all configured publishers."""
        for publisher in self._publishers:
            try:
                publisher.publish(signal)
            except Exception as e:
                logger.error(f"Publisher {type(publisher).__name__} failed: {e}")
    
    async def publish_async(self, signal) -> None:
        """Async publish to all configured publishers."""
        for publisher in self._publishers:
            try:
                if hasattr(publisher, 'publish_async'):
                    await publisher.publish_async(signal)
                else:
                    publisher.publish(signal)
            except Exception as e:
                logger.error(f"Publisher {type(publisher).__name__} failed: {e}")


@dataclass
class Container:
    """
    Application container holding all composed components.

    Use create_default() for production-style wiring,
    or create_for_testing() for tests (no external I/O).
    Impact assessment is handled by downstream consumers (e.g., RiskCast service).
    
    ✅ ACTIVATED: Now includes SignalClassifier and EnhancedConfidenceCalculator.
    """

    config: OmenConfig
    validator: SignalValidator
    enricher: SignalEnricher
    repository: SignalRepository
    publisher: OutputPublisher
    pipeline: OmenPipeline
    dlq: DeadLetterQueue
    # ✅ NEW: Activated domain services
    classifier: Optional[SignalClassifier] = None
    confidence_calculator: Optional[EnhancedConfidenceCalculator] = None

    @classmethod
    def create_default(cls) -> "Container":
        """
        Create container with default configuration.

        In production (OMEN_ENV=production):
        - Uses PostgreSQL for signal persistence (requires DATABASE_URL)
        - Falls back to in-memory if DATABASE_URL not set (with warning)

        In development (default):
        - Uses in-memory repository
        
        ✅ ACTIVATED: Now uses FULL validator with ALL 12 validation rules.
        ✅ ACTIVATED: SignalClassifier for automatic signal classification.
        ✅ ACTIVATED: EnhancedConfidenceCalculator with confidence intervals.
        """
        config = get_config()
        env = os.getenv("OMEN_ENV", "development")

        # ✅ Use FULL validator with ALL 12 validation rules activated
        validator = SignalValidator.create_full()
        enricher = SignalEnricher()
        
        # ✅ Initialize domain services
        classifier = SignalClassifier()
        confidence_calculator = get_confidence_calculator()
        
        logger.info("✅ Container initialized with FULL validation (12 rules)")
        logger.info("✅ SignalClassifier ACTIVATED")
        logger.info("✅ EnhancedConfidenceCalculator ACTIVATED")

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

        # Publisher selection: Kafka > Webhook > Console
        # Can combine multiple publishers using CompositePublisher
        publishers: List[OutputPublisher] = []
        
        # Check for Kafka (event streaming)
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if kafka_servers:
            try:
                from omen.adapters.outbound.kafka_publisher import KafkaPublisher
                kafka_topic = os.getenv("KAFKA_TOPIC", "omen.signals")
                kafka_publisher = KafkaPublisher(
                    bootstrap_servers=kafka_servers,
                    topic=kafka_topic,
                )
                publishers.append(kafka_publisher)
                logger.info("✅ KafkaPublisher ACTIVATED (servers=%s, topic=%s)", kafka_servers, kafka_topic)
            except ImportError:
                logger.warning(
                    "KAFKA_BOOTSTRAP_SERVERS set but aiokafka not installed. "
                    "Install with: pip install aiokafka"
                )
            except Exception as e:
                logger.error("Failed to initialize Kafka publisher: %s", e)
        
        # Check for Webhook
        if config.webhook_url:
            webhook_publisher = WebhookPublisher(
                url=config.webhook_url,
                secret=config.webhook_secret,
                timeout=config.webhook_timeout_seconds,
                max_retries=config.webhook_retry_attempts,
            )
            publishers.append(webhook_publisher)
            logger.info("✅ WebhookPublisher ACTIVATED (url=%s)", config.webhook_url)
        
        # Always add Console in development
        if env != "production" or not publishers:
            publishers.append(ConsolePublisher())
            if env != "production":
                logger.debug("ConsolePublisher added (development mode)")
        
        # Use composite if multiple publishers, otherwise single
        if len(publishers) > 1:
            publisher = CompositePublisher(publishers)
            logger.info("✅ CompositePublisher with %d destinations", len(publishers))
        else:
            publisher = publishers[0]
        
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
            enable_correlation=True,  # ✅ Ensure cross-source correlation is enabled
        )
        return cls(
            config=config,
            validator=validator,
            enricher=enricher,
            repository=repository,
            publisher=publisher,
            pipeline=pipeline,
            dlq=dlq,
            # ✅ NEW: Activated domain services
            classifier=classifier,
            confidence_calculator=confidence_calculator,
        )

    @classmethod
    def create_for_testing(cls) -> "Container":
        """Create container for tests (no external dependencies)."""
        config = OmenConfig(
            ruleset_version="test-v1.0.0",
            min_liquidity_usd=100.0,
        )
        validator = SignalValidator.create_minimal()
        enricher = SignalEnricher()
        repository = InMemorySignalRepository()
        publisher = ConsolePublisher()
        dlq = DeadLetterQueue()
        classifier = SignalClassifier()
        confidence_calculator = get_confidence_calculator()
        
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
            enable_correlation=False,  # Disable correlation for tests
        )
        return cls(
            config=config,
            validator=validator,
            enricher=enricher,
            repository=repository,
            publisher=publisher,
            pipeline=pipeline,
            dlq=dlq,
            classifier=classifier,
            confidence_calculator=confidence_calculator,
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
