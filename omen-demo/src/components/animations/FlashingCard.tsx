import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { TRANSITION } from '../../lib/animationConstants';
import { cn } from '../../lib/utils';

export type FlashVariant = 'green' | 'amber' | 'default';

export interface FlashingCardProps {
  children: ReactNode;
  /** Trigger flash when this value changes (e.g. count) */
  flashKey?: number | string;
  /** green = 200/success, amber = 409/duplicate */
  flashVariant?: FlashVariant;
  className?: string;
}

const flashStyles: Record<FlashVariant, string> = {
  green: 'border-[var(--accent-green)] bg-[var(--accent-green)]/15',
  amber: 'border-[var(--accent-amber)] bg-[var(--accent-amber)]/15',
  default: 'border-[var(--border-subtle)] bg-[var(--bg-tertiary)]',
};

/**
 * Card that "pops" (scale) and flashes background when flashKey changes.
 * Use for live counters (200 = green, 409 = amber).
 */
export function FlashingCard({
  children,
  flashKey,
  flashVariant = 'default',
  className = '',
}: FlashingCardProps) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      key={flashKey}
      initial={reduced ? false : { scale: 1.15 }}
      animate={{ scale: 1 }}
      transition={TRANSITION.pop}
      className={cn(
        'rounded-[var(--radius-card)] border p-4 text-center transition-colors',
        flashKey != null && flashVariant !== 'default' ? flashStyles[flashVariant] : flashStyles.default,
        className
      )}
    >
      {children}
    </motion.div>
  );
}
