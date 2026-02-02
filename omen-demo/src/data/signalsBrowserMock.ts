/**
 * Signals Browser — types and mock data for the Signals screen.
 * Full envelope + delivery for table and drawer.
 */

import type {
  SignalEventEnvelope,
  OmenSignalResponse,
  ConfidenceLevel,
} from '../lib/omen-types';

/** Category for Signals Browser (badge colors: GEOPOLITICAL=red, INFRASTRUCTURE=blue, etc.) */
export type SignalsBrowserCategory =
  | 'GEOPOLITICAL'
  | 'INFRASTRUCTURE'
  | 'OPERATIONAL'
  | 'FINANCIAL'
  | 'CLIMATE'
  | 'COMPLIANCE'
  | 'NETWORK';

/** Delivery status for drawer tab */
export type DeliveryStatusDisplay =
  | 'DELIVERED'
  | 'PENDING'
  | 'FAILED';

/** Full signal record for list + drawer (envelope + delivery) */
export interface SignalBrowserRecord extends SignalEventEnvelope {
  /** Delivery: when written to ledger */
  ledger_written_at?: string | null;
  ledger_partition?: string | null;
  ledger_sequence?: number | null;
  /** Segment index for display (seg:0, idx:1) */
  ledger_segment_index?: number;
  delivery_status?: DeliveryStatusDisplay;
  ack_id?: string | null;
  delivery_path?: 'hot_path' | 'reconcile';
}

export interface SignalsBrowserFilters {
  partition: string;
  category: string;
  confidence: string;
}

export const defaultSignalsBrowserFilters: SignalsBrowserFilters = {
  partition: '',
  category: '',
  confidence: '',
};

/** Build mock envelope + delivery for one signal */
function buildRecord(
  signalId: string,
  traceId: string,
  sourceEventId: string,
  inputHash: string,
  observedAt: string,
  emittedAt: string,
  payload: {
    title: string;
    category: SignalsBrowserCategory;
    probability: number;
    confidence_score: number;
    confidence_level: ConfidenceLevel;
    generated_at: string;
  },
  delivery: {
    ledger_written_at: string;
    ledger_partition: string;
    ledger_sequence: number;
    ledger_segment_index?: number;
    delivery_status: DeliveryStatusDisplay;
    ack_id: string | null;
    delivery_path: 'hot_path' | 'reconcile';
  }
): SignalBrowserRecord {
  const signal: OmenSignalResponse = {
    signal_id: signalId,
    source_event_id: sourceEventId,
    signal_type: 'UNCLASSIFIED',
    status: 'ACTIVE',
    impact_hints: { domains: [], direction: '', affected_asset_types: [], keywords: [] },
    title: payload.title,
    description: null,
    probability: payload.probability,
    probability_source: 'model',
    probability_is_estimate: false,
    confidence_score: payload.confidence_score,
    confidence_level: payload.confidence_level,
    confidence_factors: {},
    category: payload.category,
    tags: [],
    geographic: { regions: [], chokepoints: [] },
    temporal: { event_horizon: null, resolution_date: null },
    evidence: [],
    trace_id: traceId,
    ruleset_version: '1.0.0',
    source_url: null,
    observed_at: observedAt,
    generated_at: payload.generated_at,
  };
  return {
    schema_version: '1.0.0',
    signal_id: signalId,
    deterministic_trace_id: traceId,
    input_event_hash: inputHash,
    source_event_id: sourceEventId,
    ruleset_version: '1.0.0',
    observed_at: observedAt,
    emitted_at: emittedAt,
    signal,
    ledger_written_at: delivery.ledger_written_at,
    ledger_partition: delivery.ledger_partition,
    ledger_sequence: delivery.ledger_sequence,
    ledger_segment_index: delivery.ledger_segment_index,
    delivery_status: delivery.delivery_status,
    ack_id: delivery.ack_id,
    delivery_path: delivery.delivery_path,
  };
}

