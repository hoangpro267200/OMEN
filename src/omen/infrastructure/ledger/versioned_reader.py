"""
Versioned Ledger Reader

Reads ledger records and automatically migrates to current schema.
"""

import logging

from omen.domain.models.signal_event import SignalEvent
from omen.domain.schema.registry import SCHEMA_REGISTRY, SchemaVersion
from omen.infrastructure.ledger.reader import LedgerReader

logger = logging.getLogger(__name__)


class VersionedLedgerReader:
    """
    Wrapper around LedgerReader that handles schema migration.
    """

    def __init__(self, reader: LedgerReader) -> None:
        self._reader = reader

    def read_partition(
        self,
        partition_date: str,
        include_late: bool = True,
        migrate_to_current: bool = True,
        validate: bool = True,
    ) -> list[SignalEvent]:
        """
        Read partition with optional migration.

        Args:
            partition_date: Partition to read
            include_late: Include late partition
            migrate_to_current: Migrate old schemas to current
            validate: If True, verify CRC (passed to underlying reader)

        Returns:
            List of SignalEvent (migrated if requested)
        """
        events = list(
            self._reader.read_partition(
                partition_date,
                validate=validate,
                include_late=include_late,
            )
        )

        if not migrate_to_current:
            return events

        migrated: list[SignalEvent] = []
        for event in events:
            try:
                migrated_event = self._migrate_event(event)
                migrated.append(migrated_event)
            except Exception as e:
                logger.warning(
                    "Failed to migrate event %s: %s",
                    event.signal_id,
                    e,
                )
                migrated.append(event)

        return migrated

    def _migrate_event(self, event: SignalEvent) -> SignalEvent:
        """Migrate a single event to current schema."""
        data = event.model_dump(mode="json")
        migrated_data = SCHEMA_REGISTRY.migrate(data)
        return SignalEvent.model_validate(migrated_data)

    def read_partition_raw(
        self,
        partition_date: str,
        include_late: bool = True,
    ) -> list[dict]:
        """
        Read partition as raw dicts without migration.
        Useful for debugging or custom processing.
        """
        events = list(
            self._reader.read_partition(
                partition_date,
                validate=False,
                include_late=include_late,
            )
        )
        return [e.model_dump(mode="json") for e in events]

    def get_schema_versions(
        self,
        partition_date: str,
        include_late: bool = True,
    ) -> dict[str, int]:
        """
        Get count of records by schema version in partition.
        Useful for migration planning.
        """
        events = list(
            self._reader.read_partition(
                partition_date,
                validate=False,
                include_late=include_late,
            )
        )
        versions: dict[str, int] = {}
        for event in events:
            version = event.schema_version
            versions[version] = versions.get(version, 0) + 1
        return versions
