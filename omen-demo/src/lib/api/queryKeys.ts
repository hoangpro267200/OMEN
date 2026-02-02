/** Central React Query keys for OMEN data layer. */

export const queryKeys = {
  overview: ['omen', 'overview'] as const,
  partitions: (q?: Record<string, unknown>) => ['omen', 'partitions', q ?? {}] as const,
  partitionDetail: (partitionDate: string) => ['omen', 'partition', partitionDate] as const,
  partitionDiff: (partitionDate: string) => ['omen', 'partition', partitionDate, 'diff'] as const,
  signals: (q?: Record<string, unknown>) => ['omen', 'signals', q ?? {}] as const,
  ledgerSegments: (partitionDate: string) => ['omen', 'ledger', partitionDate, 'segments'] as const,
  ledgerFrame: (partitionDate: string, segmentFile: string, frameIndex: number) =>
    ['omen', 'ledger', partitionDate, segmentFile, frameIndex] as const,
};
