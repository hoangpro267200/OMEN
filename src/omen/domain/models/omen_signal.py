"""
OMEN Signal: Structured Intelligence Output

The canonical output of the OMEN Signal Intelligence Engine.
Contains probability assessment, confidence measurement, and contextual
information.

This signal is:
- Reproducible (deterministic trace)
- Auditable (full evidence chain)
- Context-rich (geographic, temporal)

This signal does NOT contain:
- Impact assessment
- Decision steering
- Recommendations

Downstream consumers are responsible for translating signals into
domain-specific impact and decisions.

NOTE: No logging in domain layer - maintain purity for determinism and testability.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# P1-3: Feature flag for explanation in hot path
EXPLANATIONS_HOT_PATH = os.environ.get("EXPLANATIONS_HOT_PATH", "0") == "1"

if TYPE_CHECKING:
    from .validated_signal import ValidatedSignal

from .enums import SignalType, SignalStatus
from .impact_hints import ImpactHints
from ..services.signal_classifier import SignalClassifier
from ..services.confidence_calculator import (
    EnhancedConfidenceCalculator,
    ConfidenceInterval,
    get_confidence_calculator,
)

# Module-level instances for hot path
_classifier = SignalClassifier()
_confidence_calculator = get_confidence_calculator()


def _generate_deterministic_trace_id(
    event_id: str,
    input_event_hash: Optional[str],
    ruleset_version: str,
) -> str:
    """
    Generate a reproducible trace_id from input components.

    Same inputs always produce the same trace_id, enabling:
    - Reproducibility audits
    - Idempotent reprocessing
    - Deterministic testing

    Args:
        event_id: Source event identifier
        input_event_hash: Hash of raw input data (if available)
        ruleset_version: Version of rules applied

    Returns:
        16-character hex string derived from SHA-256
    """
    hash_input = input_event_hash if input_event_hash else "no_hash"
    components = f"{event_id}|{hash_input}|{ruleset_version}"
    full_hash = hashlib.sha256(components.encode("utf-8")).hexdigest()
    return full_hash[:16]


def _validate_temporal_consistency(title: str, resolution_date: Optional[datetime]) -> bool:
    """
    Check if the year mentioned in the title matches the market resolution_date year.

    This is a data-quality check only and does NOT affect processing.

    Returns:
        True if consistent (or cannot check), False if inconsistent.
    """
    if not resolution_date or not title:
        return True  # Cannot check, assume consistent

    match = re.search(r"\b(20\d{2})\b", title)
    if not match:
        return True  # No year in title, assume consistent

    title_year = int(match.group(1))
    horizon_year = resolution_date.year
    # Domain layer is pure - return result instead of logging
    # Caller can track inconsistency via signal metadata if needed
    return title_year == horizon_year


class ConfidenceLevel(str, Enum):
    """Signal confidence level."""

    HIGH = "HIGH"  # >=0.75 — Strong validation scores
    MEDIUM = "MEDIUM"  # 0.50–0.75 — Moderate validation
    LOW = "LOW"  # <0.50 — Weak validation

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.75:
            return cls.HIGH
        if score >= 0.50:
            return cls.MEDIUM
        return cls.LOW


class SignalCategory(str, Enum):
    """Category of the signal for routing/filtering."""

    GEOPOLITICAL = "GEOPOLITICAL"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    WEATHER = "WEATHER"
    ECONOMIC = "ECONOMIC"
    REGULATORY = "REGULATORY"
    SECURITY = "SECURITY"
    OTHER = "OTHER"


class GeographicContext(BaseModel):
    """Geographic context of the signal."""

    model_config = ConfigDict(frozen=True)

    regions: list[str] = Field(
        default_factory=list,
        description="Regions mentioned or implied (e.g., 'Red Sea', 'Asia', 'Europe')",
    )
    chokepoints: list[str] = Field(
        default_factory=list,
        description="Maritime chokepoints referenced (e.g., 'suez', 'panama', 'hormuz')",
    )
    coordinates: Optional[dict] = Field(
        default=None,
        description="Primary coordinate if determinable: {lat, lng}",
    )


class TemporalContext(BaseModel):
    """Temporal context of the signal."""

    model_config = ConfigDict(frozen=True)

    event_horizon: Optional[str] = Field(
        default=None,
        description="When the event might occur (e.g., '2026-06-30', 'Q2 2026')",
    )
    resolution_date: Optional[datetime] = Field(
        default=None,
        description="When the market resolves (from source)",
    )
    signal_freshness: str = Field(
        default="current",
        description="How fresh this signal is: 'current', 'recent', 'stale'",
    )


class UncertaintyBounds(BaseModel):
    """Uncertainty bounds for a value."""

    model_config = ConfigDict(frozen=True)

    lower: float
    upper: float
    confidence_interval: str = Field(
        default="70%",
        description="Confidence interval these bounds represent",
    )


class EvidenceItem(BaseModel):
    """Single piece of evidence supporting the signal."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(description="Source name (e.g., 'Polymarket', 'Drewry')")
    source_type: str = Field(description="Type: 'market', 'research', 'news', 'internal'")
    value: Optional[str] = Field(default=None, description="The evidence value/quote")
    url: Optional[str] = Field(default=None, description="Link to source")
    observed_at: Optional[datetime] = Field(default=None)


