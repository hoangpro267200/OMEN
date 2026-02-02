import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

/** Status variants for OMEN (SEALED, OPEN, LATE, COMPLETED, FAILED, PARTIAL, etc.) */
export type BadgeVariant =
  | 'SEALED'
  | 'OPEN'
  | 'LATE'
  | 'main'
  | 'FAILED'
  | 'COMPLETED'
  | 'PARTIAL'
  | 'skipped'
  | 'high'
  | 'medium'
  | 'low'
  | 'delivered'
  | 'duplicate'
  | '200'
  | '409'
  | 'default'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info';

export interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  SEALED: 'bg-[var(--status-sealed)]/20 text-[var(--status-sealed)] border-[var(--status-sealed)]/40',
  OPEN: 'bg-[var(--status-open)]/20 text-[var(--status-open)] border-[var(--status-open)]/40',
  LATE: 'bg-[var(--status-late)]/20 text-[var(--status-late)] border-[var(--status-late)]/40',
  main: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border-[var(--border-subtle)]',
  FAILED: 'bg-[var(--status-failed)]/20 text-[var(--status-failed)] border-[var(--status-failed)]/40',
  COMPLETED: 'bg-[var(--status-completed)]/20 text-[var(--status-completed)] border-[var(--status-completed)]/40',
  PARTIAL: 'bg-[var(--status-partial)]/20 text-[var(--status-partial)] border-[var(--status-partial)]/40',
  skipped: 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] border-[var(--border-subtle)]',
  high: 'bg-[var(--accent-green)]/20 text-[var(--accent-green)] border-[var(--accent-green)]/40',
  medium: 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border-[var(--accent-amber)]/40',
  low: 'bg-[var(--accent-red)]/20 text-[var(--accent-red)] border-[var(--accent-red)]/40',
  delivered: 'bg-[var(--accent-green)]/20 text-[var(--accent-green)] border-[var(--accent-green)]/40',
  duplicate: 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border-[var(--accent-amber)]/40',
  '200': 'bg-[var(--accent-green)]/20 text-[var(--accent-green)] border-[var(--accent-green)]/40',
  '409': 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border-[var(--accent-amber)]/40',
  default: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border-[var(--border-subtle)]',
  success: 'bg-[var(--accent-green)]/20 text-[var(--accent-green)] border-[var(--accent-green)]/40',
  warning: 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border-[var(--accent-amber)]/40',
  danger: 'bg-[var(--accent-red)]/20 text-[var(--accent-red)] border-[var(--accent-red)]/40',
  info: 'bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border-[var(--accent-blue)]/40',
};

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-[var(--radius-badge)] text-xs font-medium border font-mono',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