/** Default mock list: 36 signals, mix of categories and dates */
export const defaultSignalsBrowserList: SignalBrowserRecord[] = [
  buildRecord(
    'OMEN-DEMO001ABCD',
    'a1b2c3d4e5f6g7h8',
    'evt-001',
    'sha256:abc123',
    '2026-01-28T10:00:00Z',
    '2026-01-28T10:00:05Z',
    {
      title: 'Red Sea transit disruption',
      category: 'GEOPOLITICAL',
      probability: 0.72,
      confidence_score: 0.85,
      confidence_level: 'HIGH',
      generated_at: '2026-01-28T10:00:05Z',
    },
    {
      ledger_written_at: '2026-01-28T10:00:05Z',
      ledger_partition: '2026-01-28',
      ledger_sequence: 1,
      ledger_segment_index: 0,
      delivery_status: 'DELIVERED',
      ack_id: 'riskcast-ack-1',
      delivery_path: 'hot_path',
    }
  ),
  buildRecord(
    'OMEN-DEMO002WXYZ',
    'b2c3d4e5f6g7h8i9',
    'evt-002',
    'sha256:def456',
    '2026-01-28T11:00:00Z',
    '2026-01-28T11:00:02Z',
    {
      title: 'Suez canal delay projected',
      category: 'INFRASTRUCTURE',
      probability: 0.55,
      confidence_score: 0.6,
      confidence_level: 'MEDIUM',
      generated_at: '2026-01-28T11:00:02Z',
    },
    {
      ledger_written_at: '2026-01-28T11:00:02Z',
      ledger_partition: '2026-01-28',
      ledger_sequence: 2,
      ledger_segment_index: 0,
      delivery_status: 'DELIVERED',
      ack_id: 'riskcast-ack-2',
      delivery_path: 'hot_path',
    }
  ),
  buildRecord(
    'OMEN-DEMO008LATE',
    'c3d4e5f6g7h8i9j0',
    'evt-008',
    'sha256:ghi789',
    '2026-01-29T01:55:00Z',
    '2026-01-29T02:00:00Z',
    {
      title: 'Late report: port congestion',
      category: 'GEOPOLITICAL',
      probability: 0.6,
      confidence_score: 0.55,
      confidence_level: 'MEDIUM',
      generated_at: '2026-01-29T02:00:00Z',
    },
    {
      ledger_written_at: '2026-01-29T02:00:00Z',
      ledger_partition: '2026-01-29',
      ledger_sequence: 1,
      ledger_segment_index: 0,
      delivery_status: 'DELIVERED',
      ack_id: 'riskcast-ack-8',
      delivery_path: 'reconcile',
    }
  ),
];

/* Generate more rows to reach ~36 */
const extraTitles: { title: string; category: SignalsBrowserCategory }[] = [
  { title: 'Supply chain bottleneck', category: 'OPERATIONAL' },
  { title: 'Currency volatility impact', category: 'FINANCIAL' },
  { title: 'Storm track update', category: 'CLIMATE' },
  { title: 'Regulatory filing deadline', category: 'COMPLIANCE' },
  { title: 'Network outage recovery', category: 'NETWORK' },
  { title: 'Port strike risk', category: 'GEOPOLITICAL' },
  { title: 'Pipeline maintenance', category: 'INFRASTRUCTURE' },
  { title: 'Labor shortage alert', category: 'OPERATIONAL' },
  { title: 'Insurance premium spike', category: 'FINANCIAL' },
  { title: 'Drought impact on shipping', category: 'CLIMATE' },
  { title: 'Sanctions compliance check', category: 'COMPLIANCE' },
  { title: 'API rate limit change', category: 'NETWORK' },
];

for (let i = 4; i <= 36; i++) {
  const idx = (i - 4) % extraTitles.length;
  const item = extraTitles[idx];
  const day = 27 + Math.floor(i / 15);
  const hour = (i % 24);
  const pad = (n: number) => String(n).padStart(2, '0');
  const partition = `2026-01-${pad(day)}`;
  const observedAt = `2026-01-${pad(day)}T${pad(hour)}:00:00Z`;
  const emittedAt = `2026-01-${pad(day)}T${pad(hour)}:00:0${i % 10}Z`;
  const signalId = `OMEN-DEMO${String(i).padStart(3, '0')}${['A', 'B', 'C', 'D', 'E', 'F'][i % 6]}${['X', 'Y', 'Z', 'W', 'V', 'U'][i % 6]}`;
  defaultSignalsBrowserList.push(
    buildRecord(
      signalId,
      `trace-${i}-${Date.now()}`,
      `evt-${String(i).padStart(3, '0')}`,
      `sha256:${signalId.toLowerCase()}`,
      observedAt,
      emittedAt,
      {
        title: item.title,
        category: item.category,
        probability: 0.4 + (i % 6) * 0.1,
        confidence_score: 0.5 + (i % 5) * 0.1,
        confidence_level: (i % 3 === 0 ? 'HIGH' : i % 3 === 1 ? 'MEDIUM' : 'LOW') as ConfidenceLevel,
        generated_at: emittedAt,
      },
      {
        ledger_written_at: emittedAt,
        ledger_partition: partition,
        ledger_sequence: i,
        ledger_segment_index: Math.floor(i / 10),
        delivery_status: i % 10 === 0 ? 'PENDING' : 'DELIVERED',
        ack_id: i % 10 === 0 ? null : `riskcast-ack-${i}`,
        delivery_path: i % 7 === 0 ? 'reconcile' : 'hot_path',
      }
    )
  );
}
