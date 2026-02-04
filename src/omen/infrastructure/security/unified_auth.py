"""
UNIFIED AUTHENTICATION - SINGLE SOURCE OF TRUTH
================================================

This is the ONLY authentication module to be used across the entire OMEN system.
All other authentication mechanisms are DEPRECATED.

Production-Grade Features:
- API Key validation with secure comparison
- Rate limiting (in-memory, replaceable with Redis)
- Audit logging for all auth events
- Health check endpoint
- Environment-aware behavior (dev bypass vs production enforcement)

Authentication Flow:
    Request → Rate Limit Check → API Key Extraction → Validation → Audit Log → Route Handler

Environment Behavior:
    - development: Explicit bypass with WARNING in logs
    - production: NO bypass, strict validation

Usage:
    from omen.infrastructure.security.unified_auth import verify_api_key, AuthContext
    
    @router.get("/endpoint")
    async def endpoint(auth: AuthContext = Depends(require_auth)):
        # auth.user_id contains the authenticated user/key ID
        pass
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, List, Optional, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

class AuthConfig:
    """Authentication configuration with secure defaults."""
    
    def __init__(self):
        self.env = os.getenv("OMEN_ENV", "production").lower()  # Default to production for safety
        self.is_production = self.env == "production"
        # Development bypass requires EXPLICIT opt-in with OMEN_DEV_AUTH_BYPASS=true
        self._dev_bypass_enabled = os.getenv("OMEN_DEV_AUTH_BYPASS", "false").lower() == "true"
        self.is_development = self.env == "development" and self._dev_bypass_enabled
        
        # API Keys (comma-separated for multiple keys)
        self._raw_keys = os.getenv("OMEN_SECURITY_API_KEYS", "")
        self.valid_keys = self._parse_keys(self._raw_keys)
        
        # Rate limiting
        self.rate_limit_enabled = os.getenv(
            "OMEN_SECURITY_RATE_LIMIT_ENABLED", "false"
        ).lower() == "true"
        self.rate_limit_requests = int(os.getenv("OMEN_RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("OMEN_RATE_LIMIT_WINDOW", "60"))
        
        # Session
        self.session_timeout = int(os.getenv("OMEN_SESSION_TIMEOUT", "3600"))
        
    def _parse_keys(self, raw: str) -> set[str]:
        """Parse comma-separated API keys, ignore empty."""
        if not raw:
            return set()
        return {k.strip() for k in raw.split(",") if k.strip()}
    
    def validate_production_config(self) -> List[str]:
        """Return list of configuration issues for production."""
        issues = []
        
        if not self.valid_keys:
            issues.append("No API keys configured (OMEN_SECURITY_API_KEYS)")
        
        if len(self.valid_keys) == 1:
            key = list(self.valid_keys)[0]
            if "dev" in key.lower() or "test" in key.lower():
                issues.append("Using development/test API key in production")
            
        if not self.rate_limit_enabled and self.is_production:
            issues.append("Rate limiting is disabled in production")
        
        # CRITICAL: Ensure dev bypass is never enabled in production
        if self.is_production and self._dev_bypass_enabled:
            issues.append("CRITICAL: OMEN_DEV_AUTH_BYPASS is enabled in production!")
            
        return issues

# Global config instance
config = AuthConfig()

# Log environment on module load
print(f"[UNIFIED AUTH] Loaded - ENV={config.env}, IS_DEV={config.is_development}")

# Header and query parameter names
API_KEY_HEADER_NAME = "X-API-Key"
API_KEY_QUERY_NAME = "api_key"

# Security schemes
_api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)
_api_key_query = APIKeyQuery(name=API_KEY_QUERY_NAME, auto_error=False)


# ═══════════════════════════════════════════════════════════════════════════
# AUTH CONTEXT - Result of successful authentication
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AuthContext:
    """
    Authentication context passed to route handlers.
    
    Contains all information about the authenticated user/key.
    """
    user_id: str
    api_key_hash: str = ""  # Never store actual key, only hash for logging
    scopes: List[str] = field(default_factory=list)
    authenticated_at: datetime = None
    expires_at: datetime = None
    is_development_bypass: bool = False
    
    def __post_init__(self):
        if self.authenticated_at is None:
            self.authenticated_at = datetime.now(timezone.utc)
        if self.expires_at is None:
            self.expires_at = self.authenticated_at + timedelta(seconds=config.session_timeout)
        if not self.scopes:
            # Default scopes for API keys - read access to most resources
            self.scopes = [
                "read:signals",
                "write:signals",
                "read:partners",
                "read:multi-source",
                "read:methodology",
                "read:activity",
                "read:stats",
                "read:realtime",
                "read:live-mode",
                "write:live-mode",
            ]


# ═══════════════════════════════════════════════════════════════════════════
# RATE LIMITING (In-Memory - Replace with Redis for production)
# ═══════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    Note: For multi-process deployments, replace with Redis.
    """
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old entries
        if key in self._requests:
            self._requests[key] = [t for t in self._requests[key] if t > window_start]
        else:
            self._requests[key] = []
            
        # Check limit
        if len(self._requests[key]) >= max_requests:
            return False
            
        # Record request
        self._requests[key].append(now)
        return True
        
    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - window_seconds
        
        if key not in self._requests:
            return max_requests
            
        recent = [t for t in self._requests[key] if t > window_start]
        return max(0, max_requests - len(recent))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "tracked_keys": len(self._requests),
            "total_entries": sum(len(v) for v in self._requests.values()),
        }

