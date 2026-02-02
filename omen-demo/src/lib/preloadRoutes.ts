/**
 * Route preload functions for code-split screens.
 * Call on nav link hover/focus to reduce perceived load time.
 */

export const preloadRoutes = {
  overview: () => import('../screens/OverviewPage'),
  partitions: () => import('../screens/PartitionsPage'),
  partitionDetail: () => import('../screens/PartitionDetailPage'),
  signals: () => import('../screens/SignalsPage'),
  ingestDemo: () => import('../screens/IngestDemoPage'),
  ledgerProof: () => import('../screens/LedgerProofPage'),
} as const;
