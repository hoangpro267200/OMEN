import { cn } from '../../lib/utils';

export interface LoadingSpinnerProps {
  /** Full-screen overlay (centered, optional backdrop) */
  fullscreen?: boolean;
  className?: string;
}

export function LoadingSpinner({ fullscreen = false, className }: LoadingSpinnerProps) {
  const spinner = (
    <div
      className={cn(
        'inline-block h-8 w-8 animate-spin rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent-blue)]',
        className
      )}
      role="status"
      aria-label="Loading"
    />
  );

  if (fullscreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--bg-primary)]/80">
        {spinner}
      </div>
    );
  }

  return spinner;
}
