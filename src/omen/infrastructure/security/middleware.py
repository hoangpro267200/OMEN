"""
Security Middleware - Protect all sensitive endpoints.

This middleware ensures ALL endpoints (except explicitly whitelisted ones)
require authentication. Also handles HTTPS redirection and security headers.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Set

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from omen.infrastructure.security.config import get_security_config

logger = logging.getLogger(__name__)

# Environment
OMEN_ENV = os.getenv("OMEN_ENV", "development")
IS_PRODUCTION = OMEN_ENV == "production"


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirect HTTP to HTTPS in production.

    This middleware ensures all traffic uses HTTPS when running in production.
    It respects X-Forwarded-Proto header for requests behind load balancers.
    """

    async def dispatch(self, request: Request, call_next):
        # Only redirect in production
        if IS_PRODUCTION:
            # Check if request is HTTP (not HTTPS)
            if request.url.scheme == "http":
                # Check X-Forwarded-Proto (for load balancers/proxies)
                forwarded_proto = request.headers.get("x-forwarded-proto", "")

                if forwarded_proto != "https":
                    # Redirect to HTTPS
                    https_url = request.url.replace(scheme="https")
                    logger.debug(
                        "Redirecting HTTP to HTTPS: %s -> %s",
                        str(request.url),
                        str(https_url),
                    )
                    return RedirectResponse(
                        url=str(https_url),
                        status_code=301,  # Permanent redirect
                    )

        return await call_next(request)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all authenticated API requests for audit purposes.

    Logs:
    - Request path, method
    - API key ID (not the key itself)
    - Response status
    - Processing time
    """

    async def dispatch(self, request: Request, call_next):
        import time

        start_time = time.perf_counter()

        # Extract API key info for logging (redacted)
        api_key = request.headers.get("X-API-Key", "")
        key_prefix = api_key[:8] + "..." if len(api_key) > 8 else "none"

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = (time.perf_counter() - start_time) * 1000  # ms

        # Log authenticated requests (skip public endpoints)
        path = request.url.path
        if path.startswith("/api/") and api_key:
            # Check if admin override was used
            admin_override = getattr(request.state, "admin_override", False)

            logger.info(
                "API Request: %s %s | key=%s | status=%d | time=%.2fms%s",
                request.method,
                path,
                key_prefix,
                response.status_code,
                process_time,
                " [ADMIN_OVERRIDE]" if admin_override else "",
            )

        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Global authentication middleware.

    Protects all endpoints except explicitly whitelisted ones.
    This ensures no endpoint is accidentally left unprotected.
    """

    # Endpoints that DON'T require authentication (exact match)
    PUBLIC_PATHS: Set[str] = {
        "/",
        "/health",
        "/health/",
        "/health/ready",
        "/health/live",
        "/metrics",
        "/docs",
        "/docs/",
        "/redoc",
        "/redoc/",
        "/openapi.json",
    }

    # Paths that start with these prefixes are public
    PUBLIC_PREFIXES: tuple[str, ...] = (
        "/docs",
        "/redoc",
        "/health",
    )

    # OPTIONS requests are always allowed (CORS preflight)
    ALLOWED_METHODS_WITHOUT_AUTH: Set[str] = {"OPTIONS"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # OPTIONS requests for CORS preflight
        if method in self.ALLOWED_METHODS_WITHOUT_AUTH:
            return await call_next(request)

        # Check if public endpoint
        if self._is_public(path):
            return await call_next(request)

        # Require authentication for all other endpoints
        try:
            api_key = request.headers.get("X-API-Key")

            if not api_key:
                logger.warning(
                    "Authentication required but no API key provided: %s %s", method, path
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "API key is required. Include X-API-Key header.",
                        "path": path,
                    },
                    headers={"WWW-Authenticate": "ApiKey"},
                )

            # Verify API key
            config = get_security_config()
            valid_keys = config.get_api_keys()
            
            # DEBUG: Temporary logging to diagnose auth issue
            logger.info("Auth debug: api_keys_in_config=%d, received_key_len=%d", len(valid_keys), len(api_key))
            for i, vk in enumerate(valid_keys):
                logger.info("Auth debug: valid_key[%d] len=%d, matches=%s", i, len(vk), api_key == vk)

            is_valid = False
            for valid_key in valid_keys:
                if secrets.compare_digest(api_key, valid_key):
                    is_valid = True
                    break

            if not is_valid:
                logger.warning(
                    "Invalid API key attempt: %s %s (key prefix: %s...)",
                    method,
                    path,
                    api_key[:8] if len(api_key) > 8 else "???",
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "INVALID_API_KEY",
                        "message": "The provided API key is invalid.",
                    },
                    headers={"WWW-Authenticate": "ApiKey"},
                )

        except Exception as e:
            logger.error("Authentication error: %s", e)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTHENTICATION_FAILED",
                    "message": str(e),
                },
            )

        return await call_next(request)

    def _is_public(self, path: str) -> bool:
        """Check if path is public (doesn't require authentication)."""
        # Exact match
        if path in self.PUBLIC_PATHS:
            return True

        # Prefix match
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True

        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # OMEN contract headers
        response.headers["X-OMEN-Contract-Version"] = "2.0.0"
        response.headers["X-OMEN-Contract-Type"] = "signal-only"

        return response
