import { CategoryBadge } from './CategoryBadge';
import { ConfidenceBadge } from './ConfidenceBadge';
import type { SignalBrowserRecord } from '../../data/signalsBrowserMock';

export interface SignalPayloadTabProps {
  record: SignalBrowserRecord;
}

/**
 * Tab 2: Payload (OmenSignal) — title, category, probability, confidence_score, confidence_level, generated_at.
 */
export function SignalPayloadTab({ record }: SignalPayloadTabProps) {
  const s = record.signal;
  
  // Defensive: handle missing signal data
  if (!s || typeof s !== 'object') {
    return (
      <div className="rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-4 text-center">
        <p className="text-sm text-[var(--text-muted)]">Signal payload data not available</p>
      </div>
    );
  }
  
  const probPct = typeof s.probability === 'number' ? `${(s.probability * 100).toFixed(0)}%` : String(s.probability ?? '—');

  return (
    <div className="space-y-1">
      <h3 className="mb-3 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
        Payload (OmenSignal)
      </h3>
      <div className="space-y-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Title</span>
          <span className="text-sm text-[var(--text-primary)]">{s.title}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Category</span>
          <CategoryBadge category={(s.category as string) || 'OTHER'} />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Probability</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{probPct}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Confidence Score</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{s.confidence_score}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Confidence Level</span>
          <ConfidenceBadge confidence={(s.confidence_level as string) || 'MEDIUM'} />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] py-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">Generated At</span>
          <span className="font-mono text-sm text-[var(--text-primary)]">{s.generated_at}</span>
        </div>
      </div>
    </div>
  );
}
