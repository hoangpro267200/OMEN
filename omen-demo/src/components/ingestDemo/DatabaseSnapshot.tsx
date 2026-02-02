import { Table, TableHeader, TableBody, TableHead } from '../ui/Table';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import type { DatabaseSnapshotRow } from '../../data/ingestDemoMock';

export interface DatabaseSnapshotProps {
  signalId: string;
  row: DatabaseSnapshotRow | null;
  totalRequests: number;
  onRefresh: () => void;
  className?: string;
}

/**
 * Database snapshot: exactly 1 row for the signal; Refresh button; explanation text.
 */
export function DatabaseSnapshot({
  signalId,
  row,
  totalRequests,
  onRefresh,
  className = '',
}: DatabaseSnapshotProps) {
  const hasRow = row !== null;

  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden', className)}>
      <div className="flex items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-3">
        <h3 className="font-mono text-sm font-medium text-[var(--text-primary)]">
          Database Snapshot (processed_signals)
        </h3>
        <Button variant="ghost" onClick={onRefresh} className="h-8 px-2 text-xs">
          Refresh
        </Button>
      </div>
      <div className="p-4">
        <p className="mb-4 font-mono text-sm text-[var(--text-secondary)]">
          Rows for {signalId}: {hasRow ? 1 : 0}
        </p>
        {hasRow ? (
          <Table>
            <TableHeader>
              <TableHead>signal_id</TableHead>
              <TableHead>ack_id</TableHead>
              <TableHead>partition</TableHead>
              <TableHead>source</TableHead>
              <TableHead>at</TableHead>
            </TableHeader>
            <TableBody>
              <tr className="border-b border-[var(--border-subtle)]">
                <td className="px-4 py-2 font-mono text-xs text-[var(--text-primary)]">
                  {row.signal_id}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)]">
                  {row.ack_id}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)]">
                  {row.partition}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)]">
                  {row.source}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)]">
                  {row.at}
                </td>
              </tr>
            </TableBody>
          </Table>
        ) : (
          <div className="rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-6 text-center font-mono text-sm text-[var(--text-muted)]">
            No row yet. Send at least one request to insert.
          </div>
        )}
        {totalRequests > 0 && hasRow && (
          <p className="mt-4 text-sm text-[var(--text-secondary)]">
            Despite {totalRequests} POST request{totalRequests !== 1 ? 's' : ''}, exactly 1 row exists.
            Deduplication works.
          </p>
        )}
      </div>
    </div>
  );
}
