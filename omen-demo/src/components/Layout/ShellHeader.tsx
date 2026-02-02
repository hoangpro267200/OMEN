/**
 * ShellHeader - Neural Command Center top header bar
 * Features: OMEN logo, live status indicator, signal count, time display
 */
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Menu, Activity, Bell, Settings, Zap } from 'lucide-react';
import { cn } from '../../lib/utils';
import { StatusIndicator } from '../ui/StatusIndicator';
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
  /** Current signal count */
  signalCount?: number;
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

export function ShellHeader({ 
  showSearch = true, 
  onMobileMenuToggle, 
  signalCount = 47,
  className = '' 
}: ShellHeaderProps) {
  const { isDemoMode, setDemoMode } = useDemoModeContext();
  const [dataSourceMode, setDataSourceMode] = useDataSourceMode();
  const now = useLiveTime();
  const timeStr = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const isLive = dataSourceMode === 'live';

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className={cn(
        'fixed left-0 right-0 top-0 z-40 flex h-14 items-center justify-between gap-4',
        'border-b border-border-subtle bg-bg-secondary/95 backdrop-blur-sm px-4 md:px-6',
        className
      )}
      style={{ height: HEADER_HEIGHT }}
    >
      {/* Left: Mobile menu + Logo + tagline */}
      <div className="flex min-w-0 shrink items-center gap-4">
        {onMobileMenuToggle && (
          <button
            type="button"
            onClick={onMobileMenuToggle}
            aria-label="Open menu"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-text-secondary hover:bg-bg-tertiary hover:text-text-primary md:hidden transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        
        {/* OMEN Logo */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-cyan/20 to-accent-amber/10 border border-accent-cyan/30 flex items-center justify-center shadow-glow-cyan">
              <Zap className="w-4 h-4 text-accent-cyan" />
            </div>
            <span className="font-display text-lg font-bold tracking-tight text-text-primary">
              OMEN
            </span>
          </div>
          <span className="hidden text-sm text-text-muted font-body lg:inline">
            Signal Intelligence Engine
          </span>
        </div>
      </div>

      {/* Center: Status indicators */}
      <div className="hidden md:flex items-center gap-6">
        {/* Live/Demo Status */}
        <button
          type="button"
          aria-label="Toggle data source"
          onClick={() => setDataSourceMode(dataSourceMode === 'demo' ? 'live' : 'demo')}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all',
            isLive
              ? 'border-status-success/50 bg-status-success/10 shadow-glow-success'
              : 'border-accent-amber/50 bg-accent-amber/10'
          )}
        >
          <StatusIndicator status={isLive ? 'live' : 'warning'} size="sm" />
          <span className={cn(
            'text-xs font-mono font-medium',
            isLive ? 'text-status-success' : 'text-accent-amber'
          )}>
            {isLive ? 'LIVE' : 'DEMO'}
          </span>
        </button>

        {/* Signal Count */}
        <div className="flex items-center gap-2 text-sm">
          <Activity className="w-4 h-4 text-accent-cyan" />
          <span className="font-mono text-accent-cyan font-medium">{signalCount}</span>
          <span className="text-text-muted">signals</span>
        </div>

        {/* Time */}
        <div className="flex items-center gap-2 font-mono text-sm">
          <span className="text-accent-amber tabular-nums">{timeStr}</span>
          <span className="text-text-muted">UTC</span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex shrink-0 items-center gap-2">
        {/* Demo Mode toggle */}
        <div className="hidden sm:flex items-center gap-2 mr-2">
          <span className="text-xs text-text-muted">Presentation</span>
          <button
            type="button"
            role="switch"
            aria-checked={isDemoMode}
            aria-label="Toggle demo mode"
            onClick={() => setDemoMode(!isDemoMode)}
            className={cn(
              'relative h-6 w-11 shrink-0 rounded-full border transition-colors',
              isDemoMode
                ? 'border-accent-amber bg-accent-amber/30'
                : 'border-border-subtle bg-bg-tertiary'
            )}
          >
            <motion.span
              className="absolute h-4 w-4 rounded-full bg-text-primary"
              initial={false}
              animate={{ left: isDemoMode ? '22px' : '4px' }}
              transition={{ type: 'spring', stiffness: 500, damping: 35 }}
              style={{ top: 4 }}
            />
          </button>
        </div>

        {/* Optional search */}
        {showSearch && !isDemoMode && (
          <button className="hidden md:flex h-9 w-9 items-center justify-center rounded-lg text-text-muted hover:bg-bg-tertiary hover:text-text-primary transition-colors">
            <Search className="w-4 h-4" />
          </button>
        )}

        {/* Notifications */}
        <button className="h-9 w-9 flex items-center justify-center rounded-lg text-text-muted hover:bg-bg-tertiary hover:text-text-primary transition-colors">
          <Bell className="w-4 h-4" />
        </button>

        {/* Language */}
        <LanguageSwitcher />

        {/* Connection status */}
        <ConnectionStatus />

        {/* Settings */}
        <button className="h-9 w-9 flex items-center justify-center rounded-lg text-text-muted hover:bg-bg-tertiary hover:text-text-primary transition-colors">
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </motion.header>
  );
}

export { HEADER_HEIGHT };
