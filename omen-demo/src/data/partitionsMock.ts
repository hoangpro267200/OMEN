/**
 * Types and mock data for Partitions List screen.
 */

export type PartitionType = 'MAIN' | 'LATE';
export type PartitionStatus = 'SEALED' | 'OPEN';
export type ReconcileStatus = 'COMPLETED' | 'PARTIAL' | 'SKIPPED' | 'PENDING' | 'FAILED';

export interface LedgerPartition {
  partitionDate: string;
  type: PartitionType;
  status: PartitionStatus;
  totalRecords: number;
  highwaterSequence: number;
  segmentCount: number;
  segmentNames?: string[];
  reconcileStatus: ReconcileStatus;
  reconcileTimestamp?: string;
  sealedAt?: string;
  manifestChecksum?: string;
  needsReconcile?: boolean;
}

export const defaultPartitions: LedgerPartition[] = [
  {
    partitionDate: '2026-01-28',
    type: 'MAIN',
    status: 'SEALED',
    totalRecords: 10,
    highwaterSequence: 10,
    segmentCount: 1,
    segmentNames: ['signals-001.wal'],
    reconcileStatus: 'COMPLETED',
    reconcileTimestamp: '2026-01-29T04:00:00Z',
    sealedAt: '2026-01-29T04:00:00Z',
    manifestChecksum: 'crc32:deadbeef',
    needsReconcile: false,
  },
  {
    partitionDate: '2026-01-28-late',
    type: 'LATE',
    status: 'OPEN',
    totalRecords: 1,
    highwaterSequence: 1,
    segmentCount: 1,
    segmentNames: ['signals-late-001.wal'],
    reconcileStatus: 'SKIPPED',
    sealedAt: undefined,
    manifestChecksum: undefined,
    needsReconcile: false,
  },
  {
    partitionDate: '2026-01-27',
    type: 'MAIN',
    status: 'SEALED',
    totalRecords: 25,
    highwaterSequence: 25,
    segmentCount: 3,
    segmentNames: ['signals-001.wal', 'signals-002.wal', 'signals-003.wal'],
    reconcileStatus: 'COMPLETED',
    reconcileTimestamp: '2026-01-28T03:00:00Z',
    sealedAt: '2026-01-28T03:00:00Z',
    manifestChecksum: 'crc32:a1b2c3d4',
    needsReconcile: false,
  },
];

export interface PartitionsFilters {
  dateFrom: string;
  dateTo: string;
  status: 'all' | PartitionStatus;
  includeLate: boolean;
  needsReconcileOnly: boolean;
}

export const defaultPartitionsFilters: PartitionsFilters = {
  dateFrom: '2026-01-27',
  dateTo: '2026-01-29',
  status: 'all',
  includeLate: true,
  needsReconcileOnly: false,
};
