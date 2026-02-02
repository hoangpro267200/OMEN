/**
 * Mock ApiClient — in-memory demo data + simulated latency.
 * Used only via createApiClient('demo'). Screens must not import this file.
 */

import type {
  OverviewStats,
  Partition,
  PartitionDiff,
  ReconcileResult,
  SignalEvent,
  SignalsQuery,
  PartitionsQuery,
  IngestResponse,
  LedgerSegmentsResponse,
  LedgerFrameResponse,
  CrashTailSimResult,
  ReconcileState,
} from './contracts';
import type { ApiClient } from './client';
import {
  getDemoSignalEvents,
  getDemoPartitions,
  getDemoOverviewStats,
  getDemoActivityFeed,
} from '../../data/demoData';
import {
  getProcessedIds,
  getProcessedIdsList,
  addProcessedIds,
  getIngestAckId,
  setIngestAccepted,
  hasIngestAccepted,
  deterministicAckId,
  resetDemoState,
} from '../../data/demoState';
import { getFrameRecordsForSegment } from '../../data/ledgerProofMock';

const MAIN_PARTITION = '2026-01-28';

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function jitter(minMs: number, maxMs: number): number {
  return minMs + Math.random() * (maxMs - minMs);
}

/** Ledger signal IDs for main partition (all 10 demo signals). */
function getLedgerIdsForMain(): string[] {
  return getDemoSignalEvents()
    .filter((e) => e.ledger_partition === MAIN_PARTITION)
    .map((e) => e.signal_id);
}

/** Build reconcile_state from current processed set. */
function buildReconcileState(partitionDate: string): ReconcileState | null {
  if (partitionDate !== MAIN_PARTITION) return null;
  const ledger = getLedgerIdsForMain();
  const processed = getProcessedIdsList();
  const processedSet = getProcessedIds();
  const missing = ledger.filter((id) => !processedSet.has(id));
  const status =
    missing.length === 0 ? 'COMPLETED' : missing.length < ledger.length ? 'PARTIAL' : 'FAILED';
  return {
    partition_date: partitionDate,
    last_reconcile_at: new Date().toISOString(),
    ledger_highwater: 10,
    manifest_revision: 1,
    ledger_record_count: 10,
    processed_count: processed.length,
    missing_count: missing.length,
    status,
    replayed_ids: [],
  };
}

/** Merge static partition with current reconcile state. */
function mergePartitionWithState(p: Partition): Partition {
  const state = buildReconcileState(p.partition_date);
  return { ...p, reconcile_state: state ?? p.reconcile_state ?? null };
}

function filterPartitions(partitions: Partition[], q?: PartitionsQuery): Partition[] {
  let list = partitions.map(mergePartitionWithState);
  if (q?.date_from) {
    list = list.filter((p) => p.partition_date >= q.date_from!);
  }
  if (q?.date_to) {
    list = list.filter((p) => p.partition_date <= q.date_to!);
  }
  if (q?.status) {
    list = list.filter((p) => p.status === q.status);
  }
  if (q?.includeLate === false) {
    list = list.filter((p) => p.type !== 'LATE');
  }
  if (q?.needsReconcile) {
    list = list.filter((p) => (p.reconcile_state?.missing_count ?? 0) > 0);
  }
  return list;
}

function filterSignals(events: SignalEvent[], q?: SignalsQuery): SignalEvent[] {
  let list = [...events];
  if (q?.partition) {
    list = list.filter((e) => e.ledger_partition === q.partition);
  }
  if (q?.category) {
    list = list.filter((e) => e.signal.category === q.category);
  }
  if (q?.confidence) {
    list = list.filter((e) => e.signal.confidence_level === q.confidence);
  }
  if (q?.search) {
    const s = q.search.toLowerCase();
    list = list.filter(
      (e) =>
        e.signal_id.toLowerCase().includes(s) ||
        e.deterministic_trace_id.toLowerCase().includes(s) ||
        e.source_event_id.toLowerCase().includes(s)
    );
  }
  const limit = q?.limit ?? 100;
  return list.slice(0, limit);
}

