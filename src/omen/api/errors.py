"""
Standardized API Error Handling.

All errors follow a consistent format for better client experience.

Error Response Format:
{
    "error": "ERROR_CODE",           # Machine-readable error code
    "message": "Human readable...",  # User-friendly message
    "error_code": "ERR_4XX_XXX",     # Specific error code for documentation
    "details": [...],                # Field-level errors (validation)
    "hint": "Helpful suggestion",    # How to fix the issue
    "documentation_url": "...",      # Link to relevant docs
    "timestamp": "2025-01-01T...",   # When the error occurred
    "request_id": "..."              # Trace ID for debugging
}
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Environment
OMEN_ENV = os.getenv("OMEN_ENV", "development")
IS_PRODUCTION = OMEN_ENV == "production"


class ErrorDetail(BaseModel):
    """Standard error detail for field-level errors."""
    
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class APIError(BaseModel):
    """
    Standard API Error Response.
    
    All API errors follow this format for consistency.
    """
    
    # Required fields
    error: str = Field(..., description="Error code (e.g., VALIDATION_ERROR, NOT_FOUND)")
    message: str = Field(..., description="Human-readable error message")
    
    # Optional fields
    error_code: Optional[str] = Field(None, description="Specific error code (e.g., ERR_400_001)")
    details: Optional[List[ErrorDetail]] = Field(None, description="Field-level errors")
    hint: Optional[str] = Field(None, description="Helpful suggestion to fix the issue")
    documentation_url: Optional[str] = Field(None, description="Link to documentation")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class OmenHTTPException(HTTPException):
    """
    Custom HTTP Exception with standardized format.
    
    Usage:
        raise OmenHTTPException(
            status_code=404,
            error="NOT_FOUND",
            message="Signal 'abc-123' not found",
            hint="Check if the signal ID is correct",
        )
    """
    
    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        hint: Optional[str] = None,
    ):
        self.error = error
        self.message = message
        self.error_code = error_code
        self.details = details
        self.hint = hint
        
        # Build detail dict for parent HTTPException
        detail_dict = APIError(
            error=error,
            message=message,
            error_code=error_code,
            details=[ErrorDetail(**d) for d in details] if details else None,
            hint=hint,
            documentation_url=f"https://docs.omen.io/api/errors#{error.lower().replace('_', '-')}",
        ).model_dump(mode="json")
        
        super().__init__(status_code=status_code, detail=detail_dict)


# ═══════════════════════════════════════════════════════════════════════════════
# COMMON ERROR FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def not_found(resource: str, identifier: str) -> OmenHTTPException:
    """Resource not found error."""
    return OmenHTTPException(
        status_code=404,
        error="NOT_FOUND",
        message=f"{resource} '{identifier}' not found",
        error_code="ERR_404_001",
        hint=f"Verify the {resource.lower()} ID is correct and exists",
    )


def bad_request(
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
    hint: Optional[str] = None,
) -> OmenHTTPException:
    """Bad request error."""
    return OmenHTTPException(
        status_code=400,
        error="BAD_REQUEST",
        message=message,
        error_code="ERR_400_001",
        details=details,
        hint=hint,
    )


def unauthorized(message: str = "Authentication required") -> OmenHTTPException:
    """Unauthorized error."""
    return OmenHTTPException(
        status_code=401,
        error="AUTHENTICATION_REQUIRED",
        message=message,
        error_code="ERR_401_001",
        hint="Include X-API-Key header with a valid API key",
    )


def invalid_api_key(message: str = "Invalid API key") -> OmenHTTPException:
    """Invalid API key error."""
    return OmenHTTPException(
        status_code=401,
        error="INVALID_API_KEY",
        message=message,
        error_code="ERR_401_002",
        hint="Verify your API key is correct and not expired",
    )


def forbidden(
    message: str = "Insufficient permissions",
    required_scopes: Optional[List[str]] = None,
    missing_scopes: Optional[List[str]] = None,
    your_scopes: Optional[List[str]] = None,
) -> OmenHTTPException:
    """Forbidden error."""
    details = None
    if required_scopes or missing_scopes:
        details = []
        if required_scopes:
            details.append({
                "field": "required_scopes",
                "message": f"Required: {', '.join(required_scopes)}",
            })
        if missing_scopes:
            details.append({
                "field": "missing_scopes",
                "message": f"Missing: {', '.join(missing_scopes)}",
            })
        if your_scopes:
            details.append({
                "field": "your_scopes",
                "message": f"You have: {', '.join(your_scopes)}",
            })
    
    return OmenHTTPException(
        status_code=403,
        error="INSUFFICIENT_PERMISSIONS",
        message=message,
        error_code="ERR_403_001",
        details=details,
        hint="Contact your administrator to request additional scopes",
    )


def rate_limited(retry_after: int) -> OmenHTTPException:
    """Rate limit exceeded error."""
    return OmenHTTPException(
        status_code=429,
        error="RATE_LIMITED",
        message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
        error_code="ERR_429_001",
        hint=f"Wait {retry_after} seconds before retrying",
    )


def service_unavailable(
    service: str = "Service",
    message: Optional[str] = None,
) -> OmenHTTPException:
    """Service unavailable error."""
    return OmenHTTPException(
        status_code=503,
        error="SERVICE_UNAVAILABLE",
        message=message or f"{service} is temporarily unavailable",
        error_code="ERR_503_001",
        hint="Try again in a few moments",
    )


def internal_error(
    message: str = "An internal error occurred",
    include_trace: bool = False,
) -> OmenHTTPException:
    """Internal server error."""
    details = None
    if include_trace and not IS_PRODUCTION:
        details = [{"field": "traceback", "message": traceback.format_exc()}]
    
    return OmenHTTPException(
        status_code=500,
        error="INTERNAL_ERROR",
        message=message,
        error_code="ERR_500_001",
        details=details,
        hint="If this persists, contact support with the request_id",
    )


def conflict(
    resource: str,
    identifier: str,
    reason: str = "already exists",
) -> OmenHTTPException:
    """Conflict error (duplicate, etc.)."""
    return OmenHTTPException(
        status_code=409,
        error="CONFLICT",
        message=f"{resource} '{identifier}' {reason}",
        error_code="ERR_409_001",
        hint=f"The {resource.lower()} may already exist or be in a conflicting state",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def omen_exception_handler(
    request: Request,
    exc: OmenHTTPException,
) -> JSONResponse:
    """Handle OmenHTTPException."""
    error_response = exc.detail
    
    # Add request_id if available
    if hasattr(request.state, "request_id"):
        error_response["request_id"] = request.state.request_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
        headers={"X-Error-Code": exc.error_code or exc.error},
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    details = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        details.append(ErrorDetail(
            field=field_path,
            message=error["msg"],
            code=error["type"],
        ))
    
    error_response = APIError(
        error="VALIDATION_ERROR",
        message="Request validation failed",
        error_code="ERR_422_001",
        details=details,
        hint="Check the request body and query parameters match the expected format",
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(mode="json")
    
    return JSONResponse(
        status_code=422,
        content=error_response,
        headers={"X-Error-Code": "ERR_422_001"},
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle standard HTTPException with our format."""
    # If it's already our format, pass through
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
        if hasattr(request.state, "request_id"):
            content["request_id"] = request.state.request_id
        return JSONResponse(status_code=exc.status_code, content=content)
    
    # Convert to our format
    error_code = f"ERR_{exc.status_code}_000"
    error_type = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_REQUIRED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }.get(exc.status_code, "ERROR")
    
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    
    error_response = APIError(
        error=error_type,
        message=message,
        error_code=error_code,
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(mode="json")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle uncaught exceptions."""
    # Log the full error
    logger.exception("Unhandled exception: %s", exc)
    
    # Don't expose details in production
    if IS_PRODUCTION:
        message = "An unexpected error occurred"
        details = None
    else:
        message = f"{type(exc).__name__}: {exc}"
        details = [ErrorDetail(
            field="traceback",
            message=traceback.format_exc(),
        )]
    
    error_response = APIError(
        error="INTERNAL_ERROR",
        message=message,
        error_code="ERR_500_000",
        details=details,
        hint="If this persists, contact support with the request_id",
        request_id=getattr(request.state, "request_id", None),
    ).model_dump(mode="json")
    
    return JSONResponse(
        status_code=500,
        content=error_response,
    )


def register_error_handlers(app) -> None:
    """
    Register all error handlers with the FastAPI app.
    
    Usage:
        from omen.api.errors import register_error_handlers
        register_error_handlers(app)
    """
    from fastapi import HTTPException as FastAPIHTTPException
    
    app.add_exception_handler(OmenHTTPException, omen_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