# Global rate limiter
rate_limiter = RateLimiter()


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT LOGGING (using EnhancedAuditLogger for compliance)
# ═══════════════════════════════════════════════════════════════════════════

class AuditLogger:
    """
    Security event audit logger.
    
    Uses EnhancedAuditLogger for comprehensive, compliance-ready logging.
    Falls back to simple logging if enhanced logger is not available.
    """
    
    def __init__(self):
        self.audit_log = logging.getLogger("omen.security.audit")
        self._enhanced_logger = None
        try:
            from omen.infrastructure.security.enhanced_audit import get_audit_logger
            self._enhanced_logger = get_audit_logger()
        except Exception as e:
            self.audit_log.debug("Enhanced audit logger not available: %s", e)
        
    def log_auth_success(self, request: Request, context: AuthContext):
        """Log successful authentication."""
        client_ip = self._get_client_ip(request)
        
        # Enhanced logging
        if self._enhanced_logger:
            self._enhanced_logger.log_auth_success(
                actor_id=context.user_id,
                actor_ip=client_ip,
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "scopes": context.scopes,
                    "dev_bypass": context.is_development_bypass,
                },
            )
        
        # Standard logging
        self.audit_log.info(
            "AUTH_SUCCESS | user=%s | path=%s %s | ip=%s | dev_bypass=%s",
            context.user_id,
            request.method,
            request.url.path,
            client_ip,
            context.is_development_bypass,
        )
        
    def log_auth_failure(self, request: Request, reason: str):
        """Log failed authentication."""
        client_ip = self._get_client_ip(request)
        
        # Enhanced logging
        if self._enhanced_logger:
            self._enhanced_logger.log_auth_failure(
                actor_id=None,
                actor_ip=client_ip,
                reason=reason,
            )
        
        # Standard logging
        self.audit_log.warning(
            "AUTH_FAILURE | reason=%s | path=%s %s | ip=%s",
            reason,
            request.method,
            request.url.path,
            client_ip,
        )
        
    def log_rate_limit(self, request: Request, key_hash: str):
        """Log rate limit exceeded."""
        client_ip = self._get_client_ip(request)
        
        # Enhanced logging
        if self._enhanced_logger:
            from omen.infrastructure.security.enhanced_audit import (
                AuditEvent, AuditEventType, AuditSeverity,
            )
            self._enhanced_logger.log(AuditEvent(
                event_type=AuditEventType.API_RATE_LIMITED,
                severity=AuditSeverity.WARNING,
                actor_ip=client_ip,
                description=f"Rate limit exceeded for {request.url.path}",
                details={"key_hash": key_hash},
                compliance_tags=["security", "rate-limit"],
            ))
        
        # Standard logging
        self.audit_log.warning(
            "RATE_LIMIT | key_hash=%s | path=%s %s | ip=%s",
            key_hash,
            request.method,
            request.url.path,
            self._get_client_ip(request),
        )
        
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

