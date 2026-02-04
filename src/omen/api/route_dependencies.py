"""
Route Dependencies with RBAC Enforcement.

This module provides pre-configured dependencies for all route types.
Every route MUST use one of these dependencies - no exceptions.

RBAC Scopes follow the pattern: action:resource
- read:signals - Read signal data
- write:signals - Create/modify signals
- read:partners - Read partner risk data
- write:partners - Create/modify partner data
- read:multi-source - Read multi-source analysis
- read:methodology - Read methodology docs
- read:activity - Read activity logs
- read:stats - Read statistics
- read:storage - Read storage data
- write:storage - Write storage data
- read:realtime - Read realtime data
- admin - Full admin access
- debug - Debug access

Usage:
    from omen.api.route_dependencies import require_signals_read
    
    @router.get("/signals")
    async def list_signals(auth: AuthContext = Depends(require_signals_read)):
        # auth.user_id, auth.scopes are available
        pass
"""

from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, APIKeyQuery

from omen.infrastructure.security.unified_auth import (
    AuthContext,
    authenticate,
)

logger = logging.getLogger(__name__)

# Security schemes
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)


# ═══════════════════════════════════════════════════════════════════════════
# SCOPE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

class Scopes:
    """
    Available API scopes.
    Scopes follow the pattern: action:resource
    """
    
    # Signal scopes
    SIGNALS_READ = "read:signals"
    SIGNALS_WRITE = "write:signals"
    
    # Partner scopes
    PARTNERS_READ = "read:partners"
    PARTNERS_WRITE = "write:partners"
    
    # Multi-source scopes
    MULTI_SOURCE_READ = "read:multi-source"
    
    # Methodology scopes
    METHODOLOGY_READ = "read:methodology"
    
    # Activity scopes
    ACTIVITY_READ = "read:activity"
    
    # Stats scopes
    STATS_READ = "read:stats"
    
    # Storage scopes
    STORAGE_READ = "read:storage"
    STORAGE_WRITE = "write:storage"
    
    # Realtime scopes
    REALTIME_READ = "read:realtime"
    
    # Live mode scopes
    LIVE_MODE_READ = "read:live-mode"
    LIVE_MODE_WRITE = "write:live-mode"
    
    # Admin scopes
    ADMIN = "admin"
    DEBUG = "debug"
    
    # Health (public - no auth required for basic health)
    HEALTH_READ = "read:health"


# ═══════════════════════════════════════════════════════════════════════════
# SCOPE-CHECKING DEPENDENCY FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def _create_scope_checker(required_scopes: List[str]):
    """
    Factory to create a scope-checking dependency.
    
    Args:
        required_scopes: List of scopes that are required (ANY of them grants access)
        
    Returns:
        FastAPI dependency function
    """
    async def scope_checker(
        request: Request,
        api_key_header: Annotated[str | None, Depends(_api_key_header)],
        api_key_query: Annotated[str | None, Depends(_api_key_query)],
    ) -> AuthContext:
        """Authenticate and check required scopes."""
        # First authenticate
        auth = await authenticate(request, api_key_header, api_key_query)
        
        # Check scopes
        user_scopes = set(auth.scopes)
        required = set(required_scopes)
        
        # Admin scope grants all permissions
        if Scopes.ADMIN in user_scopes or "*" in user_scopes:
            logger.debug(
                "RBAC: Admin/wildcard scope grants access to %s for user %s",
                required_scopes, auth.user_id
            )
            return auth
        
        # Check if user has ANY of the required scopes
        if not required.intersection(user_scopes):
            logger.warning(
                "RBAC: Insufficient scopes for user %s: required=%s, has=%s",
                auth.user_id, required_scopes, list(user_scopes)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_PERMISSIONS",
                    "message": "Your API key does not have the required permissions",
                    "required_scopes": required_scopes,
                    "your_scopes": list(user_scopes),
                },
            )
        
        logger.debug(
            "RBAC: Access granted to %s for user %s",
            required_scopes, auth.user_id
        )
        return auth
    
    return scope_checker


