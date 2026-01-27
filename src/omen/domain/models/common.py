"""Common value objects and enumerations used across the OMEN domain.

These are the atomic building blocks that ensure type safety and 
semantic clarity throughout the system.
"""

from enum import Enum
from typing import NewType
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib


class ConfidenceLevel(str, Enum):
    """
    Explicit confidence classification for OMEN outputs.
    
    OMEN never claims absolute accuracy. Confidence is always explicit.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    
    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Deterministic mapping from numeric score to level."""
        if score >= 0.7:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        return cls.LOW


class SignalCategory(str, Enum):
    """Primary classification of signal type."""
    GEOPOLITICAL = "GEOPOLITICAL"
    CLIMATE = "CLIMATE"
    LABOR = "LABOR"
    REGULATORY = "REGULATORY"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    ECONOMIC = "ECONOMIC"
    UNKNOWN = "UNKNOWN"


class ImpactDomain(str, Enum):
    """Target domain for impact translation."""
    LOGISTICS = "LOGISTICS"
    ENERGY = "ENERGY"
    INSURANCE = "INSURANCE"
    FINANCE = "FINANCE"


class ValidationStatus(str, Enum):
    """Result of signal validation."""
    PASSED = "PASSED"
    REJECTED_LOW_LIQUIDITY = "REJECTED_LOW_LIQUIDITY"
    REJECTED_IRRELEVANT_GEOGRAPHY = "REJECTED_IRRELEVANT_GEOGRAPHY"
    REJECTED_IRRELEVANT_SEMANTIC = "REJECTED_IRRELEVANT_SEMANTIC"
    REJECTED_INSUFFICIENT_MOVEMENT = "REJECTED_INSUFFICIENT_MOVEMENT"
    REJECTED_MANIPULATION_SUSPECTED = "REJECTED_MANIPULATION_SUSPECTED"
    REJECTED_RULE_ERROR = "REJECTED_RULE_ERROR"


# Type aliases for semantic clarity
EventId = NewType("EventId", str)
MarketId = NewType("MarketId", str)
TraceId = NewType("TraceId", str)
RulesetVersion = NewType("RulesetVersion", str)


class GeoLocation(BaseModel):
    """
    Geographic reference point.
    
    Used for proximity calculations to logistics chokepoints.
    """
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    name: str | None = None
    region_code: str | None = Field(None, description="ISO 3166-1 alpha-2")
    
    model_config = {"frozen": True}


class ProbabilityMovement(BaseModel):
    """
    Captures probability change over a time window.
    
    Essential for detecting abnormal market movements.
    """
    current: float = Field(..., ge=0, le=1)
    previous: float = Field(..., ge=0, le=1)
    delta: float = Field(..., ge=-1, le=1)
    window_hours: int = Field(..., gt=0)
    
    @property
    def is_significant(self) -> bool:
        """Movement > 10% in either direction is significant."""
        return abs(self.delta) > 0.1
    
    @property
    def direction(self) -> str:
        if self.delta > 0.01:
            return "INCREASING"
        elif self.delta < -0.01:
            return "DECREASING"
        return "STABLE"
    
    model_config = {"frozen": True}


def generate_deterministic_hash(*args: str) -> str:
    """
    Generate a deterministic SHA-256 hash from input strings.
    
    Used for reproducibility: same inputs → same hash.
    """
    combined = "|".join(str(a) for a in args)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
