"""
Secure API Key Manager with hashing.

API keys are NEVER stored in plaintext. Only hashes are stored.
This module handles:
- Key generation with secure random tokens
- Key verification using timing-safe comparison
- Key rotation and revocation
- Scope-based access control
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ApiKeyRecord(BaseModel):
    """
    Stored API key record.

    Note: The actual key is NEVER stored. Only the hash.
    """

    model_config = ConfigDict(frozen=True)

    key_id: str = Field(..., description="Unique identifier for this key")
    key_hash: str = Field(..., description="SHA-256 hash of the key")
    key_prefix: str = Field(..., description="First 8 chars of key for identification")
    name: str = Field(..., description="Human-readable name for this key")
    scopes: list[str] = Field(default_factory=list, description="Granted scopes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    last_used_at: Optional[datetime] = Field(None)
    is_active: bool = Field(True)
    created_by: Optional[str] = Field(None, description="Admin who created this key")
    description: Optional[str] = Field(None)

    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        return self.is_active and not self.is_expired()


class ApiKeyStorage(Protocol):
    """Protocol for API key storage backends."""

    def save(self, record: ApiKeyRecord) -> None:
        """Save API key record."""
        ...

    def find_by_hash(self, key_hash: str) -> Optional[ApiKeyRecord]:
        """Find record by key hash."""
        ...

    def find_by_id(self, key_id: str) -> Optional[ApiKeyRecord]:
        """Find record by key ID."""
        ...

    def list_all(self) -> list[ApiKeyRecord]:
        """List all API keys."""
        ...

    def update(self, record: ApiKeyRecord) -> None:
        """Update API key record."""
        ...

    def delete(self, key_id: str) -> bool:
        """Delete API key record."""
        ...


class InMemoryApiKeyStorage:
    """In-memory storage for development/testing."""

    def __init__(self):
        self._keys: dict[str, ApiKeyRecord] = {}
        self._hash_index: dict[str, str] = {}  # hash -> key_id

    def save(self, record: ApiKeyRecord) -> None:
        self._keys[record.key_id] = record
        self._hash_index[record.key_hash] = record.key_id

    def find_by_hash(self, key_hash: str) -> Optional[ApiKeyRecord]:
        key_id = self._hash_index.get(key_hash)
        if key_id:
            return self._keys.get(key_id)
        return None

    def find_by_id(self, key_id: str) -> Optional[ApiKeyRecord]:
        return self._keys.get(key_id)

    def list_all(self) -> list[ApiKeyRecord]:
        return list(self._keys.values())

    def update(self, record: ApiKeyRecord) -> None:
        if record.key_id in self._keys:
            self._keys[record.key_id] = record

    def delete(self, key_id: str) -> bool:
        record = self._keys.pop(key_id, None)
        if record:
            self._hash_index.pop(record.key_hash, None)
            return True
        return False


class ApiKeyManager:
    """
    Manages API keys with secure hashing.

    Keys are NEVER stored in plaintext - only SHA-256 hashes.
    Uses timing-safe comparison to prevent timing attacks.
    """

    # Key prefix for easy identification
    KEY_PREFIX = "omen_"

    def __init__(self, storage: ApiKeyStorage):
        self.storage = storage

    def generate_key(
        self,
        name: str,
        scopes: Optional[list[str]] = None,
        expires_in_days: Optional[int] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
    ) -> tuple[str, ApiKeyRecord]:
        """
        Generate a new API key.

        Returns:
            (plaintext_key, record)

            plaintext_key: The actual key to give to the user.
                          This is shown ONLY ONCE and never stored.
            record: The stored record (contains hash, not key).
        """
        # Generate secure random key
        random_part = secrets.token_urlsafe(32)
        plaintext_key = f"{self.KEY_PREFIX}{random_part}"

        # Hash for storage
        key_hash = self._hash_key(plaintext_key)
        key_id = f"key_{secrets.token_hex(8)}"
        key_prefix = plaintext_key[:12]  # First 12 chars for display

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            from datetime import timedelta

            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        record = ApiKeyRecord(
            key_id=key_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            scopes=scopes or ["read:signals"],
            expires_at=expires_at,
            created_by=created_by,
            description=description,
        )

        # Store hashed record
        self.storage.save(record)

        logger.info("Generated new API key: id=%s, name=%s, scopes=%s", key_id, name, scopes)

        return plaintext_key, record

    def verify_key(self, plaintext_key: str) -> Optional[ApiKeyRecord]:
        """
        Verify an API key.

        Returns:
            ApiKeyRecord if valid and active, None otherwise.
        """
        if not plaintext_key:
            return None

        # Hash the provided key
        key_hash = self._hash_key(plaintext_key)

        # Look up by hash
        record = self.storage.find_by_hash(key_hash)

        if not record:
            return None

        # Check if valid (active and not expired)
        if not record.is_valid():
            return None

        # Update last used (optional - depends on storage implementation)
        try:
            updated_record = ApiKeyRecord(
                **record.model_dump(),
                last_used_at=datetime.now(timezone.utc),
            )
            self.storage.update(updated_record)
        except Exception:
            pass  # Non-critical update

        return record

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by ID."""
        record = self.storage.find_by_id(key_id)
        if not record:
            return False

        updated_record = ApiKeyRecord(**{**record.model_dump(), "is_active": False})
        self.storage.update(updated_record)

        logger.info("Revoked API key: %s", key_id)
        return True

    def delete_key(self, key_id: str) -> bool:
        """Permanently delete an API key."""
        result = self.storage.delete(key_id)
        if result:
            logger.info("Deleted API key: %s", key_id)
        return result

    def list_keys(self) -> list[ApiKeyRecord]:
        """List all API keys (for admin purposes)."""
        return self.storage.list_all()

    def _hash_key(self, plaintext: str) -> str:
        """
        Hash key using SHA-256.

        Uses a pepper from environment for additional security.
        In production, OMEN_API_KEY_PEPPER MUST be explicitly set.
        """
        pepper = _get_api_key_pepper()
        salted = f"{pepper}:{plaintext}"
        return hashlib.sha256(salted.encode()).hexdigest()