# Global audit logger
audit = AuditLogger()


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _hash_key(key: str) -> str:
    """Hash API key for logging (never log actual keys)."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _auth_error(message: str, hint: str = None) -> HTTPException:
    """Create standardized auth error."""
    detail = {
        "error": "authentication_required",
        "message": message,
    }
    if hint:
        detail["hint"] = hint
    
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "ApiKey"},
    )


def _invalid_key_error() -> HTTPException:
    """Create invalid key error."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "invalid_api_key",
            "message": "The provided API key is invalid or expired",
            "hint": "Check your API key and ensure it has not expired",
        },
        headers={"WWW-Authenticate": "ApiKey"},
    )


def _rate_limit_error(remaining: int, window: int) -> HTTPException:
    """Create rate limit error."""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded. Try again in {window} seconds.",
            "remaining": remaining,
            "retry_after": window,
        },
        headers={"Retry-After": str(window)},
    )


# ═══════════════════════════════════════════════════════════════════════════
# CORE AUTH FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

async def authenticate(
    request: Request,
    api_key_header: str | None,
    api_key_query: str | None,
) -> AuthContext:
    """
    Core authentication function.
    
    This is the SINGLE source of truth for authentication.
    
    Flow:
    1. Check for development bypass
    2. Extract API key from header or query
    3. Check rate limiting
    4. Validate against configured keys
    5. Audit log the result
    6. Return AuthContext on success
    
    Args:
        request: FastAPI request object
        api_key_header: API key from X-API-Key header
        api_key_query: API key from ?api_key= query parameter
        
    Returns:
        AuthContext with authenticated user information
        
    Raises:
        HTTPException with 401/429 if authentication fails
    """
    path = request.url.path
    method = request.method
    
    # STEP 1: Development bypass (requires EXPLICIT opt-in with OMEN_DEV_AUTH_BYPASS=true)
    if config.is_development:
        import warnings
        warnings.warn(
            "⚠️ DEVELOPMENT AUTH BYPASS IS ENABLED (OMEN_DEV_AUTH_BYPASS=true). "
            "This should NEVER be used in production!",
            RuntimeWarning,
            stacklevel=3
        )
        logger.warning(
            "[DEV BYPASS] Auth skipped for %s %s - OMEN_DEV_AUTH_BYPASS=true - DO NOT USE IN PRODUCTION",
            method, path
        )
        context = AuthContext(
            user_id="dev_bypass",
            api_key_hash="dev_bypass",
            is_development_bypass=True,
            scopes=["*"],  # All scopes in dev
        )
        audit.log_auth_success(request, context)
        return context
    
    # STEP 2: Extract API key (header takes precedence)
    api_key = api_key_header or api_key_query
    
    logger.debug(
        "Auth check: %s %s | key_from_header=%s | key_from_query=%s",
        method, path,
        "yes" if api_key_header else "no",
        "yes" if api_key_query else "no",
    )
    
    if not api_key:
        audit.log_auth_failure(request, "No API key provided")
        raise _auth_error(
            "API key is required",
            f"Include {API_KEY_HEADER_NAME} header or ?{API_KEY_QUERY_NAME}= query parameter"
        )
    
    # STEP 3: Rate limiting check
    key_hash = _hash_key(api_key)
    
    if config.rate_limit_enabled:
        if not rate_limiter.is_allowed(
            key_hash,
            config.rate_limit_requests,
            config.rate_limit_window
        ):
            audit.log_rate_limit(request, key_hash)
            remaining = rate_limiter.get_remaining(
                key_hash,
                config.rate_limit_requests,
                config.rate_limit_window
            )
            raise _rate_limit_error(remaining, config.rate_limit_window)
    
    # STEP 4: Validate API key
    from omen.infrastructure.security.config import get_security_config
    
    security_config = get_security_config()
    valid_keys = security_config.get_api_keys()
    
    # Check against configured keys (using constant-time comparison)
    key_id = None
    for i, valid_key in enumerate(valid_keys):
        if secrets.compare_digest(api_key, valid_key):
            key_id = f"api_user_{key_hash}"
            break
    
    # Also check ApiKeyManager for programmatic keys
    if key_id is None:
        try:
            from omen.infrastructure.security.api_key_manager import get_api_key_manager
            manager = get_api_key_manager()
            record = manager.verify_key(api_key)
            if record:
                key_id = record.key_id
        except Exception as e:
            logger.debug("ApiKeyManager check failed: %s", e)
    
    if key_id is None:
        audit.log_auth_failure(request, f"Invalid API key (hash: {key_hash})")
        raise _invalid_key_error()
    
    # STEP 5: Create context and log success
    # Full access scopes for authenticated API keys
    context = AuthContext(
        user_id=key_id,
        api_key_hash=key_hash,
        is_development_bypass=False,
        scopes=[
            "read:signals",
            "write:signals",
            "read:partners",
            "write:partners",
            "read:multi-source",
            "read:methodology",
            "read:activity",
            "read:stats",
            "read:storage",
            "write:storage",
            "read:realtime",
            "read:live-mode",
            "write:live-mode",
        ],
    )
    
    audit.log_auth_success(request, context)
    
    logger.info(
        "[AUTH OK] %s %s | user=%s",
        method, path, key_id
    )
    
    return context


