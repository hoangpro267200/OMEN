import { useMemo } from 'react';
import { IngestDemoScreen } from './IngestDemoScreen';
import { useSignals, useIngestSignal, useResetDemoState } from '../lib/api/hooks';
import type { SignalEvent } from '../lib/api/contracts';
import type { IngestPayloadOption } from '../data/ingestDemoMock';

/**
 * Ingest Demo page — idempotent delivery demo (200 first, 409 duplicates, same ack_id).
 * Data from useSignals (payload options) + useIngestSignal / useResetDemoState.
 */
export function IngestDemoPage() {
  const { data: signals = [] } = useSignals();
  const ingestMutation = useIngestSignal();
  const resetMutation = useResetDemoState();

  const payloadOptions: IngestPayloadOption[] = useMemo(
    () =>
      signals.map((s) => ({
        id: s.signal_id,
        label: s.signal.title,
        payloadJson: JSON.stringify(s),
      })),
    [signals]
  );

  const onIngest = async (event: SignalEvent) => {
    return ingestMutation.mutateAsync(event);
  };
  const onReset = () => resetMutation.mutate();

  return (
    <IngestDemoScreen
      payloadOptions={payloadOptions.length ? payloadOptions : [{ id: 'custom', label: 'Custom', payloadJson: '{}' }]}
      onIngest={onIngest}
      onReset={onReset}
      isSending={ingestMutation.isPending}
      error={ingestMutation.error?.message ?? null}
    />
  );
}
