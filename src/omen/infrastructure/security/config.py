"""
Security configuration for OMEN.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class SecurityConfig(BaseSettings):
    """Security settings loaded from environment."""

    # API Key Authentication
    api_key_header: str = "X-API-Key"
    api_keys: list[str] = Field(
        default_factory=list,
        description="Valid API keys (comma-separated in env)",
    )

    # JWT Authentication (optional)
    jwt_enabled: bool = False
    jwt_secret: SecretStr = Field(default=SecretStr("change-me-in-production"))
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 300  # 5 req/sec for demo/dev
    rate_limit_burst: int = 50  # Allow bursts from frontend

    # CORS
    cors_enabled: bool = True
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = False

    # Webhook Security
    webhook_secret: SecretStr | None = None
    webhook_signature_header: str = "X-OMEN-Signature"

    # Field Redaction
    redact_internal_fields: bool = True
    redacted_fields: list[str] = Field(
        default_factory=lambda: ["_source_assessment", "raw_payload"],
    )

    model_config = {
        "env_prefix": "OMEN_SECURITY_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        if isinstance(v, list):
            return v
        return []


@lru_cache()
def get_security_config() -> SecurityConfig:
    """Return cached security config."""
    return SecurityConfig()
