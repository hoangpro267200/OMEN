"""
Role-Based Access Control with Scopes.

Implements fine-grained access control based on API key scopes.
Each API key can have multiple scopes that grant specific permissions.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, status

from omen.infrastructure.security.api_key_manager import (
    ApiKeyManager,
    ApiKeyRecord,
    get_api_key_manager,
)

logger = logging.getLogger(__name__)


class Scopes:
    """
    Available API scopes.
    
    Scopes follow the pattern: action:resource
    """
    
    # Signal scopes
    READ_SIGNALS = "read:signals"
    WRITE_SIGNALS = "write:signals"
    
    # Partner scopes
    READ_PARTNERS = "read:partners"
    WRITE_PARTNERS = "write:partners"
    
    # Multi-source scopes
    READ_MULTI_SOURCE = "read:multi-source"
    
    # Methodology scopes
    READ_METHODOLOGY = "read:methodology"
    
    # Activity scopes
    READ_ACTIVITY = "read:activity"
    
    # Stats scopes
    READ_STATS = "read:stats"
    
    # Storage scopes
    READ_STORAGE = "read:storage"
    WRITE_STORAGE = "write:storage"
    
    # Admin scopes
    ADMIN = "admin"
    DEBUG = "debug"
    
    # Realtime scopes
    READ_REALTIME = "read:realtime"
    
    # All available scopes for documentation
    ALL_SCOPES = [
        READ_SIGNALS,
        WRITE_SIGNALS,
        READ_PARTNERS,
        WRITE_PARTNERS,
        READ_MULTI_SOURCE,
        READ_METHODOLOGY,
        READ_ACTIVITY,
        READ_STATS,
        READ_STORAGE,
        WRITE_STORAGE,
        ADMIN,
        DEBUG,
        READ_REALTIME,
    ]
    
    # Default scopes for new keys
    DEFAULT_SCOPES = [READ_SIGNALS, READ_PARTNERS, READ_METHODOLOGY]
    
    # Read-only scopes bundle
    READ_ONLY = [
        READ_SIGNALS,
        READ_PARTNERS,
        READ_MULTI_SOURCE,
        READ_METHODOLOGY,
        READ_ACTIVITY,
        READ_STATS,
        READ_REALTIME,
    ]
    
    # Full access (everything except admin/debug)
    FULL_ACCESS = [
        READ_SIGNALS,
        WRITE_SIGNALS,
        READ_PARTNERS,
        WRITE_PARTNERS,
        READ_MULTI_SOURCE,
        READ_METHODOLOGY,
        READ_ACTIVITY,
        READ_STATS,
        READ_STORAGE,
        WRITE_STORAGE,
        READ_REALTIME,
    ]


class ScopeChecker:
    """
    Dependency for checking required scopes.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(ScopeChecker([Scopes.ADMIN]))])
        async def admin_endpoint():
            pass
    """
    
    def __init__(self, required_scopes: List[str]):
        self.required_scopes = set(required_scopes)
    
    async def __call__(
        self,
        api_key: str = None,
    ) -> ApiKeyRecord:
        """Check if the API key has required scopes."""
        from fastapi import Request
        
        # Get API key from header
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "AUTHENTICATION_REQUIRED",
                    "message": "API key is required",
                },
            )
        
        # Verify key and get record
        manager = get_api_key_manager()
        record = manager.verify_key(api_key)
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_API_KEY",
                    "message": "The provided API key is invalid or expired",
                },
            )
        
        # Check scopes
        user_scopes = set(record.scopes)
        
        # Admin scope grants all permissions
        if Scopes.ADMIN in user_scopes:
            return record
        
        # Check if user has required scopes
        if not self.required_scopes.issubset(user_scopes):
            missing = self.required_scopes - user_scopes
            logger.warning(
                "Insufficient scopes for key %s: required=%s, missing=%s",
                record.key_id, self.required_scopes, missing
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_PERMISSIONS",
                    "message": "Your API key does not have the required permissions",
                    "required_scopes": list(self.required_scopes),
                    "missing_scopes": list(missing),
                    "your_scopes": list(user_scopes),
                },
            )
        
        return record


def require_scopes(required_scopes: List[str]):
    """
    Create a dependency that checks for required scopes.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_scopes([Scopes.ADMIN]))])
    """
    return ScopeChecker(required_scopes)


async def verify_api_key_with_scopes(
    api_key: Optional[str] = None,
    required_scopes: Optional[List[str]] = None,
) -> ApiKeyRecord:
    """
    Verify API key and check scopes.
    
    Used internally by the auth system.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AUTHENTICATION_REQUIRED"},
        )
    
    manager = get_api_key_manager()
    record = manager.verify_key(api_key)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_API_KEY"},
        )
    
    if required_scopes:
        user_scopes = set(record.scopes)
        required = set(required_scopes)
        
        if Scopes.ADMIN not in user_scopes and not required.issubset(user_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_PERMISSIONS",
                    "required_scopes": list(required),
                    "missing_scopes": list(required - user_scopes),
                },
            )
    
    return record


# Convenience dependencies for common scope requirements
require_read_signals = require_scopes([Scopes.READ_SIGNALS])
require_write_signals = require_scopes([Scopes.WRITE_SIGNALS])
require_read_partners = require_scopes([Scopes.READ_PARTNERS])
require_admin = require_scopes([Scopes.ADMIN])
require_debug = require_scopes([Scopes.DEBUG])
