"""
Signal Event Envelope

Canonical schema for dual-path architecture.
Used by both hot path (webhook) and cold path (ledger).

Schema Version: 1.0.0
"""

from datetime import datetime, timezone
from typing import Optional
import hashlib
import json
import zlib

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .omen_signal import OmenSignal

SCHEMA_VERSION = "1.0.0"


class SignalEvent(BaseModel):
    """
    Signal Event Envelope for dual-path delivery.

    Wraps OmenSignal with:
    - Delivery metadata (timestamps, sequence)
    - Traceability (deterministic IDs)
    - Versioning (schema, ruleset)

    Immutability: Once created, a SignalEvent MUST NOT be modified.
    Updates = new SignalEvent with new signal_id.
    """

    model_config = ConfigDict(frozen=True)

    # === SCHEMA VERSION ===
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Schema version for evolution",
    )

    # === IDENTIFICATION (Immutable) ===
    signal_id: str = Field(
        description="Unique signal identifier (deterministic)",
    )
    deterministic_trace_id: str = Field(
        description="Trace ID for correlation",
    )
    input_event_hash: str = Field(
        description="SHA256 hash of input event",
    )
    source_event_id: str = Field(
        description="Source system event ID",
    )

    # === VERSIONING ===
    ruleset_version: str = Field(
        description="OMEN ruleset version used",
    )

    # === TIMESTAMPS (must be timezone-aware UTC) ===
    observed_at: datetime = Field(
        description="When source data was observed",
    )
    emitted_at: datetime = Field(
        description="When OMEN emitted this signal",
    )
    ledger_written_at: Optional[datetime] = Field(
        default=None,
        description="When written to ledger (set by ledger writer)",
    )

    @field_validator("observed_at", "emitted_at", "ledger_written_at", mode="before")
    @classmethod
    def _require_aware_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if getattr(v, "tzinfo", None) is None:
            raise ValueError("datetime must be timezone-aware (use datetime.now(timezone.utc))")
        return v

    # === SIGNAL PAYLOAD ===
    signal: OmenSignal = Field(
        description="Full OmenSignal payload",
    )

    # === LEDGER METADATA (Set by writer) ===
    ledger_partition: Optional[str] = Field(
        default=None,
        description="Partition date (YYYY-MM-DD)",
    )
    ledger_sequence: Optional[int] = Field(
        default=None,
        description="Sequence number within partition",
    )

    @classmethod
    def from_omen_signal(
        cls,
        signal: OmenSignal,
        input_event_hash: str,
        observed_at: datetime,
    ) -> "SignalEvent":
        """
        Create SignalEvent from OmenSignal.

        Sets emitted_at to current time.
        """
        return cls(
            signal_id=signal.signal_id,
            deterministic_trace_id=signal.trace_id,
            input_event_hash=input_event_hash,
            source_event_id=signal.source_event_id,
            ruleset_version=signal.ruleset_version,
            observed_at=observed_at,
            emitted_at=datetime.now(timezone.utc),
            signal=signal,
        )

    def with_ledger_metadata(
        self,
        partition: str,
        sequence: int,
    ) -> "SignalEvent":
        """
        Return copy with ledger metadata set.

        Called by ledger writer before persisting.
        """
        return self.model_copy(
            update={
                "ledger_partition": partition,
                "ledger_sequence": sequence,
                "ledger_written_at": datetime.now(timezone.utc),
            }
        )


class LedgerRecord(BaseModel):
    """
    Ledger record with integrity checksum.

    Format for JSONL storage:
    {"checksum":"crc32:...","length":1234,"signal":{...}}
    """

    model_config = ConfigDict(frozen=True)

    checksum: str = Field(
        description="CRC32 checksum of signal JSON",
    )
    length: int = Field(
        description="Length of signal JSON in bytes",
    )
    signal: SignalEvent = Field(
        description="Signal event payload",
    )

    @classmethod
    def create(cls, event: SignalEvent) -> "LedgerRecord":
        """
        Create ledger record with checksum.
        """
        signal_json = event.model_dump_json(exclude_none=True)
        checksum = f"crc32:{zlib.crc32(signal_json.encode()):08x}"

        return cls(
            checksum=checksum,
            length=len(signal_json),
            signal=event,
        )

    def verify(self) -> bool:
        """
        Verify record integrity.

        Returns True if checksum matches.
        """
        signal_json = self.signal.model_dump_json(exclude_none=True)
        expected = f"crc32:{zlib.crc32(signal_json.encode()):08x}"
        return self.checksum == expected


def generate_input_event_hash(event_data: dict) -> str:
    """
    Generate deterministic hash of input event.

    Used for:
    - Idempotent signal_id generation
    - Detecting duplicate inputs
    """
    canonical = json.dumps(event_data, sort_keys=True, default=str)
    hash_digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"sha256:{hash_digest}"
