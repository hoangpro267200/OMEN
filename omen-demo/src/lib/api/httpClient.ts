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
import type { ApiClient } from './client';
import { NotImplementedError } from './contracts';
import type { ApiError } from './contracts';

const STORAGE_KEY_BASE = 'omen.apiBase';
const DEFAULT_BASE = '';

function getBaseUrl(): string {
  if (typeof window === 'undefined') return DEFAULT_BASE;
  try {
    return (window as unknown as { __OMEN_API_BASE?: string }).__OMEN_API_BASE ?? localStorage.getItem(STORAGE_KEY_BASE) ?? import.meta.env?.VITE_API_BASE ?? DEFAULT_BASE;
  } catch {
    return DEFAULT_BASE;
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
  const init: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
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
      return request<SignalEvent[]>('GET', '/api/ui/signals', undefined, {
        partition: q?.partition,
        category: q?.category,
        confidence: q?.confidence,
        search: q?.search,
        limit: q?.limit,
      } as Record<string, string | number | undefined>);
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
  };
}
