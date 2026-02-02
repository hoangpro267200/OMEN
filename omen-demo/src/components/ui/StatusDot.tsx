import { cn } from '../../lib/utils';

export type StatusDotVariant = 'live' | 'idle' | 'error' | 'success' | 'warning';

export interface StatusDotProps {
  variant?: StatusDotVariant;
  /** Optional label beside the dot */
  label?: string;
  className?: string;
}

const variantStyles: Record<StatusDotVariant, string> = {
  live: 'bg-[var(--accent-green)] animate-pulse-dot shadow-[0_0_0_0_var(--accent-green)]',
  idle: 'bg-[var(--text-muted)]',
  error: 'bg-[var(--accent-red)]',
  success: 'bg-[var(--status-completed)]',
  warning: 'bg-[var(--accent-amber)]',
};

export function StatusDot({ variant = 'live', label, className = '' }: StatusDotProps) {
  const pulse = variant === 'live';

  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span
        className={cn(
          'h-2 w-2 shrink-0 rounded-full',
          pulse && 'animate-pulse-dot',
          variantStyles[variant]
        )}
        style={pulse ? { boxShadow: '0 0 0 0 var(--accent-green)' } : undefined}
      />
      {label != null && (
        <span className="text-xs font-mono text-[var(--text-secondary)]">{label}</span>
      )}
    </span>
  );
}
