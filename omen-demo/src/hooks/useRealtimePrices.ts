/**
 * Real-time price updates via Server-Sent Events.
 * POSTs signal_ids to /realtime/subscribe, connects to /realtime/prices,
 * and updates React Query cache for live-signals.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { ProcessedSignal } from '../types/omen';
import { OMEN_API_BASE } from '../lib/apiBase';

const API_BASE = OMEN_API_BASE;

interface PriceUpdate {
  signal_id: string;
  probability: number;
  previous_probability?: number;
  change_percent: number;
  timestamp: string;
}

export interface RealtimeStatus {
  connected: boolean;
  registered: number;
  subscribed: string[];
  lastUpdate: string | null;
  error: string | null;
}

export function useRealtimePrices(signalIds: string[]): RealtimeStatus {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<RealtimeStatus>({
    connected: false,
    registered: 0,
    subscribed: [],
    lastUpdate: null,
    error: null,
  });

  const subscribeToSignals = useCallback(async (ids: string[]) => {
    if (ids.length === 0) return;
    try {
      const res = await fetch(`${API_BASE}/realtime/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signal_ids: ids }),
      });
      if (!res.ok) throw new Error(`Subscribe failed: ${res.status}`);
      const data = await res.json();
      setStatus((prev) => ({
        ...prev,
        registered: data.total_registered ?? prev.registered,
        subscribed: data.subscribed ?? [],
        error:
          (data.not_found?.length as number) > 0
            ? `${data.not_found.length} signals not registered for real-time`
            : null,
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Subscribe failed';
      setStatus((prev) => ({ ...prev, error: msg }));
    }
  }, []);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const eventSource = new EventSource(`${API_BASE}/realtime/prices`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setStatus((prev) => ({ ...prev, connected: true, error: null }));
      if (signalIds.length > 0) {
        subscribeToSignals(signalIds);
      }
    };

    eventSource.addEventListener('status', (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'warning') {
          setStatus((prev) => ({ ...prev, error: data.message ?? prev.error }));
        }
        if (data.registered_signals != null) {
          setStatus((prev) => ({ ...prev, registered: data.registered_signals }));
        }
      } catch {
        // ignore parse errors
      }
    });

    eventSource.onmessage = (event: MessageEvent<string>) => {
      try {
        const update: PriceUpdate = JSON.parse(event.data);
        const momentum: ProcessedSignal['probability_momentum'] =
          update.change_percent > 1
            ? 'INCREASING'
            : update.change_percent < -1
              ? 'DECREASING'
              : 'STABLE';

        setStatus((prev) => ({ ...prev, lastUpdate: update.timestamp }));

        queryClient.setQueryData<ProcessedSignal[]>(['live-signals'], (oldData) => {
          if (!oldData || !Array.isArray(oldData)) return oldData;
          return oldData.map((signal) => {
            if (signal.signal_id !== update.signal_id) return signal;
            const hist = signal.probability_history ?? [];
            const newHistory =
              hist.length >= 24 ? [...hist.slice(1), update.probability] : [...hist, update.probability];
            return {
              ...signal,
              probability: update.probability,
              probability_history: newHistory,
              probability_momentum: momentum,
            };
          });
        });

        queryClient.invalidateQueries({ queryKey: ['signal', update.signal_id], exact: true });
      } catch (err) {
        console.error('[SSE] Failed to parse price update:', err);
      }
    };

    eventSource.onerror = () => {
      setStatus((prev) => ({ ...prev, connected: false }));
      eventSource.close();
      eventSourceRef.current = null;
      reconnectTimeoutRef.current = setTimeout(() => connect(), 5000);
    };
  }, [signalIds, subscribeToSignals, queryClient]);

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

  useEffect(() => {
    if (status.connected && signalIds.length > 0) {
      subscribeToSignals(signalIds);
    }
  }, [signalIds.join(','), status.connected, subscribeToSignals]);

  return status;
}

/** Fetch /realtime/status for header. Backs off on failure to avoid console spam. */
const REALTIME_POLL_OK_MS = 10_000;
const REALTIME_POLL_BACKOFF_MS = 30_000;

export function useRealtimeStatus(): {
  registered_signals: number;
  websocket_connected: boolean;
  status: string;
} | null {
  const [data, setData] = useState<{
    registered_signals: number;
    websocket_connected: boolean;
    status: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const schedule = (ms: number) => {
      if (cancelled) return;
      timeoutId = setTimeout(fetchStatus, ms);
    };

    const fetchStatus = async () => {
      if (cancelled) return;
      try {
        const res = await fetch(`${API_BASE}/realtime/status`);
        if (cancelled) return;
        if (res.ok) {
          const json = await res.json();
          setData({
            registered_signals: json.registered_signals ?? 0,
            websocket_connected: json.websocket_connected ?? false,
            status: json.status ?? 'idle',
          });
          schedule(REALTIME_POLL_OK_MS);
        } else {
          schedule(REALTIME_POLL_BACKOFF_MS);
        }
      } catch {
        if (!cancelled) setData(null);
        schedule(REALTIME_POLL_BACKOFF_MS);
      }
    };

    fetchStatus();
    return () => {
      cancelled = true;
      if (timeoutId != null) clearTimeout(timeoutId);
    };
  }, []);

  return data;
}
