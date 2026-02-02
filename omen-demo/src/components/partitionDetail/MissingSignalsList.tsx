import { useState } from 'react';
import { Copy } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface MissingSignalsListProps {
  signalIds: string[];
  className?: string;
}

/**
 * List of missing signal IDs with Copy All and optional export.
 */
export function MissingSignalsList({ signalIds, className = '' }: MissingSignalsListProps) {
  const [copied, setCopied] = useState(false);

  const copyAll = () => {
    const text = signalIds.join('\n');
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (signalIds.length === 0) return null;

  return (
    <div
      className={cn(
        'rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-4',
        className
      )}
    >
      <div className="mb-2 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
        Missing Signal IDs
      </div>
      <ul className="space-y-1 font-mono text-sm text-[var(--text-secondary)]">
        {signalIds.map((id) => (
          <li key={id}>• {id}</li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={copyAll}
          className="flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--border-subtle)]/30 hover:text-[var(--text-primary)]"
        >
          <Copy className="h-3.5 w-3.5" />
          {copied ? 'Copied' : 'Copy All'}
        </button>
      </div>
    </div>
  );
}
