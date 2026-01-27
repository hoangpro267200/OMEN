import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
}

export function Card({ children, className = '', glow }: CardProps) {
  return (
    <div
      className={`
        relative rounded-2xl
        bg-white/5 backdrop-blur-xl
        border border-white/10
        ${glow ? 'shadow-lg shadow-blue-500/20' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
}
