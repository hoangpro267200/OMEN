/**
 * GlassCard - Neural Command Center glassmorphism card
 * Features: Backdrop blur, gradient border, glow effects, animated entrance
 */
import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface GlassCardProps {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'elevated' | 'highlighted';
  glow?: 'cyan' | 'amber' | 'success' | 'warning' | 'error' | 'none';
  animate?: boolean;
  delay?: number;
  hover?: boolean;
  onClick?: () => void;
}

export function GlassCard({
  children,
  className,
  variant = 'default',
  glow = 'none',
  animate = true,
  delay = 0,
  hover = false,
  onClick,
}: GlassCardProps) {
  const baseStyles = cn(
    'relative rounded-xl overflow-hidden',
    // Background based on variant
    variant === 'default' && 'bg-bg-secondary/80 backdrop-blur-sm border border-border-subtle',
    variant === 'elevated' && 'bg-bg-tertiary/90 backdrop-blur-md border border-border-active',
    variant === 'highlighted' && 'bg-bg-tertiary/90 backdrop-blur-md border border-accent-cyan/30 glow-border',
    // Glow effects
    glow === 'cyan' && 'shadow-glow-cyan',
    glow === 'amber' && 'shadow-glow-amber',
    glow === 'success' && 'shadow-glow-success',
    glow === 'warning' && 'shadow-glow-amber',
    glow === 'error' && 'shadow-glow-error',
    // Hover effects
    hover && 'cursor-pointer transition-all duration-200 hover:border-border-active hover:shadow-elevated hover:-translate-y-0.5',
    className
  );

  if (!animate) {
    return (
      <div className={baseStyles} onClick={onClick}>
        {children}
      </div>
    );
  }

  return (
    <motion.div
      className={baseStyles}
      onClick={onClick}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: 'easeOut' }}
      whileHover={hover ? { y: -2, transition: { duration: 0.15 } } : undefined}
    >
      {children}
    </motion.div>
  );
}

// Header component for cards
export function GlassCardHeader({ 
  children, 
  className 
}: { 
  children: ReactNode; 
  className?: string 
}) {
  return (
    <div className={cn('px-4 py-3 border-b border-border-subtle', className)}>
      {children}
    </div>
  );
}

// Content component for cards
export function GlassCardContent({ 
  children, 
  className 
}: { 
  children: ReactNode; 
  className?: string 
}) {
  return (
    <div className={cn('p-4', className)}>
      {children}
    </div>
  );
}

// Title component for cards
export function GlassCardTitle({
  children,
  icon,
  className,
}: {
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <h3 className={cn('flex items-center gap-2 data-label', className)}>
      {icon && <span className="text-accent-cyan">{icon}</span>}
      {children}
    </h3>
  );
}
