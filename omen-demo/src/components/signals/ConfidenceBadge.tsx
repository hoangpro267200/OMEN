import { cn } from '../../lib/utils';

type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

const CONFIDENCE_STYLES: Record<ConfidenceLevel, string> = {
  HIGH: 'bg-[var(--accent-green)]/20 text-[var(--accent-green)] border-[var(--accent-green)]/40',
  MEDIUM: 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border-[var(--accent-amber)]/40',
  LOW: 'bg-[var(--accent-red)]/20 text-[var(--accent-red)] border-[var(--accent-red)]/40',
};

function normalizeConfidence(level: string): ConfidenceLevel {
  const u = level.toUpperCase();
  if (u === 'MED') return 'MEDIUM';
  if (u === 'HIGH' || u === 'MEDIUM' || u === 'LOW') return u as ConfidenceLevel;
  return 'MEDIUM';
}

function displayLabel(level: ConfidenceLevel): string {
  return level === 'MEDIUM' ? 'MED' : level;
}

export interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel | string;
  className?: string;
}

/**
 * Confidence badge: HIGH (green), MEDIUM (amber), LOW (red).
 * Displays MED for MEDIUM in table to save space.
 */
export function ConfidenceBadge({ confidence, className = '' }: ConfidenceBadgeProps) {
  const level = normalizeConfidence(confidence);
  const style = CONFIDENCE_STYLES[level];

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-[var(--radius-badge)] text-xs font-medium border font-mono',
        style,
        className
      )}
    >
      {displayLabel(level)}
    </span>
  );
}
