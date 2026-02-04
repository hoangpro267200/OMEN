/**
 * OMEN Live API hooks — connected to real backend.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
  type ApiSignalResponse,
  type ApiSystemStats,
  type ApiActivityItem,
  mapApiSignalToUi,
  mapApiStatsToUi,
  mapApiActivityToUi,
} from '../lib/mapApiToUi';
import type { ProcessedSignal } from '../types/omen';
import { OMEN_API_BASE, getOmenBaseUrl } from '../lib/apiBase';

const API_BASE = OMEN_API_BASE;

// Configure axios default headers with API key
// Hardcoded for development - matches OMEN_SECURITY_API_KEYS in backend .env
const API_KEY = import.meta.env?.VITE_API_KEY || 'dev-test-key';
axios.defaults.headers.common['X-API-Key'] = API_KEY;

/** Timeout (ms) for normal API calls — fail fast if backend is down. */
const API_TIMEOUT_MS = 12_000;

/** Timeout for /live/process — Polymarket fetch + pipeline can take 30–90s. */
const LIVE_PROCESS_TIMEOUT_MS = 90_000;

/** Raw live event from Polymarket (before OMEN processing). */
export interface LiveEvent {
  event_id: string;
  title: string;
  probability: number;
  liquidity_usd: number;
  volume_usd: number;
  keywords: string[];
  source_url: string | null;
  observed_at: string;
}

/** Stub for components that only need a no-op API. */
export function useOmenApi() {
  return {
    fetchSignal: async () => null as ProcessedSignal | null,
    isConnected: false,
  };
}

/** Số tín hiệu mặc định — nhỏ để lần đầu tải nhanh, tránh timeout. */
const DEFAULT_LIVE_PROCESS_LIMIT = 50;

const BACKEND_CHECK_TIMEOUT_MS = 6_000;

/** Fetch and process live Polymarket events through OMEN. Resilient to backend/network errors. */
export function useProcessLiveSignals(options?: { enabled?: boolean; limit?: number }) {
  const limit = options?.limit ?? DEFAULT_LIVE_PROCESS_LIMIT;
  return useQuery<ProcessedSignal[]>({
    queryKey: ['live-signals', limit],
    queryFn: async () => {
      const base = getOmenBaseUrl();
      try {
        await axios.get(`${base}/health/`, { timeout: BACKEND_CHECK_TIMEOUT_MS });
      } catch (e) {
        const msg =
          'Backend chưa chạy hoặc không phản hồi. Trong terminal chạy: python -m uvicorn omen.main:app --host 0.0.0.0 --port 8000';
        throw new Error(msg);
      }
      const { data } = await axios.post<ApiSignalResponse[]>(
        `${API_BASE}/live/process`,
        null,
        { params: { limit, min_liquidity: 1000 }, timeout: LIVE_PROCESS_TIMEOUT_MS }
      );
      return (data ?? []).map(mapApiSignalToUi);
    },
    enabled: options?.enabled ?? true,
    retry: 1,
    retryDelay: 2000,
    refetchInterval: (q) => (q.state.error ? 60_000 : 30_000),
    staleTime: 10_000,
  });
}

/** System statistics for dashboard KPIs. Resilient to backend/network errors. */
export function useSystemStats() {
  return useQuery({
    queryKey: ['system-stats'],
    queryFn: async () => {
      const { data } = await axios.get<ApiSystemStats>(`${API_BASE}/stats`);
      return mapApiStatsToUi(data);
    },
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    refetchInterval: (query) =>
      query.state.error ? 60_000 : 15_000,
    staleTime: 10_000,
  });
}

/** Activity feed for the dashboard. */
export function useActivityFeed(limit = 20) {
  return useQuery({
    queryKey: ['activity-feed', limit],
    queryFn: async () => {
      const { data } = await axios.get<ApiActivityItem[]>(`${API_BASE}/activity`, {
        params: { limit },
        timeout: API_TIMEOUT_MS,
      });
      return (data ?? []).map(mapApiActivityToUi);
    },
    refetchInterval: 30_000,  // Reduced from 10s to 30s
    staleTime: 15_000,
  });
}

/** Manually trigger signal processing and update live-signals cache. */
export function useProcessSignals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { limit?: number; min_liquidity?: number }) => {
      const { data } = await axios.post<ApiSignalResponse[]>(
        `${API_BASE}/live/process`,
        null,
        { params: { limit: params.limit ?? 10, min_liquidity: params.min_liquidity ?? 1000 } }
      );
      return (data ?? []).map(mapApiSignalToUi);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['live-signals'], data);
    },
  });
}

/** Process a single event by ID. */
export function useProcessSingleSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (eventId: string) => {
      const { data } = await axios.post<{
        signal: ApiSignalResponse | null;
        rejection_reason?: string;
        stats?: Record<string, number>;
      }>(`${API_BASE}/live/process-single`, null, {
        params: { event_id: eventId },
      });
      if (data.signal) {
        return { signal: mapApiSignalToUi(data.signal), rejected: false as const };
      }
      return { signal: null, rejected: true as const, reason: data.rejection_reason };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['live-signals'] });
    },
  });
}

/** Fetch live events from Polymarket (raw). */
export function useLiveEvents(limit = 20) {
  return useQuery({
    queryKey: ['live-events', limit],
    queryFn: async () => {
      const { data } = await axios.get<LiveEvent[]>(`${API_BASE}/live/events`, {
        params: { limit, logistics_only: true },
      });
      return data;
    },
    refetchInterval: 30_000,
  });
}

/** Process events through OMEN pipeline. */
export function useProcessEvents() {
  return useProcessSignals();
}

/** Process a single event by ID. */
export function useProcessSingleEvent() {
  return useProcessSingleSignal();
}

/** Search Polymarket events by keyword. */
export function useSearchEvents(query: string, limit = 10) {
  return useQuery({
    queryKey: ['search-events', query, limit],
    queryFn: async () => {
      const { data } = await axios.get<LiveEvent[]>(`${API_BASE}/live/events/search`, {
        params: { query, limit },
      });
      return data;
    },
    enabled: query.length >= 2,
  });
}
