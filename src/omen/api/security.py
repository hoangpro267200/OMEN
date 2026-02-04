"""
API Security - Central security configuration for all routes.

This module provides standardized security dependencies for all API routes.
Uses the UNIFIED AUTH system - no other auth mechanisms allowed.
"""

from __future__ import annotations

from fastapi import Depends

from omen.infrastructure.security.unified_auth import (
    require_auth,
    verify_api_key_simple,
    AuthContext,
    AUTH_REQUIRED,
    AUTH_REQUIRED_SIMPLE,
)
from omen.infrastructure.security.rbac import Scopes  # Keep for reference

# ═══════════════════════════════════════════════════════════════════════════
# ROUTE SECURITY CONFIGURATIONS
# All routes use the UNIFIED AUTH system
# ═══════════════════════════════════════════════════════════════════════════

# Read-only signal endpoints
READ_SIGNALS = AUTH_REQUIRED_SIMPLE

# Write signal endpoints (processing)
WRITE_SIGNALS = AUTH_REQUIRED_SIMPLE

# Partner signal read endpoints
READ_PARTNERS = AUTH_REQUIRED_SIMPLE

# Partner signal write endpoints
WRITE_PARTNERS = AUTH_REQUIRED_SIMPLE

# Multi-source intelligence endpoints
READ_MULTI_SOURCE = AUTH_REQUIRED_SIMPLE

# Real-time streaming endpoints
READ_REALTIME = AUTH_REQUIRED_SIMPLE

# Activity log endpoints
READ_ACTIVITY = AUTH_REQUIRED_SIMPLE

# Stats endpoints
READ_STATS = AUTH_REQUIRED_SIMPLE

# Methodology endpoints (documentation)
READ_METHODOLOGY = AUTH_REQUIRED_SIMPLE

# Storage endpoints
READ_STORAGE = AUTH_REQUIRED_SIMPLE
WRITE_STORAGE = AUTH_REQUIRED_SIMPLE

# Admin-only endpoints
ADMIN_ONLY = AUTH_REQUIRED_SIMPLE

# Debug endpoints (admin + debug scope)
DEBUG_ONLY = AUTH_REQUIRED_SIMPLE


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

# For code that imports _auth_dependency directly
_auth_dependency = verify_api_key_simple


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT SECURITY MATRIX (for documentation)
# ═══════════════════════════════════════════════════════════════════════════

ENDPOINT_SECURITY_MATRIX = {
    # Signals API
    "GET /api/v1/signals": "read:signals",
    "GET /api/v1/signals/{id}": "read:signals",
    "GET /api/v1/signals/stats": "read:signals",
    "POST /api/v1/signals/process": "write:signals",
    # Partner Signals API
    "GET /api/v1/partner-signals": "read:partners",
    "GET /api/v1/partner-signals/{symbol}": "read:partners",
    "GET /api/v1/partner-signals/{symbol}/price": "read:partners",
    "GET /api/v1/partner-signals/{symbol}/fundamentals": "read:partners",
    # Multi-Source API
    "GET /api/v1/multi-source/signals": "read:multi-source",
    "POST /api/v1/multi-source/process": "read:multi-source",
    # Real-time API
    "GET /api/v1/realtime/stream": "read:realtime",
    "GET /api/v1/realtime/prices": "read:realtime",
    # Live Data API
    "POST /api/v1/live/process": "write:signals",
    "POST /api/v1/live/process-single": "write:signals",
    # Stats & Activity
    "GET /api/v1/stats": "read:stats",
    "GET /api/v1/activity": "read:activity",
    # Methodology
    "GET /api/v1/methodology": "read:methodology",
    # Storage
    "GET /api/v1/storage/*": "read:storage",
    "POST /api/v1/storage/*": "write:storage",
    # Debug (DEV ONLY)
    "GET /api/v1/debug/*": "debug",
    # Admin
    "POST /api/v1/admin/*": "admin",
}
