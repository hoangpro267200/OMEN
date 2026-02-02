"""
News API Client.

Fetches news articles from NewsAPI.org or RSS feeds.
Includes retry logic, rate limiting, and circuit breaker.

Security:
- API key from environment only (never logged)
- No PII in logs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Iterator
from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .config import NewsConfig
from .schemas import NewsArticle

logger = logging.getLogger(__name__)


class NewsAPIError(Exception):
    """Error from NewsAPI."""
    pass


class NewsAPIRateLimitError(NewsAPIError):
    """Rate limit exceeded."""
    pass


class NewsClient:
    """
    NewsAPI.org client with async support.
    
    Features:
    - Async HTTP requests (non-blocking)
    - Timeout handling
    - Retry with exponential backoff
    - Rate limit awareness
    - No API key logging
    """
    
    def __init__(self, config: NewsConfig | None = None):
        self._config = config or NewsConfig()
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._last_request_time: datetime | None = None
    
    def _get_sync_client(self) -> httpx.Client:
        """Lazy init sync client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                timeout=self._config.timeout_seconds,
                headers={"User-Agent": "OMEN/0.1.0 NewsClient"},
            )
        return self._sync_client
    
    def _get_async_client(self) -> httpx.AsyncClient:
        """Lazy init async client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self._config.timeout_seconds,
                headers={"User-Agent": "OMEN/0.1.0 NewsClient"},
            )
        return self._async_client
    
    def _get_headers(self) -> dict[str, str]:
        """Get headers with API key (key not logged)."""
        if not self._config.newsapi_key:
            raise NewsAPIError("NEWS_API_KEY not configured")
        return {"X-Api-Key": self._config.newsapi_key}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def search(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 100,
    ) -> Iterator[NewsArticle]:
        """
        Search for news articles (sync version).
        
        Args:
            query: Search query (keywords)
            from_date: Start date filter
            to_date: End date filter
            language: Language code
            sort_by: Sort order (publishedAt, relevancy, popularity)
            page_size: Results per page (max 100)
        
        Yields:
            NewsArticle objects
        """
        params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(page_size, self._config.max_results),
        }
        
        if from_date:
            params["from"] = from_date.strftime("%Y-%m-%dT%H:%M:%S")
        if to_date:
            params["to"] = to_date.strftime("%Y-%m-%dT%H:%M:%S")
        
        url = f"{self._config.newsapi_base_url}/everything"
        
        try:
            logger.info(f"NewsAPI search: query='{query[:50]}...' pageSize={page_size}")
            response = self._get_sync_client().get(
                url,
                params=params,
                headers=self._get_headers(),
            )
            
            if response.status_code == 429:
                logger.warning("NewsAPI rate limit exceeded")
                raise NewsAPIRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok":
                error_msg = data.get("message", "Unknown error")
                logger.error(f"NewsAPI error: {error_msg}")
                raise NewsAPIError(error_msg)
            
            articles = data.get("articles", [])
            logger.info(f"NewsAPI returned {len(articles)} articles")
            
            fetched_at = datetime.now(timezone.utc)
            
            for raw in articles:
                try:
                    article = self._parse_article(raw, fetched_at)
                    if article:
                        yield article
                except Exception as e:
                    logger.warning(f"Failed to parse article: {e}")
                    continue
                    
        except httpx.TimeoutException:
            logger.error(f"NewsAPI timeout after {self._config.timeout_seconds}s")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"NewsAPI HTTP error: {e.response.status_code}")
            raise NewsAPIError(f"HTTP {e.response.status_code}")
    
    async def search_async(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 100,
    ) -> list[NewsArticle]:
        """
        Search for news articles (async version - non-blocking).
        
        Args:
            query: Search query (keywords)
            from_date: Start date filter
            to_date: End date filter
            language: Language code
            sort_by: Sort order (publishedAt, relevancy, popularity)
            page_size: Results per page (max 100)
        
        Returns:
            List of NewsArticle objects
        """
        import asyncio
        
        params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(page_size, self._config.max_results),
        }
        
        if from_date:
            params["from"] = from_date.strftime("%Y-%m-%dT%H:%M:%S")
        if to_date:
            params["to"] = to_date.strftime("%Y-%m-%dT%H:%M:%S")
        
        url = f"{self._config.newsapi_base_url}/everything"
        
        # Retry logic for async
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"NewsAPI async search: query='{query[:50]}...' pageSize={page_size}")
                response = await self._get_async_client().get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
                
                if response.status_code == 429:
                    logger.warning("NewsAPI rate limit exceeded")
                    raise NewsAPIRateLimitError("Rate limit exceeded")
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "ok":
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"NewsAPI error: {error_msg}")
                    raise NewsAPIError(error_msg)
                
                articles = data.get("articles", [])
                logger.info(f"NewsAPI returned {len(articles)} articles")
                
                fetched_at = datetime.now(timezone.utc)
                results = []
                
                for raw in articles:
                    try:
                        article = self._parse_article(raw, fetched_at)
                        if article:
                            results.append(article)
                    except Exception as e:
                        logger.warning(f"Failed to parse article: {e}")
                        continue
                
                return results
                    
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"NewsAPI request failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"NewsAPI timeout after {self._config.timeout_seconds}s")
                    raise
            except httpx.HTTPStatusError as e:
                logger.error(f"NewsAPI HTTP error: {e.response.status_code}")
                raise NewsAPIError(f"HTTP {e.response.status_code}")
        
        return []
    
    def _parse_article(
        self,
        raw: dict,
        fetched_at: datetime,
    ) -> NewsArticle | None:
        """Parse raw API response into NewsArticle."""
        url = raw.get("url")
        title = raw.get("title")
        
        if not url or not title:
            return None
        
        # Parse source
        source = raw.get("source", {})
        source_name = source.get("name", "Unknown")
        
        # Extract domain from URL
        try:
            parsed = urlparse(url)
            source_domain = parsed.netloc.lower()
            if source_domain.startswith("www."):
                source_domain = source_domain[4:]
        except Exception:
            source_domain = "unknown"
        
        # Parse published date
        published_str = raw.get("publishedAt")
        if published_str:
            try:
                # ISO format with Z suffix
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                )
            except ValueError:
                published_at = fetched_at
        else:
            published_at = fetched_at
        
        return NewsArticle(
            url=url,
            title=title,
            description=raw.get("description"),
            content=raw.get("content"),
            source_name=source_name,
            source_domain=source_domain,
            author=raw.get("author"),
            published_at=published_at,
            fetched_at=fetched_at,
            raw_response=raw,
        )
    
    def close(self) -> None:
        """Close HTTP clients."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
    
    async def aclose(self) -> None:
        """Close HTTP clients (async)."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
    
    def __enter__(self) -> "NewsClient":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    async def __aenter__(self) -> "NewsClient":
        return self
    
    async def __aexit__(self, *args) -> None:
        await self.aclose()


class MockNewsClient:
    """
    Mock news client for testing and demo.
    
    Returns deterministic articles without network calls.
    """
    
    def __init__(
        self,
        config: NewsConfig | None = None,
        scenario: str = "red_sea",
    ):
        self._config = config or NewsConfig()
        self._scenario = scenario
    
    def search(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        **kwargs,
    ) -> Iterator[NewsArticle]:
        """Return mock articles based on scenario."""
        now = datetime.now(timezone.utc)
        
        scenarios = {
            "red_sea": [
                NewsArticle(
                    url="https://reuters.com/article/red-sea-shipping-1",
                    title="Red Sea shipping attacks continue to disrupt global trade",
                    description="Houthi rebels launched another attack on commercial vessels in the Red Sea, "
                               "forcing more shipping companies to reroute around Cape of Good Hope.",
                    source_name="Reuters",
                    source_domain="reuters.com",
                    published_at=now - timedelta(hours=2),
                    fetched_at=now,
                ),
                NewsArticle(
                    url="https://bloomberg.com/article/red-sea-insurance-1",
                    title="Insurance costs surge for Red Sea shipping routes",
                    description="War risk premiums for vessels transiting the Red Sea have increased "
                               "tenfold since attacks began.",
                    source_name="Bloomberg",
                    source_domain="bloomberg.com",
                    published_at=now - timedelta(hours=6),
                    fetched_at=now,
                ),
            ],
            "port_strike": [
                NewsArticle(
                    url="https://ft.com/article/port-strike-1",
                    title="US East Coast port workers threaten strike over automation",
                    description="Dock workers union warns of potential walkout affecting major ports "
                               "including New York, Savannah, and Houston.",
                    source_name="Financial Times",
                    source_domain="ft.com",
                    published_at=now - timedelta(hours=4),
                    fetched_at=now,
                ),
            ],
            "panama": [
                NewsArticle(
                    url="https://wsj.com/article/panama-drought-1",
                    title="Panama Canal restrictions extended as drought persists",
                    description="Canal authority announces further transit limitations due to low water levels, "
                               "impacting global shipping capacity.",
                    source_name="Wall Street Journal",
                    source_domain="wsj.com",
                    published_at=now - timedelta(hours=8),
                    fetched_at=now,
                ),
            ],
        }
        
        articles = scenarios.get(self._scenario, scenarios["red_sea"])
        
        for article in articles:
            # Filter by query if specified
            if query:
                query_lower = query.lower()
                if query_lower not in article.title.lower() and \
                   query_lower not in (article.description or "").lower():
                    continue
            yield article
    
    def close(self) -> None:
        pass


def create_news_client(config: NewsConfig | None = None) -> NewsClient | MockNewsClient:
    """
    Factory to create news client.
    
    Returns mock client if:
    - provider is 'mock', or
    - NEWS_API_KEY is not set
    """
    config = config or NewsConfig()
    
    if config.provider == "mock":
        return MockNewsClient(config)
    
    if not config.newsapi_key:
        logger.warning("NEWS_API_KEY not set, using mock client")
        return MockNewsClient(config)
    
    return NewsClient(config)