# ═══════════════════════════════════════════════════════════════════════════
# PRE-CONFIGURED SCOPE DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════

# Signal routes
require_signals_read = _create_scope_checker([Scopes.SIGNALS_READ])
require_signals_write = _create_scope_checker([Scopes.SIGNALS_WRITE])
require_signals_any = _create_scope_checker([Scopes.SIGNALS_READ, Scopes.SIGNALS_WRITE])

# Partner routes
require_partners_read = _create_scope_checker([Scopes.PARTNERS_READ])
require_partners_write = _create_scope_checker([Scopes.PARTNERS_WRITE])
require_partners_any = _create_scope_checker([Scopes.PARTNERS_READ, Scopes.PARTNERS_WRITE])

# Multi-source routes
require_multi_source_read = _create_scope_checker([Scopes.MULTI_SOURCE_READ])

# Methodology routes
require_methodology_read = _create_scope_checker([Scopes.METHODOLOGY_READ])

# Activity routes
require_activity_read = _create_scope_checker([Scopes.ACTIVITY_READ])

# Stats routes
require_stats_read = _create_scope_checker([Scopes.STATS_READ])

# Storage routes
require_storage_read = _create_scope_checker([Scopes.STORAGE_READ])
require_storage_write = _create_scope_checker([Scopes.STORAGE_WRITE])
require_storage_any = _create_scope_checker([Scopes.STORAGE_READ, Scopes.STORAGE_WRITE])

# Realtime routes
require_realtime_read = _create_scope_checker([Scopes.REALTIME_READ])

# Live mode routes
require_live_mode_read = _create_scope_checker([Scopes.LIVE_MODE_READ])
require_live_mode_write = _create_scope_checker([Scopes.LIVE_MODE_WRITE])

# Admin routes
require_admin = _create_scope_checker([Scopes.ADMIN])

# Debug routes
require_debug = _create_scope_checker([Scopes.DEBUG])

# Combined dependencies for common use cases
require_read_only = _create_scope_checker([
    Scopes.SIGNALS_READ,
    Scopes.PARTNERS_READ,
    Scopes.MULTI_SOURCE_READ,
    Scopes.METHODOLOGY_READ,
    Scopes.ACTIVITY_READ,
    Scopes.STATS_READ,
    Scopes.REALTIME_READ,
])


# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT SCOPES FOR NEW API KEYS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_SCOPES = [
    Scopes.SIGNALS_READ,
    Scopes.PARTNERS_READ,
    Scopes.METHODOLOGY_READ,
    Scopes.STATS_READ,
    Scopes.ACTIVITY_READ,
    Scopes.REALTIME_READ,
]

READ_ONLY_SCOPES = [
    Scopes.SIGNALS_READ,
    Scopes.PARTNERS_READ,
    Scopes.MULTI_SOURCE_READ,
    Scopes.METHODOLOGY_READ,
    Scopes.ACTIVITY_READ,
    Scopes.STATS_READ,
    Scopes.REALTIME_READ,
    Scopes.LIVE_MODE_READ,
]

FULL_ACCESS_SCOPES = [
    Scopes.SIGNALS_READ,
    Scopes.SIGNALS_WRITE,
    Scopes.PARTNERS_READ,
    Scopes.PARTNERS_WRITE,
    Scopes.MULTI_SOURCE_READ,
    Scopes.METHODOLOGY_READ,
    Scopes.ACTIVITY_READ,
    Scopes.STATS_READ,
    Scopes.STORAGE_READ,
    Scopes.STORAGE_WRITE,
    Scopes.REALTIME_READ,
    Scopes.LIVE_MODE_READ,
    Scopes.LIVE_MODE_WRITE,
]

ALL_SCOPES = FULL_ACCESS_SCOPES + [Scopes.ADMIN, Scopes.DEBUG]
