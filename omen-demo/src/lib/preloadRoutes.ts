/**
 * Route preload functions for code-split screens.
 * Call on nav link hover/focus to reduce perceived load time.
 */

export const preloadRoutes = {
  overview: () => import('../screens/CommandCenter'),
  pipeline: () => import('../screens/PipelineMonitor'),
  sources: () => import('../screens/SourcesObservatory'),
  partitions: () => import('../screens/PartitionsPage'),
  partitionDetail: () => import('../screens/PartitionDetailPage'),
  signals: () => import('../screens/SignalsPage'),
  operations: () => import('../screens/OperationsScreen'),
  ingestDemo: () => import('../screens/IngestDemoPage'),
  ledgerProof: () => import('../screens/LedgerProofPage'),
} as const;
