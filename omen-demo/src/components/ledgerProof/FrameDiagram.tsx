import { cn } from '../../lib/utils';

export interface FrameDiagramProps {
  className?: string;
}

/**
 * Static visual: WAL record frame = [4 bytes LENGTH][4 bytes CRC32][N bytes PAYLOAD].
 */
export function FrameDiagram({ className = '' }: FrameDiagramProps) {
  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6', className)}>
      <h3 className="mb-4 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
        WAL Record Frame
      </h3>
      <div className="overflow-x-auto">
        <div className="inline-flex min-w-0 border border-[var(--border-subtle)]">
          <div className="border-r border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-3 text-center">
            <div className="font-mono text-xs font-medium text-[var(--text-muted)]">4 bytes</div>
            <div className="mt-1 font-mono text-sm text-[var(--text-primary)]">LENGTH</div>
            <div className="mt-0.5 text-xs text-[var(--text-secondary)]">(big-endian)</div>
          </div>
          <div className="border-r border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-3 text-center">
            <div className="font-mono text-xs font-medium text-[var(--text-muted)]">4 bytes</div>
            <div className="mt-1 font-mono text-sm text-[var(--text-primary)]">CRC32</div>
            <div className="mt-0.5 text-xs text-[var(--text-secondary)]">(big-endian)</div>
          </div>
          <div className="bg-[var(--bg-tertiary)] px-6 py-3 text-center">
            <div className="font-mono text-xs font-medium text-[var(--text-muted)]">N bytes</div>
            <div className="mt-1 font-mono text-sm text-[var(--text-primary)]">PAYLOAD</div>
            <div className="mt-0.5 text-xs text-[var(--text-secondary)]">(SignalEvent JSON)</div>
          </div>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-[var(--text-muted)]">
        <div>Payload size (e.g., 500)</div>
        <div>Checksum of payload bytes</div>
        <div>UTF-8 JSON (exclude_none)</div>
      </div>
      <div className="mt-4 rounded border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-2 font-mono text-xs text-[var(--text-secondary)] break-all">
        Example: [0x000001f4][0x1a2b3c4d][{`{"signal_id":"OMEN-DEMO001",...}`}]
      </div>
    </div>
  );
}
