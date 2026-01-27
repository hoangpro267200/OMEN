"""OMEN Configuration.

Environment-based configuration with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field

from .domain.models.common import RulesetVersion, ImpactDomain


class OmenConfig(BaseSettings):
    """
    Configuration for OMEN system.
    
    All settings can be overridden via environment variables
    with the OMEN_ prefix.
    """
    
    # Versioning
    ruleset_version: str = Field(
        default="v1.0.0",
        description="Current ruleset version"
    )
    
    # Validation thresholds
    min_liquidity_usd: float = Field(
        default=1000.0,
        description="Minimum liquidity for signal validity"
    )
    min_volume_usd: float = Field(
        default=5000.0,
        description="Minimum total volume for signal validity"
    )
    
    # Confidence thresholds
    min_confidence_for_output: float = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Minimum confidence score to emit a signal"
    )
    
    # Target domains
    target_domains: list[str] = Field(
        default=["LOGISTICS"],
        description="Domains to generate impact assessments for"
    )
    
    # Persistence
    enable_persistence: bool = Field(
        default=True,
        description="Enable signal persistence"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
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

    model_config = {
        "env_prefix": "OMEN_",
        "env_file": ".env",
        "env_file_encoding": "utf-8"
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
