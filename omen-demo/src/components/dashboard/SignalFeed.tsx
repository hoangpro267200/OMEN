import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import type { ProcessedSignal } from '../../types/omen';
import type { SeverityLabel } from '../../types/omen';

const severityStyles: Record<SeverityLabel, string> = {
  CRITICAL: 'bg-[var(--severity-critical)] pulse-critical',
  HIGH: 'bg-[var(--severity-high)]',
  MEDIUM: 'bg-[var(--severity-medium)]',
  LOW: 'bg-[var(--severity-low)]',
};

interface SignalFeedProps {
  signals: ProcessedSignal[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  className?: string;
  /** Tổng số tín hiệu (từ backend/stats). Khi có thì dùng thay vì signals.length để caption đúng theo dữ liệu đã lọc. */
  totalSignalsCount?: number;
}

function MiniSparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const w = 40;
  const h = 16;
  const pad = 2;
  const path = points
    .map((v, i) => {
      const x = pad + (i / (points.length - 1)) * (w - 2 * pad);
      const y = h - pad - ((v - min) / range) * (h - 2 * pad);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
  return (
    <svg width={w} height={h} className="shrink-0 opacity-70">
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function SignalFeed({ signals, selectedId, onSelect, className, totalSignalsCount }: SignalFeedProps) {
  const count = totalSignalsCount ?? signals.length;
  return (
    <div
      className={cn(
        'flex flex-col h-full bg-[var(--bg-secondary)] border-r border-[var(--border-subtle)]',
        className
      )}
    >
      <div className="px-4 py-3 border-b border-[var(--border-subtle)]">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          Nguồn cấp tín hiệu
        </h2>
        <p className="text-[var(--text-muted)] text-xs mt-0.5">
          {count.toLocaleString()} tín hiệu
        </p>
      </div>
      <div className="flex-1 overflow-y-auto overflow-thin-scroll">
        {signals.map((s, i) => {
          const isSelected = s.signal_id === selectedId;
          const severity = (s.severity_label || 'LOW') as SeverityLabel;
          const style = severityStyles[severity] ?? severityStyles.LOW;
          return (
            <motion.button
              key={s.signal_id}
              type="button"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              onClick={() => onSelect(s.signal_id)}
              className={cn(
                'w-full text-left px-4 py-3 border-b border-[var(--border-subtle)] transition-colors',
                'hover:bg-[var(--bg-hover)]',
                isSelected && 'bg-[var(--bg-tertiary)] border-l-2 border-l-[var(--accent-blue)]'
              )}
            >
              <div className="flex items-start gap-2">
                <span
                  className={cn(
                    'w-2 h-2 rounded-full shrink-0 mt-1.5',
                    style
                  )}
                  title={severity}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-mono text-[var(--text-muted)] truncate">
                      {s.signal_id}
                    </span>
                    {s.domain != null && (
                      <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]">
                        {s.domain}
                      </span>
                    )}
                    {s.category != null && (
                      <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] bg-[var(--bg-tertiary)] text-[var(--text-muted)]">
                        {s.category}
                      </span>
                    )}
                  </div>
                  <div className="text-sm font-medium text-[var(--text-primary)] line-clamp-2 mt-0.5">
                    {s.title}
                  </div>
                  {s.summary != null && s.summary.trim() !== '' && (
                    <div className="text-xs text-[var(--text-muted)] line-clamp-1 mt-0.5">
                      {s.summary.trim()}
                    </div>
                  )}
                  <div className="flex items-center justify-between gap-2 mt-2">
                    <span className="text-xs font-mono text-[var(--accent-cyan)]">
                      {(s.probability * 100).toFixed(0)}%
                    </span>
                    <MiniSparkline points={s.probability_history ?? []} />
                  </div>
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
