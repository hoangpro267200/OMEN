"""Layer 2: Validated Signal

Signals that have passed all validation rules and deserve attention.
Contains validation metadata for auditability.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field, computed_field

from omen.application.ports.time_provider import utc_now
from .common import (
    EventId,
    SignalCategory,
    ValidationStatus,
    ConfidenceLevel,
    GeoLocation,
    ProbabilityMovement,
    generate_deterministic_hash,
    RulesetVersion,
)
from .raw_signal import RawSignalEvent, MarketMetadata
from .explanation import ExplanationChain


class ValidationResult(BaseModel):
    """Result of a single validation rule."""

    rule_name: str
    rule_version: str
    status: ValidationStatus
    score: float = Field(..., ge=0, le=1)
    reason: str

    model_config = {"frozen": True}


class ValidatedSignal(BaseModel):
    """
    Layer 2 Output: A signal that has passed validation.

    Contains the original event data plus validation metadata,
    classification refinements, and confidence scoring.
    """

    # Original event reference
    event_id: EventId
    original_event: RawSignalEvent

    # Refined classification
    category: SignalCategory
    subcategory: str | None = None

    # Validated geography
    relevant_locations: list[GeoLocation] = Field(default_factory=list)
    affected_chokepoints: list[str] = Field(
        default_factory=list,
        description="Named logistics chokepoints (e.g., 'Suez Canal', 'Strait of Malacca')",
    )

    # Validation metadata
    validation_results: list[ValidationResult] = Field(default_factory=list)
    overall_validation_score: float = Field(..., ge=0, le=1)

    # Confidence assessment
    signal_strength: float = Field(..., ge=0, le=1)
    liquidity_score: float = Field(..., ge=0, le=1)

    # Explanation chain
    explanation: ExplanationChain

    # Versioning for reproducibility
    ruleset_version: RulesetVersion
    validated_at: datetime = Field(
        default_factory=lambda: utc_now(),
        description="When this signal was validated (timezone-aware UTC)",
    )

    @computed_field
    @property
    def validation_passed(self) -> bool:
        """All critical rules must pass."""
        critical_failures = [
            r for r in self.validation_results if r.status != ValidationStatus.PASSED
        ]
        return len(critical_failures) == 0

    @computed_field
    @property
    def deterministic_trace_id(self) -> str:
        """
        Trace ID for this validation run.

        Deterministic: same input + same ruleset → same trace ID.
        """
        return generate_deterministic_hash(
            self.original_event.input_event_hash, self.ruleset_version, "validated"
        )

    model_config = {"frozen": True}
