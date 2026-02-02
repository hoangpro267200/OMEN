import { Link, useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Badge } from '../ui/Badge';
import { ROUTES } from '../../lib/routes';
import type { LedgerPartition } from '../../data/partitionsMock';

export interface PartitionRowProps {
  partition: LedgerPartition;
  onHover: (p: LedgerPartition | null) => void;
  isHovered: boolean;
}

function formatReconcile(partition: LedgerPartition): string {
  const prefix = partition.reconcileStatus === 'COMPLETED' ? '✓' : '—';
  return `${prefix} ${partition.reconcileStatus}`;
}

function formatDateTimeShort(iso: string | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

/**
 * Table row for one partition: clickable, hover highlights and triggers context panel in parent.
 */
export function PartitionRow({ partition, onHover, isHovered }: PartitionRowProps) {
  const navigate = useNavigate();
  const detailPath = `${ROUTES.partitions}/${encodeURIComponent(partition.partitionDate)}`;

  const typeBadgeVariant = partition.type === 'LATE' ? 'LATE' : 'default';
  const statusBadgeVariant = partition.status === 'SEALED' ? 'SEALED' : 'OPEN';
  const reconcileVariant =
    partition.reconcileStatus === 'COMPLETED'
      ? 'COMPLETED'
      : partition.reconcileStatus === 'SKIPPED'
        ? 'default'
        : partition.reconcileStatus === 'FAILED'
          ? 'FAILED'
          : 'PARTIAL';

  return (
    <tr
      onMouseEnter={() => onHover(partition)}
      onMouseLeave={() => onHover(null)}
      onClick={() => navigate(detailPath)}
      className={cn(
        'cursor-pointer border-b border-[var(--border-subtle)] transition-colors last:border-0',
        isHovered && 'bg-[var(--bg-tertiary)]/50'
      )}
    >
      <td className="px-4 py-3">
        <Link
          to={detailPath}
          className="font-mono text-sm text-[var(--accent-blue)] hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {partition.partitionDate}
        </Link>
      </td>
      <td className="px-4 py-3">
        <Badge variant={typeBadgeVariant}>{partition.type}</Badge>
      </td>
      <td className="px-4 py-3">
        <Badge variant={statusBadgeVariant}>{partition.status}</Badge>
      </td>
      <td className="px-4 py-3 font-mono text-sm text-[var(--text-primary)] tabular-nums">
        {partition.totalRecords}
      </td>
      <td className="px-4 py-3 font-mono text-sm text-[var(--text-secondary)] tabular-nums">
        {partition.highwaterSequence}
      </td>
      <td className="px-4 py-3 font-mono text-sm text-[var(--text-secondary)] tabular-nums">
        {partition.segmentCount}
      </td>
      <td className="px-4 py-3">
        <span
          title={partition.reconcileTimestamp ? formatDateTimeShort(partition.reconcileTimestamp) : undefined}
          className="inline-block"
        >
          <Badge variant={reconcileVariant}>{formatReconcile(partition)}</Badge>
        </span>
      </td>
      <td className="w-24 px-4 py-3 text-right">
        {isHovered && (
          <span className="inline-flex items-center gap-0.5 text-xs font-medium text-[var(--accent-blue)]">
            View <ChevronRight className="h-3 w-3" />
          </span>
        )}
      </td>
    </tr>
  );
}
