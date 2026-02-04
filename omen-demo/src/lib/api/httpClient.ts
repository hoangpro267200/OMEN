/**
 * HTTP ApiClient — fetch to live API. Placeholder endpoints; 404/501 return NotImplementedError.
 * Screens use via createApiClient('live'). For unsupported features (e.g. simulateCrashTail), return supported: false.
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
import type { ApiClient, SourceInfo, QualityMetrics, CalibrationReport } from './client';
import { NotImplementedError } from './contracts';
import type { ApiError } from './contracts';
import { getOmenBaseUrl } from '../apiBase';

function getBaseUrl(): string {
  // Use centralized base URL from apiBase.ts (defaults to http://localhost:8000)
  return getOmenBaseUrl();
}

function getApiKey(): string {
  // Hardcoded for development - matches OMEN_SECURITY_API_KEYS in backend .env
  const DEV_API_KEY = 'dev-test-key';
  if (typeof window === 'undefined') return DEV_API_KEY;
  try {
    return (window as unknown as { __OMEN_API_KEY?: string }).__OMEN_API_KEY ?? localStorage.getItem('omen.apiKey') ?? import.meta.env?.VITE_API_KEY ?? DEV_API_KEY;
  } catch {
    return DEV_API_KEY;
  }
}

function isJsonResponse(res: Response): boolean {
  const ct = res.headers.get('Content-Type') ?? '';
  return ct.includes('application/json');
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  const base = getBaseUrl().replace(/\/$/, '');
  const url = new URL(path.startsWith('/') ? path : `/${path}`, base || window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') url.searchParams.set(k, String(v));
    });
  }
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const apiKey = getApiKey();
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  const init: RequestInit = {
    method,
    headers,
  };
  if (body !== undefined) init.body = JSON.stringify(body);
  const res = await fetch(url.toString(), init);
  const text = await res.text();

  if (!res.ok) {
    let details: unknown = text;
    if (text && isJsonResponse(res)) {
      try {
        details = JSON.parse(text);
      } catch {
        details = text;
      }
    }
    const isNotImplemented = res.status === 404 || res.status === 501;
    const gotHtml = text.trimStart().toLowerCase().startsWith('<!doctype') || text.trimStart().toLowerCase().startsWith('<html');
    const message = gotHtml
      ? 'Live API chưa sẵn sàng. Máy chủ trả về trang HTML thay vì JSON. Hãy dùng chế độ Demo hoặc cấu hình backend đúng URL.'
      : isNotImplemented
        ? 'Endpoint chưa được triển khai (404/501).'
        : res.statusText || 'Request failed';
    const err: ApiError = {
      status: res.status,
      code: gotHtml ? 'INVALID_RESPONSE_TYPE' : isNotImplemented ? 'NOT_IMPLEMENTED' : 'HTTP_ERROR',
      message,
      details,
    };
    if (isNotImplemented || gotHtml) {
      throw new NotImplementedError(message);
    }
    const e = new Error(message) as Error & { apiError?: ApiError };
    e.apiError = err;
    throw e;
  }

  if (!text) return undefined as T;
  if (!isJsonResponse(res)) {
    const gotHtml = text.trimStart().toLowerCase().startsWith('<!doctype') || text.trimStart().toLowerCase().startsWith('<html');
    throw new NotImplementedError(
      gotHtml
        ? 'Live API chưa sẵn sàng. Máy chủ trả về HTML thay vì JSON. Dùng chế độ Demo hoặc cấu hình VITE_API_BASE trỏ tới backend.'
        : 'Server trả về nội dung không phải JSON.'
    );
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error('Phản hồi API không phải JSON hợp lệ.');
  }
}

export function createHttpApiClient(): ApiClient {
  return {
    async getOverviewStats(): Promise<OverviewStats> {
      return request<OverviewStats>('GET', '/api/ui/overview');
    },

    async listPartitions(q?: PartitionsQuery): Promise<Partition[]> {
      return request<Partition[]>('GET', '/api/ui/partitions', undefined, {
        date_from: q?.date_from,
        date_to: q?.date_to,
        status: q?.status,
        includeLate: q?.includeLate,
        needsReconcile: q?.needsReconcile,
      } as Record<string, string | boolean | undefined>);
    },

    async getPartitionDetail(partitionDate: string): Promise<Partition | null> {
      return request<Partition | null>('GET', `/api/ui/partitions/${encodeURIComponent(partitionDate)}`);
    },

    async getPartitionDiff(partitionDate: string): Promise<PartitionDiff> {
      return request<PartitionDiff>('GET', `/api/ui/partitions/${encodeURIComponent(partitionDate)}/diff`);
    },

    async runReconcile(partitionDate: string): Promise<ReconcileResult> {
      return request<ReconcileResult>('POST', `/api/ui/partitions/${encodeURIComponent(partitionDate)}/reconcile`);
    },

    async listSignals(q?: SignalsQuery): Promise<SignalEvent[]> {
      // Use the main signals API with mode=live to get real signals only
      const response = await request<{ signals: SignalEvent[]; total: number }>('GET', '/api/v1/signals/', undefined, {
        mode: 'live', // Always request live signals in live mode
        partition: q?.partition,
        category: q?.category,
        confidence: q?.confidence,
        search: q?.search,
        limit: q?.limit ?? 50,
      } as Record<string, string | number | undefined>);
      
      // The API returns { signals: [...], total: N }, extract just the signals array
      return response.signals || [];
    },

    async ingestSignal(event: SignalEvent): Promise<IngestResponse> {
      return request<IngestResponse>('POST', '/api/v1/signals/ingest', event);
    },

    async resetIngestDemoState(): Promise<void> {
      // No-op in live mode
    },

    async listLedgerSegments(partitionDate: string): Promise<LedgerSegmentsResponse> {
      return request<LedgerSegmentsResponse>('GET', `/api/ui/ledger/${encodeURIComponent(partitionDate)}/segments`);
    },

    async readLedgerFrame(
      partitionDate: string,
      segmentFile: string,
      frameIndex: number
    ): Promise<LedgerFrameResponse> {
      return request<LedgerFrameResponse>(
        'GET',
        `/api/ui/ledger/${encodeURIComponent(partitionDate)}/segments/${encodeURIComponent(segmentFile)}/frames/${frameIndex}`
      );
    },

    async simulateCrashTail(
      partitionDate: string,
      segmentFile: string,
      truncateAfterFrames: number
    ): Promise<CrashTailSimResult> {
      try {
        const result = await request<CrashTailSimResult>(
          'POST',
          `/api/ui/ledger/${encodeURIComponent(partitionDate)}/segments/${encodeURIComponent(segmentFile)}/simulate-crash-tail`,
          { truncate_after_frames: truncateAfterFrames }
        );
        return result ?? { supported: false, partition_date: partitionDate, segment_file: segmentFile, before_frames: [], after_truncate_frames: [], reader_result: { returned_frames: [], warnings: [], returned_count: 0 }, proof: { ok: false, summary: 'Not supported' } };
      } catch (e) {
        if (e instanceof NotImplementedError) {
          return {
            supported: false,
            partition_date: partitionDate,
            segment_file: segmentFile,
            before_frames: [],
            after_truncate_frames: [],
            reader_result: { returned_frames: [], warnings: ['Not supported in live mode'], returned_count: 0 },
            proof: { ok: false, summary: 'Not available in live mode' },
          };
        }
        throw e;
      }
    },

    // Multi-source intelligence
    async getMultiSourceSignals(sources?: string[]): Promise<SignalEvent[]> {
      const params: Record<string, string | undefined> = {};
      if (sources?.length) {
        params.sources = sources.join(',');
      }
      const response = await request<{ signals: SignalEvent[] }>('GET', '/api/v1/multi-source/signals', undefined, params);
      return response.signals || [];
    },

    async getMultiSourceHealth(): Promise<Record<string, { status: string; enabled: boolean }>> {
      return request<Record<string, { status: string; enabled: boolean }>>('GET', '/api/v1/multi-source/sources');
    },

    async getSourcesList(): Promise<SourceInfo[]> {
      const response = await request<{ sources: SourceInfo[] }>('GET', '/api/v1/multi-source/sources');
      return response.sources || [];
    },

    // Quality metrics
    async getQualityMetrics(): Promise<QualityMetrics | null> {
      try {
        return await request<QualityMetrics>('GET', '/api/v1/stats/quality');
      } catch (e) {
        if (e instanceof NotImplementedError) return null;
        throw e;
      }
    },

    async getCalibrationReport(): Promise<CalibrationReport | null> {
      try {
        return await request<CalibrationReport>('GET', '/api/v1/stats/calibration');
      } catch (e) {
        if (e instanceof NotImplementedError) return null;
        throw e;
      }
    },
  };
}