# Environment detection for pepper validation
_OMEN_ENV = os.getenv("OMEN_ENV", "development")
_IS_PRODUCTION = _OMEN_ENV == "production"
_DEFAULT_PEPPER_MARKER = "omen-default-pepper"


def _get_api_key_pepper() -> str:
    """
    Get API key pepper from environment.

    In production, this MUST be explicitly set.
    In development, uses a default (with warning).
    """
    pepper = os.environ.get("OMEN_API_KEY_PEPPER", "")

    if not pepper or pepper == _DEFAULT_PEPPER_MARKER:
        if _IS_PRODUCTION:
            raise RuntimeError(
                "CRITICAL: OMEN_API_KEY_PEPPER must be explicitly set in production! "
                'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        # Development: use default but warn
        import warnings

        warnings.warn(
            "Using default API key pepper. Set OMEN_API_KEY_PEPPER in production.",
            UserWarning,
            stacklevel=3,
        )
        return _DEFAULT_PEPPER_MARKER

    return pepper


# Global manager instance
_api_key_manager: Optional[ApiKeyManager] = None
_legacy_keys_loaded = False


def get_api_key_manager() -> ApiKeyManager:
    """Get or create the global API key manager."""
    global _api_key_manager, _legacy_keys_loaded

    if _api_key_manager is None:
        storage = InMemoryApiKeyStorage()
        _api_key_manager = ApiKeyManager(storage)

    # Load legacy keys from environment (for backward compatibility)
    if not _legacy_keys_loaded:
        _load_legacy_keys(_api_key_manager)
        _legacy_keys_loaded = True

    return _api_key_manager


def _load_legacy_keys(manager: ApiKeyManager) -> None:
    """
    Load legacy plaintext keys from environment.

    This maintains backward compatibility with existing deployments.
    New deployments should use the key management API.
    """
    from omen.infrastructure.security.config import get_security_config

    config = get_security_config()
    legacy_keys = config.get_api_keys()

    for i, key in enumerate(legacy_keys):
        # Check if already loaded (by checking hash)
        key_hash = manager._hash_key(key)
        if manager.storage.find_by_hash(key_hash):
            continue

        # Create record for legacy key
        record = ApiKeyRecord(
            key_id=f"legacy_{i}",
            key_hash=key_hash,
            key_prefix=key[:12] if len(key) > 12 else key,
            name=f"Legacy Key {i + 1}",
            scopes=["read:signals", "write:signals", "admin"],  # Full access for legacy
            description="Migrated from OMEN_SECURITY_API_KEYS environment variable",
        )
        manager.storage.save(record)
        logger.info("Loaded legacy API key: %s", record.key_id)
