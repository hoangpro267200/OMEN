"""
API key rotation and management.

Keys are stored by hash only; plaintext is shown once on generation.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Protocol


@dataclass
class ApiKey:
    """API key record (hash stored, not plaintext)."""

    key_id: str
    key_hash: str
    created_at: datetime
    expires_at: datetime | None
    revoked: bool = False
    last_used: datetime | None = None

    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


class ApiKeyStore(Protocol):
    """Storage for API keys (hash + metadata)."""

    def save(self, api_key: ApiKey) -> None: ...
    def get_by_hash(self, key_hash: str) -> ApiKey | None: ...
    def get_by_id(self, key_id: str) -> ApiKey | None: ...


class InMemoryApiKeyStore:
    """In-memory API key store (for single-process use)."""

    def __init__(self) -> None:
        self._by_hash: dict[str, ApiKey] = {}
        self._by_id: dict[str, ApiKey] = {}

    def save(self, api_key: ApiKey) -> None:
        self._by_hash[api_key.key_hash] = api_key
        self._by_id[api_key.key_id] = api_key

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        return self._by_hash.get(key_hash)

    def get_by_id(self, key_id: str) -> ApiKey | None:
        return self._by_id.get(key_id)


class ApiKeyManager:
    """
    Manages API keys with rotation support.
    """

    def __init__(self, store: ApiKeyStore) -> None:
        self.store = store

    def generate_key(
        self,
        expires_in_days: int | None = 90,
    ) -> tuple[str, ApiKey]:
        """
        Generate new API key.
        Returns (plaintext_key, ApiKey object).
        Plaintext is shown once; only hash is stored.
        """
        key_id = secrets.token_hex(8)
        plaintext = f"omen_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(plaintext)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        self.store.save(api_key)
        return plaintext, api_key

    def verify_key(self, plaintext: str) -> ApiKey | None:
        """Verify API key and return ApiKey if valid. Updates last_used."""
        key_hash = self._hash_key(plaintext)
        api_key = self.store.get_by_hash(key_hash)

        if not api_key or not api_key.is_valid():
            return None

        api_key.last_used = datetime.now(timezone.utc)
        self.store.save(api_key)
        return api_key

    def revoke_key(self, key_id: str) -> None:
        """Revoke an API key by id."""
        api_key = self.store.get_by_id(key_id)
        if api_key:
            api_key.revoked = True
            self.store.save(api_key)

    def rotate_key(self, old_key_id: str) -> tuple[str, ApiKey]:
        """Rotate key: generate new and revoke old."""
        new_plaintext, new_key = self.generate_key()
        self.revoke_key(old_key_id)
        return new_plaintext, new_key

    def _hash_key(self, plaintext: str) -> str:
        return hashlib.sha256(plaintext.encode()).hexdigest()
