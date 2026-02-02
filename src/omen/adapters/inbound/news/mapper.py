"""
News to RawSignalEvent Mapper.

Converts quality-gated news articles to RawSignalEvent format.
Maintains determinism through stable hashing and sorted fields.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.common import ProbabilityMovement

from .config import NewsConfig
from .schemas import NewsArticle, NewsQualityScore, NewsEvent


class NewsMapper:
    """
    Maps news articles to RawSignalEvent.

    Key principles:
    - Deterministic: Same input = same output
    - Stable hashing: Sorted fields, consistent formatting
    - No external state dependencies
    """

    def __init__(self, config: NewsConfig | None = None):
        self._config = config or NewsConfig()

    def map_article(
        self,
        article: NewsArticle,
        quality: NewsQualityScore,
        asof_ts: datetime | None = None,
    ) -> RawSignalEvent | None:
        """
        Map a quality-gated article to RawSignalEvent.

        Args:
            article: The news article
            quality: Quality assessment from gate
            asof_ts: Reference timestamp for observed_at

        Returns:
            RawSignalEvent or None if not mappable
        """
        if not quality.passed_gate:
            return None

        if not quality.matched_topics:
            return None

        # Use asof_ts for determinism, fallback to article fetched_at
        observed_at = asof_ts or article.fetched_at
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)

        # Generate deterministic event_id
        event_id = self._generate_event_id(article, quality)

        # Build title from matched topics
        primary_topic = quality.matched_topics[0] if quality.matched_topics else "news"
        title = self._build_title(article, primary_topic, quality)

        # Build description
        description = self._build_description(article, quality)

        # Calculate probability from quality scores
        # Higher quality + negative sentiment = higher probability of disruption
        probability = self._calculate_probability(quality)

        # Build keywords from matched keywords + tags
        keywords = self._build_keywords(quality)

        # Build market metadata
        market = MarketMetadata(
            source="news",
            market_id=article.url_hash,
            market_url=article.url,
            total_volume_usd=0.0,  # N/A for news
            current_liquidity_usd=0.0,  # N/A for news
            created_at=article.published_at,
        )

        # Build source_metrics
        news_event = NewsEvent(
            article_url=article.url,
            article_title=article.title,
            source_domain=article.source_domain,
            published_at=article.published_at,
            credibility_score=quality.credibility_score,
            recency_score=quality.recency_score,
            combined_score=quality.combined_score,
            matched_topics=quality.matched_topics,
            matched_keywords=quality.matched_keywords,
            sentiment_score=quality.sentiment_score,
            tags=quality.tags,
            dedupe_hash=article.dedupe_hash,
        )

        # Movement based on sentiment
        movement = ProbabilityMovement(
            current=probability,
            previous=0.5,  # Baseline
            delta=probability - 0.5,
            window_hours=24,
        )

        return RawSignalEvent(
            event_id=event_id,
            title=title,
            description=description,
            probability=probability,
            movement=movement,
            keywords=keywords,
            market=market,
            observed_at=observed_at,
            source_metrics=news_event.to_source_metrics(),
        )

    def _generate_event_id(
        self,
        article: NewsArticle,
        quality: NewsQualityScore,
    ) -> str:
        """Generate deterministic event ID."""
        # Use dedupe_hash + primary topic for uniqueness
        primary_topic = quality.matched_topics[0] if quality.matched_topics else "news"
        date_str = article.published_at.strftime("%Y%m%d")

        hash_input = f"{article.dedupe_hash}|{primary_topic}|{date_str}"
        short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

        return f"news-{primary_topic.replace('_', '-')}-{date_str}-{short_hash}"

    def _build_title(
        self,
        article: NewsArticle,
        primary_topic: str,
        quality: NewsQualityScore,
    ) -> str:
        """Build signal title from article."""
        # Format topic name
        topic_display = primary_topic.replace("_", " ").title()

        # Sentiment indicator
        if quality.sentiment_score < -0.3:
            sentiment_prefix = "Alert"
        elif quality.sentiment_score < 0:
            sentiment_prefix = "Warning"
        else:
            sentiment_prefix = "Update"

        # Build title
        title = f"News {sentiment_prefix} [{topic_display}]: {article.title[:100]}"

        if len(title) > 200:
            title = title[:197] + "..."

        return title

    def _build_description(
        self,
        article: NewsArticle,
        quality: NewsQualityScore,
    ) -> str:
        """Build signal description."""
        parts = []

        # Source info
        parts.append(f"Source: {article.source_name} ({article.source_domain})")
        parts.append(f"Published: {article.published_at.strftime('%Y-%m-%d %H:%M UTC')}")

        # Quality info
        parts.append(f"Credibility: {quality.credibility_score:.0%}")

        # Tags
        if quality.tags:
            parts.append(f"Tags: {', '.join(quality.tags)}")

        # Article description
        if article.description:
            parts.append("")
            parts.append(article.description[:500])

        return " | ".join(parts[:4]) + ("\n\n" + parts[4] if len(parts) > 4 else "")

    def _calculate_probability(self, quality: NewsQualityScore) -> float:
        """
        Calculate probability of disruption from quality scores.

        Logic:
        - Base: 0.5 (neutral)
        - Negative sentiment shifts toward higher probability
        - High credibility amplifies the shift
        - Tags like 'conflict', 'blockage' increase probability
        """
        base = 0.5

        # Sentiment contribution (-0.2 to +0.2)
        sentiment_shift = -quality.sentiment_score * 0.2

        # Tag contribution (up to +0.15)
        high_risk_tags = {"conflict", "blockage", "strike", "sanctions"}
        tag_bonus = 0.05 * len(set(quality.tags) & high_risk_tags)

        # Credibility amplifier (0.8 to 1.2)
        credibility_multiplier = 0.8 + quality.credibility_score * 0.4

        # Calculate final probability
        probability = base + (sentiment_shift + tag_bonus) * credibility_multiplier

        # Clamp to valid range
        return max(0.1, min(0.95, probability))

    def _build_keywords(self, quality: NewsQualityScore) -> list[str]:
        """Build keyword list from quality assessment."""
        keywords = set()

        # Add matched keywords
        keywords.update(kw.lower() for kw in quality.matched_keywords)

        # Add tags
        keywords.update(quality.tags)

        # Add topic names
        keywords.update(t.lower().replace("_", " ") for t in quality.matched_topics)

        # Add source type
        keywords.add("news")

        return sorted(keywords)  # Sorted for determinism
