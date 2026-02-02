import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { DURATION } from '../../lib/animationConstants';
import { cn } from '../../lib/utils';

export interface SlideInRowProps {
  children: ReactNode;
  flashVariant?: 'green' | 'amber' | 'none';
  className?: string;
}

const flashBg: Record<string, string> = {
  green: 'bg-[var(--accent-green)]/10',
  amber: 'bg-[var(--accent-amber)]/10',
  none: '',
};

export function SlideInRow({
  children,
  flashVariant = 'none',
  className = '',
}: SlideInRowProps) {
  const reduced = useReducedMotion();
  const duration = DURATION.page / 1000;

  return (
    <motion.tr
      initial={reduced ? false : { opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration }}
      className={cn(
        'border-b border-[var(--border-subtle)]',
        flashVariant !== 'none' && flashBg[flashVariant],
        className
      )}
    >
      {children}
    </motion.tr>
  );
}
