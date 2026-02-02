import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface CodeBlockProps {
  children: ReactNode;
  /** Raw string (e.g. JSON or hex); if set, children are ignored and content is shown with monospace */
  raw?: string;
  language?: 'json' | 'hex' | 'text';
  className?: string;
}

export function CodeBlock({ children, raw, language = 'text', className = '' }: CodeBlockProps) {
  const content = raw != null ? String(raw) : (typeof children === 'string' ? children : null);
  const display = content ?? (children as ReactNode);

  return (
    <pre
      className={cn(
        'overflow-x-auto overflow-thin-scroll rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-4 font-mono text-xs leading-relaxed text-[var(--text-secondary)]',
        className
      )}
    >
      <code
        className={cn(
          language === 'json' && 'whitespace-pre',
          language === 'hex' && 'tracking-wider'
        )}
        data-language={language}
      >
        {display}
      </code>
    </pre>
  );
}
