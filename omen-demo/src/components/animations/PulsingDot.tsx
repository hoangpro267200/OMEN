import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { cn } from '../../lib/utils';

export type PulsingVariant = 'sealed' | 'open' | 'failed' | 'default';

export interface PulsingDotProps {
  variant?: PulsingVariant;
  /** Size in px */
  size?: number;
  className?: string;
}

const variantColors: Record<PulsingVariant, string> = {
  sealed: 'bg-[var(--status-sealed)]',
  open: 'bg-[var(--status-open)]',
  failed: 'bg-[var(--status-failed)]',
  default: 'bg-[var(--text-muted)]',
};

/**
 * Status dot with optional animation:
 * - SEALED/COMPLETED: subtle pulse on first render
 * - OPEN/PARTIAL: gentle breathing (opacity pulse)
 * - FAILED: single shake on render
 */
export function PulsingDot({ variant = 'default', size = 8, className = '' }: PulsingDotProps) {
  const reduced = useReducedMotion();

  const baseClass = cn(
    'rounded-full shrink-0',
    variantColors[variant],
    className
  );
  const style = { width: size, height: size };

  if (reduced) {
    return <span className={baseClass} style={style} aria-hidden />;
  }

  if (variant === 'failed') {
    return (
      <motion.span
        className={baseClass}
        style={style}
        initial={{ x: 0 }}
        animate={{ x: [0, -3, 3, -2, 2, 0] }}
        transition={{ duration: 0.3 }}
        aria-hidden
      />
    );
  }

  if (variant === 'open') {
    return (
      <motion.span
        className={baseClass}
        style={style}
        animate={{ opacity: [1, 0.6, 1] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        aria-hidden
      />
    );
  }

  if (variant === 'sealed') {
    return (
      <motion.span
        className={baseClass}
        style={style}
        initial={{ scale: 0.8, opacity: 0.8 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.25 }}
        aria-hidden
      />
    );
  }

  return <span className={baseClass} style={style} aria-hidden />;
}
