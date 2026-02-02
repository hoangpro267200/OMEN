import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { SignalsSearch } from '../components/signals/SignalsSearch';
import { SignalsFilterBar } from '../components/signals/SignalsFilterBar';
import { SignalsTable } from '../components/signals/SignalsTable';
import { SignalDrawer } from '../components/signals/SignalDrawer';
import {
  defaultSignalsBrowserFilters,
  type SignalBrowserRecord,
  type SignalsBrowserFilters,
} from '../data/signalsBrowserMock';

export interface SignalsScreenProps {
  signals?: SignalBrowserRecord[];
  isLoading?: boolean;
  errorMessage?: string | null;
}

const PAGE_SIZE = 10;

function filterBySearch(
  records: SignalBrowserRecord[],
  q: string
): SignalBrowserRecord[] {
  const qq = q.trim().toLowerCase();
  if (!qq) return records;
  return records.filter(
    (r) =>
      r.signal_id.toLowerCase().includes(qq) ||
      r.deterministic_trace_id.toLowerCase().includes(qq) ||
      r.source_event_id.toLowerCase().includes(qq)
  );
}

function filterByFilters(
  records: SignalBrowserRecord[],
  filters: SignalsBrowserFilters
): SignalBrowserRecord[] {
  return records.filter((r) => {
    if (filters.partition && r.ledger_partition !== filters.partition) return false;
    if (filters.category && (r.signal.category as string) !== filters.category) return false;
    if (filters.confidence && (r.signal.confidence_level as string) !== filters.confidence) return false;
    return true;
  });
}

const pageVariants = {
  initial: { opacity: 0, x: 8 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -8 },
};
const pageTransition = { duration: 0.15, ease: 'easeOut' as const };

/**
 * Signals Browser screen: header + search, filters, table, drawer. Empty state when no results.
 */
export function SignalsScreen({
  signals = [],
  isLoading = false,
  errorMessage = null,
}: SignalsScreenProps = {}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<SignalsBrowserFilters>(defaultSignalsBrowserFilters);
  const [selectedRecord, setSelectedRecord] = useState<SignalBrowserRecord | null>(null);
  const [showPartition, setShowPartition] = useState(false);
  const [showSequence, setShowSequence] = useState(false);
  const [showObservedAt, setShowObservedAt] = useState(false);

  // Data comes from props (SignalsPage via useSignals()); never use mock list here.
  const sourceList = signals ?? [];
  const filtered = useMemo(() => {
    const bySearch = filterBySearch(sourceList, searchQuery);
    return filterByFilters(bySearch, filters);
  }, [sourceList, searchQuery, filters]);

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
      {/* Header + Search */}
      <header className="mb-6">
        <h1 className="font-display text-xl font-medium text-[var(--text-primary)]">
          Signals
        </h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          Browse and search emitted signals. Click to view full envelope.
        </p>
        <div className="mt-4">
          <SignalsSearch
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search by signal_id, trace_id, source_event_id..."
            className="max-w-xl"
          />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <SignalsFilterBar
            filters={filters}
            onPartitionChange={(v) => setFilters((f) => ({ ...f, partition: v }))}
            onCategoryChange={(v) => setFilters((f) => ({ ...f, category: v }))}
            onConfidenceChange={(v) => setFilters((f) => ({ ...f, confidence: v }))}
          />
          <span className="font-mono text-xs text-[var(--text-muted)]">
            Showing {Math.min(PAGE_SIZE, filtered.length)} of {filtered.length}
          </span>
        </div>
        {/* Optional columns toggle */}
        <div className="mt-2 flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
            <input
              type="checkbox"
              checked={showPartition}
              onChange={(e) => setShowPartition(e.target.checked)}
              className="rounded border-[var(--border-subtle)] bg-[var(--bg-tertiary)]"
            />
            Ledger Partition
          </label>
          <label className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
            <input
              type="checkbox"
              checked={showSequence}
              onChange={(e) => setShowSequence(e.target.checked)}
              className="rounded border-[var(--border-subtle)] bg-[var(--bg-tertiary)]"
            />
            Ledger Sequence
          </label>
          <label className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
            <input
              type="checkbox"
              checked={showObservedAt}
              onChange={(e) => setShowObservedAt(e.target.checked)}
              className="rounded border-[var(--border-subtle)] bg-[var(--bg-tertiary)]"
            />
            Observed At
          </label>
        </div>
      </header>

      {/* Table or empty state */}
      <section className="mb-6">
        {isEmpty ? (
          <div className="rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-12 text-center">
            <p className="text-[var(--text-secondary)]">
              No signals found. Try adjusting your search or filters.
            </p>
          </div>
        ) : (
          <SignalsTable
            records={filtered}
            selectedRecord={selectedRecord}
            onSelectRecord={setSelectedRecord}
            showPartition={showPartition}
            showSequence={showSequence}
            showObservedAt={showObservedAt}
            searchQuery={searchQuery}
            pageSize={PAGE_SIZE}
          />
        )}
      </section>

      {/* Drawer */}
      <SignalDrawer record={selectedRecord} onClose={() => setSelectedRecord(null)} />
    </motion.div>
  );
}
