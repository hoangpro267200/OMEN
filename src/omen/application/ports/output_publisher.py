"""Output Publisher Port.

Defines interface for emitting OMEN signals to downstream systems.
"""

from abc import ABC, abstractmethod

from ...domain.models.omen_signal import OmenSignal


class OutputPublisher(ABC):
    """
    Abstract interface for publishing OMEN outputs.
    
    Downstream systems (like RiskCast) consume these outputs.
    OMEN doesn't know who consumes its outputs — clean separation.
    """
    
    @abstractmethod
    def publish(self, signal: OmenSignal) -> bool:
        """
        Publish a signal to downstream consumers.
        
        Returns:
            True if published successfully
        """
        ...
    
    @abstractmethod
    async def publish_async(self, signal: OmenSignal) -> bool:
        """Async version of publish."""
        ...
