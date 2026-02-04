/**
 * OMEN Hooks - Centralized export for all custom hooks
 */

// Unified Data System
export { useUnifiedData, createUnifiedDataHook } from './useUnifiedData';
export type { UseUnifiedDataOptions, UseUnifiedDataResult } from './useUnifiedData';

// Signal Data Hooks
export {
  useSignals,
  useSignalDetail,
  usePipelineStats,
  useSystemStats,
  useDataSources,
  useActivityFeed,
  useSignalSearch,
  useExplanationChain,
} from './useSignalData';

export type {
  UseSignalsOptions,
  UseSignalDetailOptions,
  UsePipelineStatsOptions,
  UseSystemStatsOptions,
  UseDataSourcesOptions,
  UseActivityFeedOptions,
  SignalSearchParams,
  Signal,
  SignalListResponse,
  PipelineStats,
  SystemStats,
  DataSource,
  ActivityItem,
  ExplanationStep,
} from './useSignalData';

// Existing hooks (re-export for convenience)
export { useDataSource } from './useDataSource';
export { useDemoMode } from './useDemoMode';
export { useKeyboardShortcuts } from './useKeyboardShortcuts';
export { useOmenApi, useProcessLiveSignals, useSystemStats as useOmenSystemStats, useActivityFeed as useOmenActivityFeed } from './useOmenApi';
export { useRealtimePrices } from './useRealtimePrices';
export { useReducedMotion } from './useReducedMotion';
export { useSignalStats } from './useSignalStats';
