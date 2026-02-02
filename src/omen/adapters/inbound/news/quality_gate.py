"""
News Quality Gate.

Determines whether a news article meets quality thresholds.
All calculations are deterministic given the same input and asof_ts.

Key principles:
- Fail-closed: Low quality news is filtered out, not escalated
- Deterministic: Same input + asof_ts = same output
- Config-driven: Thresholds from YAML, not hardcoded
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Set

from .config import NewsConfig
from .schemas import NewsArticle, NewsQualityScore

# Rule-based sentiment keywords (no LLM)
NEGATIVE_SENTIMENT_WORDS = frozenset(
    [
        "attack",
        "attacks",
        "attacked",
        "disruption",
        "disrupted",
        "disrupting",
        "strike",
        "strikes",
        "striking",
        "blockade",
        "blocked",
        "blocking",
        "crisis",
        "crises",
        "threat",
        "threatens",
        "threatening",
        "conflict",
        "war",
        "warfare",
        "sanctions",
        "sanctioned",
        "embargo",
        "embargoed",
        "shortage",
        "shortages",
        "delay",
        "delays",
        "delayed",
        "closure",
        "closed",
        "closing",
        "suspend",
        "suspended",
        "suspension",
        "halt",
        "halted",
        "halting",
        "damage",
        "damaged",
        "risk",
        "risks",
        "risky",
    ]
)

POSITIVE_SENTIMENT_WORDS = frozenset(
    [
        "resume",
        "resumed",
        "resuming",
        "recover",
        "recovered",
        "recovery",
        "reopen",
        "reopened",
        "reopening",
        "resolved",
        "resolution",
        "agreement",
        "agreed",
        "stable",
        "stabilize",
        "stabilized",
        "improve",
        "improved",
        "improvement",
        "ease",
        "eased",
        "easing",
        "normal",
        "normalize",
        "normalized",
    ]
)

# Tags to extract from content
TAG_PATTERNS = {
    "strike": re.compile(r"\b(strike|strikes|striking|walkout)\b", re.I),
    "lockdown": re.compile(r"\b(lockdown|locked down|shutdown|shut down)\b", re.I),
    "blockage": re.compile(r"\b(blockage|blocked|blocking|obstruction)\b", re.I),
    "sanctions": re.compile(r"\b(sanctions?|sanctioned|embargo)\b", re.I),
    "cyber": re.compile(r"\b(cyber|ransomware|hack|hacking|malware)\b", re.I),
    "weather": re.compile(r"\b(storm|hurricane|typhoon|cyclone|flood|drought)\b", re.I),
    "conflict": re.compile(r"\b(attack|missile|drone|military|conflict|war)\b", re.I),
}


class NewsQualityGate:
    """
    Quality gate for news articles.

    Evaluates:
    1. Source credibility (from config)
    2. Recency (exponential decay)
    3. Topic relevance (keyword matching)
    4. Deduplication

    All calculations use asof_ts for deterministic replay.
    """

    def __init__(self, config: NewsConfig | None = None):
        self._config = config or NewsConfig()
        self._credibility_map = self._config.get_credibility_map()
        self._topic_keywords = self._config.get_topic_keywords()
        self._seen_hashes: Set[str] = set()  # For dedupe within session

    def evaluate(
        self,
        article: NewsArticle,
        asof_ts: datetime | None = None,
    ) -> NewsQualityScore:
        """
        Evaluate article quality.

        Args:
            article: The news article to evaluate
            asof_ts: Reference time for recency calculation.
                     If None, uses fetched_at (live mode).
                     For replay, pass explicit asof_ts.

        Returns:
            NewsQualityScore with all assessments
        """
        # Use asof_ts for determinism (NOT datetime.utcnow())
        reference_time = asof_ts or article.fetched_at
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        # 1. Credibility score
        credibility = self._calculate_credibility(article)

        # 2. Recency score (exponential decay)
        recency = self._calculate_recency(article, reference_time)

        # 3. Topic relevance
        matched_topics, matched_keywords, relevance = self._calculate_relevance(article)

        # 4. Sentiment (rule-based)
        sentiment = self._calculate_sentiment(article)

        # 5. Extract tags
        tags = self._extract_tags(article)

        # 6. Combined score (weighted)
        combined = (
            credibility * self._config.credibility_weight + recency * self._config.recency_weight
        )

        # 7. Deduplication check
        is_duplicate = article.dedupe_hash in self._seen_hashes
        duplicate_of = None  # Could track original URL if needed

        if not is_duplicate:
            self._seen_hashes.add(article.dedupe_hash)

        # 8. Quality gate decision (fail-closed)
        passed_gate = True
        rejection_reason = None

        if credibility < self._config.min_credibility:
            passed_gate = False
            rejection_reason = (
                f"Credibility too low: {credibility:.2f} < {self._config.min_credibility}"
            )
        elif recency < self._config.min_recency:
            passed_gate = False
            rejection_reason = (
                f"Article too old: recency={recency:.2f} < {self._config.min_recency}"
            )
        elif combined < self._config.min_combined_score:
            passed_gate = False
            rejection_reason = (
                f"Combined score too low: {combined:.2f} < {self._config.min_combined_score}"
            )
        elif is_duplicate:
            passed_gate = False
            rejection_reason = "Duplicate article"
        elif relevance < 0.1:
            passed_gate = False
            rejection_reason = "No relevant topics matched"

        return NewsQualityScore(
            credibility_score=credibility,
            recency_score=recency,
            relevance_score=relevance,
            combined_score=combined,
            passed_gate=passed_gate,
            rejection_reason=rejection_reason,
            matched_topics=matched_topics,
            matched_keywords=matched_keywords,
            sentiment_score=sentiment,
            tags=tags,
            is_duplicate=is_duplicate,
            duplicate_of=duplicate_of,
        )

    def _calculate_credibility(self, article: NewsArticle) -> float:
        """Calculate source credibility score."""
        domain = article.source_domain.lower()

        # Direct lookup
        if domain in self._credibility_map:
            return self._credibility_map[domain]

        # Try without www.
        if domain.startswith("www."):
            domain_no_www = domain[4:]
            if domain_no_www in self._credibility_map:
                return self._credibility_map[domain_no_www]

        # Default credibility for unknown sources
        return self._config.get_default_credibility()

    def _calculate_recency(
        self,
        article: NewsArticle,
        reference_time: datetime,
    ) -> float:
        """
        Calculate recency score with exponential decay.

        Score = exp(-ln(2) * age_hours / half_life_hours)

        - Fresh articles (< fresh_threshold): 1.0
        - At half_life: 0.5
        - Beyond max_age: 0.0
        """
        published = article.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)

        age = reference_time - published
        age_hours = age.total_seconds() / 3600

        # Beyond max age = 0
        if age_hours > self._config.max_age_hours:
            return 0.0

        # Fresh = 1.0
        if age_hours <= self._config.fresh_threshold_hours:
            return 1.0

        # Exponential decay
        # score = exp(-ln(2) * age / half_life)
        decay_constant = math.log(2) / self._config.half_life_hours
        score = math.exp(-decay_constant * age_hours)

        return round(score, 4)

    def _calculate_relevance(
        self,
        article: NewsArticle,
    ) -> tuple[list[str], list[str], float]:
        """
        Calculate topic relevance from keyword matching.

        Returns:
            (matched_topics, matched_keywords, relevance_score)
        """
        text = f"{article.title} {article.description or ''} {article.content or ''}".lower()

        matched_topics: list[str] = []
        all_matched_keywords: list[str] = []

        for topic, keywords_dict in self._topic_keywords.items():
            primary = keywords_dict.get("primary", [])
            secondary = keywords_dict.get("secondary", [])

            # Check primary keywords (higher weight)
            for kw in primary:
                if kw.lower() in text:
                    if topic not in matched_topics:
                        matched_topics.append(topic)
                    all_matched_keywords.append(kw)

            # Check secondary keywords
            for kw in secondary:
                if kw.lower() in text:
                    if topic not in matched_topics:
                        matched_topics.append(topic)
                    all_matched_keywords.append(kw)

        # Calculate relevance score
        # 0 topics = 0.0, 1 topic = 0.5, 2+ topics = 0.8+
        if not matched_topics:
            relevance = 0.0
        elif len(matched_topics) == 1:
            relevance = 0.5 + min(len(all_matched_keywords) * 0.1, 0.3)
        else:
            relevance = 0.8 + min(len(matched_topics) * 0.05, 0.2)

        return (
            sorted(matched_topics),  # Sorted for determinism
            sorted(set(all_matched_keywords)),
            min(relevance, 1.0),
        )

    def _calculate_sentiment(self, article: NewsArticle) -> float:
        """
        Calculate sentiment score using rule-based approach.

        Returns: -1.0 (very negative) to 1.0 (very positive)
        """
        text = f"{article.title} {article.description or ''}".lower()
        words = set(re.findall(r"\b\w+\b", text))

        negative_count = len(words & NEGATIVE_SENTIMENT_WORDS)
        positive_count = len(words & POSITIVE_SENTIMENT_WORDS)

        total = negative_count + positive_count
        if total == 0:
            return 0.0

        # Scale to -1 to 1
        sentiment = (positive_count - negative_count) / total
        return round(sentiment, 2)

    def _extract_tags(self, article: NewsArticle) -> list[str]:
        """Extract tags from article content."""
        text = f"{article.title} {article.description or ''} {article.content or ''}"
        tags: list[str] = []

        for tag_name, pattern in TAG_PATTERNS.items():
            if pattern.search(text):
                tags.append(tag_name)

        return sorted(tags)  # Sorted for determinism

    def reset_dedupe_cache(self) -> None:
        """Clear deduplication cache (for new session or replay)."""
        self._seen_hashes.clear()
