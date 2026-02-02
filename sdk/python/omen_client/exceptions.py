"""
OMEN SDK Exceptions.

Custom exceptions for OMEN API errors with detailed information.
"""

from __future__ import annotations

from typing import Optional


class OmenError(Exception):
    """Base exception for OMEN SDK."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        return " ".join(parts)


class AuthenticationError(OmenError):
    """
    Raised when authentication fails.
    
    Possible causes:
    - Missing API key
    - Invalid API key
    - Expired API key
    - Revoked API key
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs,
    ):
        super().__init__(message, status_code=401, **kwargs)


class AuthorizationError(OmenError):
    """
    Raised when authorization fails.
    
    Possible causes:
    - Insufficient scopes
    - Resource not accessible
    """
    
    def __init__(
        self,
        message: str = "Access denied",
        required_scopes: Optional[list[str]] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if required_scopes:
            details["required_scopes"] = required_scopes
        super().__init__(message, status_code=403, details=details, **kwargs)


class RateLimitError(OmenError):
    """
    Raised when rate limit is exceeded.
    
    The retry_after attribute indicates when to retry.
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        details["retry_after"] = retry_after
        details["limit"] = limit
        details["remaining"] = remaining
        super().__init__(message, status_code=429, details=details, **kwargs)
        self.retry_after = retry_after


class NotFoundError(OmenError):
    """
    Raised when a resource is not found.
    """
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, status_code=404, details=details, **kwargs)


class ValidationError(OmenError):
    """
    Raised when request validation fails.
    
    The errors attribute contains field-level validation errors.
    """
    
    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[list[dict]] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        details["errors"] = errors or []
        super().__init__(message, status_code=422, details=details, **kwargs)
        self.errors = errors or []


class ServerError(OmenError):
    """
    Raised when the server encounters an error.
    """
    
    def __init__(
        self,
        message: str = "Internal server error",
        **kwargs,
    ):
        super().__init__(message, status_code=500, **kwargs)


class ServiceUnavailableError(OmenError):
    """
    Raised when the service is temporarily unavailable.
    """
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        details["retry_after"] = retry_after
        super().__init__(message, status_code=503, details=details, **kwargs)
        self.retry_after = retry_after


def raise_for_status(response) -> None:
    """
    Raise appropriate exception for HTTP error responses.
    
    Args:
        response: httpx.Response object
    
    Raises:
        OmenError or subclass
    """
    if response.is_success:
        return
    
    status_code = response.status_code
    
    try:
        data = response.json()
        message = data.get("message", data.get("detail", str(data)))
        error_code = data.get("error")
        details = data.get("details", data)
    except Exception:
        message = response.text or f"HTTP {status_code}"
        error_code = None
        details = {}
    
    # Map status codes to exceptions
    if status_code == 401:
        raise AuthenticationError(message, error_code=error_code, details=details)
    elif status_code == 403:
        raise AuthorizationError(message, error_code=error_code, details=details)
    elif status_code == 404:
        raise NotFoundError(message, error_code=error_code, details=details)
    elif status_code == 422:
        raise ValidationError(message, error_code=error_code, details=details)
    elif status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            message,
            retry_after=int(retry_after) if retry_after else None,
            error_code=error_code,
            details=details,
        )
    elif status_code == 503:
        retry_after = response.headers.get("Retry-After")
        raise ServiceUnavailableError(
            message,
            retry_after=int(retry_after) if retry_after else None,
            error_code=error_code,
            details=details,
        )
    elif status_code >= 500:
        raise ServerError(message, status_code=status_code, error_code=error_code, details=details)
    else:
        raise OmenError(message, status_code=status_code, error_code=error_code, details=details)
