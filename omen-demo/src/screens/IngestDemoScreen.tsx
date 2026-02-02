import { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import type { RequestLogEntry } from '../data/ingestDemoMock';
import type { DatabaseSnapshotRow } from '../data/ingestDemoMock';
import type { IngestPayloadOption } from '../data/ingestDemoMock';
import type { IngestResponse } from '../lib/api/contracts';
import { playTick } from '../lib/soundFx';
import { PayloadSelector } from '../components/ingestDemo/PayloadSelector';
import { PayloadPreview } from '../components/ingestDemo/PayloadPreview';
import { IngestButtons } from '../components/ingestDemo/IngestButtons';
import { LiveCounters } from '../components/ingestDemo/LiveCounters';
import { RequestLog } from '../components/ingestDemo/RequestLog';
import { DatabaseSnapshot } from '../components/ingestDemo/DatabaseSnapshot';

const pageVariants = {
  initial: { opacity: 0, x: 8 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -8 },
};
const pageTransition = { duration: 0.15, ease: 'easeOut' as const };

function nowTime(): string {
  return new Date().toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export interface IngestDemoScreenProps {
  payloadOptions: IngestPayloadOption[];
  onIngest: (event: import('../lib/api/contracts').SignalEvent) => Promise<IngestResponse>;
  onReset: () => void;
  isSending?: boolean;
  error?: string | null;
}

/**
 * Ingest Demo screen: idempotent delivery demo. POST same signal → 200 first, 409 duplicates, same ack_id.
 * Uses onIngest/onReset from props (hooks); no direct mock ingest.
 */
export function IngestDemoScreen({
  payloadOptions,
  onIngest,
  onReset,
  isSending = false,
  error: propError = null,
}: IngestDemoScreenProps) {
  const [selectedPayloadId, setSelectedPayloadId] = useState(payloadOptions[0]?.id ?? 'custom');
  const [count200, setCount200] = useState(0);
  const [count409, setCount409] = useState(0);
  const [lastAckId, setLastAckId] = useState<string | null>(null);
  const [lastIncrement, setLastIncrement] = useState<'200' | '409' | null>(null);
  const [logEntries, setLogEntries] = useState<RequestLogEntry[]>([]);
  const [localError, setLocalError] = useState<string | null>(null);
  const error = propError ?? localError;

  const payloadJson =
    payloadOptions.find((o) => o.id === selectedPayloadId)?.payloadJson ?? payloadOptions[0]?.payloadJson ?? '{}';

  const sendOne = useCallback(async () => {
    let event: import('../lib/api/contracts').SignalEvent;
    try {
      event = JSON.parse(payloadJson) as import('../lib/api/contracts').SignalEvent;
    } catch {
      return;
    }
    if (!event.signal_id) return;
    setLocalError(null);
    try {
      const res = await onIngest(event);
      if (res.status_code === 400 || res.status_code >= 500) {
        setLocalError(res.status_code === 400 ? 'Validation error (400)' : 'Server error. Try again.');
        return;
      }
      if (res.status_code === 200 && res.ack_id) {
        playTick();
        setCount200((c) => c + 1);
        setLastAckId(res.ack_id);
        setLastIncrement('200');
        setLogEntries((prev) => [
          ...prev,
          { time: nowTime(), status: 200, signal_id: res.signal_id, ack_id: res.ack_id, duplicate: false },
        ]);
      } else if (res.status_code === 409 && res.ack_id) {
        playTick();
        setCount409((c) => c + 1);
        setLastAckId(res.ack_id);
        setLastIncrement('409');
        setLogEntries((prev) => [
          ...prev,
          { time: nowTime(), status: 409, signal_id: res.signal_id, ack_id: res.ack_id, duplicate: true },
        ]);
      }
      setTimeout(() => setLastIncrement(null), 400);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Network error');
    }
  }, [payloadJson, onIngest]);

  const sendN = useCallback(
    async (n: number) => {
      let event: import('../lib/api/contracts').SignalEvent;
      try {
        event = JSON.parse(payloadJson) as import('../lib/api/contracts').SignalEvent;
      } catch {
        return;
      }
      if (!event.signal_id) return;
      setLocalError(null);
      for (let i = 0; i < n; i++) {
        try {
          const res = await onIngest(event);
          if (res.status_code === 400 || res.status_code >= 500) {
            setLocalError(res.status_code === 400 ? 'Validation error (400)' : 'Server error. Try again.');
            return;
          }
          if (res.status_code === 200 && res.ack_id) {
            playTick();
            setCount200((c) => c + 1);
            setLastAckId(res.ack_id);
            setLastIncrement('200');
            setLogEntries((prev) => [
              ...prev,
              { time: nowTime(), status: 200, signal_id: res.signal_id, ack_id: res.ack_id, duplicate: false },
            ]);
          } else if (res.status_code === 409 && res.ack_id) {
            playTick();
            setCount409((c) => c + 1);
            setLastAckId(res.ack_id);
            setLastIncrement('409');
            setLogEntries((prev) => [
              ...prev,
              { time: nowTime(), status: 409, signal_id: res.signal_id, ack_id: res.ack_id, duplicate: true },
            ]);
          }
          setTimeout(() => setLastIncrement(null), 400);
          if (i < n - 1) await new Promise((r) => setTimeout(r, 120));
        } catch (err) {
          setLocalError(err instanceof Error ? err.message : 'Network error');
          return;
        }
      }
    },
    [payloadJson, onIngest]
  );

  const onClear = useCallback(() => {
    onReset();
    setLogEntries([]);
    setCount200(0);
    setCount409(0);
    setLastAckId(null);
    setLastIncrement(null);
    setLocalError(null);
  }, [onReset]);

  const onClearLog = useCallback(() => setLogEntries([]), []);

  const dbSignalId = selectedPayloadId === 'custom' ? payloadOptions[0]?.id ?? 'custom' : selectedPayloadId;
  const dbRow: DatabaseSnapshotRow | null = useMemo(() => {
    const last = [...logEntries].reverse().find((e) => e.signal_id === dbSignalId);
    if (!last) return null;
    return {
      signal_id: last.signal_id,
      ack_id: last.ack_id,
      partition: '-',
      source: 'hot_path',
      at: last.time,
    };
  }, [logEntries, dbSignalId]);
  const totalRequests = logEntries.length;

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      className="min-h-full p-4 md:p-6"
    >
      {/* Hero */}
      <header className="mb-6 rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6">
        <h1 className="font-display text-xl font-medium text-[var(--text-primary)]">
          Ingest Demo: Idempotent Delivery
        </h1>
        <p className="mt-3 text-sm text-[var(--text-secondary)]">
          POST the same signal multiple times. First gets 200 + ack_id. Duplicates get 409 + SAME
          ack_id. Database has exactly 1 row.
        </p>
        <p className="mt-2 text-sm font-medium text-[var(--accent-green)]">
          This proves: exactly-once semantics at the consumer level.
        </p>
      </header>

      {/* Controls */}
      <section className="mb-6">
        <div className="mb-4">
          <PayloadSelector
            options={payloadOptions}
            value={selectedPayloadId}
            onChange={setSelectedPayloadId}
          />
        </div>
        <div className="mb-4">
          <PayloadPreview json={payloadJson} />
        </div>
        <div className="mt-4">
          <IngestButtons
            onSend1={() => sendOne()}
            onSend5={() => sendN(5)}
            onSend20={() => sendN(20)}
            onClear={onClear}
            disabled={isSending}
          />
        </div>
        {error && (
          <div className="mt-4 rounded-[var(--radius-card)] border border-[var(--accent-red)]/50 bg-[var(--accent-red)]/10 px-4 py-3 text-sm text-[var(--accent-red)]">
            {error}
          </div>
        )}
      </section>

      {/* Live Counters */}
      <section className="mb-6">
        <LiveCounters
          count200={count200}
          count409={count409}
          lastAckId={lastAckId}
          lastIncrement={lastIncrement}
        />
      </section>

      {/* Request Log */}
      <section className="mb-6">
        <RequestLog entries={logEntries} onClear={onClearLog} />
      </section>

      {/* Database Snapshot */}
      <section>
        <DatabaseSnapshot
          signalId={dbSignalId}
          row={dbRow}
          totalRequests={totalRequests}
          onRefresh={() => {}}
        />
      </section>
    </motion.div>
  );
}
