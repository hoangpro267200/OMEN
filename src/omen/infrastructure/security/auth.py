"""
Authentication for OMEN API.

⚠️ DEPRECATED: This module is deprecated and will be removed in a future version.
Use `omen.infrastructure.security.unified_auth` instead for all authentication needs.

Migration:
    # Old (deprecated):
    from omen.infrastructure.security.auth import verify_api_key
    
    # New (recommended):
    from omen.infrastructure.security.unified_auth import require_auth
"""
import warnings
warnings.warn(
    "omen.infrastructure.security.auth is deprecated. "
    "Use omen.infrastructure.security.unified_auth instead.",
    DeprecationWarning,
    stacklevel=2,
)

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from omen.infrastructure.security.config import SecurityConfig, get_security_config

# API Key Authentication
_api_key_header_name = "X-API-Key"
api_key_header = APIKeyHeader(name=_api_key_header_name, auto_error=False)

# API Key from query parameter (for SSE/EventSource which doesn't support headers)
from fastapi import Query
from fastapi.security import APIKeyQuery

api_key_query_scheme = APIKeyQuery(name="api_key", auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
    api_key_from_query: Annotated[str | None, Security(api_key_query_scheme)],
    config: Annotated[SecurityConfig, Depends(get_security_config)],
) -> str:
    """
    Verify API key from header or query parameter.

    Returns the validated API key ID for audit logging.
    Supports both X-API-Key header and ?api_key= query parameter (for SSE/EventSource).
    """
    import secrets as sec
    import logging
    import os
    _logger = logging.getLogger(__name__)
    
    # Development bypass - requires EXPLICIT opt-in with BOTH conditions:
    # 1. OMEN_ENV=development
    # 2. OMEN_DEV_AUTH_BYPASS=true (explicit flag)
    env = os.getenv("OMEN_ENV", "production").lower()
    bypass_enabled = os.getenv("OMEN_DEV_AUTH_BYPASS", "false").lower() == "true"
    
    if env == "development" and bypass_enabled:
        import warnings
        warnings.warn(
            "⚠️ DEVELOPMENT AUTH BYPASS IS ENABLED. "
            "This should NEVER be used in production!",
            RuntimeWarning,
            stacklevel=2
        )
        _logger.warning("Auth bypassed in development mode - OMEN_DEV_AUTH_BYPASS=true")
        return "dev_bypass"
    
    # DEBUG: Log incoming key info
    _logger.info("verify_api_key called: header=%r, query=%r", api_key, api_key_from_query)
    
    # Try header first, then query parameter (for EventSource/SSE)
    actual_key = api_key or api_key_from_query
    if not actual_key:
        _logger.warning("No API key provided in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Direct plaintext comparison with configured keys (same as middleware)
    valid_keys = config.get_api_keys()
    for i, valid_key in enumerate(valid_keys):
        if sec.compare_digest(actual_key, valid_key):
            return f"key_{i}"  # Return key index as ID

    # Also try ApiKeyManager for any programmatically generated keys
    try:
        from omen.infrastructure.security.api_key_manager import get_api_key_manager
        manager = get_api_key_manager()
        record = manager.verify_key(actual_key)
        if record:
            return record.key_id
    except Exception:
        pass  # Fall through to error

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


# JWT Authentication (optional)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class TokenPayload:
    """JWT token payload."""

    sub: str
    exp: datetime
    iat: datetime
    scopes: list[str] = field(default_factory=list)


def create_access_token(
    subject: str,
    scopes: list[str],
    config: SecurityConfig,
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "exp": now + timedelta(hours=config.jwt_expiry_hours),
        "iat": now,
        "scopes": scopes,
    }
    raw = jwt.encode(
        payload,
        config.jwt_secret.get_secret_value(),
        algorithm=config.jwt_algorithm,
    )
    return raw if isinstance(raw, str) else raw.decode("utf-8")


async def verify_jwt_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    config: Annotated[SecurityConfig, Depends(get_security_config)],
) -> TokenPayload:
    """Verify JWT token from Authorization header."""
    if not config.jwt_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication not enabled",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            config.jwt_secret.get_secret_value(),
            algorithms=[config.jwt_algorithm],
        )
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            scopes=payload.get("scopes", []),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


# Webhook Signature
def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC signature for webhook payload."""
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify webhook signature."""
    expected = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected)
