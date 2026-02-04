/**
 * DataStateWrapper - Wrapper component for data loading states
 * 
 * Handles:
 * - Loading state with skeleton
 * - Error state with retry (for Live mode)
 * - Empty state
 * - Success state (renders children)
 * 
 * IMPORTANT: In Live mode, errors show error message, NOT fake data.
 */

import React, { ReactNode } from 'react';
import { RefreshCw, AlertTriangle, Inbox } from 'lucide-react';
import { useDataModeSafe } from '../../context/DataModeContext';
import { cn } from '../../lib/utils';
import { Skeleton } from './Skeleton';

// ============================================================================
// TYPES
// ============================================================================

export interface DataStateWrapperProps {
  /** Is data loading */
  isLoading?: boolean;
  /** Is there an error */
  isError?: boolean;
  /** Error object */
  error?: Error | null;
  /** Is data empty (after loading) */
  isEmpty?: boolean;
  /** Data source indicator */
  dataSource?: 'live' | 'mock' | 'cache';
  /** Retry function */
  onRetry?: () => void;
  /** Custom loading component */
  loadingComponent?: ReactNode;
  /** Custom error title */
  errorTitle?: string;
  /** Custom empty message */
  emptyMessage?: string;
  /** Children to render when data is available */
  children: ReactNode;
  /** Additional class names */
  className?: string;
  /** Compact mode */
  compact?: boolean;
  /** Show data source badge */
  showDataSourceBadge?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export function DataStateWrapper({
  isLoading = false,
  isError = false,
  error,
  isEmpty = false,
  dataSource = 'live',
  onRetry,
  loadingComponent,
  errorTitle,
  emptyMessage = 'Không có dữ liệu',
  children,
  className,
  compact = false,
  showDataSourceBadge = true,
}: DataStateWrapperProps) {
  const { isLive, isDemo, setMode, retryConnection, state } = useDataModeSafe();

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('relative', className)}>
        {loadingComponent || (
          <div className="space-y-4 p-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}
      </div>
    );
  }

  // Error state - CRITICAL for Live mode
  if (isError) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center text-center animate-fade-in',
          compact ? 'py-6 px-4' : 'py-12 px-6',
          className
        )}
      >
        <div className={cn(
          'flex items-center justify-center rounded-2xl border mb-4',
          compact ? 'w-12 h-12' : 'w-16 h-16',
          'bg-red-500/10 border-red-500/20'
        )}>
          <AlertTriangle className={cn(compact ? 'w-6 h-6' : 'w-8 h-8', 'text-red-400')} />
        </div>

        <h3 className={cn(
          'font-bold text-[var(--text-primary)]',
          compact ? 'text-base mb-1' : 'text-lg mb-2'
        )}>
          {errorTitle || (isLive ? 'Lỗi Kết Nối API' : 'Lỗi Tải Dữ Liệu')}
        </h3>

        <p className={cn(
          'text-[var(--text-muted)] max-w-sm',
          compact ? 'text-xs mb-3' : 'text-sm mb-4'
        )}>
          {error?.message || state.errorMessage || 'Không thể tải dữ liệu. Vui lòng thử lại.'}
        </p>

        {/* Mode indicator */}
        {isLive && (
          <p className="text-xs text-red-400/70 mb-4 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Đang ở chế độ LIVE - không hiện dữ liệu giả
          </p>
        )}

        <div className="flex flex-wrap items-center justify-center gap-2">
          {onRetry && (
            <button
              onClick={onRetry}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg font-medium transition-all',
                'bg-[var(--accent-cyan)] text-black hover:bg-[var(--accent-cyan)]/90',
                compact ? 'text-xs' : 'text-sm'
              )}
            >
              <RefreshCw className="w-3 h-3" />
              Thử lại
            </button>
          )}

          {isLive && (
            <button
              onClick={() => setMode('demo')}
              className={cn(
                'px-3 py-1.5 rounded-lg font-medium transition-all',
                'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 border border-amber-500/30',
                compact ? 'text-xs' : 'text-sm'
              )}
            >
              ⚗ Xem Demo
            </button>
          )}
        </div>
      </div>
    );
  }

  // Empty state
  if (isEmpty) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center text-center animate-fade-in',
          compact ? 'py-6 px-4' : 'py-12 px-6',
          className
        )}
      >
        <div className={cn(
          'flex items-center justify-center rounded-2xl border mb-4',
          compact ? 'w-12 h-12' : 'w-16 h-16',
          'bg-[var(--bg-tertiary)] border-[var(--border-subtle)]'
        )}>
          <Inbox className={cn(compact ? 'w-6 h-6' : 'w-8 h-8', 'text-[var(--text-muted)]')} />
        </div>

        <p className={cn(
          'text-[var(--text-muted)]',
          compact ? 'text-xs' : 'text-sm'
        )}>
          {emptyMessage}
        </p>
      </div>
    );
  }

  // Success state - render children with optional data source badge
  return (
    <div className={cn('relative', className)}>
      {/* Data Source Badge */}
      {showDataSourceBadge && (
        <div className="absolute top-2 right-2 z-10">
          <DataSourceBadge source={dataSource} compact />
        </div>
      )}
      {children}
    </div>
  );
}

// ============================================================================
// DATA SOURCE BADGE - Uses text symbols to avoid icon rendering issues
// ============================================================================

interface DataSourceBadgeProps {
  source: 'live' | 'mock' | 'cache';
  compact?: boolean;
  className?: string;
}

export function DataSourceBadge({ source, compact = false, className }: DataSourceBadgeProps) {
  const config = {
    live: {
      label: '● LIVE',
      labelVi: 'Thật',
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/30',
    },
    mock: {
      label: '⚗ DEMO',
      labelVi: 'Giả',
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/30',
    },
    cache: {
      label: '◐ CACHE',
      labelVi: 'Cache',
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
      borderColor: 'border-cyan-500/30',
    },
  };

  const cfg = config[source];

  return (
    <span
      className={cn(
        'px-2 py-0.5 rounded-full border font-mono font-bold',
        compact ? 'text-[9px]' : 'text-[10px]',
        cfg.bgColor,
        cfg.borderColor,
        cfg.color,
        className
      )}
      title={`Nguồn dữ liệu: ${cfg.labelVi}`}
    >
      {cfg.label}
    </span>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default DataStateWrapper;
