import { cn } from '../../lib/utils';
import type { SignalsBrowserCategory } from '../../data/signalsBrowserMock';

const CATEGORY_STYLES: Record<SignalsBrowserCategory, string> = {
  GEOPOLITICAL: 'bg-[var(--accent-red)]/20 text-[var(--accent-red)] border-[var(--accent-red)]/40',
  INFRASTRUCTURE: 'bg-[var(--accent-blue)]/20 text-[var(--accent-blue)] border-[var(--accent-blue)]/40',
  OPERATIONAL: 'bg-[var(--text-muted)]/30 text-[var(--text-secondary)] border-[var(--border-subtle)]',
  FINANCIAL: 'bg-[var(--accent-green)]/20 text-[var(--accent-green)] border-[var(--accent-green)]/40',
  CLIMATE: 'bg-teal-500/20 text-teal-400 border-teal-500/40',
  COMPLIANCE: 'bg-purple-500/20 text-purple-400 border-purple-500/40',
  NETWORK: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
};

export interface CategoryBadgeProps {
  category: SignalsBrowserCategory | string;
  className?: string;
}

/**
 * Color-coded category badge for Signals Browser.
 * GEOPOLITICAL=red, INFRASTRUCTURE=blue, OPERATIONAL=gray, FINANCIAL=green,
 * CLIMATE=teal, COMPLIANCE=purple, NETWORK=orange.
 */
export function CategoryBadge({ category, className = '' }: CategoryBadgeProps) {
  const key = category as SignalsBrowserCategory;
  const style =
    key in CATEGORY_STYLES
      ? CATEGORY_STYLES[key]
      : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border-[var(--border-subtle)]';

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-[var(--radius-badge)] text-xs font-medium border font-mono uppercase',
        style,
        className
      )}
    >
      {category}
    </span>
  );
}
