/**
 * ActivityFeed - Neural Command Center live activity feed
 * 
 * IMPORTANT: Uses useActivityFeed hook which respects DataMode:
 * - LIVE mode: Fetches from real API. Shows error if API unavailable. NO fake data.
 * - DEMO mode: Uses mock data clearly labeled.
 */
import { useRef, useEffect } from 'react';
import { CheckCircle, XCircle, Activity, RefreshCw, AlertTriangle, Radio } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useActivityFeed, type ActivityItem } from '../../hooks/useSignalData';
import { useDataModeSafe } from '../../context/DataModeContext';
import { Skeleton } from '../ui/Skeleton';
import { format } from 'date-fns';

type ActivityType = 'signal' | 'validation' | 'rejection' | 'reconcile' | 'alert' | 'source' | 'translation';

interface ActivityConfig {
  icon: React.ReactNode;
  color: string;
  label: string;
}

const TYPE_CONFIG: Record<ActivityType, ActivityConfig> = {
  signal: {
    icon: <CheckCircle className="w-4 h-4" />,
    color: 'text-status-success',
    label: 'Signal',
  },
  validation: {
    icon: <Activity className="w-4 h-4" />,
    color: 'text-accent-cyan',
    label: 'Validation',
  },
  rejection: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'text-status-error',
    label: 'Rejection',
  },
  reconcile: {
    icon: <RefreshCw className="w-4 h-4" />,
    color: 'text-accent-amber',
    label: 'Reconcile',
  },
  alert: {
    icon: <AlertTriangle className="w-4 h-4" />,
    color: 'text-status-warning',
    label: 'Alert',
  },
  source: {
    icon: <Radio className="w-4 h-4" />,
    color: 'text-text-muted',
    label: 'Source',
  },
  translation: {
    icon: <Activity className="w-4 h-4" />,
    color: 'text-accent-cyan',
    label: 'Translation',
  },
};

// Extended activity item with more fields
export interface LiveActivityItem {
  type: ActivityType;
  id: string;
  message: string;
  time: string;
}

interface ActivityFeedProps {
  maxItems?: number;
  autoScroll?: boolean;
  className?: string;
}

// Transform API activity to display format
function transformActivity(item: ActivityItem): LiveActivityItem {
  const typeMap: Record<string, ActivityType> = {
    signal_emitted: 'signal',
    signal_ingested: 'validation',
    reconcile_completed: 'reconcile',
    error: 'rejection',
    info: 'source',
  };
  
  return {
    id: item.id,
    type: typeMap[item.type] || 'source',
    message: item.message,
    time: format(new Date(item.timestamp), 'HH:mm:ss'),
  };
}

