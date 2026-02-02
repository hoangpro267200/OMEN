import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Card } from '../ui/Card';

export interface ProofCardProps {
  /** Title with checkmark, e.g. "LEDGER-FIRST INVARIANT" */
  title: string;
  /** 1–2 line explanation */
  description: string;
  /** Inline snippet (code or visual) */
  snippet?: ReactNode;
  /** Button label, e.g. "View Emitter Code →" */
  actionLabel: string;
  /** Route path for the action link */
  actionTo: string;
  className?: string;
}

/**
 * Proof card: title (✓), explanation, snippet, action link to proof screen.
 */
export function ProofCard({
  title,
  description,
  snippet,
  actionLabel,
  actionTo,
  className = '',
}: ProofCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={cn('h-full', className)}
    >
      <Card hover className="flex h-full flex-col p-5">
        <div className="flex items-start gap-2">
          <Check className="mt-0.5 h-5 w-5 shrink-0 text-[var(--accent-green)]" aria-hidden />
          <h3 className="font-mono text-sm font-semibold uppercase tracking-wider text-[var(--text-primary)]">
            {title}
          </h3>
        </div>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">{description}</p>
        {snippet != null && (
          <div className="mt-3 rounded-[var(--radius-badge)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 font-mono text-xs text-[var(--text-muted)]">
            {snippet}
          </div>
        )}
        <div className="mt-4 flex-1" />
        <Link
          to={actionTo}
          className={cn(
            'mt-4 inline-flex w-full justify-center rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:border-[var(--border-active)] hover:bg-[var(--border-subtle)]/30 sm:w-auto'
          )}
        >
          {actionLabel}
        </Link>
      </Card>
    </motion.div>
  );
}
