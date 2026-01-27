import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

interface MainPanelProps {
  children: ReactNode;
  className?: string;
}

export function MainPanel({ children, className }: MainPanelProps) {
  return (
    <main
      className={cn(
        'flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden bg-[var(--bg-primary)]',
        className
      )}
    >
      {children}
    </main>
  );
}
