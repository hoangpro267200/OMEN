import { useState, useEffect } from 'react';
import { Shield, Wifi, WifiOff, User } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import { useRealtimeStatus } from '../../hooks/useRealtimePrices';
import type { DataSourceInfo } from '../../hooks/useDataSource';

type SystemStatus = 'OPERATIONAL' | 'DEGRADED' | 'DOWN';

interface HeaderProps {
  systemStatus?: SystemStatus;
  isLive?: boolean;
  connectionStatus?: 'connected' | 'disconnected';
  latencyMs?: number;
  className?: string;
  /** When provided, header shows honest data-source badge (live vs demo). */
  dataSource?: DataSourceInfo;
}

function LiveClock() {
  const [time, setTime] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span className="font-mono text-sm tabular-nums text-[var(--text-secondary)]">
      {time.toLocaleTimeString('en-GB', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  );
}

function DataSourceBadge({ source }: { source: DataSourceInfo }) {
  const c = (
    {
      live: { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400', dot: 'bg-green-500', label: 'TRỰC TIẾP', pulse: true },
      demo: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', dot: 'bg-yellow-500', label: 'DỮ LIỆU DEMO', pulse: false },
      cached: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', dot: 'bg-blue-500', label: 'ĐÃ LƯU', pulse: false },
      error: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', dot: 'bg-red-500', label: 'LỖI', pulse: false },
    } as const
  )[source.type];
  return (
    <div className={cn('flex items-center gap-2 px-3 py-1.5 rounded-full border', c.bg, c.border, c.text)} title={source.message}>
      <span className={cn('w-2 h-2 rounded-full', c.dot, c.pulse && 'animate-pulse')} />
      <span className="text-xs font-medium">{c.label}</span>
      {source.signalCount > 0 ? <span className="text-xs opacity-60">({source.signalCount})</span> : null}
    </div>
  );
}

export function Header({
  systemStatus = 'OPERATIONAL',
  isLive = true,
  connectionStatus = 'connected',
  latencyMs,
  className,
  dataSource,
}: HeaderProps) {
  const realtimeStatus = useRealtimeStatus();
  const statusConfig = {
    OPERATIONAL: {
      label: 'VẬN HÀNH',
      dotClass: 'bg-[var(--success)] shadow-[var(--glow-success)]',
    },
    DEGRADED: {
      label: 'SUY GIẢM',
      dotClass: 'bg-[var(--warning)] animate-pulse',
    },
    DOWN: {
      label: 'NGƯNG',
      dotClass: 'bg-[var(--danger)]',
    },
  };
  const config = statusConfig[systemStatus];

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 border-b backdrop-blur-xl',
        'border-[var(--border-subtle)]',
        systemStatus === 'OPERATIONAL' && 'border-b-[var(--success)]/20',
        className
      )}
      style={{ background: 'rgba(5, 5, 7, 0.8)', height: 64 }}
    >
      <div className="h-16 px-6 flex items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="w-9 h-9 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] flex items-center justify-center shadow-[var(--glow-blue)]">
              <Shield className="w-5 h-5 text-[var(--accent-blue)]" />
            </div>
            <span className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              OMEN
            </span>
          </motion.div>
          <div className="h-6 w-px bg-[var(--border-medium)] hidden sm:block" />
          <div className="flex items-center gap-2">
            <span className={cn('w-2 h-2 rounded-full shrink-0', config.dotClass)} />
            <span className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              {config.label}
            </span>
          </div>
          {dataSource ? (
            <DataSourceBadge source={dataSource} />
          ) : isLive ? (
            <span className="text-xs font-medium text-[var(--success)] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse" />
              SỐNG
            </span>
          ) : null}
          {realtimeStatus && (
            <span
              className={cn(
                'text-xs font-medium flex items-center gap-1',
                realtimeStatus.websocket_connected
                  ? 'text-cyan-400'
                  : 'text-[var(--text-tertiary)]'
              )}
              title={
                realtimeStatus.websocket_connected
                  ? `${realtimeStatus.registered_signals} signals tracked`
                  : 'WebSocket not connected'
              }
            >
              <span
                className={cn(
                  'w-1.5 h-1.5 rounded-full shrink-0',
                  realtimeStatus.websocket_connected
                    ? 'bg-cyan-400 animate-pulse'
                    : 'bg-[var(--text-tertiary)]'
                )}
              />
              {realtimeStatus.websocket_connected ? 'REAL-TIME' : 'POLLING'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-6">
          <LiveClock />
          {latencyMs != null && (
            <span className="font-mono text-sm tabular-nums text-[var(--success)]">
              {latencyMs} ms
            </span>
          )}
          <div className="flex items-center gap-2 text-[var(--text-tertiary)]">
            {connectionStatus === 'connected' ? (
              <Wifi className="w-4 h-4 text-[var(--success)]" />
            ) : (
              <WifiOff className="w-4 h-4 text-[var(--danger)]" />
            )}
            <span className="text-xs uppercase tracking-wider">
              {connectionStatus === 'connected' ? 'ĐÃ KẾT NỐI' : 'Ngắt kết nối'}
            </span>
          </div>
          <div className="flex items-center gap-2 pl-4 border-l border-[var(--border-subtle)]">
            <User className="w-4 h-4 text-[var(--text-tertiary)]" />
            <span className="text-sm text-[var(--text-secondary)]">Hệ thống</span>
          </div>
        </div>
      </div>
    </header>
  );
}
