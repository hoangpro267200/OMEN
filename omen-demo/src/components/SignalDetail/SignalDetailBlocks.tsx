import { useState, useCallback } from 'react';
import { Copy, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { Card } from '../common/Card';
import type { ProcessedSignal, ImpactDomain, SignalCategory } from '../../types/omen';

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(() => {
    if (value && navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(value).then(
        () => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        },
        () => {}
      );
    }
  }, [value]);
  if (!value) return null;
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)]"
      title={`Copy ${label}`}
      aria-label={`Copy ${label}`}
    >
      <Copy className="w-3.5 h-3.5" />
      {copied ? 'Đã copy' : 'Copy'}
    </button>
  );
}

export function SignalMetadataRow({ signal }: { signal: ProcessedSignal }) {
  const trace = signal.trace_id ?? signal.input_event_hash ?? null;
  const eventVal = signal.event_id ?? signal.input_event_hash ?? null;
  const ruleset = signal.ruleset_version ?? null;
  if (!trace && !eventVal && !ruleset) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[var(--text-tertiary)] shrink-0">Trace:</span>
        <code className="font-mono text-xs truncate max-w-[160px]" title={trace ?? undefined}>
          {trace ?? '—'}
        </code>
        {trace && <CopyButton value={trace} label="Trace ID" />}
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[var(--text-tertiary)] shrink-0">Event:</span>
        <code className="font-mono text-xs truncate max-w-[160px]" title={eventVal ?? undefined}>
          {eventVal ?? '—'}
        </code>
        {eventVal && <CopyButton value={eventVal} label="Event ID" />}
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[var(--text-tertiary)] shrink-0">Ruleset:</span>
        <span className="font-mono text-xs">{ruleset ?? '—'}</span>
      </div>
    </div>
  );
}

export function SignalSummaryCard({ summary }: { summary: string | undefined }) {
  if (!summary || summary.trim() === '') return null;
  return (
    <Card className="p-4" hover={false}>
      <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-2">
        Tóm tắt tác động
      </h2>
      <p className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap">{summary}</p>
    </Card>
  );
}

export function SignalDetailedExplanation({ detailed_explanation }: { detailed_explanation: string | undefined }) {
  const [open, setOpen] = useState(false);
  if (!detailed_explanation || detailed_explanation.trim() === '') return null;
  return (
    <Card className="p-4" hover={false}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 w-full text-left"
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
        )}
        <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          Giải thích chi tiết
        </span>
      </button>
      {open && (
        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <p className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap">{detailed_explanation}</p>
        </div>
      )}
    </Card>
  );
}

function formatHours(h: number): string {
  if (h < 24) return `~${h}h`;
  if (h < 48) return '<24h';
  if (h < 72) return '1–2d';
  if (h < 168) return '~72h';
  return `~${Math.round(h / 24)}d`;
}

export function SignalOnsetDuration({
  expected_onset_hours,
  expected_duration_hours,
}: {
  expected_onset_hours?: number;
  expected_duration_hours?: number;
}) {
  const hasOnset = expected_onset_hours != null && expected_onset_hours >= 0;
  const hasDuration = expected_duration_hours != null && expected_duration_hours >= 0;
  if (!hasOnset && !hasDuration) return null;
  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      {hasOnset && (
        <span
          className="text-[var(--text-secondary)]"
          title="Thời gian ước tính đến khi tác động phát sinh"
        >
          Onset: {formatHours(expected_onset_hours)}
        </span>
      )}
      {hasDuration && (
        <span
          className="text-[var(--text-secondary)]"
          title="Thời lượng ước tính của tác động"
        >
          Duration: {formatHours(expected_duration_hours)}
        </span>
      )}
    </div>
  );
}

export function SignalBadges({
  domain,
  category,
  subcategory,
}: {
  domain?: ImpactDomain;
  category?: SignalCategory;
  subcategory?: string;
}) {
  const hasAny = domain ?? category ?? (subcategory && subcategory.trim() !== '');
  if (!hasAny) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {domain && (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]">
          {domain}
        </span>
      )}
      {category && (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-[var(--bg-tertiary)] text-[var(--text-secondary)]">
          {category}
        </span>
      )}
      {subcategory && subcategory.trim() !== '' && (
        <span className="text-xs text-[var(--text-muted)]">{subcategory.trim()}</span>
      )}
    </div>
  );
}

export function SignalSourceMarket({
  source_market,
  market_url,
}: {
  source_market?: string;
  market_url?: string | null;
}) {
  const label = source_market && source_market.trim() !== '' ? source_market : 'Market';
  if (!label && !market_url) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--text-muted)]">
      <span>Nguồn: {label}</span>
      {market_url && market_url.trim() !== '' && (
        <a
          href={market_url}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1 text-[var(--accent-cyan)] hover:underline"
        >
          Xem market
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      )}
    </div>
  );
}

export function SignalAffectedSystems({ affected_systems }: { affected_systems?: string[] }) {
  if (!affected_systems?.length) return null;
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-2">
        Hệ thống bị ảnh hưởng
      </h2>
      <div className="flex flex-wrap gap-2">
        {affected_systems.map((s) => (
          <span
            key={s}
            className="px-2 py-1 rounded-md text-xs bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] text-[var(--text-secondary)]"
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
