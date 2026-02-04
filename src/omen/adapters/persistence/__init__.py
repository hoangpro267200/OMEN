"""Persistence adapters."""

from omen.adapters.persistence.in_memory_repository import InMemorySignalRepository
from omen.adapters.persistence.schema_router import (
    Schema,
    GateStatus,
    BlockReason,
    GateCheckResult,
    RoutingDecision,
    SchemaRouter,
    determine_schema,
)
from omen.adapters.persistence.audit_logger import (
    OperationType,
    AuditEntry,
    AuditLogger,
    log_attestation,
)

# Lazy imports for PostgreSQL (requires asyncpg)
def get_postgres_repository():
    """Get PostgresSignalRepository class (lazy import)."""
    from omen.adapters.persistence.postgres_repository import PostgresSignalRepository
    return PostgresSignalRepository


def get_postgres_factories():
    """Get PostgreSQL repository factory functions (lazy import)."""
    from omen.adapters.persistence.postgres_repository import (
        create_postgres_repository,
        create_schema_aware_repository,
    )
    return create_postgres_repository, create_schema_aware_repository


__all__ = [
    # Repositories
    "InMemorySignalRepository",
    "get_postgres_repository",
    "get_postgres_factories",
    # Schema routing
    "Schema",
    "GateStatus",
    "BlockReason",
    "GateCheckResult",
    "RoutingDecision",
    "SchemaRouter",
    "determine_schema",
    # Audit logging
    "OperationType",
    "AuditEntry",
    "AuditLogger",
    "log_attestation",
]
