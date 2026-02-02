import { useCallback, memo } from 'react';
import { Copy, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { CategoryBadge } from './CategoryBadge';
import { ConfidenceBadge } from './ConfidenceBadge';
import type { SignalBrowserRecord } from '../../data/signalsBrowserMock';

const TITLE_MAX = 24;
const SIGNAL_ID_MAX = 18;

function formatEmittedAt(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s;
  return s.slice(0, max - 3) + '...';
}

export interface SignalRowProps {
  record: SignalBrowserRecord;
  onClick: () => void;
  isSelected?: boolean;
  showPartition?: boolean;
  showSequence?: boolean;
  showObservedAt?: boolean;
  searchHighlight?: string;
}

/**
 * Table row for one signal: emitted_at, signal_id (copy), category, title, probability, confidence.
 * Optional: ledger partition, ledger sequence, observed_at.
 * Memoized to avoid re-renders when parent updates but this row's data is unchanged.
 */
export const SignalRow = memo(function SignalRow({
  record,
  onClick,
  isSelected = false,
  showPartition = false,
  showSequence = false,
  showObservedAt = false,
  searchHighlight,
}: SignalRowProps) {
  const copySignalId = useCallback(() => {
    navigator.clipboard.writeText(record.signal_id);
  }, [record.signal_id]);

  const s = record.signal;
  const emittedAt = formatEmittedAt(record.emitted_at);
  const signalIdDisplay = truncate(record.signal_id, SIGNAL_ID_MAX);
  const titleDisplay = truncate(s.title, TITLE_MAX);
  const probDisplay = typeof s.probability === 'number' ? (s.probability * 100).toFixed(0) + '%' : String(s.probability);
  const confidenceLevel = (s.confidence_level as string) || 'MEDIUM';

  return (
    <tr
      onClick={onClick}
      className={cn(
        'cursor-pointer border-b border-[var(--border-subtle)] transition-colors last:border-0',
        'hover:bg-[var(--bg-tertiary)]/50',
        isSelected && 'bg-[var(--bg-tertiary)]/70'
      )}
    >
      <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)] whitespace-nowrap">
        {emittedAt}
      </td>
      <td className="px-4 py-3">
        <span className="inline-flex items-center gap-1">
          <span className="font-mono text-sm text-[var(--text-primary)]" title={record.signal_id}>
            {searchHighlight ? (
              <span dangerouslySetInnerHTML={{ __html: highlightMatch(signalIdDisplay, searchHighlight) }} />
            ) : (
              signalIdDisplay
            )}
          </span>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              copySignalId();
            }}
            className="rounded p-0.5 text-[var(--text-muted)] hover:bg-[var(--border-subtle)] hover:text-[var(--text-primary)]"
            title="Copy signal ID"
            aria-label="Copy signal ID"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
        </span>
      </td>
      <td className="px-4 py-3">
        <CategoryBadge category={(s.category as string) || 'OTHER'} />
      </td>
      <td className="px-4 py-3 text-sm text-[var(--text-primary)] max-w-[200px]" title={s.title}>
        {searchHighlight ? (
          <span dangerouslySetInnerHTML={{ __html: highlightMatch(titleDisplay, searchHighlight) }} />
        ) : (
          titleDisplay
        )}
      </td>
      <td className="px-4 py-3 font-mono text-sm tabular-nums text-[var(--text-secondary)]">
        {probDisplay}
      </td>
      <td className="px-4 py-3">
        <ConfidenceBadge confidence={confidenceLevel} />
      </td>
      {showPartition && (
        <td className="px-4 py-3 font-mono text-xs text-[var(--text-muted)]">
          {record.ledger_partition ?? '—'}
        </td>
      )}
      {showSequence && (
        <td className="px-4 py-3 font-mono text-xs text-[var(--text-muted)] tabular-nums">
          {record.ledger_sequence ?? '—'}
        </td>
      )}
      {showObservedAt && (
        <td className="px-4 py-3 font-mono text-xs text-[var(--text-muted)] whitespace-nowrap">
          {record.observed_at ?? '—'}
        </td>
      )}
      <td className="w-12 px-4 py-3 text-right">
        {isSelected ? (
          <ChevronRight className="inline-block h-4 w-4 text-[var(--accent-blue)]" />
        ) : (
          <span className="inline-block w-4" />
        )}
      </td>
    </tr>
  );
});

function highlightMatch(text: string, q: string): string {
  if (!q || q.length < 2) return escapeHtml(text);
  const re = new RegExp(`(${escapeRe(q)})`, 'gi');
  return escapeHtml(text).replace(re, '<mark class="bg-[var(--accent-amber)]/40 text-[var(--text-primary)] rounded px-0.5">$1</mark>');
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
