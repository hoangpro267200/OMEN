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
}

export function createApiClient(mode: 'demo' | 'live'): ApiClient {
  return mode === 'demo' ? createMockApiClient() : createHttpApiClient();
}
