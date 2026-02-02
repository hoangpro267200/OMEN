import { motion } from 'framer-motion';
import { Filter } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { PartitionStatus } from '../../data/partitionsMock';

export interface PartitionsFilterBarProps {
  dateFrom: string;
  dateTo: string;
  onDateFromChange: (v: string) => void;
  onDateToChange: (v: string) => void;
  status: 'all' | PartitionStatus;
  onStatusChange: (v: 'all' | PartitionStatus) => void;
  includeLate: boolean;
  onIncludeLateChange: (v: boolean) => void;
  needsReconcileOnly: boolean;
  onNeedsReconcileOnlyChange: (v: boolean) => void;
  showFilters: boolean;
  onToggleFilters: () => void;
  className?: string;
}

const STATUS_OPTIONS: { value: 'all' | PartitionStatus; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'SEALED', label: 'Sealed' },
  { value: 'OPEN', label: 'Open' },
];

/**
 * Filter bar: date range, status dropdown, Include Late toggle, Needs Reconcile.
 */
export function PartitionsFilterBar({
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  status,
  onStatusChange,
  includeLate,
  onIncludeLateChange,
  needsReconcileOnly,
  onNeedsReconcileOnlyChange,
  showFilters,
  onToggleFilters,
  className = '',
}: PartitionsFilterBarProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        'rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-4',
        className
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-xs font-medium text-[var(--text-muted)]">Date range:</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => onDateFromChange(e.target.value)}
            className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-1.5 font-mono text-sm text-[var(--text-primary)]"
            aria-label="From date"
          />
          <span className="text-[var(--text-muted)]">–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => onDateToChange(e.target.value)}
            className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-1.5 font-mono text-sm text-[var(--text-primary)]"
            aria-label="To date"
          />
          <span className="text-xs font-medium text-[var(--text-muted)]">Status:</span>
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value as 'all' | PartitionStatus)}
            className="rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-1.5 font-mono text-sm text-[var(--text-primary)]"
            aria-label="Status filter"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={includeLate}
              onChange={(e) => onIncludeLateChange(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border-subtle)] bg-[var(--bg-tertiary)] text-[var(--accent-blue)]"
            />
            <span className="text-sm text-[var(--text-secondary)]">Include Late</span>
          </label>
          {showFilters && (
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={needsReconcileOnly}
                onChange={(e) => onNeedsReconcileOnlyChange(e.target.checked)}
                className="h-4 w-4 rounded border-[var(--border-subtle)] bg-[var(--bg-tertiary)] text-[var(--accent-blue)]"
              />
              <span className="text-sm text-[var(--text-secondary)]">Needs Reconcile</span>
            </label>
          )}
        </div>
        <button
          type="button"
          onClick={onToggleFilters}
          className={cn(
            'flex items-center gap-2 rounded-[var(--radius-button)] border px-3 py-1.5 text-sm font-medium transition-colors',
            showFilters
              ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)]/10 text-[var(--accent-blue)]'
              : 'border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
          )}
        >
          <Filter className="h-4 w-4" />
          {showFilters ? 'Hide filters' : 'Filters'}
        </button>
      </div>
    </motion.div>
  );
}
