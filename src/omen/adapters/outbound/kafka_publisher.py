"""
Kafka Publisher - Real Implementation.

Enables event streaming and horizontal scaling.
Publishes OMEN signals to Kafka for downstream consumers.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from omen.application.ports.output_publisher import OutputPublisher
from omen.domain.models.omen_signal import OmenSignal

logger = logging.getLogger(__name__)


class KafkaPublisher(OutputPublisher):
    """
    Production Kafka publisher.

    Publishes signals to Kafka for:
    - Event streaming to downstream systems
    - Decoupled architecture
    - Horizontal scaling
    - Replay capability

    Requires:
    - aiokafka library: pip install aiokafka
    - Kafka cluster
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str = "omen.signals",
        client_id: str = "omen-producer",
        acks: str = "all",
        compression_type: str = "gzip",
        max_batch_size: int = 16384,
        linger_ms: int = 10,
    ):
        """
        Initialize Kafka publisher.

        Args:
            bootstrap_servers: Comma-separated Kafka broker addresses
            topic: Topic to publish signals to
            client_id: Kafka client ID
            acks: Acknowledgment mode ("all", "1", "0")
            compression_type: Compression type ("gzip", "snappy", "lz4", "none")
            max_batch_size: Maximum batch size in bytes
            linger_ms: How long to wait for batch to fill
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.client_id = client_id
        self.acks = acks
        self.compression_type = compression_type
        self.max_batch_size = max_batch_size
        self.linger_ms = linger_ms
        self._producer = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Kafka producer."""
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError:
            raise ImportError(
                "aiokafka is required for Kafka publishing. " "Install with: pip install aiokafka"
            )

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            acks=self.acks,
            compression_type=self.compression_type,
            max_batch_size=self.max_batch_size,
            linger_ms=self.linger_ms,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

        await self._producer.start()
        self._initialized = True
        logger.info(
            "Kafka producer initialized: servers=%s, topic=%s",
            self.bootstrap_servers,
            self.topic,
        )

    def _ensure_initialized(self) -> None:
        """Ensure producer is initialized."""
        if not self._initialized:
            raise RuntimeError("Kafka producer not initialized. Call await initialize() first.")

    async def publish(self, signal: OmenSignal) -> bool:
        """
        Publish signal to Kafka.

        Message format:
        {
            "signal_id": "...",
            "payload": {...},
            "timestamp": "...",
            "schema_version": "2.0.0"
        }

        Returns:
            True if published successfully, False otherwise
        """
        self._ensure_initialized()

        try:
            message = {
                "signal_id": signal.signal_id,
                "source_event_id": signal.source_event_id,
                "signal_type": signal.signal_type.value if signal.signal_type else None,
                "category": signal.category.value if signal.category else None,
                "probability": signal.probability,
                "confidence_score": signal.confidence_score,
                "payload": signal.model_dump(mode="json"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "schema_version": "2.0.0",
            }

            # Send message with signal_id as key for partitioning
            await self._producer.send_and_wait(
                self.topic,
                value=message,
                key=signal.signal_id,
            )

            logger.debug("Published signal to Kafka: %s", signal.signal_id)
            return True

        except Exception as e:
            logger.error("Failed to publish signal %s to Kafka: %s", signal.signal_id, e)
            return False

    async def publish_batch(self, signals: list[OmenSignal]) -> int:
        """
        Publish multiple signals to Kafka.

        Uses batching for efficiency.

        Returns:
            Number of signals successfully published
        """
        self._ensure_initialized()

        success_count = 0
        batch = self._producer.create_batch()

        for signal in signals:
            try:
                message = {
                    "signal_id": signal.signal_id,
                    "source_event_id": signal.source_event_id,
                    "payload": signal.model_dump(mode="json"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "schema_version": "2.0.0",
                }

                # Try to add to batch
                metadata = batch.append(
                    key=signal.signal_id.encode("utf-8"),
                    value=json.dumps(message, default=str).encode("utf-8"),
                    timestamp=None,
                )

                if metadata is None:
                    # Batch is full, send it and create new one
                    await self._producer.send_batch(batch, self.topic)
                    batch = self._producer.create_batch()
                    # Retry adding to new batch
                    batch.append(
                        key=signal.signal_id.encode("utf-8"),
                        value=json.dumps(message, default=str).encode("utf-8"),
                        timestamp=None,
                    )

                success_count += 1

            except Exception as e:
                logger.error("Failed to batch signal %s: %s", signal.signal_id, e)

        # Send remaining batch
        if batch.record_count() > 0:
            try:
                await self._producer.send_batch(batch, self.topic)
            except Exception as e:
                logger.error("Failed to send batch: %s", e)
                success_count -= batch.record_count()

        logger.info("Published %d/%d signals to Kafka", success_count, len(signals))
        return success_count

    async def flush(self) -> None:
        """Flush pending messages."""
        if self._producer:
            await self._producer.flush()

    async def close(self) -> None:
        """Close Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer closed")


class KafkaPublisherConfig:
    """Configuration helper for Kafka publisher."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
    ):
        import os

        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.topic = topic or os.getenv("KAFKA_TOPIC", "omen.signals")
        self.client_id = os.getenv("KAFKA_CLIENT_ID", "omen-producer")
        self.acks = os.getenv("KAFKA_ACKS", "all")
        self.compression = os.getenv("KAFKA_COMPRESSION", "gzip")

    def create_publisher(self) -> KafkaPublisher:
        """Create Kafka publisher from config."""
        return KafkaPublisher(
            bootstrap_servers=self.bootstrap_servers,
            topic=self.topic,
            client_id=self.client_id,
            acks=self.acks,
            compression_type=self.compression,
        )


# Factory function
async def create_kafka_publisher(
    bootstrap_servers: str,
    topic: str = "omen.signals",
) -> KafkaPublisher:
    """Create and initialize a Kafka publisher."""
    publisher = KafkaPublisher(
        bootstrap_servers=bootstrap_servers,
        topic=topic,
    )
    await publisher.initialize()
    return publisher
