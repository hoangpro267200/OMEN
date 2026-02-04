"""
Source Attestation Models for OMEN Persistence Layer.

These models track the provenance and verification status of signals,
ensuring proper schema routing (demo vs live) based on data source type.

ARCHITECTURAL NOTE:
- Every signal MUST have an attestation before storage
- REAL attestation requires api_response_hash for verification
- MOCK signals are automatically attested based on source registry
- HYBRID signals combine REAL and MOCK inputs (treated as MOCK for routing)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from omen.application.ports.time_provider import utc_now


class SourceType(str, Enum):
    """
    Classification of data source authenticity.

    REAL: Data from verified live API with response hash
    MOCK: Simulated/demo data from mock sources
    HYBRID: Signal derived from mix of REAL and MOCK inputs
    """

    REAL = "REAL"
    MOCK = "MOCK"
    HYBRID = "HYBRID"


class VerificationMethod(str, Enum):
    """
    Method used to verify source authenticity.

    For REAL sources: API_RESPONSE_HASH, CERTIFICATE_CHAIN, SIGNATURE_VERIFICATION
    For MOCK sources: MOCK_SOURCE_REGISTRY
    For overrides: MANUAL_OVERRIDE (requires audit justification)
    """

    API_RESPONSE_HASH = "API_RESPONSE_HASH"
    CERTIFICATE_CHAIN = "CERTIFICATE_CHAIN"
    SIGNATURE_VERIFICATION = "SIGNATURE_VERIFICATION"
    TIMESTAMP_VALIDATION = "TIMESTAMP_VALIDATION"
    MOCK_SOURCE_REGISTRY = "MOCK_SOURCE_REGISTRY"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class AttestationStatus(str, Enum):
    """Status of the attestation process."""

    PENDING = "PENDING"  # Not yet attested
    VERIFIED = "VERIFIED"  # Successfully verified
    FAILED = "FAILED"  # Verification failed
    EXPIRED = "EXPIRED"  # Attestation too old (requires re-verification)


@dataclass(frozen=True)
class SignalAttestation:
    """
    Attestation record for a signal's data source.

    This is the core model that determines which schema (demo/live)
    receives a signal and provides the audit trail for data provenance.

    Usage:
        # For REAL sources (requires hash)
        attestation = SignalAttestation.create_real(
            signal_id="sig_123",
            source_id="polymarket",
            api_response_hash="abc123...",
        )

        # For MOCK sources
        attestation = SignalAttestation.create_mock(
            signal_id="sig_456",
            source_id="ais_mock",
        )
    """

    # Attestation identification
    id: UUID = field(default_factory=uuid4)

    # What was attested
    signal_id: str = ""
    source_id: str = ""

    # Attestation result
    source_type: SourceType = SourceType.MOCK
    verification_method: VerificationMethod = VerificationMethod.MOCK_SOURCE_REGISTRY
    status: AttestationStatus = AttestationStatus.PENDING

    # Verification evidence (required for REAL)
    api_response_hash: Optional[str] = None
    certificate_chain: Optional[dict] = None
    raw_response_sample: Optional[str] = None  # First 1000 chars for debugging

    # Determination details
    determination_reason: str = ""
    confidence: float = 1.0  # 0.0 - 1.0

    # Metadata
    attested_by: str = "system"  # System identifier or user
    attested_at: datetime = field(default_factory=lambda: utc_now())

    # Input sources (for HYBRID tracking)
    input_source_ids: list[str] = field(default_factory=list)
    input_source_types: list[SourceType] = field(default_factory=list)

    def __post_init__(self):
        """Validate attestation consistency."""
        if self.source_type == SourceType.REAL:
            if not self.api_response_hash:
                raise ValueError(
                    "REAL attestation requires api_response_hash for verification"
                )
            if self.verification_method == VerificationMethod.MOCK_SOURCE_REGISTRY:
                raise ValueError(
                    "REAL attestation cannot use MOCK_SOURCE_REGISTRY verification"
                )

    @classmethod
    def create_real(
        cls,
        signal_id: str,
        source_id: str,
        api_response_hash: str,
        verification_method: VerificationMethod = VerificationMethod.API_RESPONSE_HASH,
        raw_response_sample: Optional[str] = None,
        attested_by: str = "system",
    ) -> SignalAttestation:
        """
        Create attestation for a REAL data source.

        Args:
            signal_id: ID of the signal being attested
            source_id: ID of the data source (e.g., "polymarket")
            api_response_hash: SHA256 hash of the raw API response
            verification_method: How the source was verified
            raw_response_sample: Optional sample for debugging
            attested_by: Who/what performed the attestation

        Returns:
            SignalAttestation with REAL source type
        """
        return cls(
            signal_id=signal_id,
            source_id=source_id,
            source_type=SourceType.REAL,
            verification_method=verification_method,
            status=AttestationStatus.VERIFIED,
            api_response_hash=api_response_hash,
            raw_response_sample=raw_response_sample[:1000] if raw_response_sample else None,
            determination_reason=f"Verified via {verification_method.value} from source {source_id}",
            confidence=1.0,
            attested_by=attested_by,
        )

    @classmethod
    def create_mock(
        cls,
        signal_id: str,
        source_id: str,
        attested_by: str = "system",
    ) -> SignalAttestation:
        """
        Create attestation for a MOCK data source.

        Args:
            signal_id: ID of the signal being attested
            source_id: ID of the mock source (e.g., "ais_mock")
            attested_by: Who/what performed the attestation

        Returns:
            SignalAttestation with MOCK source type
        """
        return cls(
            signal_id=signal_id,
            source_id=source_id,
            source_type=SourceType.MOCK,
            verification_method=VerificationMethod.MOCK_SOURCE_REGISTRY,
            status=AttestationStatus.VERIFIED,
            determination_reason=f"Source {source_id} is registered as MOCK in source registry",
            confidence=1.0,
            attested_by=attested_by,
        )

    @classmethod
    def create_hybrid(
        cls,
        signal_id: str,
        input_attestations: list[SignalAttestation],
        attested_by: str = "system",
    ) -> SignalAttestation:
        """
        Create attestation for a signal derived from multiple sources.

        A HYBRID signal combines inputs from both REAL and MOCK sources.
        For routing purposes, HYBRID is treated as MOCK (cannot go to live schema).

        Args:
            signal_id: ID of the signal being attested
            input_attestations: Attestations of the input signals
            attested_by: Who/what performed the attestation

        Returns:
            SignalAttestation with HYBRID source type
        """
        input_source_ids = [a.source_id for a in input_attestations]
        input_source_types = [a.source_type for a in input_attestations]

        # Calculate confidence as minimum of inputs
        min_confidence = min((a.confidence for a in input_attestations), default=1.0)

        # Determine if truly hybrid or all same type
        unique_types = set(input_source_types)
        if len(unique_types) == 1:
            # All same type - use that type
            source_type = unique_types.pop()
            reason = f"All {len(input_attestations)} inputs are {source_type.value}"
        else:
            # Mixed - mark as HYBRID
            source_type = SourceType.HYBRID
            real_count = sum(1 for t in input_source_types if t == SourceType.REAL)
            mock_count = sum(1 for t in input_source_types if t == SourceType.MOCK)
            reason = f"Mixed inputs: {real_count} REAL, {mock_count} MOCK"

        return cls(
            signal_id=signal_id,
            source_id="hybrid",
            source_type=source_type,
            verification_method=VerificationMethod.TIMESTAMP_VALIDATION,
            status=AttestationStatus.VERIFIED,
            determination_reason=reason,
            confidence=min_confidence,
            attested_by=attested_by,
            input_source_ids=input_source_ids,
            input_source_types=input_source_types,
        )

    def is_live_eligible(self) -> bool:
        """
        Check if this attestation allows routing to live schema.

        Only REAL sources with VERIFIED status can go to live.
        MOCK and HYBRID are always routed to demo.
        """
        return (
            self.source_type == SourceType.REAL
            and self.status == AttestationStatus.VERIFIED
            and self.api_response_hash is not None
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "signal_id": self.signal_id,
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "verification_method": self.verification_method.value,
            "status": self.status.value,
            "api_response_hash": self.api_response_hash,
            "determination_reason": self.determination_reason,
            "confidence": self.confidence,
            "attested_by": self.attested_by,
            "attested_at": self.attested_at.isoformat(),
            "input_source_ids": self.input_source_ids,
            "input_source_types": [t.value for t in self.input_source_types],
        }


@dataclass(frozen=True)
class AttestationVerification:
    """Result of verifying an existing attestation."""

    attestation_id: UUID
    signal_id: str
    is_valid: bool
    verification_time: datetime = field(default_factory=lambda: utc_now())
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "attestation_id": str(self.attestation_id),
            "signal_id": self.signal_id,
            "is_valid": self.is_valid,
            "verification_time": self.verification_time.isoformat(),
            "errors": self.errors,
            "warnings": self.warnings,
        }


class AttestationError(Exception):
    """Raised when attestation cannot be completed."""

    def __init__(self, message: str, signal_id: Optional[str] = None):
        self.message = message
        self.signal_id = signal_id
        super().__init__(message)
