import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { DURATION, EASING } from '../../lib/animationConstants';
import { cn } from '../../lib/utils';

export interface AnimatedProgressBarProps {
  /** 0–100 or 0–1 (if max=1) */
  value: number;
  max?: number;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  className?: string;
  /** Stagger delay in ms (for sequential bars) */
  staggerDelay?: number;
  label?: string;
}

const variantFill: Record<string, string> = {
  default: 'bg-[var(--accent-blue)]',
  success: 'bg-[var(--accent-green)]',
  warning: 'bg-[var(--accent-amber)]',
  danger: 'bg-[var(--accent-red)]',
};

/**
 * Progress bar that animates from 0 to value. Smooth width transition.
 * Respects reduced motion (instant fill).
 */
export function AnimatedProgressBar({
  value,
  max = 100,
  variant = 'default',
  className = '',
  staggerDelay = 0,
  label,
}: AnimatedProgressBarProps) {
  const reduced = useReducedMotion();
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn('w-full', className)}>
      {label != null && (
        <div className="mb-1 text-xs font-mono text-[var(--text-muted)]">{label}</div>
      )}
      <div className="h-2 overflow-hidden rounded-full border border-[var(--border-subtle)] bg-[var(--bg-tertiary)]">
        <motion.div
          className={cn('h-full rounded-full', variantFill[variant])}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{
            duration: reduced ? 0 : DURATION.progress / 1000,
            delay: reduced ? 0 : staggerDelay / 1000,
            ease: EASING.easeOut,
          }}
        />
      </div>
    </div>
  );
}