export function createMockApiClient(): ApiClient {
  return {
    async getOverviewStats(): Promise<OverviewStats> {
      await delay(jitter(120, 220));
      const activity = getDemoActivityFeed();
      return getDemoOverviewStats(activity);
    },

    async listPartitions(q?: PartitionsQuery): Promise<Partition[]> {
      await delay(jitter(120, 220));
      const raw = getDemoPartitions();
      return filterPartitions(raw, q);
    },

    async getPartitionDetail(partitionDate: string): Promise<Partition | null> {
      await delay(jitter(120, 220));
      const raw = getDemoPartitions();
      const p = raw.find((x) => x.partition_date === partitionDate) ?? null;
      return p ? mergePartitionWithState(p) : null;
    },

    async getPartitionDiff(partitionDate: string): Promise<PartitionDiff> {
      await delay(jitter(150, 300));
      if (partitionDate !== MAIN_PARTITION) {
        return { ledger_ids: [], processed_ids: [], missing_ids: [] };
      }
      const ledger_ids = getLedgerIdsForMain();
      const processed_ids = getProcessedIdsList();
      const processedSet = getProcessedIds();
      const missing_ids = ledger_ids.filter((id) => !processedSet.has(id));
      return { ledger_ids, processed_ids, missing_ids };
    },

    async runReconcile(partitionDate: string): Promise<ReconcileResult> {
      const baseMs = 1200;
      await delay(baseMs + jitter(0, 300));
      if (partitionDate !== MAIN_PARTITION) {
        return {
          status: 'SKIPPED',
          partition_date: partitionDate,
          ledger_count: 0,
          processed_count: 0,
          missing_count: 0,
          replayed_count: 0,
          replayed_ids: [],
          duration_ms: baseMs,
          reason: 'Only main partition 2026-01-28 is reconcilable in demo',
        };
      }
      const ledger_ids = getLedgerIdsForMain();
      const processedSet = getProcessedIds();
      const missing_ids = ledger_ids.filter((id) => !processedSet.has(id));
      addProcessedIds(missing_ids);
      const processed_count = getProcessedIdsList().length;
      return {
        status: missing_ids.length === 0 ? 'COMPLETED' : 'COMPLETED',
        partition_date: partitionDate,
        ledger_count: ledger_ids.length,
        processed_count,
        missing_count: 0,
        replayed_count: missing_ids.length,
        replayed_ids: missing_ids,
        duration_ms: Math.round(baseMs + Math.random() * 300),
      };
    },

    async listSignals(q?: SignalsQuery): Promise<SignalEvent[]> {
      await delay(jitter(120, 220));
      const events = getDemoSignalEvents();
      return filterSignals(events, q);
    },

    async ingestSignal(event: SignalEvent): Promise<IngestResponse> {
      await delay(jitter(80, 200));
      const signalId = event.signal_id;
      const now = new Date().toISOString();
      if (hasIngestAccepted(signalId)) {
        const ackId = getIngestAckId(signalId)!;
        return {
          status_code: 409,
          ack_id: ackId,
          duplicate: true,
          signal_id: signalId,
          timestamp: now,
        };
      }
      const ackId = deterministicAckId(signalId);
      setIngestAccepted(signalId, ackId);
      return {
        status_code: 200,
        ack_id: ackId,
        duplicate: false,
        signal_id: signalId,
        timestamp: now,
      };
    },

    async resetIngestDemoState(): Promise<void> {
      resetDemoState();
    },

    async listLedgerSegments(partitionDate: string): Promise<LedgerSegmentsResponse> {
      await delay(jitter(120, 220));
      const parts = getDemoPartitions();
      const p = parts.find((x) => x.partition_date === partitionDate);
      const segments = p?.segments ?? [];
      return { partition_date: partitionDate, segments };
    },

    async readLedgerFrame(
      partitionDate: string,
      segmentFile: string,
      frameIndex: number
    ): Promise<LedgerFrameResponse> {
      await delay(jitter(120, 220));
      const records = getFrameRecordsForSegment(partitionDate, segmentFile);
      // frameIndex is 0-based; ledgerProofMock uses recordIndex 1-based, so records[i] has recordIndex i+1
      const frame = records[frameIndex];
      if (!frame) {
        return {
          partition_date: partitionDate,
          segment_file: segmentFile,
          frame_index: frameIndex,
          payload_length: 0,
          crc32_hex: '0x00000000',
          crc_ok: false,
          payload_preview: '',
          byte_offset: 0,
        };
      }
      return {
        partition_date: partitionDate,
        segment_file: segmentFile,
        frame_index: frameIndex,
        payload_length: frame.length,
        crc32_hex: `0x${frame.crc32Hex}`,
        crc_ok: true,
        payload_preview: frame.payloadPreview,
        payload_json: undefined,
        byte_offset: frame.offset,
      };
    },

    async simulateCrashTail(
      partitionDate: string,
      segmentFile: string,
      truncateAfterFrames: number
    ): Promise<CrashTailSimResult> {
      await delay(jitter(150, 300));
      const records = getFrameRecordsForSegment(partitionDate, segmentFile);
      const before_frames = records.slice(0, truncateAfterFrames + 1).map((r, i) => ({
        index: i,
        length: r.length,
        crc_ok: true,
      }));
      const after_truncate_frames = records.slice(truncateAfterFrames).map((_, i) => ({
        index: truncateAfterFrames + i,
        complete: false,
        note: 'Truncated',
      }));
      return {
        supported: true,
        partition_date: partitionDate,
        segment_file: segmentFile,
        before_frames,
        after_truncate_frames,
        reader_result: {
          returned_frames: before_frames.map((f) => f.index),
          warnings: [],
          returned_count: before_frames.length,
        },
        proof: {
          ok: true,
          summary: `Demo: truncated after frame ${truncateAfterFrames}; reader returned ${before_frames.length} frames.`,
        },
      };
    },
  };
}
