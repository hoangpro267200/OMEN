import { useMemo } from 'react';
import { SignalsScreen } from './SignalsScreen';
import { useSignals } from '../lib/api/hooks';
import type { SignalEvent } from '../lib/api/contracts';
import type { SignalBrowserRecord } from '../data/signalsBrowserMock';

function mapSignalEventToRecord(e: SignalEvent): SignalBrowserRecord {
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

/**
 * Signals page — renders SignalsScreen (browse/search signals, table, drawer).
 * Data from useSignals() only.
 */
export function SignalsPage() {
  const { data: signals = [], isLoading, error } = useSignals();
  const records = useMemo(() => signals.map(mapSignalEventToRecord), [signals]);
  return (
    <SignalsScreen
      signals={records}
      isLoading={isLoading}
      errorMessage={error?.message ?? null}
    />
  );
}
