import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Table, TableHeader, TableBody, TableHead } from '../ui/Table';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import type { RequestLogEntry } from '../../data/ingestDemoMock';

export interface RequestLogProps {
  entries: RequestLogEntry[];
  onClear: () => void;
  className?: string;
}

/**
 * Request log: real-time feed. New rows slide in from top; 200 green flash, 409 amber; Duplicate Yes/No badge.
 */
export function RequestLog({ entries, onClear, className = '' }: RequestLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [entries.length]);

  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden', className)}>
      <div className="flex items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-3">
        <h3 className="font-mono text-sm font-medium text-[var(--text-primary)]">Request Log</h3>
        <Button variant="ghost" onClick={onClear} className="h-8 px-2 text-xs">
          Clear Log
        </Button>
      </div>
      <div className="max-h-[320px] overflow-y-auto overflow-thin-scroll" ref={scrollRef}>
        <Table>
          <TableHeader>
            <TableHead>Time</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Signal ID</TableHead>
            <TableHead>Ack ID</TableHead>
            <TableHead>Duplicate</TableHead>
          </TableHeader>
          <TableBody>
            <AnimatePresence initial={false}>
              {entries.map((entry, i) => (
                <motion.tr
                  key={`${entry.time}-${i}`}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className={cn(
                    'border-b border-[var(--border-subtle)]',
                    entry.status === 200 && 'bg-[var(--accent-green)]/10',
                    entry.status === 409 && 'bg-[var(--accent-amber)]/10'
                  )}
                >
                  <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)] whitespace-nowrap">
                    {entry.time}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={cn(
                        'inline-flex items-center px-2 py-0.5 rounded-[var(--radius-badge)] text-xs font-medium font-mono',
                        entry.status === 200
                          ? 'bg-[var(--accent-green)]/20 text-[var(--accent-green)]'
                          : 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)]'
                      )}
                    >
                      {entry.status === 200 ? '200 ✓' : '409'}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-[var(--text-primary)]">
                    {entry.signal_id}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)]">
                    {entry.ack_id}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={cn(
                        'inline-flex items-center px-2 py-0.5 rounded-[var(--radius-badge)] text-xs font-medium',
                        entry.duplicate
                          ? 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)]'
                          : 'bg-[var(--accent-green)]/20 text-[var(--accent-green)]'
                      )}
                    >
                      {entry.duplicate ? 'Yes' : 'No'}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </TableBody>
        </Table>
        {entries.length === 0 && (
          <div className="px-4 py-8 text-center font-mono text-sm text-[var(--text-muted)]">
            No requests yet. Send 1 or more to see the log.
          </div>
        )}
      </div>
    </div>
  );
}
