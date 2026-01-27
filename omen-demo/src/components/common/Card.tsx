import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface CardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
  hover?: boolean;
}

export function Card({ children, className = '', glow, hover = true }: CardProps) {
  const Comp = hover ? motion.div : 'div';
  const props = hover
    ? {
        whileHover: { y: -2, boxShadow: '0 8px 30px rgba(59, 130, 246, 0.12)' },
        transition: { duration: 0.2 },
      }
    : {};

  return (
    <Comp
      className={cn(
        'relative rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-subtle)]',
        glow && 'shadow-[var(--glow-blue)]',
        className
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}
