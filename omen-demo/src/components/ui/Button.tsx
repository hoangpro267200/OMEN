import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost';

export interface ButtonProps {
  children: ReactNode;
  variant?: ButtonVariant;
  className?: string;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  onClick?: () => void;
  'data-demo-target'?: string;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--accent-blue)] text-white border-transparent hover:opacity-90 active:opacity-95',
  secondary:
    'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-[var(--border-subtle)] hover:border-[var(--border-active)] hover:bg-[var(--border-subtle)]/30',
  ghost:
    'bg-transparent text-[var(--text-secondary)] border-transparent hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
};

export function Button({
  children,
  variant = 'primary',
  className = '',
  disabled = false,
  type = 'button',
  onClick,
  'data-demo-target': dataDemoTarget,
}: ButtonProps) {
  return (
    <motion.button
      type={type}
      data-demo-target={dataDemoTarget}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-[var(--radius-button)] border px-4 py-2 text-sm font-medium transition-colors',
        'disabled:opacity-50 disabled:pointer-events-none',
        variantStyles[variant],
        className
      )}
      whileHover={disabled ? undefined : { scale: 1.02, y: -1 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      transition={{ duration: 0.1 }}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </motion.button>
  );
}
