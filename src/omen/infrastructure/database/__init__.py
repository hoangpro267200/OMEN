"""Database migration infrastructure."""

from omen.infrastructure.database.migrations import (
    Migration,
    MigrationRunner,
    RISKCAST_MIGRATIONS,
    run_riskcast_migrations,
)
from omen.infrastructure.database.postgres_migrations import (
    PostgresMigration,
    PostgresMigrationRunner,
    run_postgres_migrations,
)

__all__ = [
    # SQLite migrations (RiskCast)
    "Migration",
    "MigrationRunner",
    "RISKCAST_MIGRATIONS",
    "run_riskcast_migrations",
    # PostgreSQL migrations (OMEN persistence)
    "PostgresMigration",
    "PostgresMigrationRunner",
    "run_postgres_migrations",
]