class ValidationScore(BaseModel):
    """Score from a validation rule."""

    model_config = ConfigDict(frozen=True)

    rule_name: str
    rule_version: str
    score: float = Field(ge=0, le=1)
    reasoning: str


class OmenSignal(BaseModel):
    """
    Structured intelligence output (probability, confidence, context).

    This is a signal, not a decision or recommendation.
    Downstream consumers use it for their own impact and decisions.
    """

    model_config = ConfigDict(frozen=True)

    # === IDENTIFICATION ===
    signal_id: str = Field(
        description="Unique signal identifier (e.g., 'OMEN-RS2024-001')",
    )
    source_event_id: str = Field(
        description="Original event ID from source (e.g., Polymarket market ID)",
    )
    input_event_hash: Optional[str] = Field(
        default=None,
        description="Hash of the input RawSignalEvent, for idempotency and repository indexing.",
    )

    # === CLASSIFICATION ===
    signal_type: SignalType = Field(
        default=SignalType.UNCLASSIFIED,
        description="Signal category. Classification, not impact.",
    )

    # === LIFECYCLE ===
    status: SignalStatus = Field(
        default=SignalStatus.ACTIVE,
        description="Lifecycle state. Operational, not decision.",
    )

    # === ROUTING HINTS ===
    impact_hints: ImpactHints = Field(
        default_factory=ImpactHints,
        description="Routing metadata. NOT impact assessment.",
    )

    # === CORE SIGNAL DATA ===
    title: str = Field(
        description="Human-readable title of the event/signal",
    )
    description: Optional[str] = Field(
        default=None,
        description="Extended description if available",
    )

    # === PROBABILITY (from source market) ===
    probability: float = Field(
        ge=0,
        le=1,
        description="Probability from source market (0-1). "
        "This is market-derived, not OMEN-computed.",
    )
    probability_source: str = Field(
        default="polymarket",
        description="Source of probability data",
    )
    probability_is_estimate: bool = Field(
        default=False,
        description="True if probability is estimated/fallback, not from live market",
    )

    # === CONFIDENCE (OMEN-computed) ===
    confidence_score: float = Field(
        ge=0,
        le=1,
        description="OMEN's confidence in signal quality (0-1). "
        "Based on liquidity, source reliability, validation scores.",
    )
    confidence_method: str = Field(
        default="enhanced_calculator_v2",
        description="Method used to calculate confidence_score (enhanced_calculator_v2 uses EnhancedConfidenceCalculator)",
    )
    confidence_level: ConfidenceLevel = Field(
        description="Categorical confidence: HIGH, MEDIUM, LOW",
    )
    confidence_factors: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of confidence by factor: "
        "{liquidity: 0.8, geographic: 0.9, source_reliability: 0.85}",
    )

    # === UNCERTAINTY ===
    probability_uncertainty: Optional[UncertaintyBounds] = Field(
        default=None,
        description="Uncertainty bounds on probability if calculable",
    )
    confidence_interval: Optional[dict] = Field(
        default=None,
        description="Confidence interval from EnhancedConfidenceCalculator: {point_estimate, lower_bound, upper_bound, confidence_level, method}",
    )

    # === CATEGORIZATION ===
    category: SignalCategory = Field(
        description="Primary category of this signal",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Additional tags for filtering (e.g., ['shipping', 'conflict', 'oil'])",
    )
    keywords_matched: list[str] = Field(
        default_factory=list,
        description="Logistics keywords found in this signal",
    )

    # === GEOGRAPHIC CONTEXT ===
    geographic: GeographicContext = Field(
        default_factory=GeographicContext,
        description="Geographic context: regions, chokepoints, coordinates",
    )

    # === TEMPORAL CONTEXT ===
    temporal: TemporalContext = Field(
        default_factory=TemporalContext,
        description="Temporal context: event horizon, resolution date",
    )

    # === EVIDENCE & TRACEABILITY ===
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Evidence items supporting this signal",
    )
    validation_scores: list[ValidationScore] = Field(
        default_factory=list,
        description="Scores from each validation rule",
    )
    
    # === EXPLANATION (P1-3: Feature-flagged via EXPLANATIONS_HOT_PATH=1) ===
    explanation_text: Optional[str] = Field(
        default=None,
        description="Human-readable explanation chain (only populated when EXPLANATIONS_HOT_PATH=1)",
    )
    explanation_summary: Optional[str] = Field(
        default=None,
        description="Brief summary of reasoning steps (only populated when EXPLANATIONS_HOT_PATH=1)",
    )

    # === TRACEABILITY ===
    trace_id: str = Field(
        description="Deterministic trace ID for reproducibility",
    )
    ruleset_version: str = Field(
        default="1.0.0",
        description="Version of validation/processing rules used",
    )

    # === METADATA ===
    source_url: Optional[str] = Field(
        default=None,
        description="URL to the source market/event",
    )
    observed_at: Optional[datetime] = Field(
        default=None,
        description="When source data was observed (from source system)",
    )
    generated_at: Optional[datetime] = Field(
        default=None,
        description="When this signal was generated (set from ProcessingContext)",
    )

    # === VALIDATION HELPERS ===
    @field_validator("confidence_score", mode="after")
    @classmethod
    def _round_confidence(cls, v: float) -> float:
        """Round confidence score to 4 decimal places for stability."""
        return round(v, 4)

    @classmethod
    def from_validated_event(
        cls,
        validated_signal: "ValidatedSignal",
        enrichment: dict,
    ) -> "OmenSignal":
        """
        Create an OmenSignal from a validated event and enrichment context.

        NOTE: This creates a SIGNAL only. No impact calculations.
        Impact assessment is the responsibility of downstream systems.
        """
        from .validated_signal import ValidatedSignal, ValidationResult

        event = validated_signal.original_event
        res_date = event.market.resolution_date

        # Data-quality only: log if title year and resolution year diverge.
        _validate_temporal_consistency(event.title, res_date)

        regions = enrichment.get("matched_regions", [])
        chokepoints = enrichment.get("matched_chokepoints", [])
        if not chokepoints and getattr(validated_signal, "affected_chokepoints", None):
            chokepoints = [
                cp.lower().replace(" ", "-") for cp in validated_signal.affected_chokepoints
            ]
        geographic = GeographicContext(regions=regions, chokepoints=chokepoints)

        temporal = TemporalContext(
            event_horizon=res_date.isoformat() if res_date else None,
            resolution_date=res_date,
        )

        factors = dict(enrichment.get("confidence_factors", {}))
        if not factors:
            factors = {
                "liquidity": getattr(validated_signal, "liquidity_score", 0.5),
                "geographic": 0.5,
                "source_reliability": 0.85,
            }
            for r in getattr(validated_signal, "validation_results", []) or []:
                if r.rule_name == "liquidity_validation":
                    factors["liquidity"] = r.score
                elif r.rule_name == "geographic_relevance":
                    factors["geographic"] = r.score
            factors.setdefault("liquidity", validated_signal.liquidity_score)
            factors.setdefault("geographic", 0.5)
        
        # === P0-2: Use EnhancedConfidenceCalculator instead of inline calculation ===
        # Extract base confidence from validation scores average
        base_confidence = (
            sum(factors.values()) / len(factors) if factors else 0.5
        )
        # Data completeness: based on how many validation rules passed
        data_completeness = min(1.0, len(factors) / 3.0) if factors else 0.5
        # Source reliability from factors or default
        source_reliability = factors.get("source_reliability", 0.85)
        
        # Calculate confidence with interval using the service
        confidence_result = _confidence_calculator.calculate_confidence_with_interval(
            base_confidence=base_confidence,
            data_completeness=data_completeness,
            source_reliability=source_reliability,
        )
        confidence_score = confidence_result.point_estimate
        confidence_interval_data = {
            "point_estimate": confidence_result.point_estimate,
            "lower_bound": confidence_result.lower_bound,
            "upper_bound": confidence_result.upper_bound,
            "confidence_level": confidence_result.confidence_level,
            "method": confidence_result.method,
        }

        keyword_cats = enrichment.get("keyword_categories", {})
        category = cls._infer_category(keyword_cats)
        if category == SignalCategory.OTHER:
            category = cls._map_validated_category(
                getattr(validated_signal, "category", None),
            )

        val_results: list[ValidationResult] = enrichment.get(
            "validation_results",
            getattr(validated_signal, "validation_results", []) or [],
        )
        validation_scores = [
            ValidationScore(
                rule_name=r.rule_name,
                rule_version=r.rule_version,
                score=r.score,
                reasoning=r.reason,
            )
            for r in val_results
        ]

        evidence = [
            EvidenceItem(
                source=event.market.source,
                source_type="market",
                url=event.market.market_url,
                observed_at=event.observed_at,
            )
        ]

        tags = (enrichment.get("matched_keywords") or [])[:10]
        keywords_matched = list(enrichment.get("matched_keywords") or [])
        ruleset = getattr(validated_signal, "ruleset_version", "1.0.0")
        if hasattr(ruleset, "value"):
            ruleset = str(ruleset) if not isinstance(ruleset, str) else ruleset
        ruleset_str = ruleset if isinstance(ruleset, str) else "1.0.0"
        input_event_hash = getattr(event, "input_event_hash", None)

        trace_id = getattr(validated_signal, "deterministic_trace_id", None)
        if not trace_id:
            trace_id = _generate_deterministic_trace_id(
                event_id=str(event.event_id),
                input_event_hash=input_event_hash,
                ruleset_version=ruleset_str,
            )

        # === CLASSIFICATION ===
        signal_type, impact_hints = _classifier.classify(
            title=event.title,
            description=event.description,
        )

        # === STATUS: Determine from confidence ===
        if confidence_score >= 0.7:
            status = SignalStatus.ACTIVE
        elif confidence_score >= 0.5:
            status = SignalStatus.MONITORING
        elif confidence_score >= 0.3:
            status = SignalStatus.CANDIDATE
        else:
            status = SignalStatus.DEGRADED

        # === P1-3: EXPLANATION (feature-flagged) ===
        explanation_text = None
        explanation_summary = None
        if EXPLANATIONS_HOT_PATH:
            explanation_chain = getattr(validated_signal, "explanation", None)
            if explanation_chain and hasattr(explanation_chain, "steps"):
                # Build human-readable explanation text
                explanation_parts = []
                for step in explanation_chain.steps:
                    if hasattr(step, "to_human_readable"):
                        explanation_parts.append(step.to_human_readable())
                    elif hasattr(step, "reasoning"):
                        explanation_parts.append(
                            f"Step {step.step_id}: {step.rule_name} - {step.reasoning}"
                        )
                if explanation_parts:
                    explanation_text = "\n\n".join(explanation_parts)
                # Summary is the chain of rule names
                if hasattr(explanation_chain, "summary"):
                    explanation_summary = explanation_chain.summary

        return cls(
            signal_id=f"OMEN-{trace_id[:12].upper()}",
            source_event_id=str(event.event_id),
            input_event_hash=input_event_hash,
            title=event.title,
            description=event.description,
            probability=event.probability,
            probability_source=event.market.source,
            probability_is_estimate=getattr(event, "probability_is_fallback", False),
            confidence_score=confidence_score,
            confidence_level=ConfidenceLevel.from_score(confidence_score),
            confidence_factors=factors,
            confidence_interval=confidence_interval_data,  # P0-2: Add confidence interval
            category=category,
            tags=tags,
            keywords_matched=keywords_matched,
            geographic=geographic,
            temporal=temporal,
            evidence=evidence,
            validation_scores=validation_scores,
            explanation_text=explanation_text,  # P1-3: Feature-flagged explanation
            explanation_summary=explanation_summary,  # P1-3: Feature-flagged explanation summary
            trace_id=trace_id,
            ruleset_version=ruleset,
            source_url=event.market.market_url,
            observed_at=getattr(event, "observed_at", None),
            generated_at=getattr(validated_signal, "validated_at", None),
            # === NEW FIELDS ===
            signal_type=signal_type,
            status=status,
            impact_hints=impact_hints,
        )

    @staticmethod
    def _infer_category(keyword_categories: dict) -> SignalCategory:
        """Infer primary category from matched keyword categories."""
        relevance_order = [
            ("geopolitical", SignalCategory.GEOPOLITICAL),
            ("security", SignalCategory.SECURITY),
            ("weather", SignalCategory.WEATHER),
            ("infrastructure", SignalCategory.INFRASTRUCTURE),
            ("economic", SignalCategory.ECONOMIC),
            ("regulatory", SignalCategory.REGULATORY),
        ]
        for key, cat in relevance_order:
            if key in keyword_categories and keyword_categories[key]:
                return cat
        return SignalCategory.OTHER

    @staticmethod
    def _map_validated_category(common_category: object) -> SignalCategory:
        """Map common.SignalCategory to SignalCategory."""
        from .common import SignalCategory as CommonCategory

        if common_category is None:
            return SignalCategory.OTHER
        m = {
            CommonCategory.GEOPOLITICAL: SignalCategory.GEOPOLITICAL,
            CommonCategory.INFRASTRUCTURE: SignalCategory.INFRASTRUCTURE,
            CommonCategory.CLIMATE: SignalCategory.WEATHER,
            CommonCategory.ECONOMIC: SignalCategory.ECONOMIC,
            CommonCategory.REGULATORY: SignalCategory.REGULATORY,
            CommonCategory.LABOR: SignalCategory.OTHER,
            CommonCategory.UNKNOWN: SignalCategory.OTHER,
        }
        return m.get(common_category, SignalCategory.OTHER)
