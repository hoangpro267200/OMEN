import { useCallback } from 'react';
import { CodeBlock } from '../ui/CodeBlock';
import { Button } from '../ui/Button';
import { Copy } from 'lucide-react';
import type { SignalBrowserRecord } from '../../data/signalsBrowserMock';

export interface SignalRawTabProps {
  record: SignalBrowserRecord;
}

/**
 * Tab 4: Raw JSON — full record as formatted JSON with Copy JSON button.
 */
export function SignalRawTab({ record }: SignalRawTabProps) {
  const json = JSON.stringify(
    {
      schema_version: record.schema_version,
      signal_id: record.signal_id,
      deterministic_trace_id: record.deterministic_trace_id,
      input_event_hash: record.input_event_hash,
      source_event_id: record.source_event_id,
      ruleset_version: record.ruleset_version,
      observed_at: record.observed_at,
      emitted_at: record.emitted_at,
      ledger_written_at: record.ledger_written_at,
      ledger_partition: record.ledger_partition,
      ledger_sequence: record.ledger_sequence,
      delivery_status: record.delivery_status,
      ack_id: record.ack_id,
      signal: record.signal,
    },
    null,
    2
  );

  const copyJson = useCallback(() => navigator.clipboard.writeText(json), [json]);

  return (
    <div className="space-y-1">
      <h3 className="mb-3 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
        Raw JSON
      </h3>
      <div className="relative">
        <CodeBlock raw={json} language="json" className="max-h-[60vh] overflow-y-auto">{' '}</CodeBlock>
        <div className="mt-2 flex justify-end">
          <Button variant="secondary" onClick={copyJson} className="gap-1 text-xs">
            <Copy className="h-3 w-3" />
            Copy JSON
          </Button>
        </div>
      </div>
    </div>
  );
}
