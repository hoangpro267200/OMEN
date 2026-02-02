"""
Polymarket client configuration (env-based).

Reads from .env / process env. Supports proxy via HTTP_PROXY, HTTPS_PROXY, NO_PROXY
(httpx trust_env). No custom proxy vars; use standard env for corporate compatibility.
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


def _omen_version() -> str:
    try:
        from importlib.metadata import version
        return version("omen")
    except Exception:
        return "0.1.0"


class PolymarketSettings(BaseSettings):
    """
    Polymarket API and client settings.

    All settings can be overridden via environment variables with POLYMARKET_ prefix.
    Proxy: use standard HTTP_PROXY, HTTPS_PROXY, NO_PROXY (trust_env=true uses them).
    """

    gamma_api_url: str = Field(
        default="https://gamma-api.polymarket.com",
        description="Gamma API base URL (events, markets)",
    )
    clob_api_url: str = Field(
        default="https://clob.polymarket.com",
        description="CLOB API base URL (price, book, midpoint)",
    )
    ws_url: str = Field(
        default="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        description="WebSocket URL for real-time price stream",
    )
    api_url: str = Field(
        default="https://api.polymarket.com",
        description="Legacy Polymarket API base URL (PolymarketClient)",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for legacy API (Bearer token)",
    )
    timeout_s: float = Field(
        default=10.0,
        ge=1.0,
        le=300.0,
        description="HTTP request timeout in seconds",
    )
    retry_max: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max retry attempts for transient failures",
    )
    retry_backoff_s: float = Field(
        default=0.5,
        ge=0.0,
        description="Exponential backoff base in seconds",
    )
    httpx_trust_env: bool = Field(
        default=True,
        description="Let httpx use HTTP_PROXY/HTTPS_PROXY/NO_PROXY",
    )
    user_agent: str = Field(
        default_factory=lambda: f"OMEN/{_omen_version()} PolymarketClient",
        description="User-Agent header for Polymarket requests",
    )

    model_config = {
        "env_prefix": "POLYMARKET_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


_polymarket_settings: Optional[PolymarketSettings] = None


def get_polymarket_settings() -> PolymarketSettings:
    """Return Polymarket settings (singleton)."""
    global _polymarket_settings
    if _polymarket_settings is None:
        _polymarket_settings = PolymarketSettings()
    return _polymarket_settings
