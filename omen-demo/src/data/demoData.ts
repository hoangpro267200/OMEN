/**
 * Demo data — deterministic seed data for mock client.
 * Used only by mockClient; screens must not import this file.
 */

import type { SignalEvent, Partition, OverviewStats, OverviewActivityItem } from '../lib/api/contracts';

function buildSignalEvent(
  i: number,
  title: string,
  category: SignalEvent['signal']['category']
): SignalEvent {
  const id = `OMEN-DEMO${String(i).padStart(3, '0')}`;
  const traceId = `trace-${id.toLowerCase().slice(-6)}`;
  const emitted = `2026-01-28T10:00:0${i % 10}Z`;
  return {
    schema_version: '1.0.0',
    signal_id: id,
    deterministic_trace_id: traceId,
    input_event_hash: `sha256:${id.toLowerCase()}`,
    source_event_id: `evt-${String(i).padStart(3, '0')}`,
    ruleset_version: '1.0.0',
    observed_at: '2026-01-28T10:00:00Z',
    emitted_at: emitted,
    ledger_written_at: emitted,
    ledger_partition: '2026-01-28',
    ledger_sequence: i,
    signal: {
      signal_id: id,
      source_event_id: `evt-${String(i).padStart(3, '0')}`,
      title,
      probability: 0.5 + (i % 5) * 0.1,
      confidence_score: 0.6 + (i % 4) * 0.1,
      confidence_level: (i % 3 === 0 ? 'HIGH' : i % 3 === 1 ? 'MEDIUM' : 'LOW') as 'HIGH' | 'MEDIUM' | 'LOW',
      category,
      trace_id: traceId,
      ruleset_version: '1.0.0',
      generated_at: emitted,
    },
  };
}

export function getDemoSignalEvents(): SignalEvent[] {
  const titles = [
    'Red Sea transit disruption',
    'Suez canal delay projected',
    'Port congestion alert',
    'Supply chain bottleneck',
    'Currency volatility impact',
    'Storm track update',
    'Regulatory filing deadline',
    'Network outage recovery',
    'Late report: port congestion',
    'Insurance premium spike',
  ];
  const categories: SignalEvent['signal']['category'][] = [
    'GEOPOLITICAL',
    'INFRASTRUCTURE',
    'OPERATIONAL',
    'FINANCIAL',
    'CLIMATE',
    'COMPLIANCE',
    'NETWORK',
    'GEOPOLITICAL',
    'INFRASTRUCTURE',
    'FINANCIAL',
  ];
  return Array.from({ length: 10 }, (_, i) =>
    buildSignalEvent(i + 1, titles[i], categories[i])
  );
}

export function getDemoPartitions(): Partition[] {
  const segment = {
    file: 'signals-001.wal',
    record_count: 10,
    size_bytes: 8192,
    checksum: 'crc32:deadbeef',
    is_sealed: true,
  };
  return [
    {
      partition_date: '2026-01-28',
      type: 'MAIN',
      status: 'SEALED',
      total_records: 10,
      highwater_sequence: 10,
      segments: [segment],
      manifest: {
        schema_version: '1.0.0',
        partition_date: '2026-01-28',
        sealed_at: '2026-01-29T04:00:00Z',
        total_records: 10,
        highwater_sequence: 10,
        manifest_revision: 1,
        is_late_partition: false,
        segments: [segment],
      },
      reconcile_state: {
        partition_date: '2026-01-28',
        last_reconcile_at: '2026-01-29T05:00:00Z',
        ledger_highwater: 10,
        manifest_revision: 1,
        ledger_record_count: 10,
        processed_count: 8,
        missing_count: 2,
        status: 'PARTIAL',
        replayed_ids: [],
      },
    },
    {
      partition_date: '2026-01-28-late',
      type: 'LATE',
      status: 'OPEN',
      total_records: 1,
      highwater_sequence: 1,
      segments: [
        { file: 'signals-late-001.wal', record_count: 1, size_bytes: 1024, checksum: 'crc32:abc', is_sealed: false },
      ],
    },
  ];
}

export function getDemoOverviewStats(activity: OverviewActivityItem[]): OverviewStats {
  return {
    signals_today: 247,
    signals_trend: '↑ 12%',
    signals_trend_up: true,
    hot_path_ok: 245,
    hot_path_pct: '99.2%',
    duplicates: 2,
    duplicates_sub: '(409s)',
    partitions_sealed: 1,
    partitions_open: 1,
    partitions_sub: 'sealed/open',
    last_reconcile: '2m ago ✓',
    last_reconcile_status: 'COMPLETED',
    activity_feed: activity,
  };
}

export function getDemoActivityFeed(): OverviewActivityItem[] {
  return [
    { time: '10:05:32', id: 'OMEN-DEMO007', status: 'Delivered', channel: 'hot_path' },
    { time: '10:05:30', id: 'OMEN-DEMO006', status: 'Delivered', channel: 'hot_path' },
    { time: '10:05:28', id: 'OMEN-DEMO005', status: 'Duplicate', channel: '409' },
    { time: '10:05:25', id: 'OMEN-DEMO004', status: 'Delivered', channel: 'hot_path' },
    { time: '10:05:22', id: 'OMEN-DEMO003', status: 'Delivered', channel: 'hot_path' },
    { time: '10:05:18', id: 'OMEN-DEMO002', status: 'Duplicate', channel: '409' },
    { time: '10:05:15', id: 'OMEN-DEMO001', status: 'Delivered', channel: 'hot_path' },
  ];
}
