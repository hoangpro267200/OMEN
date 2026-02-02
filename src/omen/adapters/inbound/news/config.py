"""
News Source Configuration.

Loads from environment variables and YAML config file.
No hardcoded secrets - all sensitive values from env.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _load_yaml_config() -> dict[str, Any]:
    """Load news.yaml configuration file."""
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "news.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_YAML_CONFIG = _load_yaml_config()


class NewsConfig(BaseSettings):
    """
    News source configuration.
    
    Loads from:
    1. Environment variables (NEWS_* prefix)
    2. news.yaml config file (defaults)
    """
    
    # Provider selection
    provider: str = Field(
        default="newsapi",
        description="News provider: 'newsapi', 'rss', or 'mock'",
    )
    
    # NewsAPI settings (from env)
    newsapi_key: str = Field(
        default="",
        alias="NEWS_API_KEY",
        description="NewsAPI.org API key",
    )
    newsapi_base_url: str = Field(
        default="https://newsapi.org/v2",
        description="NewsAPI base URL",
    )
    
    # Timeouts and retries (from YAML or defaults)
    timeout_seconds: float = Field(
        default=_YAML_CONFIG.get("providers", {}).get("newsapi", {}).get("timeout_seconds", 20.0),
    )
    retry_attempts: int = Field(
        default=_YAML_CONFIG.get("providers", {}).get("newsapi", {}).get("retry_attempts", 3),
    )
    retry_backoff_seconds: float = Field(
        default=_YAML_CONFIG.get("providers", {}).get("newsapi", {}).get("retry_backoff_seconds", 1.0),
    )
    max_results: int = Field(
        default=_YAML_CONFIG.get("providers", {}).get("newsapi", {}).get("max_results", 100),
    )
    
    # Quality gate thresholds (from YAML)
    min_credibility: float = Field(
        default=_YAML_CONFIG.get("quality_gate", {}).get("min_credibility", 0.3),
    )
    min_recency: float = Field(
        default=_YAML_CONFIG.get("quality_gate", {}).get("min_recency", 0.1),
    )
    min_combined_score: float = Field(
        default=_YAML_CONFIG.get("quality_gate", {}).get("min_combined_score", 0.2),
    )
    
    # Recency parameters (from YAML)
    max_age_hours: int = Field(
        default=_YAML_CONFIG.get("recency", {}).get("max_age_hours", 72),
    )
    half_life_hours: float = Field(
        default=_YAML_CONFIG.get("recency", {}).get("half_life_hours", 6.0),
    )
    fresh_threshold_hours: float = Field(
        default=_YAML_CONFIG.get("recency", {}).get("fresh_threshold_hours", 2.0),
    )
    
    # Dedupe parameters (from YAML)
    dedupe_similarity_threshold: float = Field(
        default=_YAML_CONFIG.get("dedupe", {}).get("similarity_threshold", 0.85),
    )
    dedupe_window_hours: int = Field(
        default=_YAML_CONFIG.get("dedupe", {}).get("window_hours", 24),
    )
    
    # Scoring parameters (from YAML)
    credibility_weight: float = Field(
        default=_YAML_CONFIG.get("scoring", {}).get("credibility_weight", 0.6),
    )
    recency_weight: float = Field(
        default=_YAML_CONFIG.get("scoring", {}).get("recency_weight", 0.4),
    )
    max_confidence_boost: float = Field(
        default=_YAML_CONFIG.get("scoring", {}).get("max_confidence_boost", 0.10),
    )
    
    model_config = {
        "env_prefix": "NEWS_",
        "env_file": ".env",
        "extra": "ignore",
    }
    
    @property
    def max_age(self) -> timedelta:
        """Maximum age for articles."""
        return timedelta(hours=self.max_age_hours)
    
    @property
    def half_life(self) -> timedelta:
        """Half-life for recency decay."""
        return timedelta(hours=self.half_life_hours)
    
    @property
    def dedupe_window(self) -> timedelta:
        """Window for deduplication."""
        return timedelta(hours=self.dedupe_window_hours)
    
    def get_credibility_map(self) -> dict[str, float]:
        """Load credibility map from YAML config."""
        cred_config = _YAML_CONFIG.get("credibility", {})
        result: dict[str, float] = {}
        
        # Load tiered domains
        for tier_name in ["tier_1", "tier_2", "tier_3", "tier_4"]:
            tier = cred_config.get(tier_name, {})
            score = tier.get("score", 0.5)
            for domain in tier.get("domains", []):
                result[domain.lower()] = score
        
        return result
    
    def get_topic_keywords(self) -> dict[str, dict[str, list[str]]]:
        """Load topic keywords from YAML config."""
        return _YAML_CONFIG.get("topic_keywords", {})
    
    def get_default_credibility(self) -> float:
        """Get default credibility for unknown sources."""
        return _YAML_CONFIG.get("credibility", {}).get("default_score", 0.3)
