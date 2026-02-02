"""OMEN Configuration.

Environment-based configuration with sensible defaults.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from .domain.models.common import RulesetVersion, ImpactDomain


class RetentionConfig(BaseSettings):
    """Ledger retention policy configuration. Loads from OMEN_RETENTION_* env."""

    # Retention tiers (days)
    hot_retention_days: int = Field(default=7, description="Hot: active partitions")
    warm_retention_days: int = Field(default=30, description="Warm: compressed, accessible")
    cold_retention_days: int = Field(default=365, description="Cold: archived")
    delete_after_days: Optional[int] = Field(
        default=None,
        description="Delete after N days (None = keep forever)",
    )
    # Auto-seal
    auto_seal_after_hours: int = Field(default=24, description="Seal main partition after N hours")
    seal_grace_period_hours: int = Field(default=2, description="Grace period for late arrivals")
    late_seal_after_days: int = Field(default=7, description="Seal late partitions after N days")
    # Compression
    compress_after_days: int = Field(default=7, description="Compress sealed segments after N days")
    compression_algorithm: str = Field(default="gzip", description="gzip, zstd, lz4")
    compression_level: int = Field(default=6, ge=1, le=9, description="Gzip level 1-9")
    # Archive
    archive_path: Optional[str] = Field(
        default=None, description="Archive path (None = base/_archive)"
    )
    archive_format: str = Field(default="directory", description="directory, tar, tar.gz")

    model_config = {"env_prefix": "OMEN_RETENTION_", "extra": "ignore"}


# Default retention (for use outside OmenConfig)
DEFAULT_RETENTION = RetentionConfig()


class OmenConfig(BaseSettings):
    """
    Configuration for OMEN system.

    All settings can be overridden via environment variables
    with the OMEN_ prefix.
    """

    # Versioning
    ruleset_version: str = Field(default="v1.0.0", description="Current ruleset version")

    # Validation thresholds
    min_liquidity_usd: float = Field(
        default=1000.0, description="Minimum liquidity for signal validity"
    )
    min_volume_usd: float = Field(
        default=5000.0, description="Minimum total volume for signal validity"
    )

    # Confidence thresholds
    min_confidence_for_output: float = Field(
        default=0.3, ge=0, le=1, description="Minimum confidence score to emit a signal"
    )

    # Target domains
    target_domains: list[str] = Field(
        default=["LOGISTICS"], description="Domains to generate impact assessments for"
    )

    # Persistence
    enable_persistence: bool = Field(default=True, description="Enable signal persistence")

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: str = Field(
        default="json",
        description="Log format: 'json' (production) or 'pretty' (development)",
    )

    # Webhook
    webhook_url: str | None = Field(
        default=None,
        description="URL to POST signals to (outbound webhook)",
    )
    webhook_secret: str | None = Field(
        default=None,
        description="Optional HMAC secret for webhook signature",
    )
    webhook_timeout_seconds: int = Field(default=30, description="Webhook HTTP timeout")
    webhook_retry_attempts: int = Field(default=3, description="Webhook retry attempts")

    # Ledger
    ledger_base_path: str = Field(
        default="/data/ledger",
        description="Ledger base path",
    )
    retention: RetentionConfig = Field(
        default_factory=RetentionConfig,
        description="Retention policy",
    )

    model_config = {
        "env_prefix": "OMEN_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore security config vars with nested prefix
    }

    @property
    def parsed_ruleset_version(self) -> RulesetVersion:
        return RulesetVersion(self.ruleset_version)

    @property
    def parsed_target_domains(self) -> frozenset[ImpactDomain]:
        return frozenset(ImpactDomain(d) for d in self.target_domains)


settings = OmenConfig()


def get_config() -> OmenConfig:
    """Return the application config."""
    return settings
