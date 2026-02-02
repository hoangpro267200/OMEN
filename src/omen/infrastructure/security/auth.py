"""
Authentication for OMEN API.
"""

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


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
    config: Annotated[SecurityConfig, Depends(get_security_config)],
) -> str:
    """
    Verify API key from header using secure hashed verification.

    Returns the validated API key ID for audit logging.
    Uses ApiKeyManager for secure hash-based verification.
    Keys are NEVER compared in plaintext - only hashes are compared.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Use ApiKeyManager for secure hash-based verification
    from omen.infrastructure.security.api_key_manager import get_api_key_manager

    manager = get_api_key_manager()
    record = manager.verify_key(api_key)

    if record:
        # Return key_id for audit logging (never return the actual key)
        return record.key_id

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