# ═══════════════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════

async def require_auth(
    request: Request,
    api_key_header: Annotated[str | None, Depends(_api_key_header)],
    api_key_query: Annotated[str | None, Depends(_api_key_query)],
) -> AuthContext:
    """
    FastAPI dependency for authentication.
    
    Returns full AuthContext with user info, scopes, etc.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(auth: AuthContext = Depends(require_auth)):
            pass
    """
    return await authenticate(request, api_key_header, api_key_query)


async def verify_api_key_simple(
    request: Request,
    api_key_header: Annotated[str | None, Depends(_api_key_header)],
    api_key_query: Annotated[str | None, Depends(_api_key_query)],
) -> str:
    """
    Simple auth that returns just the user_id string.
    
    For backward compatibility with existing code.
    """
    auth = await authenticate(request, api_key_header, api_key_query)
    return auth.user_id


def get_auth_dependency():
    """Factory function for authentication dependency."""
    return require_auth


# Alias for backward compatibility
verify_api_key = verify_api_key_simple


# ═══════════════════════════════════════════════════════════════════════════
# SCOPE CHECKING
# ═══════════════════════════════════════════════════════════════════════════

def require_scope(scope: str):
    """
    Factory for scope-checking dependency.
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            auth: AuthContext = Depends(require_auth),
            _: None = Depends(require_scope("admin:write"))
        ):
            ...
    """
    async def checker(auth: AuthContext = Depends(require_auth)):
        if "*" in auth.scopes or scope in auth.scopes:
            return None
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "insufficient_scope",
                "message": f"Required scope: {scope}",
                "your_scopes": auth.scopes,
            }
        )
    return checker


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════

def get_auth_health() -> Dict[str, Any]:
    """
    Return auth system health for monitoring.
    
    Called by /health/auth endpoint.
    """
    issues = config.validate_production_config() if config.is_production else []
    
    return {
        "status": "healthy" if not issues else "degraded",
        "environment": config.env,
        "is_production": config.is_production,
        "rate_limiting_enabled": config.rate_limit_enabled,
        "rate_limit_config": {
            "requests_per_window": config.rate_limit_requests,
            "window_seconds": config.rate_limit_window,
        },
        "api_keys_configured": len(config.valid_keys),
        "rate_limiter_stats": rate_limiter.get_stats(),
        "issues": issues,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTE DEPENDENCIES (Pre-configured for common use cases)
# ═══════════════════════════════════════════════════════════════════════════

# Standard auth - use for all protected routes
AUTH_REQUIRED = [Depends(require_auth)]

# Simple auth - returns just user_id string
AUTH_REQUIRED_SIMPLE = [Depends(verify_api_key_simple)]
