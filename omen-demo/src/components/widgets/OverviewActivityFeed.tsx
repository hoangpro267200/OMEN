import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

import type { OverviewActivityEvent } from '../../data/overviewMock';

export type { OverviewActivityEvent };

export interface OverviewActivityFeedProps {
  events: OverviewActivityEvent[];
  maxItems?: number;
  className?: string;
}

/**
 * Last N events in real-time feed style: time | id | status | channel.
 */
export function OverviewActivityFeed({
  events,
  maxItems = 10,
  className = '',
}: OverviewActivityFeedProps) {
  const list = events.slice(0, maxItems);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [list.length]);

  return (
    <div
      className={cn(
        'rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden',
        className
      )}
    >
      <div className="border-b border-[var(--border-subtle)] px-4 py-2">
        <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Activity
        </h3>
      </div>
      <div className="max-h-64 overflow-y-auto overflow-thin-scroll">
        {list.length === 0 ? (
          <div className="px-4 py-6 text-center font-mono text-xs text-[var(--text-muted)]">
            No events yet
          </div>
        ) : (
          list.map((event, i) => (
            <motion.div
              key={`${event.time}-${event.id}-${i}`}
              initial={{ opacity: 0, x: 4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-center gap-3 border-b border-[var(--border-subtle)] px-4 py-2 last:border-0 hover:bg-[var(--bg-tertiary)]/50"
            >
              <span className="shrink-0 font-mono text-xs tabular-nums text-[var(--text-muted)]">
                {event.time}
              </span>
              <span className="shrink-0 font-mono text-xs text-[var(--text-primary)]">
                {event.id}
              </span>
              <span
                className={cn(
                  'shrink-0 font-mono text-xs',
                  event.status === 'Delivered' && 'text-[var(--accent-green)]',
                  event.status === 'Duplicate' && 'text-[var(--accent-amber)]',
                  event.status === 'Failed' && 'text-[var(--accent-red)]',
                  !['Delivered', 'Duplicate', 'Failed'].includes(event.status) && 'text-[var(--text-secondary)]'
                )}
              >
                {event.status}
              </span>
              <span className="ml-auto shrink-0 font-mono text-xs text-[var(--text-muted)]">
                {event.channel}
              </span>
            </motion.div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
