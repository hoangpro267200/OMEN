"""
Input Validation Utilities
==========================

Provides validated query parameters and input sanitization for API endpoints.
All user input should be validated through these utilities to prevent:
- SQL injection
- XSS attacks
- Buffer overflow
- Invalid data types
"""

import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException, status

# ═══════════════════════════════════════════════════════════════════════════
# COMMON VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════

class SignalQueryParams(BaseModel):
    """Validated query parameters for signal endpoints."""
    
    limit: int = Field(default=50, ge=1, le=500, description="Max results to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    category: Optional[str] = Field(default=None, max_length=50, description="Filter by category")
    source: Optional[str] = Field(default=None, max_length=50, description="Filter by source")
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum confidence")
    max_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Maximum confidence")
    
    @field_validator("category", "source", mode="before")
    @classmethod
    def sanitize_string(cls, v):
        if v is None:
            return v
        if not isinstance(v, str):
            return str(v)
        # Remove any potentially dangerous characters
        sanitized = re.sub(r'[<>"\';(){}\\]', '', v)
        return sanitized.strip()[:50]


class SignalIdParam(BaseModel):
    """Validated signal ID parameter."""
    
    signal_id: str = Field(..., min_length=10, max_length=50)
    
    @field_validator("signal_id")
    @classmethod
    def validate_format(cls, v):
        # OMEN signal IDs: OMEN-DEMO###XXXX or OMEN-LIVE###XXXX
        pattern = r'^OMEN-(DEMO|LIVE)\d{3}[A-Z0-9]{4}$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid signal ID format: {v}. Expected format: OMEN-DEMO###XXXX or OMEN-LIVE###XXXX")
        return v


class DateRangeParams(BaseModel):
    """Validated date range parameters."""
    
    start_date: Optional[str] = Field(default=None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(default=None, description="End date (ISO format)")
    
    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return v
        if not isinstance(v, str):
            return str(v)
        # ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
        pattern = r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid date format: {v}. Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ")
        return v


class PaginationParams(BaseModel):
    """Generic pagination parameters."""
    
    page: int = Field(default=1, ge=1, le=10000, description="Page number")
    per_page: int = Field(default=50, ge=1, le=500, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        return self.per_page


# ═══════════════════════════════════════════════════════════════════════════
# REQUEST SIZE LIMITS
# ═══════════════════════════════════════════════════════════════════════════

MAX_REQUEST_SIZE = 1024 * 1024  # 1MB default

def validate_request_size(content_length: Optional[int], max_size: int = MAX_REQUEST_SIZE) -> None:
    """
    Validate request body size.
    
    Raises HTTPException 413 if body exceeds max_size.
    """
    if content_length and content_length > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "request_too_large",
                "message": f"Request body exceeds maximum size of {max_size} bytes",
                "max_size_bytes": max_size,
                "received_bytes": content_length,
            }
        )


# ═══════════════════════════════════════════════════════════════════════════
# SQL INJECTION PREVENTION
# ═══════════════════════════════════════════════════════════════════════════

DANGEROUS_SQL_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
    r"(--|#|/\*|\*/)",
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))",
    r"(\bEXEC\b|\bEXECUTE\b)",
    r"(\bxp_\w+)",
]

def check_sql_injection(value: str) -> bool:
    """
    Check if string contains potential SQL injection patterns.
    
    Returns True if suspicious patterns detected.
    """
    if not value:
        return False
    for pattern in DANGEROUS_SQL_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False


def sanitize_for_query(value: str, field_name: str = "input") -> str:
    """
    Sanitize string for use in queries.
    
    Raises HTTPException 400 if SQL injection detected.
    """
    if check_sql_injection(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_input",
                "message": f"Field '{field_name}' contains invalid characters",
                "field": field_name,
            }
        )
    return value


# ═══════════════════════════════════════════════════════════════════════════
# XSS PREVENTION
# ═══════════════════════════════════════════════════════════════════════════

DANGEROUS_HTML_PATTERNS = [
    r"<script[^>]*>",
    r"</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<embed[^>]*>",
    r"<object[^>]*>",
]

def check_xss(value: str) -> bool:
    """
    Check if string contains potential XSS patterns.
    
    Returns True if suspicious patterns detected.
    """
    if not value:
        return False
    for pattern in DANGEROUS_HTML_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False


