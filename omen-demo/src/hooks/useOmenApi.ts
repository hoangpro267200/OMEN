/**
 * OMEN Live API hooks — fetch Polymarket data and process via backend.
 * Demo stub remains for backward compatibility; use the hooks below for live mode.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import type { OmenSignal } from '../types/omen';

const API_BASE =
  (import.meta.env.VITE_OMEN_API_URL as string) || 'http://localhost:8000/api/v1';

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

/** Processed signal returned by POST /live/process — matches OmenSignal for UI. */
export type ProcessedSignal = OmenSignal;

/** Stub for components that only need a no-op API. */
export function useOmenApi() {
  return {
    fetchSignal: async () => null as OmenSignal | null,
    isConnected: false,
  };
}

/** Fetch live events from Polymarket. */
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
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { limit?: number; min_liquidity?: number }) => {
      const { data } = await axios.post<ProcessedSignal[]>(
        `${API_BASE}/live/process`,
        null,
        { params: { limit: params.limit ?? 10, min_liquidity: params.min_liquidity ?? 1000 } }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['live-events'] });
    },
  });
}

/** Process a single event by ID. */
export function useProcessSingleEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (eventId: string) => {
      const { data } = await axios.post<{
        signal: ProcessedSignal | null;
        rejection_reason?: string;
        stats?: Record<string, number>;
      }>(`${API_BASE}/live/process-single`, null, {
        params: { event_id: eventId },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['live-events'] });
    },
  });
}

/** Search Polymarket events by keyword. */
export function useSearchEvents(query: string, limit = 10) {
  return useQuery({
    queryKey: ['search-events', query, limit],
    queryFn: async () => {
      const { data } = await axios.get<LiveEvent[]>(
        `${API_BASE}/live/events/search`,
        { params: { query, limit } }
      );
      return data;
    },
    enabled: query.length >= 2,
  });
}
