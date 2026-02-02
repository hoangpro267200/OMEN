import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { cn } from '../../lib/utils';

export interface AnimatedCounterProps {
  value: number;
  /** Duration for count-up in ms */
  duration?: number;
  className?: string;
  /** Optional formatter (e.g. for decimals) */
  format?: (n: number) => string;
}

/**
 * Numbers count up from 0 to value. Uses requestAnimationFrame for smooth increment.
 * Respects reduced motion (snap to value).
 */
export function AnimatedCounter({
  value,
  duration = 600,
  className = '',
  format = (n) => String(Math.round(n)),
}: AnimatedCounterProps) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(reduced ? value : 0);

  useEffect(() => {
    if (reduced) {
      setDisplay(value);
      return;
    }
    let start: number | null = null;
    const startVal = display;
    const diff = value - startVal;

    const step = (t: number) => {
      if (start == null) start = t;
      const elapsed = t - start;
      const progress = Math.min(1, elapsed / duration);
      const easeOut = 1 - (1 - progress) ** 2;
      setDisplay(startVal + diff * easeOut);
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps -- only re-run on value change

  const finalDisplay = reduced ? value : display;

  return (
    <motion.span
      key={value}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className={cn('tabular-nums', className)}
    >
      {format(finalDisplay)}
    </motion.span>
  );
}
