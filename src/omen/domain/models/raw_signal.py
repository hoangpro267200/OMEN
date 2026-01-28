"""Layer 1: Raw Signal Event

The entry point to OMEN. Represents unprocessed market data 
normalized into a common internal format.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator, computed_field

from .common import (
    EventId, 
    MarketId, 
    GeoLocation, 
    ProbabilityMovement,
    generate_deterministic_hash
)


class MarketMetadata(BaseModel):
    """
    Metadata about the source prediction market.

    OMEN is market-agnostic; this captures source-specific details.
    """
    source: str = Field(..., description="Market source identifier (e.g., 'polymarket')")
    market_id: MarketId
    market_url: str | None = None
    created_at: datetime | None = None
    resolution_date: datetime | None = None
    total_volume_usd: float = Field(..., ge=0)
    current_liquidity_usd: float = Field(..., ge=0)
    num_traders: int | None = Field(None, ge=0)
    condition_token_id: str | None = Field(
        default=None,
        description="Polymarket condition token ID for CLOB/WebSocket price tracking. "
        "Required for real-time price updates.",
    )
    clob_token_ids: list[str] | None = Field(
        default=None,
        description="CLOB token IDs (YES and NO tokens) for orderbook access.",
    )

    model_config = {"frozen": True}


class RawSignalEvent(BaseModel):
    """
    Layer 1 Output: Normalized prediction market event.
    
    This is the common internal format that all market adapters
    must produce, regardless of source API structure.
    
    Immutable once created.
    """
    # Identity
    event_id: EventId = Field(..., description="Unique event identifier")
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    
    # Probability data
    probability: float = Field(..., ge=0, le=1, description="Current YES probability")
    probability_is_fallback: bool = Field(
        default=False,
        description="True if probability is a fallback value (e.g. 0.5) when market data was missing",
    )
    movement: ProbabilityMovement | None = None
    
    # Classification hints (may be refined in Layer 2)
    keywords: list[str] = Field(default_factory=list)
    inferred_locations: list[GeoLocation] = Field(default_factory=list)
    
    # Market metadata
    market: MarketMetadata
    
    # Timestamps
    observed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When OMEN observed this data"
    )
    market_last_updated: datetime | None = None
    
    # Raw payload for debugging (not used in processing)
    raw_payload: dict[str, Any] | None = Field(
        None, 
        exclude=True,
        description="Original API response, excluded from serialization"
    )
    
    @field_validator("keywords", mode="before")
    @classmethod
    def normalize_keywords(cls, v: list[str] | None) -> list[str]:
        """Lowercase and deduplicate keywords."""
        if not v:
            return []
        return list(set(k.lower().strip() for k in v if k.strip()))
    
    @computed_field
    @property
    def input_event_hash(self) -> str:
        """
        Deterministic hash covering ALL fields that define event identity.

        IMPORTANT: If any of these fields change, the hash changes.
        This is the canonical "event fingerprint" for deduplication.

        Included fields:
        - event_id (primary identity)
        - title (event description)
        - description (detailed context)
        - probability (current market state)
        - movement (probability delta — serialized)
        - keywords (semantic tags — sorted for determinism)
        - market.source (data source)
        - market.market_id (source-specific ID)
        - market.total_volume_usd (market size)
        - market.current_liquidity_usd (market depth)

        NOT included (intentionally):
        - observed_at (observation time, not event identity)
        - raw_payload (debug data)
        - inferred_locations (derived, not source data)
        """
        movement_str = ""
        if self.movement:
            movement_str = (
                f"{self.movement.current}|{self.movement.previous}"
                f"|{self.movement.delta}|{self.movement.window_hours}"
            )
        keywords_str = ",".join(sorted(self.keywords))
        hash_input = "|".join([
            str(self.event_id),
            self.title,
            self.description or "",
            f"{self.probability:.10f}",
            movement_str,
            keywords_str,
            self.market.source,
            str(self.market.market_id),
            f"{self.market.total_volume_usd:.2f}",
            f"{self.market.current_liquidity_usd:.2f}",
        ])
        return generate_deterministic_hash(hash_input)
    
    @property
    def has_sufficient_liquidity(self) -> bool:
        """Quick check for minimum liquidity threshold."""
        return self.market.current_liquidity_usd >= 1000  # $1000 minimum
    
    model_config = {"frozen": True}
