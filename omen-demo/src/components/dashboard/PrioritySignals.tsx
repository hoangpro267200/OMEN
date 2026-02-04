/**
 * PrioritySignals - Neural Command Center high priority signals table
 * 
 * IMPORTANT: Uses useSignals hook which respects DataMode:
 * - LIVE mode: Fetches from real API. Shows error if API unavailable. NO fake data.
 * - DEMO mode: Uses mock data clearly labeled.
 */
import { ChevronRight, RefreshCw, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';
import { StatusIndicator } from '../ui/StatusIndicator';
import { MiniGauge } from '../ui/Gauge';
import { useSignals, type Signal } from '../../hooks/useSignalData';
import { useDataModeSafe } from '../../context/DataModeContext';
import { Skeleton } from '../ui/Skeleton';
import { formatDistanceToNow } from 'date-fns';

export interface PrioritySignal {
  id: string;
  title: string;
  status: 'active' | 'monitoring' | 'candidate';
  probability: number;
  confidence: number;
  category: string;
  timeAgo: string;
}

const STATUS_CONFIG = {
  active: {
    label: 'ACTIVE',
    className: 'bg-status-error/20 text-status-error border-status-error/30',
    indicatorStatus: 'error' as const,
  },
  monitoring: {
    label: 'WATCH',
    className: 'bg-status-warning/20 text-status-warning border-status-warning/30',
    indicatorStatus: 'warning' as const,
  },
  candidate: {
    label: 'LOW',
    className: 'bg-text-muted/20 text-text-muted border-text-muted/30',
    indicatorStatus: 'inactive' as const,
  },
};

// Transform API Signal to PrioritySignal format
function transformSignal(signal: Signal): PrioritySignal {
  const statusMap: Record<string, 'active' | 'monitoring' | 'candidate'> = {
    ACTIVE: 'active',
    MONITORING: 'monitoring',
    CANDIDATE: 'candidate',
    ARCHIVED: 'candidate',
  };
  
  // Handle null/undefined observed_at - use generated_at as fallback, then "recently"
  let timeAgo = 'recently';
  const timestamp = signal.observed_at || signal.generated_at;
  if (timestamp) {
    try {
      const date = new Date(timestamp);
      // Check if valid date (not epoch or invalid)
      if (!isNaN(date.getTime()) && date.getFullYear() > 2000) {
        timeAgo = formatDistanceToNow(date, { addSuffix: true });
      }
    } catch {
      // Keep default "recently"
    }
  }
  
  return {
    id: signal.signal_id,
    title: signal.title,
    status: statusMap[signal.status] || 'candidate',
    probability: signal.probability,
    confidence: signal.confidence_score,
    category: signal.category,
    timeAgo,
  };
}

export interface PrioritySignalsProps {
  onSignalClick?: (signal: PrioritySignal) => void;
  maxItems?: number;
  className?: string;
}

export function PrioritySignals({
  onSignalClick,
  maxItems = 5,
  className,
}: PrioritySignalsProps) {
  const { isLive, isDemo, setMode, state } = useDataModeSafe();
  
  // Use the unified data hook - respects DataMode
  const { data, isLoading, isError, error, refetch, dataSource } = useSignals({
    limit: maxItems,
    status: 'ACTIVE,MONITORING',
  });

  // Transform API signals to display format
  const displaySignals = data?.signals.slice(0, maxItems).map(transformSignal) || [];

  // -------------------------------------------------------------------------
  // Loading State
  // -------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className={cn('space-y-3', className)}>
        {Array.from({ length: maxItems }).map((_, i) => (
          <div key={`signal-skeleton-${i}`} className="flex gap-4 py-3 border-b border-border-subtle/50">
            <Skeleton className="w-16 h-6" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/3" />
            </div>
            <Skeleton className="w-12 h-6" />
            <Skeleton className="w-10 h-6" />
          </div>
        ))}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Error State - CRITICAL: Shows error in Live mode, NO fake data
  // -------------------------------------------------------------------------
  if (isError) {
    return (
      <div className={cn('py-8 text-center', className)}>
        <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 rounded-2xl bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="w-6 h-6 text-red-400" />
        </div>
        <h3 className="text-base font-bold text-text-primary mb-2">
          {isLive ? 'Lỗi Tải Dữ Liệu' : 'Không thể tải signals'}
        </h3>
        <p className="text-sm text-text-muted mb-4 max-w-sm mx-auto">
          {error?.message || state.errorMessage || 'Không thể kết nối server'}
        </p>
        {isLive && (
          <p className="text-xs text-red-400/70 mb-4 flex items-center justify-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Chế độ LIVE - không hiện dữ liệu giả
          </p>
        )}
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg bg-accent-cyan text-black hover:bg-accent-cyan/90 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Thử lại
          </button>
          {isLive && (
            <button
              onClick={() => setMode('demo')}
              className="px-3 py-1.5 text-sm font-medium rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-colors"
            >
              ⚗ Xem Demo
            </button>
          )}
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Empty State
  // -------------------------------------------------------------------------
  if (displaySignals.length === 0) {
    return (
      <div className={cn('py-8 text-center text-text-muted', className)}>
        <p className="text-sm">Không có signals ưu tiên</p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Success State - Data Table
  // -------------------------------------------------------------------------
  return (
    <div className={cn('relative overflow-x-auto', className)} data-tour="signal-feed">
      {/* Data Source Badge - Use text only to avoid icon rendering issues */}
      <div className="absolute top-0 right-0 z-10">
        <span className={cn(
          'px-2 py-0.5 rounded-full border text-[9px] font-mono font-bold',
          dataSource === 'mock' 
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
        )}>
          {dataSource === 'mock' ? '⚗ DEMO' : '● LIVE'}
        </span>
      </div>

      <table className="w-full">
        <thead>
          <tr className="text-left text-xs text-text-muted border-b border-border-subtle">
            <th className="pb-3 font-medium font-mono">Status</th>
            <th className="pb-3 font-medium font-mono">Signal</th>
            <th className="pb-3 font-medium font-mono text-right">Probability</th>
            <th className="pb-3 font-medium font-mono text-right">Confidence</th>
            <th className="pb-3 font-medium font-mono text-right">Category</th>
            <th className="pb-3 font-medium font-mono text-right">Time</th>
            <th className="pb-3 w-8"></th>
          </tr>
        </thead>
        <tbody>
          {displaySignals.map((signal, index) => {
            const status = STATUS_CONFIG[signal.status];
            return (
              <tr
                key={`signal-row-${signal.id}-${index}`}
                onClick={() => onSignalClick?.(signal)}
                className="border-b border-border-subtle/50 hover:bg-bg-tertiary/30 transition-colors cursor-pointer group animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {/* Status */}
                <td className="py-3 pr-4">
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono border',
                      status.className
                    )}
                  >
                    <StatusIndicator
                      status={status.indicatorStatus}
                      size="xs"
                      pulse={signal.status === 'active'}
                    />
                    {status.label}
                  </span>
                </td>

                {/* Signal info */}
                <td className="py-3 pr-4">
                  <div>
                    <p className="text-sm font-medium text-text-primary group-hover:text-accent-cyan transition-colors">
                      {signal.title}
                    </p>
                    <p className="text-xs text-text-muted font-mono">{signal.id}</p>
                  </div>
                </td>

                {/* Probability */}
                <td className="py-3 pr-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <MiniGauge
                      value={signal.probability * 100}
                      size={24}
                      color={signal.probability >= 0.5 ? 'error' : signal.probability >= 0.3 ? 'warning' : 'success'}
                    />
                    <span className="font-mono text-accent-cyan">
                      {(signal.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </td>

                {/* Confidence */}
                <td className="py-3 pr-4 text-right">
                  <span
                    className={cn(
                      'font-mono',
                      signal.confidence >= 0.7
                        ? 'text-status-success'
                        : signal.confidence >= 0.5
                        ? 'text-status-warning'
                        : 'text-status-error'
                    )}
                  >
                    {signal.confidence.toFixed(2)}
                  </span>
                </td>

                {/* Category */}
                <td className="py-3 pr-4 text-right">
                  <span className="px-2 py-1 rounded text-xs font-mono bg-bg-tertiary text-text-secondary border border-border-subtle">
                    {signal.category}
                  </span>
                </td>

                {/* Time */}
                <td className="py-3 pr-4 text-right text-xs text-text-muted font-mono">
                  {signal.timeAgo}
                </td>

                {/* Arrow */}
                <td className="py-3">
                  <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-accent-cyan transition-colors" />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
