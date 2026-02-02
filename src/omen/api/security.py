"""
API Security - Central security configuration for all routes.

This module provides standardized security dependencies for all API routes.
RBAC is enforced at the route level to ensure proper access control.
"""

from __future__ import annotations

from fastapi import Depends
from typing import List

from omen.infrastructure.security.auth import verify_api_key
from omen.infrastructure.security.rbac import (
    Scopes,
    require_scopes,
    require_read_signals,
    require_write_signals,
    require_read_partners,
    require_admin,
)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTE SECURITY CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════════

# Read-only signal endpoints
READ_SIGNALS = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_SIGNALS])),
]

# Write signal endpoints (processing)
WRITE_SIGNALS = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.WRITE_SIGNALS])),
]

# Partner signal read endpoints
READ_PARTNERS = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_PARTNERS])),
]

# Partner signal write endpoints
WRITE_PARTNERS = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.WRITE_PARTNERS])),
]

# Multi-source intelligence endpoints
READ_MULTI_SOURCE = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_MULTI_SOURCE])),
]

# Real-time streaming endpoints
READ_REALTIME = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_REALTIME])),
]

# Activity log endpoints
READ_ACTIVITY = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_ACTIVITY])),
]

# Stats endpoints
READ_STATS = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_STATS])),
]

# Methodology endpoints (documentation)
READ_METHODOLOGY = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_METHODOLOGY])),
]

# Storage endpoints
READ_STORAGE = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.READ_STORAGE])),
]

WRITE_STORAGE = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.WRITE_STORAGE])),
]

# Admin-only endpoints
ADMIN_ONLY = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.ADMIN])),
]

# Debug endpoints (admin + debug scope)
DEBUG_ONLY = [
    Depends(verify_api_key),
    Depends(require_scopes([Scopes.DEBUG])),
]


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
