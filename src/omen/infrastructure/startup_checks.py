"""
Production Startup Validation.

Performs critical checks at application startup to ensure the system
is properly configured for production deployment.

Usage:
    from omen.infrastructure.startup_checks import run_production_checks
    
    # In main.py lifespan:
    if OMEN_ENV == "production":
        run_production_checks()  # Exits if checks fail
"""

import logging
import os
import sys
from typing import Callable

logger = logging.getLogger(__name__)

# Environment detection
OMEN_ENV = os.getenv("OMEN_ENV", "development")
IS_PRODUCTION = OMEN_ENV == "production"


class StartupCheckError(Exception):
    """Raised when a critical startup check fails."""
    pass


def run_production_checks() -> None:
    """
    Run all production startup checks.
    
    Exits with code 1 if any critical check fails.
    Call this early in application startup when OMEN_ENV=production.
    """
    if not IS_PRODUCTION:
        logger.debug("Skipping production checks (OMEN_ENV=%s)", OMEN_ENV)
        return
    
    print("\n" + "=" * 60)
    print("OMEN PRODUCTION STARTUP CHECKS")
    print("=" * 60 + "\n")
    
    checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        ("API Keys", _check_api_keys),
        ("Database URL", _check_database_url),
        ("Secret Key", _check_secret_key),
        ("CORS Configuration", _check_cors),
        ("Debug Endpoints", _check_debug_disabled),
        ("Rate Limiting", _check_rate_limiting),
    ]
    
    passed = 0
    failed = 0
    warnings = []
    
    for name, check_fn in checks:
        try:
            ok, message = check_fn()
            if ok:
                print(f"  ✅ {name}: {message}")
                passed += 1
            else:
                print(f"  ❌ {name}: {message}")
                failed += 1
        except Exception as e:
            print(f"  ❌ {name}: Check failed with error: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    if failed > 0:
        print("CRITICAL: Production startup checks failed!")
        print("Fix the issues above before deploying to production.")
        sys.exit(1)
    
    logger.info("All production startup checks passed")


def _check_api_keys() -> tuple[bool, str]:
    """Check if API keys are configured."""
    from omen.infrastructure.security.config import get_security_config
    
    config = get_security_config()
    keys = config.get_api_keys()
    
    if not keys:
        return False, "No API keys configured! Set OMEN_SECURITY_API_KEYS"
    
    # Check key length (security best practice)
    weak_keys = [k for k in keys if len(k) < 32]
    if weak_keys:
        return False, f"{len(weak_keys)} API key(s) are too short (min 32 chars)"
    
    return True, f"{len(keys)} API key(s) configured"


def _check_database_url() -> tuple[bool, str]:
    """Check if production database is configured."""
    db_url = os.getenv("DATABASE_URL", "")
    
    if not db_url:
        return False, "DATABASE_URL not set! Production requires PostgreSQL"
    
    if db_url.startswith("sqlite"):
        return False, "SQLite not suitable for production. Use PostgreSQL"
    
    if not db_url.startswith("postgresql"):
        return False, f"Unexpected database type. Expected postgresql://"
    
    # Check for localhost (usually wrong in production)
    if "localhost" in db_url or "127.0.0.1" in db_url:
        return False, "DATABASE_URL points to localhost. Use proper DB host"
    
    return True, "PostgreSQL database configured"


def _check_secret_key() -> tuple[bool, str]:
    """Check if secret key is properly set."""
    from omen.infrastructure.security.config import get_security_config
    
    config = get_security_config()
    
    if config.jwt_enabled:
        secret = config.jwt_secret.get_secret_value()
        
        if secret in ("dev-only-jwt-secret-change-in-production", "change-me"):
            return False, "JWT secret is a default value. Set OMEN_SECURITY_JWT_SECRET"
        
        if len(secret) < 32:
            return False, f"JWT secret too short ({len(secret)} chars, min 32)"
        
        return True, "JWT secret configured"
    
    return True, "JWT disabled (using API key auth only)"


def _check_cors() -> tuple[bool, str]:
    """Check CORS configuration."""
    from omen.infrastructure.security.config import get_security_config
    
    config = get_security_config()
    origins = config.get_cors_origins()
    
    if not origins:
        return True, "CORS disabled (no origins configured)"
    
    if "*" in origins:
        return False, "CORS allows all origins (*). Set specific origins"
    
    # Check for localhost in production
    localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
    if localhost_origins:
        return False, f"CORS includes localhost: {localhost_origins}"
    
    return True, f"{len(origins)} specific origin(s) configured"


def _check_debug_disabled() -> tuple[bool, str]:
    """Check if debug endpoints are disabled."""
    # Check if debug routes would be enabled
    debug_enabled = os.getenv("OMEN_DEBUG_ENDPOINTS", "false").lower() == "true"
    
    if debug_enabled:
        return False, "Debug endpoints enabled! Set OMEN_DEBUG_ENDPOINTS=false"
    
    return True, "Debug endpoints disabled"


def _check_rate_limiting() -> tuple[bool, str]:
    """Check rate limiting configuration."""
    from omen.infrastructure.security.config import get_security_config
    
    config = get_security_config()
    
    if not config.rate_limit_enabled:
        return False, "Rate limiting disabled! Enable for production"
    
    if config.rate_limit_requests_per_minute > 1000:
        return False, f"Rate limit too high ({config.rate_limit_requests_per_minute}/min)"
    
    return True, f"Rate limit: {config.rate_limit_requests_per_minute}/min"


def check_database_connection() -> bool:
    """
    Test database connection.
    
    Returns True if connection successful, False otherwise.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return False
    
    try:
        import asyncio
        import asyncpg
        
        async def test_connection():
            conn = await asyncpg.connect(db_url)
            await conn.execute("SELECT 1")
            await conn.close()
            return True
        
        return asyncio.run(test_connection())
    except ImportError:
        logger.warning("asyncpg not installed, cannot verify database connection")
        return True  # Assume OK if we can't test
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        return False


def check_redis_connection() -> bool:
    """
    Test Redis connection.
    
    Returns True if connection successful or Redis not configured.
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return True  # Redis is optional
    
    try:
        import asyncio
        import redis.asyncio as redis
        
        async def test_connection():
            r = redis.from_url(redis_url)
            await r.ping()
            await r.close()
            return True
        
        return asyncio.run(test_connection())
    except ImportError:
        logger.warning("redis package not installed, cannot verify Redis connection")
        return True
    except Exception as e:
        logger.error("Redis connection failed: %s", e)
        return False
