/**
 * Shared test data for E2E and integration tests.
 */

export const testSignal = {
  signal_id: 'test-signal-001',
  deterministic_trace_id: 'trace-001',
  source_event_id: 'evt-001',
  emitted_at: new Date().toISOString(),
  signal: {
    category: 'COMPLIANCE',
    title: 'Test signal',
    probability: 0.95,
    confidence_level: 'HIGH',
  },
  ledger_partition: null,
  ledger_sequence: null,
  ledger_written_at: null,
};

export const testPartition = {
  partitionDate: '2026-01-30',
  status: 'SEALED' as const,
  totalRecords: 150,
  type: 'ON_TIME' as const,
  needsReconcile: false,
};

export const mockApiResponses = {
  overview: {
    signals_today: 1250,
    signals_trend: '+12%',
    signals_trend_up: true,
    hot_path_ok: 1200,
    hot_path_pct: '96%',
    duplicates: 5,
    duplicates_sub: '0.4%',
    partitions_sealed: 28,
    partitions_open: 2,
    partitions_sub: '30 total',
    last_reconcile: '2026-01-30T00:00:00Z',
    last_reconcile_status: 'OK',
    activity_feed: [],
  },
  signals: [testSignal],
  partitions: [testPartition],
};
