"""Console output publisher."""

import json
from datetime import datetime

from ...application.ports.output_publisher import OutputPublisher
from ...domain.models.omen_signal import OmenSignal


class ConsolePublisher(OutputPublisher):
    """Publishes OMEN signals to console/stdout."""

    def publish(self, signal: OmenSignal) -> bool:
        """Publish signal to console."""
        output = {
            "timestamp": datetime.utcnow().isoformat(),
            "signal": {
                "signal_id": signal.signal_id,
                "event_id": signal.event_id,
                "category": signal.category.value,
                "domain": signal.domain.value,
                "severity": signal.severity,
                "severity_label": signal.severity_label,
                "confidence_level": signal.confidence_level.value,
                "confidence_score": signal.confidence_score,
                "probability": signal.current_probability,
                "momentum": signal.probability_momentum,
                "title": signal.title,
                "summary": signal.summary,
                "is_actionable": signal.is_actionable,
                "urgency": signal.urgency,
            },
        }
        print(json.dumps(output, indent=2))
        return True

    async def publish_async(self, signal: OmenSignal) -> bool:
        """Async version of publish."""
        return self.publish(signal)
