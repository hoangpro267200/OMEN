"""Security configuration, auth, rate limiting, validation, and audit.

NOTE: rbac_enforcement module was removed (deprecated).
Use unified_auth for all authentication and authorization needs.
"""

from omen.infrastructure.security.config import SecurityConfig, get_security_config
from omen.infrastructure.security.unified_auth import (
    AuthConfig,
    AuthContext,
    require_auth,
    verify_api_key,
)
from omen.infrastructure.security.enhanced_audit import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    EnhancedAuditLogger,
    get_audit_logger,
    audit_auth_success,
    audit_auth_failure,
    audit_access_denied,
    audit_security_alert,
)

__all__ = [
    # Config
    "SecurityConfig",
    "get_security_config",
    # Auth
    "AuthConfig",
    "AuthContext",
    "require_auth",
    "verify_api_key",
    # Audit
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "EnhancedAuditLogger",
    "get_audit_logger",
    "audit_auth_success",
    "audit_auth_failure",
    "audit_access_denied",
    "audit_security_alert",
]
