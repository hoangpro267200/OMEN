"""
Audit Logger for OMEN Persistence Layer.

Logs all database write operations to the audit.operation_log table.
This provides an immutable audit trail for compliance and debugging.

IMPORTANT:
- All INSERT/UPDATE/DELETE operations MUST be logged
- The audit schema has triggers preventing UPDATE/DELETE
- Logs include old/new values for change tracking
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Type of database operation."""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UPSERT = "UPSERT"


@dataclass
class AuditEntry:
    """
    Audit log entry for a database operation.

    This is logged to audit.operation_log for every write operation.
    """

    # Entry identification
    id: UUID = field(default_factory=uuid4)
    operation_id: str = ""  # Unique ID for this operation

    # Request context
    trace_id: Optional[str] = None
    request_id: Optional[str] = None

    # Operation details
    operation_type: OperationType = OperationType.INSERT
    target_schema: str = "demo"
    target_table: str = "signals"
    target_id: Optional[str] = None  # Primary key of affected row

    # Actor information
    performed_by: Optional[str] = None  # API key hash or system identifier
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None

    # Change details
    old_value: Optional[dict] = None  # For UPDATE/DELETE
    new_value: Optional[dict] = None  # For INSERT/UPDATE

    # Attestation link
    attestation_id: Optional[UUID] = None
    source_type: Optional[str] = None  # REAL, MOCK, HYBRID

    # Metadata
    reason: Optional[str] = None
    metadata: Optional[dict] = None

    # Timestamp
    logged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Generate operation_id if not provided."""
        if not self.operation_id:
            self.operation_id = f"op_{self.id.hex[:12]}"

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": str(self.id),
            "operation_id": self.operation_id,
            "trace_id": self.trace_id,
            "operation_type": self.operation_type.value,
            "target_schema": self.target_schema,
            "target_table": self.target_table,
            "target_id": self.target_id,
            "performed_by": self.performed_by,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "attestation_id": str(self.attestation_id) if self.attestation_id else None,
            "source_type": self.source_type,
            "reason": self.reason,
            "metadata": self.metadata,
            "logged_at": self.logged_at.isoformat(),
        }


class AuditLogger:
    """
    Logs database operations to the audit schema.

    Usage:
        async with pool.acquire() as conn:
            audit_logger = AuditLogger(conn)
            await audit_logger.log_insert(
                schema="demo",
                table="signals",
                record_id="sig_123",
                new_value=signal.to_dict(),
                attestation_id=attestation.id,
            )
    """

    def __init__(self, connection):
        """
        Initialize audit logger.

        Args:
            connection: asyncpg connection (not pool)
        """
        self._conn = connection

    async def log_insert(
        self,
        schema: str,
        table: str,
        record_id: str,
        new_value: dict,
        attestation_id: Optional[UUID] = None,
        source_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        performed_by: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEntry:
        """
        Log an INSERT operation.

        Args:
            schema: Target schema (demo, live)
            table: Target table name
            record_id: Primary key of inserted row
            new_value: The inserted record data
            attestation_id: Link to source attestation
            source_type: REAL, MOCK, or HYBRID
            trace_id: Request trace ID
            performed_by: Who performed the operation
            reason: Why the operation was performed
            metadata: Additional metadata

        Returns:
            AuditEntry that was logged
        """
        entry = AuditEntry(
            operation_type=OperationType.INSERT,
            target_schema=schema,
            target_table=table,
            target_id=record_id,
            new_value=new_value,
            attestation_id=attestation_id,
            source_type=source_type,
            trace_id=trace_id,
            performed_by=performed_by or "system",
            reason=reason or "Signal ingestion",
            metadata=metadata,
        )
        await self._write_entry(entry)
        return entry

    async def log_update(
        self,
        schema: str,
        table: str,
        record_id: str,
        old_value: dict,
        new_value: dict,
        trace_id: Optional[str] = None,
        performed_by: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEntry:
        """
        Log an UPDATE operation.

        Args:
            schema: Target schema (demo, live)
            table: Target table name
            record_id: Primary key of updated row
            old_value: Previous record state
            new_value: New record state
            trace_id: Request trace ID
            performed_by: Who performed the operation
            reason: Why the operation was performed
            metadata: Additional metadata

        Returns:
            AuditEntry that was logged
        """
        entry = AuditEntry(
            operation_type=OperationType.UPDATE,
            target_schema=schema,
            target_table=table,
            target_id=record_id,
            old_value=old_value,
            new_value=new_value,
            trace_id=trace_id,
            performed_by=performed_by or "system",
            reason=reason or "Signal update",
            metadata=metadata,
        )
        await self._write_entry(entry)
        return entry

    async def log_upsert(
        self,
        schema: str,
        table: str,
        record_id: str,
        new_value: dict,
        old_value: Optional[dict] = None,
        attestation_id: Optional[UUID] = None,
        source_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        performed_by: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEntry:
        """
        Log an UPSERT operation.

        Args:
            schema: Target schema (demo, live)
            table: Target table name
            record_id: Primary key of affected row
            new_value: The new/updated record data
            old_value: Previous record state (if update)
            attestation_id: Link to source attestation
            source_type: REAL, MOCK, or HYBRID
            trace_id: Request trace ID
            performed_by: Who performed the operation
            reason: Why the operation was performed
            metadata: Additional metadata

        Returns:
            AuditEntry that was logged
        """
        entry = AuditEntry(
            operation_type=OperationType.UPSERT,
            target_schema=schema,
            target_table=table,
            target_id=record_id,
            old_value=old_value,
            new_value=new_value,
            attestation_id=attestation_id,
            source_type=source_type,
            trace_id=trace_id,
            performed_by=performed_by or "system",
            reason=reason or "Signal upsert",
            metadata=metadata,
        )
        await self._write_entry(entry)
        return entry

    async def log_delete(
        self,
        schema: str,
        table: str,
        record_id: str,
        old_value: dict,
        trace_id: Optional[str] = None,
        performed_by: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEntry:
        """
        Log a DELETE operation.

        Args:
            schema: Target schema (demo, live)
            table: Target table name
            record_id: Primary key of deleted row
            old_value: The deleted record data
            trace_id: Request trace ID
            performed_by: Who performed the operation
            reason: Why the operation was performed
            metadata: Additional metadata

        Returns:
            AuditEntry that was logged
        """
        entry = AuditEntry(
            operation_type=OperationType.DELETE,
            target_schema=schema,
            target_table=table,
            target_id=record_id,
            old_value=old_value,
            trace_id=trace_id,
            performed_by=performed_by or "system",
            reason=reason or "Signal deletion",
            metadata=metadata,
        )
        await self._write_entry(entry)
        return entry

    async def _write_entry(self, entry: AuditEntry) -> None:
        """
        Write audit entry to database.

        This inserts into audit.operation_log which is protected
        by triggers that prevent UPDATE/DELETE.
        """
        try:
            await self._conn.execute(
                """
                INSERT INTO audit.operation_log (
                    id, operation_id, trace_id, operation_type,
                    target_schema, target_table, target_id,
                    performed_by, source_ip, user_agent,
                    old_value, new_value,
                    attestation_id, source_type,
                    reason, metadata, logged_at
                ) VALUES (
                    $1, $2, $3, $4::operation_type,
                    $5, $6, $7,
                    $8, $9, $10,
                    $11, $12,
                    $13, $14::source_type,
                    $15, $16, $17
                )
                """,
                entry.id,
                entry.operation_id,
                entry.trace_id,
                entry.operation_type.value,
                entry.target_schema,
                entry.target_table,
                entry.target_id,
                entry.performed_by,
                entry.source_ip,
                entry.user_agent,
                json.dumps(entry.old_value) if entry.old_value else None,
                json.dumps(entry.new_value) if entry.new_value else None,
                entry.attestation_id,
                entry.source_type,
                entry.reason,
                json.dumps(entry.metadata) if entry.metadata else None,
                entry.logged_at,
            )
            logger.debug(
                "Audit log: %s %s.%s id=%s",
                entry.operation_type.value,
                entry.target_schema,
                entry.target_table,
                entry.target_id,
            )
        except Exception as e:
            # Log error but don't fail the main operation
            # Audit logging should not block business operations
            logger.error(
                "Failed to write audit log: %s (operation: %s %s.%s)",
                e,
                entry.operation_type.value,
                entry.target_schema,
                entry.target_table,
            )
            # Re-raise in development for visibility
            import os
            if os.environ.get("OMEN_ENV") == "development":
                raise


async def log_attestation(
    connection,
    attestation,
) -> None:
    """
    Log a source attestation to audit.source_attestations.

    This is separate from operation_log and specifically tracks
    how signals were classified (REAL/MOCK/HYBRID).

    Args:
        connection: asyncpg connection
        attestation: SignalAttestation to log
    """
    try:
        await connection.execute(
            """
            INSERT INTO audit.source_attestations (
                id, signal_id, source_id,
                source_type, verification_method,
                api_response_hash, raw_response_sample,
                determination_reason, confidence,
                attested_by, attested_at
            ) VALUES (
                $1, $2, $3,
                $4::source_type, $5::verification_method,
                $6, $7,
                $8, $9,
                $10, $11
            )
            ON CONFLICT (signal_id) DO NOTHING
            """,
            attestation.id,
            attestation.signal_id,
            attestation.source_id,
            attestation.source_type.value,
            attestation.verification_method.value,
            attestation.api_response_hash,
            attestation.raw_response_sample,
            attestation.determination_reason,
            attestation.confidence,
            attestation.attested_by,
            attestation.attested_at,
        )
        logger.debug(
            "Logged attestation for signal %s: %s",
            attestation.signal_id,
            attestation.source_type.value,
        )
    except Exception as e:
        logger.error(
            "Failed to log attestation for signal %s: %s",
            attestation.signal_id,
            e,
        )
        raise
