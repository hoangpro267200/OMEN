import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Filter } from 'lucide-react';
import { PartitionsFilterBar } from '../components/partitions/PartitionsFilterBar';
import { PartitionsTable } from '../components/partitions/PartitionsTable';
import { Button } from '../components/ui/Button';
import { ROUTES } from '../lib/routes';
import {
  defaultPartitionsFilters,
  type LedgerPartition,
  type PartitionsFilters,
} from '../data/partitionsMock';

export interface PartitionsScreenProps {
  partitions?: LedgerPartition[];
  isLoading?: boolean;
  errorMessage?: string | null;
}

const pageVariants = {
  initial: { opacity: 0, x: 8 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -8 },
};
const pageTransition = { duration: 0.15, ease: 'easeOut' as const };

function filterPartitions(
  partitions: LedgerPartition[],
  filters: PartitionsFilters
): LedgerPartition[] {
  return partitions.filter((p) => {
    const date = p.partitionDate.replace(/-late$/, '');
    if (filters.dateFrom && date < filters.dateFrom) return false;
    if (filters.dateTo && date > filters.dateTo) return false;
    if (filters.status !== 'all' && p.status !== filters.status) return false;
    if (!filters.includeLate && p.type === 'LATE') return false;
    if (filters.needsReconcileOnly && !p.needsReconcile) return false;
    return true;
  });
}

function computeSummary(partitions: LedgerPartition[]) {
  const sealed = partitions.filter((p) => p.status === 'SEALED').length;
  const open = partitions.filter((p) => p.status === 'OPEN').length;
  const late = partitions.filter((p) => p.type === 'LATE').length;
  const totalRecords = partitions.reduce((s, p) => s + p.totalRecords, 0);
  return { total: partitions.length, sealed, open, late, totalRecords };
}

/**
 * Partitions List screen: header, filter bar, table, context panel on hover, summary bar, empty state.
 */
export function PartitionsScreen({
  partitions = [],
  isLoading = false,
  errorMessage = null,
}: PartitionsScreenProps = {}) {
  const [filters, setFilters] = useState<PartitionsFilters>(defaultPartitionsFilters);
  const [showFilters, setShowFilters] = useState(true);

  const filtered = useMemo(
    () => filterPartitions(partitions, filters),
    [partitions, filters]
  );
  const summary = useMemo(() => computeSummary(filtered), [filtered]);
  const isEmpty = filtered.length === 0;

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      className="min-h-full p-4 md:p-6"
    >
      {errorMessage && (
        <div className="mb-4 rounded-[var(--radius-card)] border border-[var(--accent-red)]/50 bg-[var(--accent-red)]/10 px-4 py-3 text-sm text-[var(--accent-red)]">
          {errorMessage}
        </div>
      )}
      {isLoading && (
        <div className="mb-4 h-12 rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] skeleton" />
      )}
      {/* Header */}
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-xl font-medium text-[var(--text-primary)]">
            Partitions
          </h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            Ledger partitions by emitted_at date. Sealed = immutable.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowFilters((v) => !v)}
          className="flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--border-subtle)]/30"
        >
          <Filter className="h-4 w-4" />
          {showFilters ? 'Hide filters' : 'Filters'}
        </button>
      </header>

      {/* Filter bar */}
      {showFilters && (
        <PartitionsFilterBar
          dateFrom={filters.dateFrom}
          dateTo={filters.dateTo}
          onDateFromChange={(v) => setFilters((f) => ({ ...f, dateFrom: v }))}
          onDateToChange={(v) => setFilters((f) => ({ ...f, dateTo: v }))}
          status={filters.status}
          onStatusChange={(v) => setFilters((f) => ({ ...f, status: v }))}
          includeLate={filters.includeLate}
          onIncludeLateChange={(v) => setFilters((f) => ({ ...f, includeLate: v }))}
          needsReconcileOnly={filters.needsReconcileOnly}
          onNeedsReconcileOnlyChange={(v) => setFilters((f) => ({ ...f, needsReconcileOnly: v }))}
          showFilters={showFilters}
          onToggleFilters={() => setShowFilters((v) => !v)}
          className="mb-6"
        />
      )}

      {/* Table */}
      <section className="mb-6">
        {isEmpty ? (
          <div className="rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-12 text-center">
            <p className="text-[var(--text-secondary)]">
              No partitions in selected range. Adjust filters or run Ingest Demo.
            </p>
            <Link to={ROUTES.ingestDemo} className="mt-4 inline-block">
              <Button variant="primary">Run Ingest Demo</Button>
            </Link>
          </div>
        ) : (
          <PartitionsTable partitions={filtered} showContextPanel />
        )}
      </section>

      {/* Summary bar */}
      <footer className="rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-4 py-3 font-mono text-sm text-[var(--text-secondary)]">
        Total: {summary.total} partition{summary.total !== 1 ? 's' : ''} · {summary.sealed} sealed ·{' '}
        {summary.open} open · {summary.late} late · {summary.totalRecords} total records
      </footer>
    </motion.div>
  );
}
