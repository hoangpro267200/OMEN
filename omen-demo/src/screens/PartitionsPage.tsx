import { useMemo } from 'react';
import { PartitionsScreen } from './PartitionsScreen';
import { usePartitions } from '../lib/api/hooks';
import type { Partition } from '../lib/api/contracts';
import type { LedgerPartition } from '../data/partitionsMock';

function mapPartitionToLedger(p: Partition): LedgerPartition {
  const rs = p.reconcile_state;
  return {
    partitionDate: p.partition_date,
    type: p.type,
    status: p.status,
    totalRecords: p.total_records,
    highwaterSequence: p.highwater_sequence,
    segmentCount: p.segments.length,
    segmentNames: p.segments.map((s) => s.file),
    reconcileStatus: (rs?.status ?? 'SKIPPED') as LedgerPartition['reconcileStatus'],
    reconcileTimestamp: rs?.last_reconcile_at,
    sealedAt: p.manifest?.sealed_at,
    manifestChecksum: p.manifest?.segments?.[0]?.checksum,
    needsReconcile: (rs?.missing_count ?? 0) > 0,
  };
}

/**
 * Partitions list route — ledger partitions table, filters, context panel, summary.
 * Data from usePartitions() only; no direct mock imports for list.
 */
export function PartitionsPage() {
  const { data: partitions = [], isLoading, error } = usePartitions();
  const ledgerPartitions = useMemo(
    () => partitions.map(mapPartitionToLedger),
    [partitions]
  );
  return (
    <PartitionsScreen
      partitions={ledgerPartitions}
      isLoading={isLoading}
      errorMessage={error?.message}
    />
  );
}
