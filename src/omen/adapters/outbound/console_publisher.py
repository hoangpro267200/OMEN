"""Console output publisher."""

import json
from datetime import datetime, timezone

from ...application.ports.output_publisher import OutputPublisher
from ...domain.models.omen_signal import OmenSignal


class ConsolePublisher(OutputPublisher):
    """Publishes OMEN signals to console/stdout."""

    def publish(self, signal: OmenSignal) -> bool:
        """Publish signal to console (pure contract fields only)."""
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signal": {
                "signal_id": signal.signal_id,
                "source_event_id": signal.source_event_id,
                "title": signal.title,
                "description": signal.description,
                "category": signal.category.value,
                "probability": signal.probability,
                "probability_source": signal.probability_source,
                "confidence_level": signal.confidence_level.value,
                "confidence_score": signal.confidence_score,
                "trace_id": signal.trace_id,
                "ruleset_version": signal.ruleset_version,
                "generated_at": signal.generated_at.isoformat(),
            },
        }
        print(json.dumps(output, indent=2))
        return True

    async def publish_async(self, signal: OmenSignal) -> bool:
        """Async version of publish."""
        return self.publish(signal)
