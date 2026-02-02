"""
Geographic Relevance Validation.

Validates that a signal is relevant to logistics chokepoints or regions.
Uses both chokepoint keywords and expanded logistics keyword database.
Logistics keywords use word-boundary matching (see keywords.get_matched_keywords).
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt

from ...models.raw_signal import RawSignalEvent
from ...models.validated_signal import ValidationResult
from ...models.common import ValidationStatus, GeoLocation
from ...models.explanation import ExplanationStep
from ..base import Rule
from .keywords import get_matched_keywords, calculate_relevance_score

# Known logistics chokepoints with coordinates
CHOKEPOINTS: dict[str, GeoLocation] = {
    "Suez Canal": GeoLocation(latitude=30.5, longitude=32.3, name="Suez Canal"),
    "Panama Canal": GeoLocation(latitude=9.1, longitude=-79.7, name="Panama Canal"),
    "Strait of Malacca": GeoLocation(latitude=2.5, longitude=101.5, name="Strait of Malacca"),
    "Strait of Hormuz": GeoLocation(latitude=26.5, longitude=56.3, name="Strait of Hormuz"),
    "Bab el-Mandeb": GeoLocation(latitude=12.5, longitude=43.3, name="Bab el-Mandeb"),
    "Red Sea": GeoLocation(latitude=20.0, longitude=38.0, name="Red Sea"),
    "Cape of Good Hope": GeoLocation(latitude=-34.4, longitude=18.5, name="Cape of Good Hope"),
    "English Channel": GeoLocation(latitude=50.5, longitude=-1.0, name="English Channel"),
    "Taiwan Strait": GeoLocation(latitude=24.0, longitude=119.0, name="Taiwan Strait"),
}

# Keywords that indicate geographic relevance
GEO_KEYWORDS: dict[str, list[str]] = {
    "Suez Canal": ["suez", "egypt", "port said", "red sea"],
    "Panama Canal": ["panama", "central america", "colon"],
    "Strait of Malacca": ["malacca", "singapore", "malaysia", "indonesia"],
    "Strait of Hormuz": ["hormuz", "iran", "oman", "persian gulf", "gulf"],
    "Bab el-Mandeb": ["bab el-mandeb", "yemen", "djibouti", "aden"],
    "Red Sea": ["red sea", "houthi", "yemen", "saudi"],
    "Taiwan Strait": ["taiwan", "china", "taipei"],
}


@dataclass(frozen=True)
class GeographicRelevanceConfig:
    """Configuration for geographic relevance checking. Immutable."""

    proximity_threshold_km: float = 500.0  # Max distance to chokepoint
    require_keyword_match: bool = True
    min_keyword_matches: int = 1


class GeographicRelevanceRule(Rule[RawSignalEvent, ValidationResult]):
    """
    Validates geographic relevance to logistics infrastructure.

    A signal is relevant if:
    1. Its inferred locations are near known chokepoints, OR
    2. Its keywords match chokepoint-related terms
    """

    def __init__(self, config: GeographicRelevanceConfig | None = None):
        self._config = config or GeographicRelevanceConfig()

    @property
    def name(self) -> str:
        return "geographic_relevance"

    @property
    def version(self) -> str:
        return "3.0.0"  # Expanded: use logistics keyword database; pass on 1+ match

    def apply(self, input_data: RawSignalEvent) -> ValidationResult:
        """Check geographic relevance via chokepoints and/or logistics keywords."""
        matched_chokepoints: list[str] = []
        match_reasons: list[str] = []
        event_text = f"{input_data.title} {input_data.description or ''}".lower()
        event_keywords = set(k.lower() for k in input_data.keywords)

        # Chokepoint keyword matches (whole-word in text to avoid "sport" matching "port")
        for chokepoint, keywords in GEO_KEYWORDS.items():
            for kw in keywords:
                in_keywords = kw in event_keywords
                in_text = bool(re.search(r"\b" + re.escape(kw) + r"\b", event_text))
                if in_keywords or in_text:
                    if chokepoint not in matched_chokepoints:
                        matched_chokepoints.append(chokepoint)
                        match_reasons.append(f"keyword '{kw}' → {chokepoint}")
                    break

        # Location proximity
        for loc in input_data.inferred_locations:
            for cp_name, cp_loc in CHOKEPOINTS.items():
                distance = self._haversine_distance(loc, cp_loc)
                if distance <= self._config.proximity_threshold_km:
                    if cp_name not in matched_chokepoints:
                        matched_chokepoints.append(cp_name)
                        match_reasons.append(f"location within {distance:.0f}km of {cp_name}")

        # Expanded: any logistics keyword match counts as relevant
        logistics_matched = get_matched_keywords(event_text)
        if matched_chokepoints:
            score = min(1.0, len(matched_chokepoints) * 0.3 + 0.4)
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=score,
                reason=f"Relevant to {len(matched_chokepoints)} chokepoint(s): {', '.join(matched_chokepoints)}",
            )
        if logistics_matched:
            score = calculate_relevance_score(logistics_matched)
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.PASSED,
                score=score,
                reason=f"Found {len(logistics_matched)} logistics keyword(s): {', '.join(logistics_matched[:5])}{'...' if len(logistics_matched) > 5 else ''}",
            )
        return ValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            status=ValidationStatus.REJECTED_IRRELEVANT_GEOGRAPHY,
            score=0.1,
            reason="No geographic relevance to known logistics chokepoints or keywords",
        )

    def _haversine_distance(self, loc1: GeoLocation, loc2: GeoLocation) -> float:
        """Calculate distance between two points in kilometers."""
        R = 6371  # Earth's radius in km

        lat1, lon1 = radians(loc1.latitude), radians(loc1.longitude)
        lat2, lon2 = radians(loc2.latitude), radians(loc2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation for this validation."""
        ts = processing_time or datetime.now(timezone.utc)
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={
                "keyword_count": len(input_data.keywords),
                "location_count": len(input_data.inferred_locations),
                "title_length": len(input_data.title),
            },
            output_summary={
                "status": output_data.status.value,
                "score": output_data.score,
                "reason": output_data.reason,
            },
            reasoning=output_data.reason,
            confidence_contribution=output_data.score * 0.25,
            timestamp=ts,
        )
