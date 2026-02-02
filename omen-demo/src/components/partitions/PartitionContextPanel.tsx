import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { LedgerPartition } from '../../data/partitionsMock';
import { ROUTES } from '../../lib/routes';

export interface PartitionContextPanelProps {
  partition: LedgerPartition;
  className?: string;
}

function formatDateTime(iso: string | undefined): string {
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
 * Context panel shown on row hover: partition summary + Open Detail link.
 */
export function PartitionContextPanel({ partition, className = '' }: PartitionContextPanelProps) {
  const detailPath = `${ROUTES.partitions}/${encodeURIComponent(partition.partitionDate)}`;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      transition={{ duration: 0.15 }}
      className={cn(
        'absolute right-0 top-0 z-10 w-64 rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-4 shadow-lg',
        className
      )}
    >
      <div className="font-mono text-sm font-medium text-[var(--text-primary)]">
        {partition.partitionDate}{' '}
        <span className="text-[var(--text-muted)]">({partition.status})</span>
      </div>
      <dl className="mt-3 space-y-1.5 text-xs">
        <div>
          <dt className="text-[var(--text-muted)]">Sealed at</dt>
          <dd className="font-mono text-[var(--text-secondary)]">
            {formatDateTime(partition.sealedAt)}
          </dd>
        </div>
        <div>
          <dt className="text-[var(--text-muted)]">Total records</dt>
          <dd className="font-mono text-[var(--text-secondary)]">{partition.totalRecords}</dd>
        </div>
        <div>
          <dt className="text-[var(--text-muted)]">Segments</dt>
          <dd className="font-mono text-[var(--text-secondary)]">
            {partition.segmentNames?.join(', ') ?? partition.segmentCount}
          </dd>
        </div>
        {partition.manifestChecksum && (
          <div>
            <dt className="text-[var(--text-muted)]">Manifest checksum</dt>
            <dd className="break-all font-mono text-[var(--text-secondary)]">
              {partition.manifestChecksum}
            </dd>
          </div>
        )}
      </dl>
      <Link
        to={detailPath}
        className="mt-4 flex w-full items-center justify-center gap-1 rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:border-[var(--accent-blue)] hover:text-[var(--accent-blue)]"
      >
        Open Detail <ChevronRight className="h-4 w-4" />
      </Link>
    </motion.div>
  );
}
