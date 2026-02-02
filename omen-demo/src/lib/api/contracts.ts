/**
 * API contracts — single source of truth for types and DTOs.
 * Screens may import types from here. Data access only via hooks.
 */

/* ---------------------------------------------------------------------------
   Signal / OmenSignal
   --------------------------------------------------------------------------- */

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type SignalCategory =
  | 'GEOPOLITICAL'
  | 'INFRASTRUCTURE'
  | 'OPERATIONAL'
  | 'FINANCIAL'
  | 'CLIMATE'
  | 'COMPLIANCE'
  | 'NETWORK';

export interface OmenSignal {
  signal_id: string;
  source_event_id: string;
  title: string;
  probability: number;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  category: SignalCategory;
  trace_id: string;
  ruleset_version: string;
  generated_at: string;
}

export interface SignalEvent {
  schema_version: string;
  signal_id: string;
  deterministic_trace_id: string;
  input_event_hash: string;
  source_event_id: string;
  ruleset_version: string;
  observed_at: string;
  emitted_at: string;
  ledger_written_at?: string;
  ledger_partition?: string;
  ledger_sequence?: number;
  signal: OmenSignal;
}

/* ---------------------------------------------------------------------------
   Partition / Segment / Manifest / ReconcileState
   --------------------------------------------------------------------------- */

export interface Segment {
  file: string;
  record_count: number;
  size_bytes: number;
  checksum: string;
  is_sealed: boolean;
}

export interface Manifest {
  schema_version: string;
  partition_date: string;
  sealed_at: string;
  total_records: number;
  highwater_sequence: number;
  manifest_revision: number;
  is_late_partition: boolean;
  segments: Segment[];
}

export type PartitionStatus = 'SEALED' | 'OPEN';
export type PartitionType = 'MAIN' | 'LATE';

export interface ReconcileState {
  partition_date: string;
  last_reconcile_at: string;
  ledger_highwater: number;
  manifest_revision: number;
  ledger_record_count: number;
  processed_count: number;
  missing_count: number;
  status: 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'SKIPPED';
  replayed_ids?: string[];
}

export interface Partition {
  partition_date: string;
  type: PartitionType;
  status: PartitionStatus;
  total_records: number;
  highwater_sequence: number;
  segments: Segment[];
  manifest?: Manifest;
  reconcile_state?: ReconcileState | null;
}

/* ---------------------------------------------------------------------------
   Diff + Reconcile result
   --------------------------------------------------------------------------- */

export interface PartitionDiff {
  ledger_ids: string[];
  processed_ids: string[];
  missing_ids: string[];
}

export interface ReconcileResult {
  status: 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'SKIPPED';
  partition_date: string;
  ledger_count: number;
  processed_count: number;
  missing_count: number;
  replayed_count: number;
  replayed_ids: string[];
  duration_ms: number;
  reason?: string;
}

/* ---------------------------------------------------------------------------
   Ingest
   --------------------------------------------------------------------------- */

export interface IngestResponse {
  status_code: 200 | 409 | 400 | 500;
  ack_id: string;
  duplicate: boolean;
  signal_id: string;
  timestamp: string;
}

/* ---------------------------------------------------------------------------
   Queries
   --------------------------------------------------------------------------- */

export interface PartitionsQuery {
  date_from?: string;
  date_to?: string;
  status?: 'SEALED' | 'OPEN';
  includeLate?: boolean;
  needsReconcile?: boolean;
}

export interface SignalsQuery {
  partition?: string;
  category?: SignalCategory;
  confidence?: ConfidenceLevel;
  search?: string;
  limit?: number;
}

/* ---------------------------------------------------------------------------
   Overview
   --------------------------------------------------------------------------- */

export interface OverviewActivityItem {
  time: string;
  id: string;
  status: string;
  channel: string;
}

export interface OverviewStats {
  signals_today: number;
  signals_trend: string;
  signals_trend_up: boolean;
  hot_path_ok: number;
  hot_path_pct: string;
  duplicates: number;
  duplicates_sub: string;
  partitions_sealed: number;
  partitions_open: number;
  partitions_sub: string;
  last_reconcile: string;
  last_reconcile_status: string;
  activity_feed?: OverviewActivityItem[];
}

/* ---------------------------------------------------------------------------
   Ledger proof
   --------------------------------------------------------------------------- */

export interface LedgerSegmentsResponse {
  partition_date: string;
  segments: Segment[];
}

export interface LedgerFrameResponse {
  partition_date: string;
  segment_file: string;
  frame_index: number;
  payload_length: number;
  crc32_hex: string;
  crc_ok: boolean;
  payload_preview: string;
  payload_json?: unknown;
  byte_offset: number;
}

export interface CrashTailSimResult {
  supported: boolean;
  partition_date: string;
  segment_file: string;
  before_frames: Array<{ index: number; length: number; crc_ok: boolean }>;
  after_truncate_frames: Array<{ index: number; complete: boolean; note?: string }>;
  reader_result: {
    returned_frames: number[];
    warnings: string[];
    returned_count: number;
  };
  proof: {
    ok: boolean;
    summary: string;
  };
}

/* ---------------------------------------------------------------------------
   Errors
   --------------------------------------------------------------------------- */

export interface ApiError {
  status?: number;
  code: string;
  message: string;
  details?: unknown;
}

export class NotImplementedError extends Error {
  code = 'NOT_IMPLEMENTED';
  constructor(message = 'Not implemented in live mode') {
    super(message);
    this.name = 'NotImplementedError';
  }
}
