"""
Encryption at rest (Fernet / AES-128-CBC with HMAC).

Uses PBKDF2 key derivation from password when key not provided.

SECURITY NOTES:
- In production, OMEN_ENCRYPTION_SALT MUST be explicitly set
- Salt should be at least 16 bytes of random data
- Never use default salt in production
"""

import base64
import os
import secrets

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


# Environment detection
OMEN_ENV = os.getenv("OMEN_ENV", "development")
IS_PRODUCTION = OMEN_ENV == "production"

# Default salt marker (to detect if not explicitly set)
_DEFAULT_SALT_MARKER = "dev-only-default-salt-change-in-production"


def _get_encryption_salt() -> bytes:
    """
    Get encryption salt from environment.
    
    In production, this MUST be explicitly set.
    In development, uses a default (with warning).
    """
    salt = os.environ.get("OMEN_ENCRYPTION_SALT", "")
    
    if not salt or salt == _DEFAULT_SALT_MARKER:
        if IS_PRODUCTION:
            raise RuntimeError(
                "CRITICAL: OMEN_ENCRYPTION_SALT must be explicitly set in production! "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        # Development: use default but warn
        import warnings
        warnings.warn(
            "Using default encryption salt. Set OMEN_ENCRYPTION_SALT in production.",
            UserWarning,
            stacklevel=3,
        )
        return _DEFAULT_SALT_MARKER.encode()
    
    return salt.encode()


class DataEncryptor:
    """
    Encrypt/decrypt data at rest.
    Uses Fernet (AES-128-CBC with HMAC).
    """

    def __init__(
        self,
        key: bytes | None = None,
        password: str | None = None,
    ) -> None:
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography is required for encryption")
        if key is not None:
            self._fernet = Fernet(key)
        elif password is not None:
            self._fernet = Fernet(self._derive_key(password))
        else:
            raise ValueError("Either key or password required")

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        return self._fernet.decrypt(data)

    def _derive_key(self, password: str) -> bytes:
        salt = _get_encryption_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    @classmethod
    def generate_key(cls) -> bytes:
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography is required")
        return Fernet.generate_key()
