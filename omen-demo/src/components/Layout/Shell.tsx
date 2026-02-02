import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface ShellProps {
  children: ReactNode;
  className?: string;
}

/**
 * Main app shell — full viewport, Mission Control layout.
 */
export function Shell({ children, className = '' }: ShellProps) {
  return (
    <div
      className={cn(
        'flex h-full w-full flex-col bg-[var(--bg-primary)] text-[var(--text-primary)]',
        className
      )}
    >
      {children}
    </div>
  );
}
