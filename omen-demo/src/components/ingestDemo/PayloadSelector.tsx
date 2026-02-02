import { cn } from '../../lib/utils';
import type { IngestPayloadOption } from '../../data/ingestDemoMock';

export interface PayloadSelectorProps {
  options: IngestPayloadOption[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}

/**
 * Payload dropdown: OMEN-DEMO001ABCD (Red Sea), OMEN-DEMO002WXYZ (Suez), OMEN-DEMO008LATE (Late arrival), Custom...
 */
export function PayloadSelector({
  options,
  value,
  onChange,
  className = '',
}: PayloadSelectorProps) {
  return (
    <label className={cn('flex flex-col gap-1', className)}>
      <span className="text-xs font-medium text-[var(--text-muted)]">Payload</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] focus:border-[var(--border-active)] focus:outline-none"
      >
        {options.map((opt) => (
          <option key={opt.id} value={opt.id}>
            {opt.label}
          </option>
        ))}
        <option value="custom">Custom... (advanced)</option>
      </select>
    </label>
  );
}
