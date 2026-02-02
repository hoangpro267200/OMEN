import { Table, TableHeader, TableBody, TableHead } from '../ui/Table';
import { Badge } from '../ui/Badge';
import type { ReconcileHistoryEntry } from '../../data/partitionDetailMock';

export interface ReconcileHistoryTableProps {
  entries: ReconcileHistoryEntry[];
  className?: string;
}

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

/**
 * Zone 2: Reconcile History table (collapsed by default).
 */
export function ReconcileHistoryTable({ entries, className = '' }: ReconcileHistoryTableProps) {
  if (entries.length === 0) {
    return (
      <p className="font-mono text-sm text-[var(--text-muted)]">No reconcile runs yet.</p>
    );
  }

  return (
    <Table className={className}>
      <TableHeader>
        <TableHead>Run Time</TableHead>
        <TableHead>Status</TableHead>
        <TableHead>Ledger</TableHead>
        <TableHead>Processed</TableHead>
        <TableHead>Missing</TableHead>
        <TableHead>Replayed</TableHead>
      </TableHeader>
      <TableBody>
        {entries.map((e, i) => (
          <tr
            key={e.runTime + i}
            className="transition-colors hover:bg-[var(--bg-tertiary)]/50"
          >
            <td className="px-4 py-3 font-mono text-sm text-[var(--text-secondary)]">
              {formatDateTime(e.runTime)}
            </td>
            <td className="px-4 py-3">
              <Badge
                variant={
                  e.status === 'COMPLETED'
                    ? 'COMPLETED'
                    : e.status === 'FAILED'
                      ? 'FAILED'
                      : 'PARTIAL'
                }
              >
                {e.status}
              </Badge>
            </td>
            <td className="px-4 py-3 font-mono text-sm tabular-nums text-[var(--text-primary)]">
              {e.ledgerCount}
            </td>
            <td className="px-4 py-3 font-mono text-sm tabular-nums text-[var(--text-primary)]">
              {e.processedCount}
            </td>
            <td className="px-4 py-3 font-mono text-sm tabular-nums text-[var(--text-secondary)]">
              {e.missingCount}
            </td>
            <td className="px-4 py-3 font-mono text-sm tabular-nums text-[var(--text-secondary)]">
              {e.replayedCount}
            </td>
          </tr>
        ))}
      </TableBody>
    </Table>
  );
}
