/**
 * ApiClient interface — single contract for demo and live data.
 * Screens use hooks only; hooks get client from createApiClient(dataSourceMode).
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
} from './contracts';
import { createMockApiClient } from './mockClient';
import { createHttpApiClient } from './httpClient';

// Multi-source types
export interface SourceInfo {
  name: string;
  enabled: boolean;
  priority: number;
  weight: number;
  status?: string;
}

export interface QualityMetrics {
  total_received: number;
  total_validated: number;
  total_rejected: number;
  rejection_rate: string;
  validation_rate: string;
  avg_validation_score: string;
  rejections_by_rule: Record<string, number>;
  rejections_by_status: Record<string, number>;
  confidence_distribution: Record<string, number>;
}

export interface CalibrationReport {
  total_predictions: number;
  predictions_within_bounds: number;
  coverage_rate: number;
  mean_absolute_error: number;
  mean_absolute_percent_error: number;
  is_well_calibrated: boolean;
  errors_by_metric: Record<string, number[]>;
}

export interface ApiClient {
  getOverviewStats(): Promise<OverviewStats>;

  listPartitions(q?: PartitionsQuery): Promise<Partition[]>;
  getPartitionDetail(partitionDate: string): Promise<Partition | null>;
  getPartitionDiff(partitionDate: string): Promise<PartitionDiff>;

  runReconcile(partitionDate: string): Promise<ReconcileResult>;

  listSignals(q?: SignalsQuery): Promise<SignalEvent[]>;

  ingestSignal(event: SignalEvent): Promise<IngestResponse>;
  resetIngestDemoState(): Promise<void>;

  listLedgerSegments(partitionDate: string): Promise<LedgerSegmentsResponse>;
  readLedgerFrame(
    partitionDate: string,
    segmentFile: string,
    frameIndex: number
  ): Promise<LedgerFrameResponse>;
  simulateCrashTail(
    partitionDate: string,
    segmentFile: string,
    truncateAfterFrames: number
  ): Promise<CrashTailSimResult>;
  
  // Multi-source intelligence (optional - not all clients implement)
  getMultiSourceSignals?(sources?: string[]): Promise<SignalEvent[]>;
  getMultiSourceHealth?(): Promise<Record<string, { status: string; enabled: boolean }>>;
  getSourcesList?(): Promise<SourceInfo[]>;
  
  // Quality metrics (optional - not all clients implement)
  getQualityMetrics?(): Promise<QualityMetrics | null>;
  getCalibrationReport?(): Promise<CalibrationReport | null>;
}

export function createApiClient(mode: 'demo' | 'live'): ApiClient {
  return mode === 'demo' ? createMockApiClient() : createHttpApiClient();
}
