"""
Signal Classifier

Performs CLASSIFICATION and SEMANTIC ANALYSIS.
NOT impact assessment.

Input: title, description (text)
Output: SignalType, ImpactHints

⚠️ This classifier MUST NOT:
- Calculate severity scores
- Estimate delays or costs
- Quantify risk
- Make recommendations
"""

import re
from typing import Optional
from ..models.enums import SignalType, ImpactDirection, AffectedDomain
from ..models.impact_hints import ImpactHints


# === PATTERN DEFINITIONS ===

SIGNAL_TYPE_PATTERNS: dict[SignalType, list[str]] = {
    SignalType.GEOPOLITICAL_CONFLICT: [
        "attack", "military", "war", "conflict", "missile",
        "drone", "strike", "combat", "houthi", "invasion"
    ],
    SignalType.GEOPOLITICAL_SANCTIONS: [
        "sanction", "embargo", "tariff", "ban", "restriction"
    ],
    SignalType.SHIPPING_ROUTE_RISK: [
        "shipping", "route", "vessel", "maritime", "sea",
        "port", "canal", "strait", "red sea", "suez", "chokepoint"
    ],
    SignalType.PORT_OPERATIONS: [
        "port", "terminal", "dock", "congestion", "berth"
    ],
    SignalType.ENERGY_SUPPLY: [
        "oil", "gas", "energy", "fuel", "petroleum", "pipeline"
    ],
    SignalType.LABOR_DISRUPTION: [
        "strike", "labor", "union", "walkout", "worker"
    ],
    SignalType.CLIMATE_EVENT: [
        "hurricane", "typhoon", "flood", "drought", "storm", "weather"
    ],
    SignalType.SUPPLY_CHAIN_DISRUPTION: [
        "supply chain", "disruption", "shortage", "bottleneck"
    ],
    SignalType.REGULATORY_CHANGE: [
        "regulation", "policy", "law", "compliance", "legislation"
    ],
}

NEGATIVE_KEYWORDS = [
    # Existing negative operational terms
    "disrupt", "attack", "block", "close", "delay", "halt",
    "suspend", "cancel", "crisis", "threat", "risk", "shortage",
    # Conflict / military terms are ALWAYS negative in OMEN's semantics
    "conflict", "clash", "military", "war", "invasion", "strike",
    "missile", "bomb", "combat", "battle", "tension", "escalation",
    "hostility", "aggression",
]

# NOTE: "resolution" is intentionally excluded – it often appears in
# market metadata (resolution_date) and is semantically ambiguous.
POSITIVE_KEYWORDS = [
    "reopen", "resume", "recover", "improve", "stabilize",
    "agreement", "peace", "ceasefire", "de-escalation",
    "treaty", "deal", "cooperation",
]

DOMAIN_MAPPING: dict[SignalType, list[AffectedDomain]] = {
    SignalType.GEOPOLITICAL_CONFLICT: [
        AffectedDomain.LOGISTICS, AffectedDomain.SHIPPING, AffectedDomain.ENERGY
    ],
    SignalType.SHIPPING_ROUTE_RISK: [
        AffectedDomain.LOGISTICS, AffectedDomain.SHIPPING, AffectedDomain.ENERGY
    ],
    SignalType.PORT_OPERATIONS: [
        AffectedDomain.LOGISTICS, AffectedDomain.SHIPPING
    ],
    SignalType.ENERGY_SUPPLY: [
        AffectedDomain.ENERGY, AffectedDomain.LOGISTICS
    ],
    SignalType.LABOR_DISRUPTION: [
        AffectedDomain.LOGISTICS, AffectedDomain.MANUFACTURING
    ],
    SignalType.CLIMATE_EVENT: [
        AffectedDomain.LOGISTICS, AffectedDomain.AGRICULTURE, AffectedDomain.INFRASTRUCTURE
    ],
    SignalType.SUPPLY_CHAIN_DISRUPTION: [
        AffectedDomain.LOGISTICS, AffectedDomain.MANUFACTURING
    ],
}

ASSET_PATTERNS: dict[str, list[str]] = {
    "shipping_routes": ["route", "lane", "passage", "strait", "canal"],
    "ports": ["port", "terminal", "harbor", "dock"],
    "vessels": ["ship", "vessel", "tanker", "container"],
    "oil_transport": ["oil", "petroleum", "tanker", "crude"],
}

