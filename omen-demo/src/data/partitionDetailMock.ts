/**
 * Types and mock data for Partition Detail screen.
 */

import type { PartitionType, PartitionStatus, ReconcileStatus } from './partitionsMock';

export interface PartitionDetailData {
  partitionDate: string;
  type: PartitionType;
  status: PartitionStatus;
  lastReconcileAt: string | null;
  /** Ledger = source of truth count */
  ledgerCount: number;
  /** RiskCast = processed count (before reconcile) */
  riskcastCount: number;
  missingSignalIds: string[];
  /** After reconcile: replayed signal id → ack_id */
  replayedAcks: Record<string, string>;
  manifest: PartitionManifest;
  segments: PartitionSegment[];
  reconcileHistory: ReconcileHistoryEntry[];
  highwater: HighwaterData;
}

export interface PartitionManifest {
  sealedAt: string;
  totalRecords: number;
  highwater: number;
  revision: number;
  checksum: string;
}

export interface PartitionSegment {
  name: string;
  records: number;
  sizeBytes: number;
  checksum: string;
  status: string;
}

export interface ReconcileHistoryEntry {
  runTime: string;
  status: ReconcileStatus;
  ledgerCount: number;
  processedCount: number;
  missingCount: number;
  replayedCount: number;
}

export interface HighwaterData {
  lastSeen: number;
  current: number;
  status: 'no_change' | 'increased';
}

function defaultManifest(_partitionDate: string): PartitionManifest {
  return {
    sealedAt: '2026-01-29T04:00:00Z',
    totalRecords: 10,
    highwater: 10,
    revision: 1,
    checksum: 'crc32:deadbeef',
  };
}

function defaultSegments(): PartitionSegment[] {
  return [
    {
      name: 'signals-001.wal',
      records: 10,
      sizeBytes: 8192,
      checksum: 'crc32:deadbeef',
      status: 'sealed (read-only)',
    },
  ];
}

function defaultReconcileHistory(): ReconcileHistoryEntry[] {
  return [
    {
      runTime: '2026-01-29T05:00:00Z',
      status: 'COMPLETED',
      ledgerCount: 10,
      processedCount: 10,
      missingCount: 0,
      replayedCount: 2,
    },
    {
      runTime: '2026-01-29T04:30:00Z',
      status: 'PARTIAL',
      ledgerCount: 10,
      processedCount: 8,
      missingCount: 2,
      replayedCount: 0,
    },
  ];
}

/** Mock by partition date. Default: 10 ledger, 8 riskcast, 2 missing (OMEN-DEMO005, OMEN-DEMO009). */
export function getPartitionDetail(partitionDate: string): PartitionDetailData {
  const isLate = partitionDate.endsWith('-late');
  const type: PartitionType = isLate ? 'LATE' : 'MAIN';
  const status: PartitionStatus = isLate ? 'OPEN' : 'SEALED';
  const ledgerCount = isLate ? 1 : 10;
  const riskcastCount = isLate ? 1 : 8;
  const missingSignalIds = isLate ? [] : ['OMEN-DEMO005', 'OMEN-DEMO009'];

  return {
    partitionDate,
    type,
    status,
    lastReconcileAt: isLate ? null : '2026-01-29T04:30:00Z',
    ledgerCount,
    riskcastCount,
    missingSignalIds: [...missingSignalIds],
    replayedAcks: {},
    manifest: defaultManifest(partitionDate),
    segments: defaultSegments(),
    reconcileHistory: defaultReconcileHistory(),
    highwater: {
      lastSeen: 10,
      current: 10,
      status: 'no_change',
    },
  };
}
