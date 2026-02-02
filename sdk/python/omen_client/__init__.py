"""
OMEN Python SDK

Official Python client for the OMEN Signal Intelligence API.

Installation:
    pip install omen-client

Quick Start:
    >>> from omen_client import OmenClient
    >>> client = OmenClient(api_key="your-api-key")
    >>> signals = client.partner_signals.list()
    >>> for partner in signals.partners:
    ...     print(f"{partner.symbol}: {partner.signals.price_change_percent}%")
"""

from .client import OmenClient, AsyncOmenClient
from .models import (
    PartnerSignalMetrics,
    PartnerSignalConfidence,
    PartnerSignalEvidence,
    PartnerSignalResponse,
    PartnerSignalsListResponse,
    OmenSignal,
    SignalType,
    ConfidenceLevel,
)
from .exceptions import (
    OmenError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError,
)

__version__ = "2.0.0"
__all__ = [
    # Client
    "OmenClient",
    "AsyncOmenClient",
    # Models
    "PartnerSignalMetrics",
    "PartnerSignalConfidence",
    "PartnerSignalEvidence",
    "PartnerSignalResponse",
    "PartnerSignalsListResponse",
    "OmenSignal",
    "SignalType",
    "ConfidenceLevel",
    # Exceptions
    "OmenError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
]
