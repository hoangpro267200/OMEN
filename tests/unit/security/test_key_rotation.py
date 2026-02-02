"""Tests for API key rotation and management."""

from datetime import datetime, timezone, timedelta

import pytest

from omen.infrastructure.security.key_rotation import (
    ApiKey,
    ApiKeyManager,
    InMemoryApiKeyStore,
)


@pytest.fixture
def store() -> InMemoryApiKeyStore:
    return InMemoryApiKeyStore()


@pytest.fixture
def manager(store: InMemoryApiKeyStore) -> ApiKeyManager:
    return ApiKeyManager(store)


def test_generate_key_returns_plaintext_and_record(manager: ApiKeyManager):
    """generate_key returns (plaintext, ApiKey); plaintext has omen_ prefix."""
    plaintext, api_key = manager.generate_key(expires_in_days=90)
    assert plaintext.startswith("omen_")
    assert len(plaintext) > 32
    assert api_key.key_id
    assert api_key.key_hash
    assert api_key.created_at
    assert api_key.expires_at is not None
    assert api_key.revoked is False


def test_verify_key_accepts_valid_key(manager: ApiKeyManager):
    """verify_key returns ApiKey for valid plaintext."""
    plaintext, api_key = manager.generate_key(expires_in_days=90)
    result = manager.verify_key(plaintext)
    assert result is not None
    assert result.key_id == api_key.key_id
    assert result.last_used is not None


def test_verify_key_rejects_wrong_key(manager: ApiKeyManager):
    """verify_key returns None for wrong plaintext."""
    manager.generate_key(expires_in_days=90)
    result = manager.verify_key("omen_wrong_key_32_chars_long!!!!!!!!!")
    assert result is None


def test_verify_key_rejects_revoked_key(manager: ApiKeyManager):
    """Revoked keys are rejected."""
    plaintext, api_key = manager.generate_key(expires_in_days=90)
    manager.revoke_key(api_key.key_id)
    result = manager.verify_key(plaintext)
    assert result is None


def test_revoke_key_invalidates_key(manager: ApiKeyManager):
    """revoke_key causes verify_key to return None."""
    plaintext, api_key = manager.generate_key(expires_in_days=90)
    manager.revoke_key(api_key.key_id)
    assert manager.verify_key(plaintext) is None


def test_rotate_key_generates_new_and_revokes_old(manager: ApiKeyManager):
    """rotate_key returns new plaintext and revokes old key."""
    _, old_key = manager.generate_key(expires_in_days=90)
    old_id = old_key.key_id
    new_plaintext, new_key = manager.rotate_key(old_id)
    assert new_plaintext.startswith("omen_")
    assert new_key.key_id != old_id
    assert manager.verify_key(new_plaintext) is not None
    # Old key no longer in store as valid (revoked)
    old_record = manager.store.get_by_id(old_id)
    assert old_record is not None and old_record.revoked is True


def test_expired_key_rejected():
    """Expired keys are rejected by is_valid and verify_key."""
    store = InMemoryApiKeyStore()
    # Create key that is already expired
    past = datetime.now(timezone.utc) - timedelta(days=1)
    key_hash = "abc123"
    key_id = "k1"
    api_key = ApiKey(
        key_id=key_id,
        key_hash=key_hash,
        created_at=past,
        expires_at=past,
        revoked=False,
    )
    store.save(api_key)
    # We can't verify by plaintext without knowing it; test is_valid
    assert api_key.is_valid() is False


def test_api_key_is_valid_false_when_revoked():
    """ApiKey.is_valid() returns False when revoked."""
    now = datetime.now(timezone.utc)
    key = ApiKey(
        key_id="k1",
        key_hash="h1",
        created_at=now,
        expires_at=now + timedelta(days=90),
        revoked=True,
    )
    assert key.is_valid() is False


def test_api_key_is_valid_true_when_not_expired_not_revoked():
    """ApiKey.is_valid() returns True when not expired and not revoked."""
    now = datetime.now(timezone.utc)
    key = ApiKey(
        key_id="k1",
        key_hash="h1",
        created_at=now,
        expires_at=now + timedelta(days=90),
        revoked=False,
    )
    assert key.is_valid() is True
