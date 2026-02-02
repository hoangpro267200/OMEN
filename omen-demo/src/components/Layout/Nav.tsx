import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface NavProps {
  children?: ReactNode;
  className?: string;
}

/**
 * Side or top navigation — placeholder for demo shell.
 */
export function Nav({ children, className = '' }: NavProps) {
  return (
    <nav
      className={cn(
        'flex items-center gap-4 border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-4 py-3 font-mono text-sm',
        'border-b',
        className
      )}
      aria-label="Main navigation"
    >
      {children ?? (
        <>
          <span className="font-display font-medium text-[var(--text-primary)]">OMEN</span>
          <span className="text-[var(--text-muted)]">Signal Intelligence</span>
        </>
      )}
    </nav>
  );
}
