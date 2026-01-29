"""
Signal Intelligence Enums

ARCHITECTURAL NOTE:
These enums are for CLASSIFICATION and LIFECYCLE, not impact assessment.

SignalType: What category of event (not how severe)
SignalStatus: Where in lifecycle (not what to do)
ImpactDirection: Semantic polarity (not impact magnitude)
AffectedDomain: Routing hint (not impact scope)
"""

from enum import Enum


class SignalType(str, Enum):
    """
    Categorical classification of signal.
    This is WHAT TYPE of event, not HOW SEVERE.
    """
    # Geopolitical
    GEOPOLITICAL_CONFLICT = "GEOPOLITICAL_CONFLICT"
    GEOPOLITICAL_SANCTIONS = "GEOPOLITICAL_SANCTIONS"
    GEOPOLITICAL_DIPLOMATIC = "GEOPOLITICAL_DIPLOMATIC"

    # Supply Chain
    SUPPLY_CHAIN_DISRUPTION = "SUPPLY_CHAIN_DISRUPTION"
    SHIPPING_ROUTE_RISK = "SHIPPING_ROUTE_RISK"
    PORT_OPERATIONS = "PORT_OPERATIONS"

    # Energy
    ENERGY_SUPPLY = "ENERGY_SUPPLY"
    ENERGY_INFRASTRUCTURE = "ENERGY_INFRASTRUCTURE"

    # Labor
    LABOR_DISRUPTION = "LABOR_DISRUPTION"

    # Climate
    CLIMATE_EVENT = "CLIMATE_EVENT"
    NATURAL_DISASTER = "NATURAL_DISASTER"

    # Regulatory
    REGULATORY_CHANGE = "REGULATORY_CHANGE"

    # Default
    UNCLASSIFIED = "UNCLASSIFIED"


class SignalStatus(str, Enum):
    """
    Lifecycle state of signal.
    This is WHERE in lifecycle, not WHAT ACTION to take.
    """
    CANDIDATE = "CANDIDATE"        # Newly detected
    ACTIVE = "ACTIVE"              # Validated, relevant
    MONITORING = "MONITORING"      # Confidence declining
    DEGRADED = "DEGRADED"          # Low confidence
    RESOLVED = "RESOLVED"          # Event concluded
    INVALIDATED = "INVALIDATED"    # False positive


class ImpactDirection(str, Enum):
    """
    Semantic polarity from NLP analysis.
    This is SENTIMENT, not SEVERITY.
    """
    NEGATIVE = "negative"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class AffectedDomain(str, Enum):
    """
    Domains for signal routing.
    This is WHERE TO ROUTE, not IMPACT SCOPE.
    """
    LOGISTICS = "logistics"
    SHIPPING = "shipping"
    ENERGY = "energy"
    FINANCE = "finance"
    MANUFACTURING = "manufacturing"
    AGRICULTURE = "agriculture"
    INFRASTRUCTURE = "infrastructure"
