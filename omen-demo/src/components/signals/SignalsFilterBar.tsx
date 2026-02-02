import { cn } from '../../lib/utils';
import type { SignalsBrowserFilters } from '../../data/signalsBrowserMock';

const PARTITION_OPTIONS = ['', '2026-01-27', '2026-01-28', '2026-01-29', '2026-01-30'];
const CATEGORY_OPTIONS = [
  '',
  'GEOPOLITICAL',
  'INFRASTRUCTURE',
  'OPERATIONAL',
  'FINANCIAL',
  'CLIMATE',
  'COMPLIANCE',
  'NETWORK',
];
const CONFIDENCE_OPTIONS = ['', 'HIGH', 'MEDIUM', 'LOW'];

export interface SignalsFilterBarProps {
  filters: SignalsBrowserFilters;
  onPartitionChange: (v: string) => void;
  onCategoryChange: (v: string) => void;
  onConfidenceChange: (v: string) => void;
  className?: string;
}

/**
 * Filters: Partition, Category, Confidence dropdowns.
 */
export function SignalsFilterBar({
  filters,
  onPartitionChange,
  onCategoryChange,
  onConfidenceChange,
  className = '',
}: SignalsFilterBarProps) {
  return (
    <div className={cn('flex flex-wrap items-center gap-3', className)}>
      <label className="flex items-center gap-2">
        <span className="text-xs font-medium text-[var(--text-muted)]">Partition</span>
        <select
          value={filters.partition}
          onChange={(e) => onPartitionChange(e.target.value)}
          className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-1.5 font-mono text-sm text-[var(--text-primary)] focus:border-[var(--border-active)] focus:outline-none"
        >
          {PARTITION_OPTIONS.map((p) => (
            <option key={p || 'all'} value={p}>
              {p || 'All'}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2">
        <span className="text-xs font-medium text-[var(--text-muted)]">Category</span>
        <select
          value={filters.category}
          onChange={(e) => onCategoryChange(e.target.value)}
          className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-1.5 font-mono text-sm text-[var(--text-primary)] focus:border-[var(--border-active)] focus:outline-none"
        >
          {CATEGORY_OPTIONS.map((c) => (
            <option key={c || 'all'} value={c}>
              {c || 'All'}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2">
        <span className="text-xs font-medium text-[var(--text-muted)]">Confidence</span>
        <select
          value={filters.confidence}
          onChange={(e) => onConfidenceChange(e.target.value)}
          className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-1.5 font-mono text-sm text-[var(--text-primary)] focus:border-[var(--border-active)] focus:outline-none"
        >
          {CONFIDENCE_OPTIONS.map((c) => (
            <option key={c || 'all'} value={c}>
              {c || 'All'}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
