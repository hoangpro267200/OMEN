import { useMemo } from 'react';
import { SignalsScreen } from './SignalsScreen';
import { useSignals } from '../lib/api/hooks';
import type { SignalEvent, OmenSignal } from '../lib/api/contracts';
import type { SignalBrowserRecord } from '../data/signalsBrowserMock';

/**
 * Map API signal response to SignalBrowserRecord format.
 * The API can return either:
 * 1. Nested format (mock/demo): { signal_id, ..., signal: { title, probability, ... } }
 * 2. Flat format (live API): { signal_id, title, probability, ... } 
 * 
 * This function handles both cases.
 */
function mapSignalEventToRecord(e: SignalEvent | Record<string, unknown>): SignalBrowserRecord {
  // Check if this is already a nested format (has signal property with title)
  const hasNestedSignal = e.signal && typeof e.signal === 'object' && 'title' in (e.signal as object);
  
  if (hasNestedSignal) {
    // Already in correct format (mock/demo data)
    return {
      ...e,
      ledger_written_at: e.ledger_written_at ?? null,
      ledger_partition: e.ledger_partition ?? null,
      ledger_sequence: e.ledger_sequence ?? null,
      delivery_status: 'DELIVERED',
      ack_id: null,
      delivery_path: 'hot_path',
    } as SignalBrowserRecord;
  }
  
  // Flat format from live API - need to construct the nested structure
  const flat = e as Record<string, unknown>;
  const signalId = (flat.signal_id as string) || '';
  const now = new Date().toISOString();
  
  // Build the nested signal object from flat fields
  const signal: OmenSignal = {
    signal_id: signalId,
    source_event_id: (flat.source_event_id as string) || '',
    title: (flat.title as string) || 'Unknown Signal',
    probability: typeof flat.probability === 'number' ? flat.probability : 0.5,
    confidence_score: typeof flat.confidence_score === 'number' ? flat.confidence_score : 0.5,
    confidence_level: ((flat.confidence_level as string) || 'MEDIUM') as OmenSignal['confidence_level'],
    category: ((flat.category as string) || 'GEOPOLITICAL') as OmenSignal['category'],
    trace_id: (flat.trace_id as string) || '',
    ruleset_version: (flat.ruleset_version as string) || '1.0.0',
    generated_at: (flat.generated_at as string) || now,
  };
  
  return {
    schema_version: '1.0.0',
    signal_id: signalId,
    deterministic_trace_id: (flat.trace_id as string) || signalId,
    input_event_hash: `sha256:${signalId.toLowerCase()}`,
    source_event_id: signal.source_event_id,
    ruleset_version: signal.ruleset_version,
    observed_at: (flat.generated_at as string) || now,
    emitted_at: (flat.generated_at as string) || now,
    signal,
    ledger_written_at: (flat.ledger_written_at as string) ?? null,
    ledger_partition: (flat.ledger_partition as string) ?? null,
    ledger_sequence: (flat.ledger_sequence as number) ?? null,
    delivery_status: 'DELIVERED',
    ack_id: null,
    delivery_path: 'hot_path',
  } as SignalBrowserRecord;
}

/**
 * Signals page — renders SignalsScreen (browse/search signals, table, drawer).
 * Data from useSignals() only.
 */
export function SignalsPage() {
  const { data: signals = [], isLoading, error, refetch } = useSignals();
  const records = useMemo(() => signals.map(mapSignalEventToRecord), [signals]);
  return (
    <SignalsScreen
      signals={records}
      isLoading={isLoading}
      errorMessage={error?.message ?? null}
      onRetry={refetch}
    />
  );
}