# Terms that typically come from metadata / field names rather than content.
METADATA_PATTERNS = [
    "resolution",   # e.g. resolution_date
    "horizon",      # event_horizon
    "generated",    # generated_at
    "observed",     # observed_at
]

# Domain / conflict terms we want to capture explicitly from content.
DOMAIN_KEYWORDS = [
    "military", "conflict", "clash", "war", "border",
    "shipping", "route", "port", "vessel",
    "oil", "gas", "energy", "pipeline",
    "strike", "labor", "union",
    "flood", "hurricane", "earthquake",
]


class SignalClassifier:
    """
    Classifies signals by type and generates routing hints.

    ⚠️ NOT an impact assessor. Does NOT calculate:
    - Severity
    - Delay
    - Cost
    - Risk score
    """

    def classify(
        self,
        title: str,
        description: Optional[str] = None,
    ) -> tuple[SignalType, ImpactHints]:
        """
        Classify signal and generate routing hints.

        IMPORTANT: Only analyse CONTENT fields (title + description).
        Do NOT include:
        - temporal fields (event_horizon, resolution_date)
        - metadata (trace_id, source_event_id, generated_at, observed_at)
        - numeric fields (probability, confidence, liquidity)

        Returns:
            (SignalType, ImpactHints) — classification and routing metadata
        """
        # Combine ONLY content fields
        text = f"{title} {description or ''}".lower()

        signal_type = self._classify_type(text)
        direction = self._detect_direction(text, signal_type)
        domains = self._get_domains(signal_type)
        asset_types = self._extract_assets(text)
        keywords = self._extract_keywords(text)

        hints = ImpactHints(
            domains=domains,
            direction=direction,
            affected_asset_types=asset_types,
            keywords=keywords,
        )

        return signal_type, hints

    def _classify_type(self, text: str) -> SignalType:
        """Match against type patterns. Highest score wins."""
        scores = {}
        for sig_type, patterns in SIGNAL_TYPE_PATTERNS.items():
            score = sum(1 for p in patterns if p in text)
            if score > 0:
                scores[sig_type] = score

        if not scores:
            return SignalType.UNCLASSIFIED
        return max(scores, key=scores.get)

    def _detect_direction(self, text: str, signal_type: SignalType) -> ImpactDirection:
        """
        Detect semantic polarity with override rules based on signal_type.

        RULE: Some signal types are always negative by definition:
        - GEOPOLITICAL_CONFLICT
        - NATURAL_DISASTER
        - LABOR_DISRUPTION
        - SUPPLY_CHAIN_DISRUPTION
        """
        always_negative_types = {
            SignalType.GEOPOLITICAL_CONFLICT,
            SignalType.NATURAL_DISASTER,
            SignalType.LABOR_DISRUPTION,
            SignalType.SUPPLY_CHAIN_DISRUPTION,
        }
        if signal_type in always_negative_types:
            return ImpactDirection.NEGATIVE

        # Fallback: keyword-based detection for other types
        neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
        pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)

        if neg > pos:
            return ImpactDirection.NEGATIVE
        elif pos > neg:
            return ImpactDirection.POSITIVE
        elif neg > 0 or pos > 0:
            return ImpactDirection.NEUTRAL
        return ImpactDirection.UNKNOWN

    def _get_domains(self, signal_type: SignalType) -> list[AffectedDomain]:
        """Get routing domains for signal type."""
        return DOMAIN_MAPPING.get(signal_type, [])

    def _extract_assets(self, text: str) -> list[str]:
        """Extract mentioned asset types."""
        assets = []
        for asset, patterns in ASSET_PATTERNS.items():
            if any(p in text for p in patterns):
                assets.append(asset)
        return assets

    def _extract_keywords(self, text: str) -> list[str]:
        """
        Extract impact-relevant keywords from CONTENT.

        Excludes metadata-like terms that often come from field names.
        """
        found: list[str] = []

        # From positive / negative keyword lists, but skip metadata-like tokens.
        for kw in NEGATIVE_KEYWORDS + POSITIVE_KEYWORDS:
            if kw in text and kw not in METADATA_PATTERNS:
                found.append(kw)

        # Add domain-specific terms from content if present.
        for kw in DOMAIN_KEYWORDS:
            if kw in text and kw not in found:
                found.append(kw)

        return list(set(found))
