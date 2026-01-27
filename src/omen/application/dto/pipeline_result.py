"""Pipeline result data transfer objects."""

from dataclasses import dataclass, field
from typing import Any

from ...domain.models.omen_signal import OmenSignal
from ...domain.models.validated_signal import ValidationResult


@dataclass
class PipelineStats:
    """Statistics from a pipeline run."""
    events_received: int = 0
    events_deduplicated: int = 0
    events_validated: int = 0
    events_rejected_validation: int = 0
    events_no_impact: int = 0
    events_failed: int = 0
    assessments_generated: int = 0
    signals_generated: int = 0
    processing_time_ms: float = 0.0


@dataclass
class PipelineResult:
    """Result of processing one or more events through the pipeline."""
    success: bool
    signals: list[OmenSignal] = field(default_factory=list)
    validation_failures: list[ValidationResult] = field(default_factory=list)
    stats: PipelineStats = field(default_factory=PipelineStats)
    error: str | None = None
    cached: bool = False
    
    @property
    def signal_count(self) -> int:
        return len(self.signals)
    
    @property
    def has_actionable_signals(self) -> bool:
        return any(s.is_actionable for s in self.signals)
