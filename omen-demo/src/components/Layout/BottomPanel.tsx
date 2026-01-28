import { Activity, Database, CheckCircle, XCircle } from 'lucide-react';
import type { SystemStats } from '../../types/omen';
import { cn } from '../../lib/utils';

interface BottomPanelProps {
  stats: SystemStats;
  className?: string;
}

export function BottomPanel({ stats, className }: BottomPanelProps) {
  const processed = stats.events_processed ?? 0;
  const validated = stats.events_validated ?? 0;
  const apiRejected = (stats.events_rejected ?? null) != null ? Number(stats.events_rejected) : null;
  const derivedRejected = Math.max(0, processed - validated);
  const rejected = apiRejected != null && apiRejected > 0 ? apiRejected : derivedRejected;
  const validatedPct = processed ? Math.round((validated / processed) * 100) : 0;
  const rejectedPct = processed ? Math.round((rejected / processed) * 100) : 0;

  return (
    <footer
      className={cn(
        'fixed bottom-0 left-0 right-0 z-40 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 flex items-center',
        className
      )}
      style={{ height: 48 }}
    >
      <div className="flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-2 text-[var(--text-tertiary)]">
          <Database className="w-4 h-4" />
          <span className="text-xs font-medium uppercase tracking-wider">
            Nguồn dữ liệu
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[var(--success)]" />
            <span className="text-[var(--text-secondary)]">Polymarket</span>
            <span className="text-[var(--text-muted)] font-mono">{stats.events_per_second}/phút</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[var(--text-muted)]" />
            <span className="text-[var(--text-muted)]">Kalshi</span>
            <span className="text-[var(--text-muted)]">Chưa cấu hình</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[var(--success)]" />
            <span className="text-[var(--text-secondary)]">Nội bộ</span>
            <span className="text-[var(--text-muted)]">12 nguồn</span>
          </span>
        </div>
        <div className="h-4 w-px bg-[var(--border-default)]" />
        <div className="flex items-center gap-2 text-[var(--text-tertiary)]">
          <Activity className="w-4 h-4" />
          <span className="text-xs font-medium uppercase tracking-wider">
            Xử lý
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <span className="text-[var(--text-secondary)]">
            Đã xử lý: <span className="font-mono text-[var(--text-primary)]">{stats.events_processed.toLocaleString()}</span>
          </span>
          <span className="flex items-center gap-1 text-[var(--success)]">
            <CheckCircle className="w-4 h-4" />
            Đã xác thực: <span className="font-mono">{stats.events_validated.toLocaleString()}</span>
            <span className="text-[var(--text-muted)]">({validatedPct}%)</span>
          </span>
          <span className="text-[var(--text-secondary)]">
            Tín hiệu: <span className="font-mono text-[var(--accent-cyan)]">{stats.signals_generated.toLocaleString()}</span>
          </span>
          <span className="flex items-center gap-1 text-[var(--danger)]">
            <XCircle className="w-4 h-4 flex-shrink-0" />
            Từ chối: <span className="font-mono text-[var(--danger)]">{rejected.toLocaleString()}</span>
            <span className="text-[var(--text-muted)]">({rejectedPct}%)</span>
          </span>
        </div>
      </div>
    </footer>
  );
}
