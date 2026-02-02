import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface CardProps {
  children: ReactNode;
  className?: string;
  /** Glass-morphism style with subtle border */
  variant?: 'default' | 'elevated';
  hover?: boolean;
}

export function Card({
  children,
  className = '',
  variant = 'default',
  hover = true,
}: CardProps) {
  const Comp = hover ? motion.div : 'div';
  const props = hover
    ? {
        whileHover: { y: -1, transition: { duration: 0.15 } },
        transition: { duration: 0.2 },
      }
    : {};

  return (
    <Comp
      className={cn(
        'relative rounded-[var(--radius-card)] border',
        'bg-[var(--bg-secondary)]/80 border-[var(--border-subtle)]',
        'backdrop-blur-sm',
        variant === 'elevated' && 'bg-[var(--bg-tertiary)] border-[var(--border-active)]',
        className
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}
