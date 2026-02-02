import { Button } from '../ui/Button';
import { Copy } from 'lucide-react';
import type { SignalBrowserRecord } from '../../data/signalsBrowserMock';

export interface SignalDeliveryTabProps {
  record: SignalBrowserRecord;
}

function CopyButton({ text }: { text: string; label?: string }) {
  const copy = () => navigator.clipboard.writeText(text);
  return (
    <Button variant="ghost" onClick={copy} className="h-7 px-2 text-xs">
      <Copy className="mr-1 h-3 w-3" />
      Copy
    </Button>
  );
}

/**
 * Tab 3: Delivery — ledger_written_at, ledger_partition, ledger_sequence (seg:0, idx:1), delivery_status, ack_id.
 */
export function SignalDeliveryTab({ record }: SignalDeliveryTabProps) {
  const seg = record.ledger_segment_index ?? 0;
  const idx = record.ledger_sequence ?? 0;
  const seqDisplay = `${record.ledger_sequence ?? '—'} (seg:${seg}, idx:${idx})`;
  const statusDisplay = record.delivery_status
    ? `${record.delivery_status} via ${record.delivery_path ?? 'hot_path'}`
    : '—';

  return (
    <div className="space-y-1">
      <h3 className="mb-3 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
        Delivery
      </h3>
      <div className="space-y-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Ledger Written At</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">
            {record.ledger_written_at ?? '—'}
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Ledger Partition</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">
            {record.ledger_partition ?? '—'}
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Ledger Sequence</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{seqDisplay}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Delivery Status</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{statusDisplay}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Ack ID</span>
          <span className="flex items-center gap-2 font-mono text-sm text-[var(--text-primary)]">
            {record.ack_id ?? '—'}
            {record.ack_id && <CopyButton text={record.ack_id} label="Ack ID" />}
          </span>
        </div>
      </div>
    </div>
  );
}
