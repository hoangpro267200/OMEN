"""Kafka output publisher (future implementation)."""

from omen.application.ports.output_publisher import OutputPublisher
from omen.domain.models.omen_signal import OmenSignal


class KafkaPublisher(OutputPublisher):
    """Publishes OMEN signals to Kafka (stub for future implementation)."""

    def __init__(self, brokers: str | None = None, topic: str | None = None):
        """
        Initialize Kafka publisher.

        Args:
            brokers: Kafka broker addresses
            topic: Kafka topic name
        """
        self.brokers = brokers
        self.topic = topic
        # Future: Initialize Kafka producer here

    async def publish(self, signal: OmenSignal) -> None:
        """Publish signal to Kafka."""
        # Future: Implement Kafka publishing
        # For now, this is a stub
        raise NotImplementedError("Kafka publisher not yet implemented")
