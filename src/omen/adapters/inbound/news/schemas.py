"""
News Data Schemas.

Pydantic models for news articles and quality scoring.
All models are immutable for reproducibility.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field


class NewsArticle(BaseModel):
    """
    Raw news article from provider.
    
    This is the input format before quality gating and mapping.
    """
    
    # Identity
    url: str = Field(..., description="Article URL (primary key)")
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    content: str | None = Field(None, max_length=50000)
    
    # Source
    source_name: str = Field(..., description="Publisher name")
    source_domain: str = Field(..., description="Publisher domain (e.g., 'reuters.com')")
    author: str | None = None
    
    # Timestamps
    published_at: datetime = Field(..., description="Publication timestamp")
    fetched_at: datetime = Field(..., description="When OMEN fetched this article")
    
    # Raw provider response (for debugging, not used in processing)
    raw_response: dict[str, Any] | None = Field(None, exclude=True)
    
    model_config = {"frozen": True}
    
    @computed_field
    @property
    def url_hash(self) -> str:
        """Deterministic hash of URL for deduplication."""
        return hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:16]
    
    @computed_field
    @property
    def title_normalized(self) -> str:
        """Normalized title for similarity comparison."""
        # Lowercase, remove punctuation, collapse whitespace
        text = self.title.lower()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    
    @computed_field
    @property
    def dedupe_hash(self) -> str:
        """
        Deterministic hash for deduplication.
        
        Uses: normalized title + source domain
        Same article from same source = same hash
        """
        hash_input = f"{self.title_normalized}|{self.source_domain.lower()}"
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]


class NewsQualityScore(BaseModel):
    """
    Quality assessment for a news article.
    
    All scores are deterministic given the same input and asof_ts.
    """
    
    # Individual scores (0-1)
    credibility_score: float = Field(..., ge=0, le=1, description="Source credibility")
    recency_score: float = Field(..., ge=0, le=1, description="Time decay score")
    relevance_score: float = Field(..., ge=0, le=1, description="Topic relevance")
    
    # Combined score
    combined_score: float = Field(..., ge=0, le=1, description="Weighted combination")
    
    # Quality gate result
    passed_gate: bool = Field(..., description="Whether article passed quality gate")
    rejection_reason: str | None = Field(None, description="Reason if rejected")
    
    # Matched topics
    matched_topics: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    
    # Sentiment (rule-based, not LLM)
    sentiment_score: float = Field(
        default=0.0,
        ge=-1,
        le=1,
        description="Sentiment: -1 (negative) to 1 (positive)",
    )
    
    # Tags extracted from content
    tags: list[str] = Field(
        default_factory=list,
        description="Tags like 'strike', 'blockage', 'sanctions'",
    )
    
    # Deduplication
    is_duplicate: bool = Field(default=False)
    duplicate_of: str | None = Field(None, description="URL of original if duplicate")
    
    model_config = {"frozen": True}


class NewsEvent(BaseModel):
    """
    Canonical news event after quality gating.
    
    This is stored in source_metrics of RawSignalEvent.
    Not a separate canonical type to maintain compatibility.
    """
    
    # From article
    article_url: str
    article_title: str
    source_domain: str
    published_at: datetime
    
    # Quality scores
    credibility_score: float
    recency_score: float
    combined_score: float
    
    # Classification
    matched_topics: list[str]
    matched_keywords: list[str]
    sentiment_score: float
    tags: list[str]
    
    # Deduplication
    dedupe_hash: str
    
    model_config = {"frozen": True}
    
    def to_source_metrics(self) -> dict[str, Any]:
        """Convert to source_metrics dict for RawSignalEvent."""
        return {
            "article_url": self.article_url,
            "article_title": self.article_title,
            "source_domain": self.source_domain,
            "published_at": self.published_at.isoformat(),
            "credibility_score": self.credibility_score,
            "recency_score": self.recency_score,
            "combined_score": self.combined_score,
            "matched_topics": sorted(self.matched_topics),  # Sorted for determinism
            "matched_keywords": sorted(self.matched_keywords),
            "sentiment_score": self.sentiment_score,
            "tags": sorted(self.tags),
            "dedupe_hash": self.dedupe_hash,
        }
