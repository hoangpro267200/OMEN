import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';
import type { DataSourceInfo } from '../../hooks/useDataSource';
import { StatusDot } from '../ui/StatusDot';
import { Badge } from '../ui/Badge';

export interface HeaderProps {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  className?: string;
  /** Dashboard header props (when used in App) */
  systemStatus?: string;
  isLive?: boolean;
  connectionStatus?: string;
  latencyMs?: number;
  dataSource?: DataSourceInfo;
  signalsCount?: number;
  enableRealtimePolling?: boolean;
}

/**
 * Page/section header — Mission Control style.
 * Supports simple (title/subtitle/actions) or full dashboard (systemStatus, dataSource, etc.).
 */
export function Header({
  title,
  subtitle,
  actions,
  className = '',
  systemStatus,
  isLive,
  connectionStatus,
  latencyMs,
  dataSource,
  signalsCount,
}: HeaderProps) {
  const isDashboard = systemStatus != null || dataSource != null;

  if (isDashboard) {
    return (
      <header
        className={cn(
          'flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-6 py-4',
          className
        )}
      >
        <div className="flex items-center gap-4">
          <span className="font-display text-lg font-medium tracking-tight text-[var(--text-primary)]">
            OMEN
          </span>
          <span className="text-sm text-[var(--text-muted)]">Signal Intelligence</span>
          {systemStatus != null && (
            <Badge variant={connectionStatus === 'disconnected' ? 'danger' : 'success'}>
              {systemStatus}
            </Badge>
          )}
          {isLive != null && (
            <StatusDot variant={isLive ? 'live' : 'idle'} label={isLive ? 'LIVE' : 'DEMO'} />
          )}
        </div>
        <div className="flex items-center gap-6 font-mono text-xs text-[var(--text-secondary)]">
          {connectionStatus != null && (
            <span>
              <span className="text-[var(--text-muted)]">Connection </span>
              {connectionStatus}
            </span>
          )}
          {latencyMs != null && (
            <span>
              <span className="text-[var(--text-muted)]">Latency </span>
              {latencyMs} ms
            </span>
          )}
          {signalsCount != null && (
            <span>
              <span className="text-[var(--text-muted)]">Signals </span>
              {signalsCount}
            </span>
          )}
          {dataSource != null && (
            <span className="text-[var(--text-muted)]">{dataSource.source}</span>
          )}
        </div>
      </header>
    );
  }

  return (
    <header
      className={cn(
        'flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-6 py-4',
        className
      )}
    >
      <div>
        {title != null && (
          <h1 className="font-display text-lg font-medium tracking-tight text-[var(--text-primary)]">
            {title}
          </h1>
        )}
        {subtitle != null && (
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">{subtitle}</p>
        )}
      </div>
      {actions != null && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
