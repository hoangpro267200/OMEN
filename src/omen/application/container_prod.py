"""
Production Dependency Injection Container.

Async-compatible container with support for:
- PostgreSQL signal repository
- Redis rate limiting
- Kafka publisher

This is the production-ready container for horizontal scaling.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from omen.adapters.outbound.console_publisher import ConsolePublisher
from omen.adapters.outbound.webhook_publisher import WebhookPublisher
from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.application.pipeline import OmenPipeline, PipelineConfig
from omen.application.ports.output_publisher import OutputPublisher
from omen.application.ports.signal_repository import SignalRepository
from omen.config import OmenConfig, get_config
from omen.domain.rules.validation.anomaly_detection_rule import AnomalyDetectionRule
from omen.domain.rules.validation.geographic_relevance_rule import GeographicRelevanceRule
from omen.domain.rules.validation.liquidity_rule import LiquidityValidationRule
from omen.domain.rules.validation.semantic_relevance_rule import SemanticRelevanceRule
from omen.domain.services.signal_enricher import SignalEnricher
from omen.domain.services.signal_validator import SignalValidator
from omen.infrastructure.dead_letter import DeadLetterQueue

logger = logging.getLogger(__name__)


@dataclass
class ProductionContainer:
    """
    Production-ready container with async initialization.
    
    Supports:
    - PostgreSQL for signal persistence (horizontal scaling)
    - Redis for rate limiting (distributed)
    - Kafka for event streaming (optional)
    
    Environment variables:
    - OMEN_ENV: "development" or "production"
    - DATABASE_URL: PostgreSQL connection string
    - REDIS_URL: Redis connection string
    - KAFKA_BOOTSTRAP_SERVERS: Kafka servers (optional)
    """
    
    config: OmenConfig
    validator: SignalValidator
    enricher: SignalEnricher
    repository: SignalRepository
    publisher: OutputPublisher
    pipeline: OmenPipeline
    dlq: DeadLetterQueue
    rate_limiter: Optional[object] = None
    _initialized: bool = False
    
    @classmethod
    async def create_production(cls) -> "ProductionContainer":
        """
        Create production container with PostgreSQL and Redis.
        
        Requires:
        - DATABASE_URL environment variable
        - REDIS_URL environment variable (optional)
        """
        config = get_config()
        env = os.getenv("OMEN_ENV", "development")
        
        logger.info("Creating production container (env=%s)", env)
        
        # Validator and enricher
        validator = SignalValidator(
            rules=[
                LiquidityValidationRule(min_liquidity_usd=config.min_liquidity_usd),
                AnomalyDetectionRule(),
                SemanticRelevanceRule(),
                GeographicRelevanceRule(),
            ]
        )
        enricher = SignalEnricher()
        
        # Repository - PostgreSQL in production, in-memory for dev
        repository: SignalRepository
        if env == "production":
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                logger.warning("DATABASE_URL not set, falling back to in-memory repository")
                repository = InMemorySignalRepository()
            else:
                try:
                    from omen.adapters.persistence.postgres_repository import (
                        create_postgres_repository,
                    )
                    repository = await create_postgres_repository(
                        dsn=database_url,
                        min_pool_size=int(os.getenv("DB_POOL_MIN", "5")),
                        max_pool_size=int(os.getenv("DB_POOL_MAX", "20")),
                    )
                    logger.info("PostgreSQL repository initialized")
                except ImportError as e:
                    logger.warning("PostgreSQL not available: %s. Using in-memory.", e)
                    repository = InMemorySignalRepository()
                except Exception as e:
                    logger.error("Failed to initialize PostgreSQL: %s. Using in-memory.", e)
                    repository = InMemorySignalRepository()
        else:
            repository = InMemorySignalRepository()
            logger.info("Using in-memory repository (development mode)")
        
        # Rate limiter - Redis in production
        rate_limiter = None
        if env == "production":
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    from omen.infrastructure.security.redis_rate_limit import (
                        create_redis_rate_limiter,
                    )
                    rate_limiter = await create_redis_rate_limiter(
                        redis_url=redis_url,
                        requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "600")),
                        burst_size=int(os.getenv("RATE_LIMIT_BURST", "50")),
                    )
                    logger.info("Redis rate limiter initialized")
                except ImportError as e:
                    logger.warning("Redis not available: %s", e)
                except Exception as e:
                    logger.error("Failed to initialize Redis rate limiter: %s", e)
        
        # Publisher
        if config.webhook_url:
            publisher = WebhookPublisher(
                url=config.webhook_url,
                secret=config.webhook_secret,
                timeout=config.webhook_timeout_seconds,
                max_retries=config.webhook_retry_attempts,
            )
        else:
            publisher = ConsolePublisher()
        
        # Dead letter queue
        # TODO: Use Redis-backed DLQ in production
        dlq = DeadLetterQueue()
        
        # Pipeline
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
        
        container = cls(
            config=config,
            validator=validator,
            enricher=enricher,
            repository=repository,
            publisher=publisher,
            pipeline=pipeline,
            dlq=dlq,
            rate_limiter=rate_limiter,
            _initialized=True,
        )
        
        logger.info("Production container created successfully")
        return container
    
    @classmethod
    def create_development(cls) -> "ProductionContainer":
        """Create container for development (in-memory, no external deps)."""
        config = get_config()
        
        validator = SignalValidator(
            rules=[
                LiquidityValidationRule(min_liquidity_usd=config.min_liquidity_usd),
                AnomalyDetectionRule(),
                SemanticRelevanceRule(),
                GeographicRelevanceRule(),
            ]
        )
        enricher = SignalEnricher()
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
            _initialized=True,
        )
    
    async def shutdown(self) -> None:
        """Cleanup resources on shutdown."""
        logger.info("Shutting down production container...")
        
        # Close PostgreSQL pool
        if hasattr(self.repository, 'close'):
            try:
                await self.repository.close()
                logger.info("PostgreSQL repository closed")
            except Exception as e:
                logger.error("Error closing repository: %s", e)
        
        # Close Redis
        if self.rate_limiter and hasattr(self.rate_limiter, 'close'):
            try:
                await self.rate_limiter.close()
                logger.info("Redis rate limiter closed")
            except Exception as e:
                logger.error("Error closing rate limiter: %s", e)
        
        logger.info("Production container shutdown complete")


# Global container instance
_production_container: Optional[ProductionContainer] = None


async def get_production_container() -> ProductionContainer:
    """
    Get or create the production container.
    
    First call will initialize the container.
    Subsequent calls return the cached instance.
    """
    global _production_container
    
    if _production_container is None:
        env = os.getenv("OMEN_ENV", "development")
        if env == "production":
            _production_container = await ProductionContainer.create_production()
        else:
            _production_container = ProductionContainer.create_development()
    
    return _production_container


async def shutdown_production_container() -> None:
    """Shutdown the production container."""
    global _production_container
    
    if _production_container:
        await _production_container.shutdown()
        _production_container = None
