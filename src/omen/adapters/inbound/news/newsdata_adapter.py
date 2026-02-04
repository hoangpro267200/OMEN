"""
NewsData.io News Adapter
FREE tier: 200 credits/day
https://newsdata.io
"""

import os
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """News article from NewsData.io."""
    article_id: str
    title: str
    description: Optional[str]
    content: Optional[str]
    source_name: str
    source_url: str
    link: str
    category: List[str]
    country: List[str]
    language: str
    published_at: datetime
    sentiment: Optional[str]
    image_url: Optional[str]
    
    LOGISTICS_KEYWORDS = [
        "shipping", "freight", "port", "container", "supply chain",
        "logistics", "trade", "tariff", "export", "import",
        "customs", "cargo", "vessel", "maritime", "carrier",
    ]
    
    @property
    def is_logistics_related(self) -> bool:
        """Check if article is logistics/trade related."""
        text = f"{self.title} {self.description or ''}".lower()
        return any(kw in text for kw in self.LOGISTICS_KEYWORDS)
    
    @property
    def sentiment_score(self) -> float:
        """Convert sentiment to numeric score."""
        if self.sentiment == "positive":
            return 1.0
        elif self.sentiment == "negative":
            return -1.0
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['is_logistics_related'] = self.is_logistics_related
        data['sentiment_score'] = self.sentiment_score
        data['published_at'] = self.published_at.isoformat()
        return data


class NewsDataAdapter:
    """
    NewsData.io News API Adapter.
    
    Features:
    - 200 free credits/day
    - 80,000+ news sources globally
    - Sentiment analysis included
    """
    
    BASE_URL = "https://newsdata.io/api/1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NEWSDATA_API_KEY", "")
        
        if not self.api_key:
            raise ValueError(
                "NEWSDATA_API_KEY not configured. "
                "Get free key at https://newsdata.io/register"
            )
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "OMEN/1.0"}
        )
        logger.info("NewsDataAdapter initialized")
    
    def _parse_article(self, item: Dict[str, Any]) -> NewsArticle:
        """Parse API response item to NewsArticle."""
        pub_date = item.get("pubDate")
        if pub_date:
            try:
                pub_date = pub_date.replace(" ", "T").replace("Z", "+00:00")
                if "+" not in pub_date and "-" not in pub_date[-6:]:
                    pub_date += "+00:00"
                published_at = datetime.fromisoformat(pub_date)
            except ValueError:
                published_at = datetime.utcnow()
        else:
            published_at = datetime.utcnow()
        
        return NewsArticle(
            article_id=item.get("article_id", ""),
            title=item.get("title", ""),
            description=item.get("description"),
            content=item.get("content"),
            source_name=item.get("source_name", "") or item.get("source_id", ""),
            source_url=item.get("source_url", ""),
            link=item.get("link", ""),
            category=item.get("category") or [],
            country=item.get("country") or [],
            language=item.get("language", "en"),
            published_at=published_at,
            sentiment=item.get("sentiment"),
            image_url=item.get("image_url"),
        )
    
    async def get_latest_news(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        country: Optional[str] = None,
        language: str = "en",
        size: int = 10
    ) -> List[NewsArticle]:
        """Get latest news articles."""
        params = {
            "apikey": self.api_key,
            "language": language,
            "size": min(size, 50),
        }
        
        if query:
            params["q"] = query
        if category:
            params["category"] = category
        if country:
            params["country"] = country
        
        try:
            response = await self.client.get(f"{self.BASE_URL}/latest", params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "success":
                error_msg = data.get("results", {}).get("message", "Unknown error")
                raise ValueError(f"NewsData API error: {error_msg}")
            
            articles = []
            for item in data.get("results", []):
                try:
                    articles.append(self._parse_article(item))
                except Exception as e:
                    logger.warning(f"Failed to parse article: {e}")
            
            logger.info(f"Fetched {len(articles)} news articles")
            return articles
            
        except httpx.HTTPError as e:
            logger.error(f"NewsData API HTTP error: {e}")
            raise
    
    async def get_logistics_news(self, size: int = 20) -> List[NewsArticle]:
        """Get logistics and trade related news."""
        queries = [
            "shipping container freight logistics",
            "supply chain trade port",
        ]
        
        all_articles: Dict[str, NewsArticle] = {}
        
        for query in queries:
            try:
                articles = await self.get_latest_news(
                    query=query,
                    category="business",
                    size=min(size // 2, 25)
                )
                for article in articles:
                    if article.article_id not in all_articles:
                        if article.is_logistics_related:
                            all_articles[article.article_id] = article
            except Exception as e:
                logger.warning(f"Failed query '{query}': {e}")
        
        sorted_articles = sorted(
            all_articles.values(),
            key=lambda x: x.published_at,
            reverse=True
        )
        
        return sorted_articles[:size]
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


_adapter_instance: Optional[NewsDataAdapter] = None

def get_newsdata_adapter() -> NewsDataAdapter:
    """Get or create NewsData adapter instance."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = NewsDataAdapter()
    return _adapter_instance
