import { useCallback } from 'react';
import { Copy } from 'lucide-react';
import { Button } from '../ui/Button';
import type { SignalBrowserRecord } from '../../data/signalsBrowserMock';

export interface SignalEnvelopeTabProps {
  record: SignalBrowserRecord;
}

function CopyButton({ text }: { text: string; label?: string }) {
  const copy = useCallback(() => navigator.clipboard.writeText(text), [text]);
  return (
    <Button variant="ghost" onClick={copy} className="h-7 px-2 text-xs">
      <Copy className="mr-1 h-3 w-3" />
      Copy
    </Button>
  );
}

/**
 * Tab 1: Envelope (SignalEvent) — schema_version, signal_id, trace_id, input_event_hash, source_event_id, ruleset_version, observed_at, emitted_at.
 */
export function SignalEnvelopeTab({ record }: SignalEnvelopeTabProps) {
  return (
    <div className="space-y-1">
      <h3 className="mb-3 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
        Envelope (SignalEvent)
      </h3>
      <div className="space-y-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Schema Version</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{record.schema_version}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Signal ID</span>
          <span className="flex items-center gap-2 font-mono text-sm text-[var(--text-primary)]">
            {record.signal_id}
            <CopyButton text={record.signal_id} label="Signal ID" />
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Trace ID</span>
          <span className="flex items-center gap-2 font-mono text-sm text-[var(--text-primary)]">
            {record.deterministic_trace_id}
            <CopyButton text={record.deterministic_trace_id} label="Trace ID" />
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Input Event Hash</span>
          <span className="font-mono text-sm text-[var(--text-secondary)]">{record.input_event_hash}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Source Event ID</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{record.source_event_id}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Ruleset Version</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{record.ruleset_version}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Observed At</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{record.observed_at}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Emitted At</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{record.emitted_at}</span>
        </div>
      </div>
    </div>
  );
}
