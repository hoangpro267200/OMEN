import { useParams } from 'react-router-dom';
import { useMemo } from 'react';
import { PartitionDetailScreen } from './PartitionDetailScreen';
import { usePartitionDetail, usePartitionDiff, useRunReconcile } from '../lib/api/hooks';
import type { Partition, PartitionDiff } from '../lib/api/contracts';
import type {
  PartitionDetailData,
  PartitionManifest,
  PartitionSegment,
  ReconcileHistoryEntry,
  HighwaterData,
} from '../data/partitionDetailMock';
import type { ReconcileStatus } from '../data/partitionsMock';

function mapPartitionAndDiffToDetail(
  _partitionDate: string,
  p: Partition | null,
  d: PartitionDiff | undefined
): PartitionDetailData | null {
  if (!p) return null;
  const rs = p.reconcile_state;
  const manifest: PartitionManifest = p.manifest
    ? {
        sealedAt: p.manifest.sealed_at,
        totalRecords: p.manifest.total_records,
        highwater: p.manifest.highwater_sequence,
        revision: p.manifest.manifest_revision,
        checksum: p.segments[0]?.checksum ?? 'crc32:deadbeef',
      }
    : {
        sealedAt: '',
        totalRecords: p.total_records,
        highwater: p.highwater_sequence,
        revision: 0,
        checksum: 'crc32:deadbeef',
      };
  const segments: PartitionSegment[] = p.segments.map((s) => ({
    name: s.file,
    records: s.record_count,
    sizeBytes: s.size_bytes,
    checksum: s.checksum,
    status: s.is_sealed ? 'sealed (read-only)' : 'open',
  }));
  const ledgerCount = d ? d.ledger_ids.length : p.total_records;
  const processedIds = d ? d.processed_ids : [];
  const missingIds = d ? d.missing_ids : [];
  const replayedAcks: Record<string, string> = {};
  const reconcileHistory: ReconcileHistoryEntry[] = rs
    ? [
        {
          runTime: rs.last_reconcile_at,
          status: rs.status as ReconcileStatus,
          ledgerCount: rs.ledger_record_count,
          processedCount: rs.processed_count,
          missingCount: rs.missing_count,
          replayedCount: rs.replayed_ids?.length ?? 0,
        },
      ]
    : [];
  const highwater: HighwaterData = {
    lastSeen: rs?.ledger_highwater ?? p.highwater_sequence,
    current: p.highwater_sequence,
    status: 'no_change',
  };
  return {
    partitionDate: p.partition_date,
    type: p.type,
    status: p.status,
    lastReconcileAt: rs?.last_reconcile_at ?? null,
    ledgerCount,
    riskcastCount: processedIds.length,
    missingSignalIds: missingIds,
    replayedAcks,
    manifest,
    segments,
    reconcileHistory,
    highwater,
  };
}

/**
 * Partition detail route — completeness gauge, Run Reconcile, manifest, history, highwater.
 * Data from usePartitionDetail + usePartitionDiff; reconcile via useRunReconcile.
 */
export function PartitionDetailPage() {
  const { partitionId } = useParams<{ partitionId: string }>();
  const partitionDate = partitionId ?? '';
  const { data: partition, isLoading: loadingDetail, error: errorDetail } = usePartitionDetail(partitionDate);
  const { data: diff, isLoading: loadingDiff } = usePartitionDiff(partitionDate);
  const runReconcileMutation = useRunReconcile();

  const lastReconcileResult = runReconcileMutation.data;
  const detail = useMemo(() => {
    const base = partition ? mapPartitionAndDiffToDetail(partitionDate, partition, diff) : null;
    if (!base) return null;
    if (lastReconcileResult?.replayed_ids?.length) {
      return {
        ...base,
        replayedAcks: Object.fromEntries(
          lastReconcileResult.replayed_ids.map((id) => [
            id,
            `riskcast-ack-${id.slice(-4).toLowerCase()}`,
          ])
        ),
      };
    }
    return base;
  }, [partitionDate, partition, diff, lastReconcileResult]);

  const onRunReconcile = () => {
    if (!partitionDate || runReconcileMutation.isPending) return;
    runReconcileMutation.mutate(partitionDate);
  };

  return (
    <PartitionDetailScreen
      partitionDate={partitionDate}
      detail={detail}
      isLoading={loadingDetail || loadingDiff}
      errorMessage={errorDetail?.message ?? null}
      onRunReconcile={onRunReconcile}
      isReconciling={runReconcileMutation.isPending}
    />
  );
}
