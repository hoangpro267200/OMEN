/**
 * React Query hooks — the ONLY way screens access data.
 * Screens may import only from this file (and types from contracts).
 * Do NOT import mockClient, demoData, or demoState in screens.
 * 
 * NOTE: Uses DataModeContext for consistent mode state across the app.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useCallback } from 'react';
import { createApiClient } from './client';
import type { PartitionsQuery, SignalsQuery } from './contracts';
import { useDataModeSafe, type DataMode } from '../../context/DataModeContext';
import { queryKeys } from './queryKeys';

// Re-create client when mode changes
// IMPORTANT: In LIVE mode, ALWAYS use live client. If not connected, return errors, NOT demo data.
function useApiClient() {
  const { state } = useDataModeSafe();
  const mode = state.mode;
  // STRICT: Use live client when in live mode, regardless of connection status.
  // Errors will show in UI if not connected, but NEVER fake data.
  return useMemo(() => createApiClient(mode), [mode]);
}

// Compatibility wrapper: returns [mode, setMode] like the old useDataSourceMode
function useDataSourceMode(): [DataMode, (mode: DataMode) => void] {
  const { state, setMode } = useDataModeSafe();
  const setModeWrapper = useCallback((mode: DataMode) => {
    setMode(mode);
  }, [setMode]);
  return [state.mode, setModeWrapper];
}

// Hook to check if API is actually available
function useCanFetchLive(): boolean {
  const { canUseLiveData, isLive } = useDataModeSafe();
  return isLive && canUseLiveData;
}

export { useDataSourceMode, useApiClient, useCanFetchLive };

// Overview
export function useOverviewStats() {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: [...queryKeys.overview],
    queryFn: () => client.getOverviewStats(),
    staleTime: mode === 'demo' ? 2_000 : 10_000,
    refetchInterval: mode === 'demo' ? 5_000 : false,
    retry: mode === 'live' ? 0 : 1,
  });
}

// Partitions
export function usePartitions(query?: PartitionsQuery) {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: [...queryKeys.partitions((query ?? {}) as Record<string, unknown>), mode],
    queryFn: () => client.listPartitions(query),
    staleTime: 5_000,
    retry: mode === 'live' ? 0 : 1,
  });
}

export function usePartitionDetail(partitionDate: string) {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: [...queryKeys.partitionDetail(partitionDate), mode],
    queryFn: () => client.getPartitionDetail(partitionDate),
    enabled: !!partitionDate,
    staleTime: 2_000,
    retry: mode === 'live' ? 0 : 1,
  });
}

export function usePartitionDiff(partitionDate: string) {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: [...queryKeys.partitionDiff(partitionDate), mode],
    queryFn: () => client.getPartitionDiff(partitionDate),
    enabled: !!partitionDate,
    staleTime: 2_000,
    retry: mode === 'live' ? 0 : 1,
  });
}

// Signals
export function useSignals(query?: SignalsQuery) {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: [...queryKeys.signals((query ?? {}) as Record<string, unknown>), mode],
    queryFn: () => client.listSignals(query),
    staleTime: 5_000,
    retry: mode === 'live' ? 0 : 1,
  });
}

// Ledger
export function useLedgerSegments(partitionDate: string) {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: [...queryKeys.ledgerSegments(partitionDate), mode],
    queryFn: () => client.listLedgerSegments(partitionDate),
    enabled: !!partitionDate,
    staleTime: 5_000,
    retry: mode === 'live' ? 0 : 1,
  });
}

export function useLedgerFrame(partitionDate: string, segmentFile: string, frameIndex: number) {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: [...queryKeys.ledgerFrame(partitionDate, segmentFile, frameIndex), mode],
    queryFn: () => client.readLedgerFrame(partitionDate, segmentFile, frameIndex),
    enabled: !!partitionDate && !!segmentFile && frameIndex >= 0,
    staleTime: 2_000,
    retry: mode === 'live' ? 0 : 1,
  });
}

// Mutations
export function useRunReconcile() {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (partitionDate: string) => client.runReconcile(partitionDate),
    onSuccess: (_data, partitionDate) => {
      qc.invalidateQueries({ queryKey: queryKeys.overview });
      qc.invalidateQueries({ queryKey: queryKeys.partitions({}) });
      qc.invalidateQueries({ queryKey: queryKeys.partitionDetail(partitionDate) });
      qc.invalidateQueries({ queryKey: queryKeys.partitionDiff(partitionDate) });
    },
  });
}

export function useIngestSignal() {
  const client = useApiClient();
  return useMutation({
    mutationFn: (event: Parameters<typeof client.ingestSignal>[0]) => client.ingestSignal(event),
  });
}

export function useResetDemoState() {
  const client = useApiClient();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => client.resetIngestDemoState(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.overview });
      qc.invalidateQueries({ queryKey: queryKeys.partitions({}) });
      qc.invalidateQueries({ queryKey: queryKeys.signals({}) });
    },
  });
}

// Multi-Source Intelligence
export function useMultiSourceSignals(sources?: string[]) {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: ['multi-source', 'signals', sources, mode],
    queryFn: () => client.getMultiSourceSignals?.(sources) ?? Promise.resolve([]),
    staleTime: 10_000,
    retry: mode === 'live' ? 0 : 1,
    enabled: !!client.getMultiSourceSignals,
  });
}

export function useMultiSourceHealth() {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: ['multi-source', 'health', mode],
    queryFn: () => client.getMultiSourceHealth?.() ?? Promise.resolve({}),
    staleTime: 30_000,
    retry: mode === 'live' ? 0 : 1,
    enabled: !!client.getMultiSourceHealth,
  });
}

export function useSourcesList() {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: ['multi-source', 'sources', mode],
    queryFn: () => client.getSourcesList?.() ?? Promise.resolve([]),
    staleTime: 60_000,
    retry: mode === 'live' ? 0 : 1,
    enabled: !!client.getSourcesList,
  });
}

// Quality Metrics
export function useQualityMetrics() {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: ['stats', 'quality', mode],
    queryFn: () => client.getQualityMetrics?.() ?? Promise.resolve(null),
    staleTime: 30_000,
    retry: mode === 'live' ? 0 : 1,
    enabled: !!client.getQualityMetrics,
  });
}

export function useCalibrationReport() {
  const client = useApiClient();
  const [mode] = useDataSourceMode();
  return useQuery({
    queryKey: ['stats', 'calibration', mode],
    queryFn: () => client.getCalibrationReport?.() ?? Promise.resolve(null),
    staleTime: 60_000,
    retry: mode === 'live' ? 0 : 1,
    enabled: !!client.getCalibrationReport,
  });
}
