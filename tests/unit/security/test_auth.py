"""Tests for auth module (webhook signature, JWT helpers)."""

from datetime import datetime

import pytest
from pydantic import SecretStr

from omen.infrastructure.security.auth import (
    create_access_token,
    generate_webhook_signature,
    TokenPayload,
    verify_webhook_signature,
)
from omen.infrastructure.security.config import SecurityConfig


def test_generate_webhook_signature_is_deterministic():
    """Same payload and secret produce same signature."""
    payload = b'{"signal_id":"OMEN-ABC","severity":0.5}'
    secret = "test-secret"
    a = generate_webhook_signature(payload, secret)
    b = generate_webhook_signature(payload, secret)
    assert a == b
    assert isinstance(a, str)
    assert len(a) == 64  # SHA256 hex


def test_verify_webhook_signature_accepts_valid():
    """Verify accepts correct signature."""
    payload = b'{"x":1}'
    secret = "s"
    sig = generate_webhook_signature(payload, secret)
    assert verify_webhook_signature(payload, sig, secret) is True


def test_verify_webhook_signature_rejects_invalid():
    """Verify rejects wrong signature."""
    payload = b'{"x":1}'
    assert verify_webhook_signature(payload, "wrong", "s") is False
    assert verify_webhook_signature(payload, "", "s") is False


def test_verify_webhook_signature_rejects_tampered_payload():
    """Verify rejects signature for different payload."""
    payload = b'{"x":1}'
    secret = "s"
    sig = generate_webhook_signature(payload, secret)
    assert verify_webhook_signature(b'{"x":2}', sig, secret) is False


def test_create_access_token_returns_jwt_string():
    """create_access_token returns a non-empty string."""
    config = SecurityConfig(
        api_keys=[],
        jwt_secret=SecretStr("test-secret"),
    )
    token = create_access_token("client-1", ["read"], config)
    assert isinstance(token, str)
    assert len(token) > 0


def test_token_payload_dataclass():
    """TokenPayload has expected fields."""
    p = TokenPayload(
        sub="u",
        exp=datetime.utcnow(),
        iat=datetime.utcnow(),
        scopes=["a"],
    )
    assert p.sub == "u"
    assert p.scopes == ["a"]
