import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Menu } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Badge } from '../ui/Badge';
import { ConnectionStatus } from '../ui/ConnectionStatus';
import { LanguageSwitcher } from '../ui/LanguageSwitcher';
import { useDemoModeContext } from '../../context/DemoModeContext';
import { useDataSourceMode } from '../../lib/mode/store';

const HEADER_HEIGHT = 56;

export interface ShellHeaderProps {
  /** Optional: show global search (hidden when demo mode) */
  showSearch?: boolean;
  /** Mobile: toggle sidebar drawer */
  onMobileMenuToggle?: () => void;
  className?: string;
}

function useLiveTime() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export function ShellHeader({ showSearch = true, onMobileMenuToggle, className = '' }: ShellHeaderProps) {
  const { isDemoMode, setDemoMode } = useDemoModeContext();
  const [dataSourceMode, setDataSourceMode] = useDataSourceMode();
  const now = useLiveTime();
  const timeStr = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const showSearchInput = showSearch && !isDemoMode;

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className={cn(
        'fixed left-0 right-0 top-0 z-40 flex h-14 items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-4 md:px-6',
        className
      )}
      style={{ height: HEADER_HEIGHT }}
    >
      {/* Left: Mobile menu + Logo + tagline */}
      <div className="flex min-w-0 shrink items-center gap-3">
        {onMobileMenuToggle && (
          <button
            type="button"
            onClick={onMobileMenuToggle}
            aria-label="Open menu"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-button)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)] md:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <span className="font-mono text-lg font-semibold tracking-tight text-[var(--text-primary)]">
          OMEN
        </span>
        {isDemoMode && (
          <Badge variant="OPEN" className="shrink-0">
            DEMO
          </Badge>
        )}
        <span className="hidden truncate text-sm text-[var(--text-muted)] sm:inline">
          Signal Intelligence
        </span>
      </div>

      {/* Center: Optional search (hidden in demo mode) */}
      {showSearchInput && (
        <div className="hidden flex-1 max-w-md justify-center px-4 md:flex">
          <div className="flex w-full max-w-xs items-center gap-2 rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-1.5">
            <Search className="h-4 w-4 shrink-0 text-[var(--text-muted)]" />
            <input
              type="search"
              placeholder="Search…"
              className="min-w-0 flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
              aria-label="Search"
            />
          </div>
        </div>
      )}

      {/* Right: Data Source, Demo Mode toggle, time, status */}
      <div className="flex shrink-0 items-center gap-4">
        {/* Data Source: Demo | Live */}
        <div className="flex items-center gap-2">
          <span className="hidden text-xs text-[var(--text-muted)] sm:inline">
            Data
          </span>
          <button
            type="button"
            aria-label="Toggle data source (demo / live)"
            onClick={() => setDataSourceMode(dataSourceMode === 'demo' ? 'live' : 'demo')}
            className={cn(
              'rounded-[var(--radius-button)] border px-2 py-1 font-mono text-xs font-medium transition-colors',
              dataSourceMode === 'demo'
                ? 'border-[var(--accent-amber)] bg-[var(--accent-amber)]/20 text-[var(--accent-amber)]'
                : 'border-[var(--accent-blue)] bg-[var(--accent-blue)]/20 text-[var(--accent-blue)]'
            )}
          >
            {dataSourceMode === 'demo' ? 'Demo' : 'Live'}
          </button>
        </div>
        {/* Demo Mode toggle (presentation overlay) */}
        <div className="flex items-center gap-2">
          <span className="hidden text-xs text-[var(--text-muted)] sm:inline">
            Demo Mode
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={isDemoMode}
            aria-label="Toggle demo mode"
            onClick={() => setDemoMode(!isDemoMode)}
            className={cn(
              'relative h-6 w-11 shrink-0 rounded-full border transition-colors',
              isDemoMode
                ? 'border-[var(--accent-amber)] bg-[var(--accent-amber)]/30'
                : 'border-[var(--border-subtle)] bg-[var(--bg-tertiary)]'
            )}
          >
            <motion.span
              className="absolute top-1 h-4 w-4 rounded-full bg-[var(--text-primary)]"
              initial={false}
              animate={{ left: isDemoMode ? '22px' : '4px' }}
              transition={{ type: 'spring', stiffness: 500, damping: 35 }}
              style={{ top: 4 }}
            />
          </button>
        </div>

        {/* Date/time */}
        <div className="hidden font-mono text-xs text-[var(--text-secondary)] md:block">
          <span className="text-[var(--text-muted)]">{dateStr}</span>
          <span className="ml-2 tabular-nums">{timeStr}</span>
        </div>

        {/* Language */}
        <LanguageSwitcher />
        {/* WebSocket connection status */}
        <ConnectionStatus />
      </div>
    </motion.header>
  );
}

export { HEADER_HEIGHT };
