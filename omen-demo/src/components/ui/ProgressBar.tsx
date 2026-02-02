import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface ProgressBarProps {
  /** 0–100 */
  value: number;
  max?: number;
  /** Optional label (e.g. "75%" or "3/4") */
  label?: string;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  className?: string;
  showValue?: boolean;
}

const variantFill: Record<string, string> = {
  default: 'bg-[var(--accent-blue)]',
  success: 'bg-[var(--accent-green)]',
  warning: 'bg-[var(--accent-amber)]',
  danger: 'bg-[var(--accent-red)]',
};

export function ProgressBar({
  value,
  max = 100,
  label,
  variant = 'default',
  className = '',
  showValue = false,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn('w-full', className)}>
      {(label != null || showValue) && (
        <div className="mb-1 flex justify-between text-xs font-mono text-[var(--text-muted)]">
          {label != null && <span>{label}</span>}
          {showValue && <span>{Math.round(pct)}%</span>}
        </div>
      )}
      <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-tertiary)] border border-[var(--border-subtle)]">
        <motion.div
          className={cn('h-full rounded-full', variantFill[variant])}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}
