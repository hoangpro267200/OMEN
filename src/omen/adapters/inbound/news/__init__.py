"""
News/NLP Signal Source for OMEN.

Provides early detection and context confirmation through news article analysis.
"""

from .config import NewsConfig
from .schemas import NewsArticle, NewsQualityScore
from .source import NewsSignalSource, create_news_source
from .mapper import NewsMapper
from .quality_gate import NewsQualityGate

__all__ = [
    "NewsConfig",
    "NewsArticle",
    "NewsQualityScore",
    "NewsSignalSource",
    "create_news_source",
    "NewsMapper",
    "NewsQualityGate",
]
