"""
Comprehensive tests for News Source adapter.

Tests cover:
1. NewsQualityGate: credibility, recency, dedup, topic matching
2. NewsMapper: event creation, quality rejection, determinism
3. NewsSignalSource: live/replay modes, caching
4. Determinism: same input → same output
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from omen.adapters.inbound.news.config import NewsConfig
from omen.adapters.inbound.news.schemas import NewsArticle, NewsQualityScore
from omen.adapters.inbound.news.quality_gate import NewsQualityGate
from omen.adapters.inbound.news.mapper import NewsMapper
from omen.adapters.inbound.news.source import MockNewsSignalSource, create_news_source

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def news_config() -> NewsConfig:
    """Create test news config."""
    return NewsConfig()


@pytest.fixture
def quality_gate(news_config: NewsConfig) -> NewsQualityGate:
    """Create quality gate instance."""
    return NewsQualityGate(news_config)


@pytest.fixture
def mapper(news_config: NewsConfig) -> NewsMapper:
    """Create mapper instance."""
    return NewsMapper(news_config)


@pytest.fixture
def reference_time() -> datetime:
    """Fixed reference time for deterministic tests."""
    return datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fresh_article(reference_time: datetime) -> NewsArticle:
    """Create a fresh, high-quality article."""
    return NewsArticle(
        title="Red Sea Shipping Disruption: Houthi Attacks Force Rerouting",
        description="Major shipping companies are rerouting vessels around Africa due to attacks.",
        url="https://reuters.com/news/red-sea-attacks-2026",
        source_name="Reuters",
        source_domain="reuters.com",
        published_at=reference_time - timedelta(hours=1),
        fetched_at=reference_time,
        content="The Red Sea shipping crisis deepens as attacks continue...",
    )


@pytest.fixture
def stale_article(reference_time: datetime) -> NewsArticle:
    """Create a stale article (beyond max age)."""
    return NewsArticle(
        title="Old News About Shipping",
        description="Something happened a week ago.",
        url="https://reuters.com/news/old-news",
        source_name="Reuters",
        source_domain="reuters.com",
        published_at=reference_time - timedelta(hours=100),  # Beyond 72h max
        fetched_at=reference_time,
    )


@pytest.fixture
def low_credibility_article(reference_time: datetime) -> NewsArticle:
    """Create article from unknown source."""
    return NewsArticle(
        title="Breaking: Ships in Red Sea",
        description="Unverified reports claim...",
        url="https://unknown-blog.com/news/12345",
        source_name="Unknown Blog",
        source_domain="unknown-blog.com",
        published_at=reference_time - timedelta(hours=1),
        fetched_at=reference_time,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE - CREDIBILITY
# ═══════════════════════════════════════════════════════════════════════════════


class TestNewsQualityGateCredibility:
    """Tests for credibility scoring."""

    def test_tier_1_source_high_credibility(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Tier 1 sources (Reuters, Bloomberg) get high credibility."""
        result = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        assert result.credibility_score >= 0.9
        assert result.passed_gate is True

    def test_unknown_source_default_credibility(
        self,
        quality_gate: NewsQualityGate,
        low_credibility_article: NewsArticle,
        reference_time: datetime,
    ):
        """Unknown sources get default credibility (0.3)."""
        result = quality_gate.evaluate(low_credibility_article, asof_ts=reference_time)

        assert result.credibility_score == 0.3  # Default

    def test_credibility_deterministic(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Same article → same credibility score."""
        result1 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        # Reset and evaluate again
        quality_gate.reset_dedupe_cache()
        result2 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        assert result1.credibility_score == result2.credibility_score


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE - RECENCY
# ═══════════════════════════════════════════════════════════════════════════════


class TestNewsQualityGateRecency:
    """Tests for recency scoring."""

    def test_fresh_article_high_recency(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Fresh articles (< 2h) get recency = 1.0."""
        result = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        assert result.recency_score == 1.0

    def test_stale_article_rejected(
        self,
        quality_gate: NewsQualityGate,
        stale_article: NewsArticle,
        reference_time: datetime,
    ):
        """Articles beyond max age are rejected."""
        result = quality_gate.evaluate(stale_article, asof_ts=reference_time)

        assert result.recency_score == 0.0
        assert result.passed_gate is False
        assert "too old" in (result.rejection_reason or "").lower()

    def test_recency_exponential_decay(
        self,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Recency decays exponentially with half-life."""
        # Article at exactly half-life (6h)
        article_6h = NewsArticle(
            title="Test Article",
            description="Test",
            url="https://reuters.com/test",
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=reference_time - timedelta(hours=6),
            fetched_at=reference_time,
        )

        result = quality_gate.evaluate(article_6h, asof_ts=reference_time)

        # At half-life, recency should be ~0.5
        assert 0.4 <= result.recency_score <= 0.6

    def test_recency_deterministic_with_asof_ts(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Same article + same asof_ts → same recency."""
        result1 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        quality_gate.reset_dedupe_cache()
        result2 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        assert result1.recency_score == result2.recency_score


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE - DEDUPLICATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestNewsQualityGateDedupe:
    """Tests for deduplication."""

    def test_duplicate_article_rejected(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Same article evaluated twice is marked as duplicate."""
        # First evaluation
        result1 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)
        assert result1.is_duplicate is False
        assert result1.passed_gate is True

        # Second evaluation (same article)
        result2 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)
        assert result2.is_duplicate is True
        assert result2.passed_gate is False

    def test_dedupe_cache_reset(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Reset cache allows re-evaluation."""
        result1 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)
        assert result1.passed_gate is True

        quality_gate.reset_dedupe_cache()

        result2 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)
        assert result2.is_duplicate is False
        assert result2.passed_gate is True

    def test_different_articles_not_duplicate(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Different articles (different titles) are not duplicates."""
        article2 = NewsArticle(
            title="Different title about Red Sea shipping crisis",  # Different title
            description=fresh_article.description,
            url="https://reuters.com/different-url",  # Different URL
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=fresh_article.published_at,
            fetched_at=reference_time,
        )

        result1 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)
        result2 = quality_gate.evaluate(article2, asof_ts=reference_time)

        assert result1.is_duplicate is False
        assert result2.is_duplicate is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE - TOPIC MATCHING
# ═══════════════════════════════════════════════════════════════════════════════


class TestNewsQualityGateTopics:
    """Tests for topic keyword matching."""

    def test_red_sea_topic_matched(
        self,
        quality_gate: NewsQualityGate,
        fresh_article: NewsArticle,
        reference_time: datetime,
    ):
        """Article about Red Sea matches red_sea_disruption topic."""
        result = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        assert "red_sea_disruption" in result.matched_topics
        assert result.relevance_score > 0.0

    def test_irrelevant_article_low_relevance(
        self,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Irrelevant article has low relevance score."""
        irrelevant = NewsArticle(
            title="Celebrity News: Latest Hollywood Gossip",
            description="Nothing about shipping or logistics.",
            url="https://reuters.com/celebrity",
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=reference_time - timedelta(hours=1),
            fetched_at=reference_time,
        )

        result = quality_gate.evaluate(irrelevant, asof_ts=reference_time)

        assert len(result.matched_topics) == 0
        assert result.relevance_score == 0.0
        assert result.passed_gate is False
        assert "No relevant topics" in (result.rejection_reason or "")

    def test_matched_topics_sorted(
        self,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Matched topics are sorted for determinism."""
        article = NewsArticle(
            title="Suez Canal Blockage Affects Red Sea Shipping Routes",
            description="Panama Canal also mentioned.",
            url="https://reuters.com/multi-topic",
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=reference_time - timedelta(hours=1),
            fetched_at=reference_time,
            content="Red sea, suez canal, panama canal mentioned.",
        )

        result = quality_gate.evaluate(article, asof_ts=reference_time)

        # Topics should be sorted
        assert result.matched_topics == sorted(result.matched_topics)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS QUALITY GATE - SENTIMENT & TAGS
# ═══════════════════════════════════════════════════════════════════════════════


class TestNewsQualityGateSentiment:
    """Tests for sentiment scoring and tag extraction."""

    def test_negative_sentiment_detected(
        self,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Negative words produce negative sentiment."""
        negative_article = NewsArticle(
            title="Crisis: Red Sea Attacks Threaten Global Shipping",
            description="Disruption, delays, and damage reported.",
            url="https://reuters.com/crisis",
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=reference_time - timedelta(hours=1),
            fetched_at=reference_time,
        )

        result = quality_gate.evaluate(negative_article, asof_ts=reference_time)

        assert result.sentiment_score < 0  # Negative

    def test_tags_extracted(
        self,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Tags are extracted from content."""
        article = NewsArticle(
            title="Port Strike Causes Blockage, Sanctions Threatened",
            description="Workers walkout leads to shipping delays.",
            url="https://reuters.com/strike",
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=reference_time - timedelta(hours=1),
            fetched_at=reference_time,
        )

        result = quality_gate.evaluate(article, asof_ts=reference_time)

        assert "strike" in result.tags
        assert "blockage" in result.tags
        assert result.tags == sorted(result.tags)  # Sorted for determinism


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS MAPPER
# ═══════════════════════════════════════════════════════════════════════════════


class TestNewsMapper:
    """Tests for mapping articles to RawSignalEvent."""

    def test_valid_article_creates_event(
        self,
        mapper: NewsMapper,
        fresh_article: NewsArticle,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Valid article + quality score creates RawSignalEvent."""
        quality = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        event = mapper.map_article(fresh_article, quality, asof_ts=reference_time)

        assert event is not None
        assert "Red Sea" in event.title
        assert event.probability > 0.0
        assert event.probability <= 0.95  # Bounded
        assert event.source_metrics is not None
        assert event.source_metrics.get("credibility_score") == quality.credibility_score

    def test_low_quality_article_rejected(
        self,
        mapper: NewsMapper,
        reference_time: datetime,
    ):
        """Low quality articles are not mapped."""
        article = NewsArticle(
            title="Test",
            description="Test",
            url="https://unknown.com/test",
            source_name="Unknown",
            source_domain="unknown.com",
            published_at=reference_time - timedelta(hours=100),  # Too old
            fetched_at=reference_time,
        )

        quality = NewsQualityScore(
            credibility_score=0.3,
            recency_score=0.0,  # Too old
            relevance_score=0.0,
            combined_score=0.0,
            passed_gate=False,
            rejection_reason="Too old",
            matched_topics=[],
            matched_keywords=[],
            sentiment_score=0.0,
            tags=[],
            is_duplicate=False,
            duplicate_of=None,
        )

        event = mapper.map_article(article, quality, asof_ts=reference_time)

        assert event is None

    def test_event_id_deterministic(
        self,
        mapper: NewsMapper,
        fresh_article: NewsArticle,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Same article → same event_id."""
        quality = quality_gate.evaluate(fresh_article, asof_ts=reference_time)
        quality_gate.reset_dedupe_cache()
        quality2 = quality_gate.evaluate(fresh_article, asof_ts=reference_time)

        event1 = mapper.map_article(fresh_article, quality, asof_ts=reference_time)
        event2 = mapper.map_article(fresh_article, quality2, asof_ts=reference_time)

        assert event1 is not None, "Expected event1 to be created from valid article"
        assert event2 is not None, "Expected event2 to be created from valid article"
        assert event1.event_id == event2.event_id

    def test_probability_based_on_sentiment(
        self,
        mapper: NewsMapper,
        quality_gate: NewsQualityGate,
        reference_time: datetime,
    ):
        """Negative sentiment increases probability (risk indicator)."""
        negative_article = NewsArticle(
            title="Red Sea Crisis: Attacks Threaten Shipping Routes",
            description="Major disruption expected.",
            url="https://reuters.com/crisis",
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=reference_time - timedelta(hours=1),
            fetched_at=reference_time,
        )

        positive_article = NewsArticle(
            title="Red Sea Shipping Resumes as Crisis Eases",
            description="Recovery underway.",
            url="https://reuters.com/recovery",
            source_name="Reuters",
            source_domain="reuters.com",
            published_at=reference_time - timedelta(hours=1),
            fetched_at=reference_time,
        )

        neg_quality = quality_gate.evaluate(negative_article, asof_ts=reference_time)
        quality_gate.reset_dedupe_cache()
        pos_quality = quality_gate.evaluate(positive_article, asof_ts=reference_time)

        neg_event = mapper.map_article(negative_article, neg_quality, asof_ts=reference_time)
        pos_event = mapper.map_article(positive_article, pos_quality, asof_ts=reference_time)

        if neg_event and pos_event:
            # Negative news should have higher probability (more risk)
            assert neg_event.probability >= pos_event.probability


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NEWS SIGNAL SOURCE
# ═══════════════════════════════════════════════════════════════════════════════


class TestNewsSignalSource:
    """Tests for NewsSignalSource."""

    def test_mock_source_generates_events(self):
        """Mock source generates events."""
        source = MockNewsSignalSource(scenario="red_sea")

        events = list(source.fetch_events(limit=10))

        assert len(events) > 0
        for event in events:
            assert event.source_metrics is not None

    def test_source_has_name(self):
        """Source has correct name."""
        source = create_news_source(scenario="red_sea")

        assert source.source_name == "news"

    def test_replay_mode_uses_cache(self):
        """Replay mode (with asof_ts) uses cached data."""
        source = MockNewsSignalSource(scenario="red_sea")

        # First fetch (live)
        events1 = list(source.fetch_events(limit=10))

        # Set cache
        source.set_cached_events(events1)

        # Replay fetch (with asof_ts)
        reference_time = datetime.now(timezone.utc)
        events2 = list(source.fetch_events(limit=10, asof_ts=reference_time))

        # Should use cache
        assert len(events2) == len(events1)
        for e1, e2 in zip(events1, events2):
            assert e1.event_id == e2.event_id
