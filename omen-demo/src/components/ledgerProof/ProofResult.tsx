import { Check, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ProofResultProps {
  success: boolean;
  title: string;
  lines: string[];
  className?: string;
}

/**
 * Success or warning proof result display (green check or amber warning).
 */
export function ProofResult({ success, title, lines, className = '' }: ProofResultProps) {
  return (
    <div
      className={cn(
        'rounded-[var(--radius-card)] border p-4',
        success
          ? 'border-[var(--accent-green)]/50 bg-[var(--accent-green)]/10'
          : 'border-[var(--accent-amber)]/50 bg-[var(--accent-amber)]/10',
        className
      )}
    >
      <div className="flex items-start gap-3">
        {success ? (
          <Check className="h-5 w-5 shrink-0 text-[var(--accent-green)]" />
        ) : (
          <AlertTriangle className="h-5 w-5 shrink-0 text-[var(--accent-amber)]" />
        )}
        <div>
          <p className={cn('font-mono text-sm font-medium', success ? 'text-[var(--accent-green)]' : 'text-[var(--accent-amber)]')}>
            {title}
          </p>
          <ul className="mt-2 space-y-1 text-sm text-[var(--text-secondary)]">
            {lines.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