export function ActivityFeed({
  maxItems = 20,
  autoScroll = true,
  className,
}: ActivityFeedProps) {
  const { isLive, isDemo, setMode, state } = useDataModeSafe();
  const containerRef = useRef<HTMLDivElement>(null);

  // Use the unified data hook
  const { data, isLoading, isError, error, refetch, dataSource } = useActivityFeed({
    limit: maxItems,
  });

  // Transform API data to display format
  const list = data?.map(transformActivity) || [];

  // Auto-scroll to latest on new items
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [list.length, autoScroll]);

  // -------------------------------------------------------------------------
  // Loading State
  // -------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className={cn('space-y-2 p-2', className)}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={`skeleton-${i}`} className="flex gap-2 items-start">
            <Skeleton className="w-4 h-4 rounded-full" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Error State - Shows error in Live mode, NO fake data
  // -------------------------------------------------------------------------
  if (isError) {
    return (
      <div className={cn('flex flex-col items-center justify-center h-full py-6 px-4 text-center', className)}>
        <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center mb-3">
          <AlertTriangle className="w-5 h-5 text-red-400" />
        </div>
        <p className="text-sm text-text-primary mb-1">Lỗi tải activity</p>
        <p className="text-xs text-text-muted mb-3">
          {error?.message || state.errorMessage || 'Không kết nối được server'}
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="text-xs px-2 py-1 rounded bg-accent-cyan text-black hover:bg-accent-cyan/90"
          >
            Thử lại
          </button>
          {isLive && (
            <button
              onClick={() => setMode('demo')}
              className="text-xs px-2 py-1 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30"
            >
              Xem Demo
            </button>
          )}
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Success State
  // -------------------------------------------------------------------------
  return (
    <div
      ref={containerRef}
      className={cn(
        'h-full overflow-y-auto overflow-thin-scroll space-y-1 pr-2 relative',
        className
      )}
    >
      {/* Data Source Badge - Use text only to avoid icon issues */}
      <div className="sticky top-0 right-0 z-10 flex justify-end pb-1">
        <span className={cn(
          'px-1.5 py-0.5 rounded-full border text-[8px] font-mono font-bold',
          dataSource === 'mock' 
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
        )}>
          {dataSource === 'mock' ? '⚗ DEMO' : '● LIVE'}
        </span>
      </div>

      {/* Activity List - Use simple div instead of AnimatePresence to avoid DOM issues */}
      <div className="space-y-1">
        {list.map((item, index) => {
          const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.source;
          return (
            <div
              key={`activity-${item.id}-${index}`}
              className="flex items-start gap-2 p-2 rounded-lg hover:bg-bg-tertiary/50 transition-colors animate-fade-in"
              style={{ animationDelay: `${index * 20}ms` }}
            >
              <span className={cn('mt-0.5 shrink-0', config.color)}>
                {config.icon}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary truncate">{item.message}</p>
                <p className="text-xs text-text-muted font-mono">{item.time}</p>
              </div>
            </div>
          );
        })}
      </div>

      {list.length === 0 && (
        <div className="text-center py-4 text-text-muted text-sm">
          Không có hoạt động
        </div>
      )}
    </div>
  );
}

// Compact version for dashboard
interface CompactActivityFeedProps {
  maxItems?: number;
  className?: string;
}

export function CompactActivityFeed({
  maxItems = 6,
  className,
}: CompactActivityFeedProps) {
  const { isLive, setMode } = useDataModeSafe();
  
  const { data, isLoading, isError, error, refetch, dataSource } = useActivityFeed({
    limit: maxItems,
  });

  const list = data?.map(transformActivity) || [];

  if (isLoading) {
    return (
      <div className={cn('space-y-1', className)}>
        {Array.from({ length: maxItems }).map((_, i) => (
          <Skeleton key={`compact-skeleton-${i}`} className="h-8 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className={cn('py-4 text-center', className)}>
        <p className="text-xs text-red-400 mb-2">
          {error?.message || 'Lỗi tải dữ liệu'}
        </p>
        <div className="flex justify-center gap-2">
          <button onClick={() => refetch()} className="text-xs text-accent-cyan hover:underline">
            Thử lại
          </button>
          {isLive && (
            <button onClick={() => setMode('demo')} className="text-xs text-amber-400 hover:underline">
              Xem Demo
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-1 relative', className)}>
      {/* Data Source Badge */}
      <div className="absolute top-0 right-0">
        <span className={cn(
          'text-[8px] font-mono px-1 rounded',
          dataSource === 'mock' ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'
        )}>
          {dataSource === 'mock' ? 'DEMO' : 'LIVE'}
        </span>
      </div>

      {list.map((item, index) => {
        const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.source;
        return (
          <div
            key={`compact-${item.id}-${index}`}
            className="flex items-center gap-2 px-2 py-1.5 text-xs rounded hover:bg-bg-tertiary/30 transition-colors"
          >
            <span className={cn('shrink-0', config.color)}>{config.icon}</span>
            <span className="flex-1 truncate text-text-secondary">{item.message}</span>
            <span className="shrink-0 text-text-muted font-mono">{item.time}</span>
          </div>
        );
      })}
    </div>
  );
}
