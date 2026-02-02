import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { useDemoModeContext } from '../../context/DemoModeContext';

export interface CalloutOverlayProps {
  /** Target id or data-demo-target value (for auto-actions) */
  target: string;
  /** Label shown in demo mode (e.g. "Ledger count", "Click to reconcile") */
  label: string;
  children: ReactNode;
  /** Optional position of label */
  position?: 'top' | 'left' | 'right' | 'bottom';
  className?: string;
}

const positionClasses = {
  top: '-top-6 left-0',
  left: 'top-1/2 -left-2 -translate-y-1/2 -translate-x-full',
  right: 'top-1/2 -right-2 -translate-y-1/2 translate-x-full',
  bottom: '-bottom-6 left-0',
};

/**
 * Wraps content and shows a callout label in Demo Mode.
 * Use data-demo-target on the inner element for Play Scene auto-actions.
 */
export function CalloutOverlay({
  target,
  label,
  children,
  position = 'top',
  className = '',
}: CalloutOverlayProps) {
  const { isDemoMode } = useDemoModeContext();

  return (
    <div className={cn('relative inline-block', className)}>
      {children}
      {isDemoMode && (
        <div
          className={cn(
            'absolute z-10 rounded-[var(--radius-badge)] border border-[var(--accent-amber)]/50 bg-[var(--accent-amber)]/10 px-2 py-1 font-mono text-xs text-[var(--accent-amber)] whitespace-nowrap',
            positionClasses[position]
          )}
          data-demo-callout={label}
        >
          [{target}] ← {label}
        </div>
      )}
    </div>
  );
}
