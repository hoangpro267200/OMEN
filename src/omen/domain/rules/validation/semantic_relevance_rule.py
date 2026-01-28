"""
Semantic Relevance Validation.

Validates that a signal's content is semantically relevant to logistics risk.
Uses word-boundary matching so "port"≠"sport", "strike"≠"striker".
Rejects obvious sports/entertainment content via blocklist.
"""

import re
from datetime import datetime

from ...models.raw_signal import RawSignalEvent
from ...models.validated_signal import ValidationResult
from ...models.common import ValidationStatus
from ...models.explanation import ExplanationStep
from ..base import Rule


# Cụm từ thể thao/giải trí — nếu có trong text thì loại ngay (không phải logistics)
OFF_TOPIC_BLOCKLIST: set[str] = {
    "ligue 1", "serie a", "premier league", "la liga", "bundesliga",
    "vua phá lưới", "top scorer", "relegation", "xuống hạng",
    "championship", "world cup", "euro", "uefa", "fifa",
}

# Semantic categories and their keywords (whole-word match)
RISK_CATEGORIES: dict[str, set[str]] = {
    "conflict": {
        "war", "attack", "military", "missile", "bomb", "strike", "combat",
        "invasion", "conflict", "hostility", "warfare", "armed",
    },
    "sanctions": {
        "sanction", "embargo", "ban", "restriction", "tariff", "trade war",
        "blacklist", "prohibition", "blockade",
    },
    "labor": {
        "strike", "labor", "union", "workers", "protest", "walkout",
        "shutdown", "stoppage", "industrial action",
    },
    "infrastructure": {
        "port", "canal", "bridge", "tunnel", "terminal", "dock", "berth",
        "closure", "damage", "collapse", "blockage",
    },
    "climate": {
        "storm", "hurricane", "typhoon", "flood", "drought", "weather",
        "cyclone", "tsunami", "earthquake",
    },
    "regulatory": {
        "regulation", "law", "policy", "compliance", "inspection",
        "customs", "border", "visa", "permit",
    },
}

# Minimum relevance score to pass
MIN_RELEVANCE_SCORE = 0.3


class SemanticRelevanceRule(Rule[RawSignalEvent, ValidationResult]):
    """
    Validates semantic relevance using keyword matching and category detection.
    """

    @property
    def name(self) -> str:
        return "semantic_relevance"

    @property
    def version(self) -> str:
        return "2.0.0"

    def _word_match(self, keyword: str, text: str) -> bool:
        """True if keyword appears as whole word in text."""
        return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))

    def apply(self, input_data: RawSignalEvent) -> ValidationResult:
        """Check semantic relevance. Reject off-topic (sports) first; then require whole-word risk keywords."""
        text = (
            f"{input_data.title} {input_data.description or ''} "
            f"{' '.join(input_data.keywords)}"
        ).lower()

        # Chặn thể thao / giải trí
        for phrase in OFF_TOPIC_BLOCKLIST:
            if phrase in text:
                return ValidationResult(
                    rule_name=self.name,
                    rule_version=self.version,
                    status=ValidationStatus.REJECTED_IRRELEVANT_SEMANTIC,
                    score=0.0,
                    reason=f"Off-topic (sports/entertainment): '{phrase}'",
                )

        # Find matching categories (whole-word only)
        category_matches: dict[str, list[str]] = {}
        for category, keywords in RISK_CATEGORIES.items():
            matched = [kw for kw in keywords if self._word_match(kw, text)]
            if matched:
                category_matches[category] = matched

        if not category_matches:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_IRRELEVANT_SEMANTIC,
                score=0.1,
                reason="No logistics risk keywords detected",
            )

        # Calculate score based on category diversity and match count
        total_matches = sum(len(m) for m in category_matches.values())
        category_count = len(category_matches)

        score = min(1.0, (category_count * 0.2) + (total_matches * 0.1))

        if score < MIN_RELEVANCE_SCORE:
            return ValidationResult(
                rule_name=self.name,
                rule_version=self.version,
                status=ValidationStatus.REJECTED_IRRELEVANT_SEMANTIC,
                score=score,
                reason=f"Low semantic relevance score: {score:.2f}",
            )

        categories_str = ", ".join(category_matches.keys())
        return ValidationResult(
            rule_name=self.name,
            rule_version=self.version,
            status=ValidationStatus.PASSED,
            score=score,
            reason=f"Relevant to risk categories: {categories_str}",
        )

    def explain(
        self,
        input_data: RawSignalEvent,
        output_data: ValidationResult,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation for this validation."""
        ts = processing_time if processing_time is not None else datetime.utcnow()
        return ExplanationStep(
            step_id=1,
            rule_name=self.name,
            rule_version=self.version,
            input_summary={
                "title_length": len(input_data.title),
                "keyword_count": len(input_data.keywords),
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
