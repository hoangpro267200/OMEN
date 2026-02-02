import { cn } from '../../lib/utils';
import type { WalSegment } from '../../data/ledgerProofMock';

export interface SegmentSelectorProps {
  partitions: string[];
  segments: WalSegment[];
  selectedPartition: string;
  selectedSegment: string;
  onPartitionChange: (p: string) => void;
  onSegmentChange: (filename: string) => void;
  className?: string;
}

/**
 * Partition dropdown, Segment dropdown; Status, Records, Size for selected segment.
 */
export function SegmentSelector({
  partitions,
  segments,
  selectedPartition,
  selectedSegment,
  onPartitionChange,
  onSegmentChange,
  className = '',
}: SegmentSelectorProps) {
  const filteredSegments = segments.filter((s) => s.partition === selectedPartition);
  const current =
    filteredSegments.find((s) => s.filename === selectedSegment) ?? filteredSegments[0];

  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-4', className)}>
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-[var(--text-muted)]">Partition</span>
          <select
            value={selectedPartition}
            onChange={(e) => onPartitionChange(e.target.value)}
            className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] focus:border-[var(--border-active)] focus:outline-none"
          >
            {partitions.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-[var(--text-muted)]">Segment</span>
          <select
            value={selectedSegment}
            onChange={(e) => onSegmentChange(e.target.value)}
            className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] focus:border-[var(--border-active)] focus:outline-none min-w-[180px]"
          >
            {filteredSegments.map((s) => (
              <option key={s.filename} value={s.filename}>
                {s.filename}
              </option>
            ))}
          </select>
        </label>
        {current && (
          <div className="flex flex-wrap items-center gap-4 font-mono text-sm text-[var(--text-secondary)]">
            <span>
              Status:{' '}
              <span className="text-[var(--status-sealed)]">{current.status}</span>
              {current.status === 'SEALED' && ' (read-only)'}
            </span>
            <span>Records: {current.recordCount}</span>
            <span>Size: {current.sizeBytes.toLocaleString()} bytes</span>
          </div>
        )}
      </div>
    </div>
  );
}
