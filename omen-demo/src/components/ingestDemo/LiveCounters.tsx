import { useCallback } from 'react';
import { motion } from 'framer-motion';
import { Copy } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';

export interface LiveCountersProps {
  count200: number;
  count409: number;
  lastAckId: string | null;
  /** Trigger flash: '200' | '409' | null */
  lastIncrement?: '200' | '409' | null;
  className?: string;
}

/**
 * Live counters: 200 (Accepted), 409 (Duplicates), Last Ack ID with Copy.
 * Counters tick up with pop animation; 200 green flash, 409 amber flash.
 */
export function LiveCounters({
  count200,
  count409,
  lastAckId,
  lastIncrement = null,
  className = '',
}: LiveCountersProps) {
  const copyAck = useCallback(() => {
    if (lastAckId) navigator.clipboard.writeText(lastAckId);
  }, [lastAckId]);

  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6', className)}>
      <h3 className="mb-4 text-center font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
        Response Summary
      </h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* 200 Accepted */}
        <motion.div
          key={`200-${count200}`}
          initial={lastIncrement === '200' ? { scale: 1.15 } : false}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          className={cn(
            'rounded-[var(--radius-card)] border p-4 text-center transition-colors',
            lastIncrement === '200'
              ? 'border-[var(--accent-green)] bg-[var(--accent-green)]/15'
              : 'border-[var(--border-subtle)] bg-[var(--bg-tertiary)]'
          )}
        >
          <div className="font-mono text-2xl font-bold tabular-nums text-[var(--text-primary)]">
            {count200}
          </div>
          <div className="mt-1 font-mono text-lg font-medium text-[var(--text-muted)]">200</div>
          <div className="mt-0.5 text-xs font-medium text-[var(--text-secondary)]">Accepted</div>
        </motion.div>

        {/* 409 Duplicates */}
        <motion.div
          key={`409-${count409}`}
          initial={lastIncrement === '409' ? { scale: 1.15 } : false}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          className={cn(
            'rounded-[var(--radius-card)] border p-4 text-center transition-colors',
            lastIncrement === '409'
              ? 'border-[var(--accent-amber)] bg-[var(--accent-amber)]/15'
              : 'border-[var(--border-subtle)] bg-[var(--bg-tertiary)]'
          )}
        >
          <div className="font-mono text-2xl font-bold tabular-nums text-[var(--text-primary)]">
            {count409}
          </div>
          <div className="mt-1 font-mono text-lg font-medium text-[var(--text-muted)]">409</div>
          <div className="mt-0.5 text-xs font-medium text-[var(--text-secondary)]">Duplicates</div>
        </motion.div>

        {/* Last Ack ID */}
        <div className="rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-4">
          <div className="text-xs font-medium text-[var(--text-muted)]">Last Ack ID</div>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
            <span className="font-mono text-sm text-[var(--text-primary)] break-all">
              {lastAckId ?? '—'}
            </span>
            {lastAckId && (
              <Button variant="ghost" onClick={copyAck} className="h-8 px-2 text-xs">
                <Copy className="mr-1 h-3 w-3" />
                Copy
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
