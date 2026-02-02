import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Table, TableHeader, TableBody, TableHead } from '../ui/Table';
import { SignalRow } from './SignalRow';
import type { SignalBrowserRecord } from '../../data/signalsBrowserMock';

const ROW_HEIGHT = 52;
const VIRTUALIZATION_THRESHOLD = 100;

export interface SignalsTableProps {
  records: SignalBrowserRecord[];
  selectedRecord: SignalBrowserRecord | null;
  onSelectRecord: (record: SignalBrowserRecord | null) => void;
  showPartition?: boolean;
  showSequence?: boolean;
  showObservedAt?: boolean;
  searchQuery?: string;
  pageSize?: number;
  className?: string;
}

/**
 * Signals table: header, optional column toggles, rows. Click row to open drawer.
 * Uses virtual scrolling when record count exceeds VIRTUALIZATION_THRESHOLD.
 */
export function SignalsTable({
  records,
  selectedRecord,
  onSelectRecord,
  showPartition = false,
  showSequence = false,
  showObservedAt = false,
  searchQuery = '',
  pageSize = 10,
  className = '',
}: SignalsTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const total = records.length;
  const useVirtual = total > VIRTUALIZATION_THRESHOLD;
  const showing = useVirtual ? total : Math.min(pageSize, total);

  const virtualizer = useVirtualizer({
    count: total,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 5,
  });

  const virtualItems = useVirtual ? virtualizer.getVirtualItems() : [];
  const totalSize = useVirtual ? virtualizer.getTotalSize() : 0;

  return (
    <div className={className}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-xs text-[var(--text-muted)]">
          Showing {showing} of {total}
          {useVirtual && ' (virtualized)'}
        </span>
      </div>

      {useVirtual ? (
        <div
          ref={parentRef}
          className="h-[600px] overflow-auto overflow-thin-scroll rounded-[var(--radius-card)] border border-[var(--border-subtle)]"
        >
          <table className="w-full border-collapse text-left text-sm font-body table-fixed">
            <thead className="sticky top-0 z-10 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]">
              <tr>
                <th className="w-[140px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Emitted At</th>
                <th className="w-[180px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Signal ID</th>
                <th className="w-[120px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Category</th>
                <th className="min-w-[120px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Title</th>
                <th className="w-[56px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Prob</th>
                <th className="w-[80px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Conf</th>
                {showPartition && <th className="w-[100px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Ledger Partition</th>}
                {showSequence && <th className="w-[80px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Ledger Sequence</th>}
                {showObservedAt && <th className="w-[140px] px-4 py-3 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">Observed At</th>}
                <th className="w-12 px-4 py-3">{' '}</th>
              </tr>
            </thead>
          </table>
          <div
            style={{
              height: `${totalSize}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {virtualItems.map((virtualRow) => {
              const rec = records[virtualRow.index];
              return (
                <div
                  key={rec.signal_id}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <table className="w-full border-collapse text-left text-sm font-body table-fixed">
                    <tbody>
                      <SignalRow
                        record={rec}
                        onClick={() => onSelectRecord(rec)}
                        isSelected={selectedRecord?.signal_id === rec.signal_id}
                        showPartition={showPartition}
                        showSequence={showSequence}
                        showObservedAt={showObservedAt}
                        searchHighlight={searchQuery.trim().length >= 2 ? searchQuery.trim() : undefined}
                      />
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableHead>Emitted At</TableHead>
            <TableHead>Signal ID</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Title</TableHead>
            <TableHead>Prob</TableHead>
            <TableHead>Conf</TableHead>
            {showPartition && <TableHead>Ledger Partition</TableHead>}
            {showSequence && <TableHead>Ledger Sequence</TableHead>}
            {showObservedAt && <TableHead>Observed At</TableHead>}
            <TableHead className="w-12">{' '}</TableHead>
          </TableHeader>
          <TableBody>
            {records.slice(0, pageSize).map((rec) => (
              <SignalRow
                key={rec.signal_id}
                record={rec}
                onClick={() => onSelectRecord(rec)}
                isSelected={selectedRecord?.signal_id === rec.signal_id}
                showPartition={showPartition}
                showSequence={showSequence}
                showObservedAt={showObservedAt}
                searchHighlight={searchQuery.trim().length >= 2 ? searchQuery.trim() : undefined}
              />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
