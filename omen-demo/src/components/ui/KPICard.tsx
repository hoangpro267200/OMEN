import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface KPICardProps {
  label: string;
  value: string | number;
  /** Optional trend: e.g. "+12%" or "-5%" */
  trend?: string;
  trendUp?: boolean;
  /** Optional subtitle or unit */
  subtitle?: string;
  /** Size: default (xl) or hero (48px value) */
  size?: 'default' | 'hero';
  className?: string;
  children?: ReactNode;
}

export function KPICard({
  label,
  value,
  trend,
  trendUp,
  subtitle,
  size = 'default',
  className = '',
  children,
}: KPICardProps) {
  const valueSize = size === 'hero' ? 'text-[2.5rem] md:text-[3rem]' : 'text-xl';
  return (
    <motion.div
      className={cn(
        'rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-4',
        size === 'hero' && 'bg-gradient-to-br from-[var(--bg-secondary)] to-[var(--bg-tertiary)]',
        className
      )}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] font-mono">
        {label}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className={cn('font-mono font-medium text-[var(--text-primary)] tabular-nums', valueSize)}>
          {value}
        </span>
        {trend != null && (
          <span
            className={cn(
              'text-xs font-mono',
              trendUp === true && 'text-[var(--accent-green)]',
              trendUp === false && 'text-[var(--accent-red)]',
              trendUp == null && 'text-[var(--text-secondary)]'
            )}
          >
            {trend}
          </span>
        )}
      </div>
      {subtitle != null && (
        <div className="mt-0.5 text-xs text-[var(--text-muted)]">{subtitle}</div>
      )}
      {children}
    </motion.div>
  );
}
