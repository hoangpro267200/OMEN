import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { DURATION, TRANSITION } from '../../lib/animationConstants';
import { cn } from '../../lib/utils';

export interface AnimatedPageProps {
  children: ReactNode;
  className?: string;
}

/**
 * Wraps page content with route-keyed fade + slide. Use inside AnimatePresence with key={pathname}.
 * Respects prefers-reduced-motion (no slide, shorter fade).
 */
export function AnimatedPage({ children, className = '' }: AnimatedPageProps) {
  const reduced = useReducedMotion();

  const initial = reduced
    ? { opacity: 0 }
    : { opacity: 0, y: 8 };
  const animate = reduced
    ? { opacity: 1 }
    : { opacity: 1, y: 0 };
  const exit = reduced
    ? { opacity: 0 }
    : { opacity: 0, y: -8 };
  const duration = reduced ? 0.08 : DURATION.page / 1000;

  return (
    <motion.div
      initial={initial}
      animate={animate}
      exit={exit}
      transition={{ duration, ease: TRANSITION.page.ease }}
      className={cn('min-h-full', className)}
    >
      {children}
    </motion.div>
  );
}

/**
 * Hook to get location pathname for use as AnimatePresence key.
 */
export function usePageKey(): string {
  return useLocation().pathname;
}