def sanitize_html(value: str) -> str:
    """
    Sanitize string by escaping HTML characters.
    """
    if not value:
        return value
    html_escape = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
    }
    for char, escape in html_escape.items():
        value = value.replace(char, escape)
    return value


def validate_safe_string(value: str, field_name: str = "input", max_length: int = 1000) -> str:
    """
    Validate that string is safe (no SQL injection, no XSS).
    
    Raises HTTPException 400 if validation fails.
    """
    if not value:
        return value
        
    if len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "input_too_long",
                "message": f"Field '{field_name}' exceeds maximum length of {max_length}",
                "field": field_name,
                "max_length": max_length,
            }
        )
    
    if check_sql_injection(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_input",
                "message": f"Field '{field_name}' contains invalid characters",
                "field": field_name,
            }
        )
    
    if check_xss(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_input",
                "message": f"Field '{field_name}' contains potentially unsafe content",
                "field": field_name,
            }
        )
    
    return value


# ═══════════════════════════════════════════════════════════════════════════
# API KEY VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_api_key_format(key: str) -> bool:
    """
    Validate API key format.
    
    Valid keys are 16-64 characters, alphanumeric with dashes/underscores.
    """
    if not key:
        return False
    if len(key) < 8 or len(key) > 64:
        return False
    # Allow alphanumeric, dashes, underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, key))


# ═══════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE INPUT VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

class InputValidator:
    """
    Comprehensive input validation with XSS and injection prevention.
    
    Usage:
        validator = InputValidator()
        is_valid, error = validator.validate_input("user input")
        safe_value = validator.sanitize("user input")
    """
    
    # Dangerous patterns
    SQL_PATTERNS = DANGEROUS_SQL_PATTERNS
    XSS_PATTERNS = DANGEROUS_HTML_PATTERNS
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 10000) -> str:
        """
        Sanitize string input.
        
        - Truncates to max length
        - HTML escapes dangerous characters
        - Removes control characters
        """
        if not isinstance(value, str):
            raise ValueError("Expected string input")
        
        # Truncate to max length
        value = value[:max_length]
        
        # Remove control characters
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        
        # HTML escape
        value = sanitize_html(value)
        
        return value
    
    @classmethod
    def validate_no_injection(cls, value: str) -> bool:
        """Check for SQL injection patterns."""
        return not check_sql_injection(value)
    
    @classmethod
    def validate_no_xss(cls, value: str) -> bool:
        """Check for XSS patterns."""
        return not check_xss(value)
    
    @classmethod
    def validate_input(cls, value: any) -> tuple[bool, str]:
        """
        Comprehensive input validation.
        
        Returns:
            (is_valid, error_message)
        """
        if value is None:
            return True, "OK"
        
        if isinstance(value, str):
            if not cls.validate_no_injection(value):
                return False, "Potential SQL injection detected"
            if not cls.validate_no_xss(value):
                return False, "Potential XSS detected"
        elif isinstance(value, (list, dict)):
            # Recursively validate collections
            items = value.values() if isinstance(value, dict) else value
            for item in items:
                is_valid, error = cls.validate_input(item)
                if not is_valid:
                    return is_valid, error
        
        return True, "OK"
    
    @classmethod
    def sanitize(cls, value: any, max_length: int = 10000) -> any:
        """
        Sanitize any value recursively.
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            return cls.sanitize_string(value, max_length)
        elif isinstance(value, dict):
            return {k: cls.sanitize(v, max_length) for k, v in value.items()}
        elif isinstance(value, list):
            return [cls.sanitize(v, max_length) for v in value]
        
        return value


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def clean_string(value: str, allow_spaces: bool = True, max_length: int = 255) -> str:
    """
    Clean and normalize a string value.
    
    - Strips whitespace
    - Removes control characters
    - Normalizes whitespace
    - Truncates to max_length
    """
    if not value:
        return ""
    
    # Remove control characters except newline and tab
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    
    # Normalize whitespace
    if allow_spaces:
        cleaned = re.sub(r'\s+', ' ', cleaned)
    else:
        cleaned = re.sub(r'\s+', '', cleaned)
    
    # Strip and truncate
    return cleaned.strip()[:max_length]
