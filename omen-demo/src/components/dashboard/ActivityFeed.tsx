import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import type { ActivityFeedItem } from '../../types/omen';

const typeColors: Record<ActivityFeedItem['type'], string> = {
  signal: 'text-[var(--accent-cyan)]',
  validation: 'text-[var(--accent-green)]',
  translation: 'text-[var(--accent-blue)]',
  alert: 'text-[var(--accent-orange)]',
  source: 'text-[var(--text-tertiary)]',
};

interface ActivityFeedProps {
  items: ActivityFeedItem[];
  maxItems?: number;
  className?: string;
}

export function ActivityFeed({ items, maxItems = 50, className }: ActivityFeedProps) {
  const list = items.slice(0, maxItems);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [list.length]);

  return (
    <div
      className={cn(
        'flex flex-col bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded-xl overflow-hidden',
        className
      )}
    >
      <div className="px-4 py-2 border-b border-[var(--border-subtle)]">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          Hoạt động trực tiếp
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto overflow-thin-scroll max-h-48 min-h-[120px]">
        {list.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            className="px-4 py-2 border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-hover)]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className={cn('text-sm', typeColors[item.type])}>
                {item.message}
              </span>
              <span className="text-xs text-[var(--text-muted)] shrink-0">
                {item.time}
              </span>
            </div>
          </motion.div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
