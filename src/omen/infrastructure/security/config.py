"""
Security configuration for OMEN.

SECURITY NOTES:
- In production, ALL secrets MUST be explicitly set via environment variables
- Default values are only for development/testing
- The application will fail fast in production if secrets are not configured
"""

import os
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


# Environment detection
OMEN_ENV = os.getenv("OMEN_ENV", "development")
IS_PRODUCTION = OMEN_ENV == "production"


class SecurityConfig(BaseSettings):
    """Security settings loaded from environment."""

    # API Key Authentication - OMEN_SECURITY_API_KEYS env var (comma-separated)
    api_key_header: str = "X-API-Key"
    api_keys: str = Field(
        default="",
        description="Valid API keys (comma-separated in env)",
    )
    
    def get_api_keys(self) -> list[str]:
        """Parse comma-separated API keys from env."""
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    # JWT Authentication (optional)
    jwt_enabled: bool = False
    jwt_secret: SecretStr = Field(
        default=SecretStr("dev-only-jwt-secret-change-in-production"),
        description="JWT secret key - MUST be set explicitly in production",
    )
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    @field_validator("jwt_secret", mode="after")
    @classmethod
    def validate_jwt_secret_in_production(cls, v: SecretStr) -> SecretStr:
        """Ensure JWT secret is explicitly set in production."""
        if IS_PRODUCTION:
            secret_value = v.get_secret_value()
            if secret_value in (
                "dev-only-jwt-secret-change-in-production",
                "change-me-in-production",
                "",
            ):
                raise ValueError(
                    "CRITICAL: JWT secret must be explicitly set in production! "
                    "Set OMEN_SECURITY_JWT_SECRET environment variable."
                )
        return v

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 300  # 5 req/sec for demo/dev
    rate_limit_burst: int = 50  # Allow bursts from frontend

    # CORS - OMEN_SECURITY_CORS_ORIGINS env var (comma-separated)
    cors_enabled: bool = True
    cors_origins: str = Field(
        default="*",
        description="CORS origins (comma-separated in env)",
    )
    cors_allow_credentials: bool = False
    
    def get_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins from env."""
        if not self.cors_origins:
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Webhook Security
    webhook_secret: SecretStr | None = None
    webhook_signature_header: str = "X-OMEN-Signature"

    # Field Redaction - OMEN_SECURITY_REDACTED_FIELDS env var (comma-separated)
    redact_internal_fields: bool = True
    redacted_fields: str = Field(
        default="_source_assessment,raw_payload",
        description="Fields to redact (comma-separated in env)",
    )
    
    def get_redacted_fields(self) -> list[str]:
        """Parse comma-separated redacted fields from env."""
        if not self.redacted_fields:
            return ["_source_assessment", "raw_payload"]
        return [f.strip() for f in self.redacted_fields.split(",") if f.strip()]

    model_config = {
        "env_prefix": "OMEN_SECURITY_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",  # Ignore other env vars like NEWS_API_KEY, ALPHAVANTAGE_API_KEY
    }


@lru_cache()
def get_security_config() -> SecurityConfig:
    """Return cached security config."""
    return SecurityConfig()
