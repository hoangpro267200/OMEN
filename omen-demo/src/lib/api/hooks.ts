/**
 * React Query hooks — the ONLY way screens access data.
 * Screens may import only from this file (and types from contracts).
 * Do NOT import mockClient, demoData, or demoState in screens.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { createApiClient } from './client';
import type { PartitionsQuery, SignalsQuery } from './contracts';
import { useDataSourceMode } from '../mode/store';
import { queryKeys } from './queryKeys';

// Re-create client when mode changes (hooks use getDataSourceMode() so they get fresh client per render when mode toggled)
function useApiClient() {
  const [mode] = useDataSourceMode();
  return useMemo(() => createApiClient(mode), [mode]);
}

export { useDataSourceMode, useApiClient };

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
