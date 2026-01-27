/**
 * Real-time price updates via Server-Sent Events.
 * Updates React Query cache for live-signals and optional per-signal cache.
 */

import { useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { ProcessedSignal } from '../types/omen';

const API_BASE =
  (import.meta.env.VITE_OMEN_API_URL as string) || 'http://localhost:8000/api/v1';

interface PriceUpdate {
  signal_id: string;
  probability: number;
  change_percent: number;
  timestamp: string;
}

export function useRealtimePrices(signalIds: string[]) {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (signalIds.length === 0) return;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const eventSource = new EventSource(`${API_BASE}/realtime/prices`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      fetch(`${API_BASE}/realtime/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signalIds),
      }).catch(console.error);
    };

    eventSource.onmessage = (event: MessageEvent<string>) => {
      try {
        const update: PriceUpdate = JSON.parse(event.data);
        const momentum: ProcessedSignal['probability_momentum'] =
          update.change_percent > 1
            ? 'INCREASING'
            : update.change_percent < -1
              ? 'DECREASING'
              : 'STABLE';

        queryClient.setQueryData<ProcessedSignal[]>(['live-signals'], (oldData) => {
          if (!oldData || !Array.isArray(oldData)) return oldData;
          return oldData.map((signal) => {
            if (signal.signal_id !== update.signal_id) return signal;
            const hist = signal.probability_history ?? [];
            const newHistory =
              hist.length > 0 ? [...hist.slice(1), update.probability] : [update.probability];
            return {
              ...signal,
              probability: update.probability,
              probability_history: newHistory,
              probability_momentum: momentum,
            };
          });
        });
      } catch (err) {
        console.error('[SSE] Failed to parse price update:', err);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      eventSourceRef.current = null;
      reconnectTimeoutRef.current = setTimeout(() => connect(), 5000);
    };
  }, [signalIds, queryClient]);

  useEffect(() => {
    connect();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [connect]);
}
