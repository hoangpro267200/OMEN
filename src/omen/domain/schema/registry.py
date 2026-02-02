"""
Schema Version Registry

Manages schema versions and migrations for SignalEvent.
Supports forward compatibility (read old data) and migration.

NOTE: No logging in domain layer - maintain purity for determinism.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class SchemaVersion(Enum):
    """All known schema versions."""

    V1_0_0 = "1.0.0"
    V1_1_0 = "1.1.0"  # Future: adds severity field
    V1_2_0 = "1.2.0"  # Future: adds impact_score

    @classmethod
    def current(cls) -> "SchemaVersion":
        """Current schema version for new records."""
        return cls.V1_0_0

    @classmethod
    def from_string(cls, version: str) -> "SchemaVersion":
        """Parse version string."""
        for v in cls:
            if v.value == version:
                return v
        raise ValueError(f"Unknown schema version: {version}")

    @classmethod
    def is_supported(cls, version: str) -> bool:
        """Check if version is supported."""
        try:
            cls.from_string(version)
            return True
        except ValueError:
            return False


@dataclass
class SchemaMigration:
    """Definition of a schema migration."""

    from_version: SchemaVersion
    to_version: SchemaVersion
    migrate_func: Callable[[dict], dict]
    description: str


class SchemaRegistry:
    """
    Registry of schema versions and migrations.

    Usage:
        registry = SchemaRegistry()
        migrated_data = registry.migrate(old_data, target_version)
    """

    def __init__(self) -> None:
        self._migrations: list[SchemaMigration] = []
        self._register_default_migrations()

    def _register_default_migrations(self) -> None:
        """Register built-in migrations."""
        # 1.0.0 -> 1.1.0: Add severity field
        self.register_migration(
            from_version=SchemaVersion.V1_0_0,
            to_version=SchemaVersion.V1_1_0,
            migrate_func=self._migrate_1_0_0_to_1_1_0,
            description="Add severity field with default MEDIUM",
        )

        # 1.1.0 -> 1.2.0: Add impact_score field
        self.register_migration(
            from_version=SchemaVersion.V1_1_0,
            to_version=SchemaVersion.V1_2_0,
            migrate_func=self._migrate_1_1_0_to_1_2_0,
            description="Add impact_score derived from probability",
        )

    def register_migration(
        self,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
        migrate_func: Callable[[dict], dict],
        description: str = "",
    ) -> None:
        """Register a migration path."""
        self._migrations.append(
            SchemaMigration(
                from_version=from_version,
                to_version=to_version,
                migrate_func=migrate_func,
                description=description,
            )
        )
        # Migration registered (no logging in domain layer)

    def migrate(
        self,
        data: dict,
        target_version: SchemaVersion | None = None,
    ) -> dict:
        """
        Migrate data to target version.

        Args:
            data: Record data with schema_version field
            target_version: Target version (default: current)

        Returns:
            Migrated data with updated schema_version
        """
        target = target_version or SchemaVersion.current()

        current_version_str = data.get("schema_version", "1.0.0")
        try:
            current = SchemaVersion.from_string(current_version_str)
        except ValueError:
            # Unknown schema version, default to 1.0.0 (no logging in domain)
            current = SchemaVersion.V1_0_0

        if current == target:
            return data

        # Find and apply migration path
        path = self._find_migration_path(current, target)

        result = dict(data)
        for migration in path:
            # Apply migration (no logging in domain layer)
            result = migration.migrate_func(result)
            result["schema_version"] = migration.to_version.value

        return result

    def _find_migration_path(
        self,
        from_v: SchemaVersion,
        to_v: SchemaVersion,
    ) -> list[SchemaMigration]:
        """Find sequence of migrations."""
        path: list[SchemaMigration] = []
        current = from_v

        while current != to_v:
            migration = next(
                (m for m in self._migrations if m.from_version == current),
                None,
            )
            if not migration:
                raise ValueError(f"No migration path from {current.value} to {to_v.value}")
            path.append(migration)
            current = migration.to_version

        return path

    # ─────────────────────────────────────────────────────────────────────────
    # Migration Functions
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _migrate_1_0_0_to_1_1_0(data: dict) -> dict:
        """Add severity field based on probability."""
        result = dict(data)

        if "signal" in result:
            signal = dict(result["signal"])
            probability = signal.get("probability", 0.5)

            if probability >= 0.8:
                signal["severity"] = "CRITICAL"
            elif probability >= 0.6:
                signal["severity"] = "HIGH"
            elif probability >= 0.4:
                signal["severity"] = "MEDIUM"
            else:
                signal["severity"] = "LOW"

            result["signal"] = signal

        return result

    @staticmethod
    def _migrate_1_1_0_to_1_2_0(data: dict) -> dict:
        """Add impact_score field."""
        result = dict(data)

        if "signal" in result:
            signal = dict(result["signal"])
            probability = signal.get("probability", 0.5)
            confidence = signal.get("confidence_score", 0.5)
            signal["impact_score"] = round(probability * confidence, 3)
            result["signal"] = signal

        return result


# Global registry instance
SCHEMA_REGISTRY = SchemaRegistry()
