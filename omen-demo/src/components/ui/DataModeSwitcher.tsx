/**
 * DataModeSwitcher - Clear mode switching between Live and Demo
 * 
 * Two modes ONLY:
 * - LIVE: Real data from API. If API fails, shows error (NOT fake data)
 * - DEMO: Mock data for demonstrations
 * 
 * NO HYBRID MODE. Clear separation between real and fake data.
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  ChevronDown,
  Check,
  AlertTriangle,
  Zap,
  Database,
  TestTube,
} from 'lucide-react';
import { useDataModeSafe, type DataMode, type ConnectionStatus } from '../../context/DataModeContext';
import { cn } from '../../lib/utils';

// ============================================================================
// MODE CONFIG - Only Live and Demo
// ============================================================================

interface ModeConfig {
  label: string;
  labelVi: string;
  description: string;
  descriptionVi: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  borderColor: string;
  glowColor: string;
}

const modeConfig: Record<DataMode, ModeConfig> = {
  live: {
    label: 'LIVE',
    labelVi: 'DỮ LIỆU THẬT',
    description: 'Real-time data from production API',
    descriptionVi: 'Dữ liệu thật từ server API',
    icon: <Database className="w-4 h-4" />,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/50',
    glowColor: 'shadow-emerald-500/20',
  },
  demo: {
    label: 'DEMO',
    labelVi: 'DỮ LIỆU GIẢ',
    description: 'Simulated mock data for demonstrations',
    descriptionVi: 'Dữ liệu giả lập để demo',
    icon: <TestTube className="w-4 h-4" />,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/50',
    glowColor: 'shadow-amber-500/20',
  },
};

const connectionStatusConfig: Record<
  ConnectionStatus,
  { label: string; color: string; pulse: boolean }
> = {
  connected: { label: 'Connected', color: 'bg-emerald-400', pulse: true },
  connecting: { label: 'Connecting...', color: 'bg-amber-400', pulse: true },
  disconnected: { label: 'Offline', color: 'bg-gray-500', pulse: false },
  error: { label: 'Error', color: 'bg-red-400', pulse: false },
};

// ============================================================================
// COMPACT SWITCHER (For Header)
// ============================================================================

export interface DataModeSwitcherCompactProps {
  className?: string;
  showConnectionDot?: boolean;
}

export function DataModeSwitcherCompact({
  className,
  showConnectionDot = true,
}: DataModeSwitcherCompactProps) {
  const { state, toggleMode, shouldShowError, liveAllowed, liveBlockers } = useDataModeSafe();
  const config = modeConfig[state.mode];
  const connStatus = connectionStatusConfig[state.connectionStatus];
  
  // Disable switching TO live if backend blocks it
  const canSwitchToLive = liveAllowed;
  const isDisabled = state.isTransitioning || (state.mode === 'demo' && !canSwitchToLive);
  
  // Build tooltip message
  let tooltipMsg = state.mode === 'live' && shouldShowError 
    ? 'Connection error - Click to switch to Demo' 
    : `Click to switch to ${state.mode === 'live' ? 'Demo' : 'Live'}`;
  
  if (state.mode === 'demo' && !canSwitchToLive) {
    tooltipMsg = `LIVE mode blocked: ${liveBlockers[0] || 'Data sources not ready'}`;
  }

  return (
    <motion.button
      onClick={toggleMode}
      disabled={isDisabled}
      className={cn(
        'relative flex items-center gap-2 px-3 py-1.5 rounded-full',
        'border transition-all duration-300',
        'hover:scale-[1.02] active:scale-[0.98]',
        'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[var(--bg-primary)]',
        config.bgColor,
        config.borderColor,
        // Show red border if in Live mode but error
        state.mode === 'live' && shouldShowError && 'border-red-500/50',
        // Show muted style if LIVE is blocked
        state.mode === 'demo' && !canSwitchToLive && 'opacity-70',
        `focus:ring-current`,
        isDisabled && 'opacity-50 cursor-not-allowed',
        className
      )}
      whileHover={!isDisabled ? { scale: 1.02 } : {}}
      whileTap={!isDisabled ? { scale: 0.98 } : {}}
      aria-label={`Mode: ${config.labelVi}. ${isDisabled ? 'Disabled' : 'Click to switch.'}`}
      title={tooltipMsg}
    >
      {/* Animated Icon */}
      <AnimatePresence mode="wait">
        <motion.span
          key={state.mode}
          initial={{ rotate: -180, opacity: 0, scale: 0.5 }}
          animate={{ rotate: 0, opacity: 1, scale: 1 }}
          exit={{ rotate: 180, opacity: 0, scale: 0.5 }}
          transition={{ duration: 0.2 }}
          className={cn(
            config.color,
            state.mode === 'live' && shouldShowError && 'text-red-400'
          )}
        >
          {state.mode === 'live' && shouldShowError ? <WifiOff className="w-4 h-4" /> : config.icon}
        </motion.span>
      </AnimatePresence>

      {/* Label - show both modes clearly */}
      <AnimatePresence mode="wait">
        <motion.span
          key={`label-${state.mode}`}
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -10, opacity: 0 }}
          transition={{ duration: 0.15 }}
          className={cn(
            'text-xs font-mono font-bold tracking-wider',
            state.mode === 'live' && shouldShowError ? 'text-red-400' : config.color
          )}
        >
          {state.mode === 'live' && shouldShowError ? 'LỖI' : config.label}
        </motion.span>
      </AnimatePresence>

      {/* Connection Status Indicator */}
      {showConnectionDot && state.mode === 'live' && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full transition-colors',
            shouldShowError ? 'bg-red-400' : connStatus.color,
            !shouldShowError && connStatus.pulse && 'animate-pulse'
          )}
          title={shouldShowError ? 'Không kết nối được' : connStatus.label}
        />
      )}

      {/* Demo indicator + LIVE blocked warning */}
      {state.mode === 'demo' && (
        <span className={cn(
          "text-[10px] font-normal",
          canSwitchToLive ? "text-amber-400/70" : "text-red-400/70"
        )}>
          {canSwitchToLive ? '(demo)' : '(LIVE blocked)'}
        </span>
      )}

      {/* Transition Progress Bar */}
      {state.isTransitioning && (
        <motion.div
          className="absolute inset-0 rounded-full overflow-hidden pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <motion.div
            className="h-full bg-white/10"
            initial={{ width: '0%' }}
            animate={{ width: `${state.transitionProgress}%` }}
            transition={{ duration: 0.05 }}
          />
        </motion.div>
      )}
    </motion.button>
  );
}

// ============================================================================
// FULL SWITCHER (Dropdown with Details)
// ============================================================================

export interface DataModeSwitcherFullProps {
  className?: string;
}

export function DataModeSwitcherFull({ className }: DataModeSwitcherFullProps) {
  const { state, setMode, canUseLiveData, retryConnection, liveAllowed, liveBlockers } = useDataModeSafe();
  const [isOpen, setIsOpen] = useState(false);
  const currentConfig = modeConfig[state.mode];
  const connStatus = connectionStatusConfig[state.connectionStatus];

  // Close on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  return (
    <div className={cn('relative', className)}>
      {/* Trigger Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-3 px-4 py-2.5 rounded-xl',
          'border transition-all duration-300',
          'hover:bg-white/5',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[var(--bg-primary)]',
          currentConfig.bgColor,
          currentConfig.borderColor,
          `focus:ring-current`
        )}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className={currentConfig.color}>{currentConfig.icon}</span>
        <div className="text-left">
          <div className={cn('text-sm font-mono font-bold', currentConfig.color)}>
            {currentConfig.label}
          </div>
          <div className="text-xs text-[var(--text-muted)]">{connStatus.label}</div>
        </div>
        <ChevronDown
          className={cn(
            'w-4 h-4 text-[var(--text-muted)] transition-transform duration-200',
            isOpen && 'rotate-180'
          )}
        />
      </motion.button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Dropdown Panel */}
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className={cn(
                'absolute top-full left-0 mt-2 w-80 p-2 rounded-xl z-50',
                'bg-[var(--bg-secondary)]/95 backdrop-blur-xl',
                'border border-[var(--border-subtle)]',
                'shadow-2xl shadow-black/50'
              )}
              role="listbox"
            >
              {/* Mode Options - Only Live and Demo */}
              {(['live', 'demo'] as DataMode[]).map((mode) => {
                const cfg = modeConfig[mode];
                const isSelected = state.mode === mode;
                // LIVE mode disabled if backend blocks it
                const isDisabled = mode === 'live' && !liveAllowed;

                return (
                  <motion.button
                    key={mode}
                    onClick={() => {
                      setMode(mode);
                      setIsOpen(false);
                    }}
                    disabled={isDisabled}
                    role="option"
                    aria-selected={isSelected}
                    className={cn(
                      'w-full flex items-start gap-3 p-3 rounded-lg',
                      'transition-all duration-200',
                      'focus:outline-none focus:ring-2 focus:ring-[var(--accent-cyan)]',
                      isSelected && cfg.bgColor,
                      isSelected && cfg.borderColor,
                      isSelected && 'border',
                      !isSelected && 'hover:bg-white/5'
                    )}
                    whileHover={{ x: 4 }}
                  >
                    {/* Icon */}
                    <span className={cn('mt-0.5', isSelected ? cfg.color : 'text-[var(--text-muted)]')}>
                      {cfg.icon}
                    </span>

                    {/* Text */}
                    <div className="flex-1 text-left">
                      <div
                        className={cn(
                          'text-sm font-medium flex items-center gap-2',
                          isSelected ? cfg.color : 'text-[var(--text-primary)]'
                        )}
                      >
                        {cfg.label}
                        <span className="text-[10px] opacity-70">({cfg.labelVi})</span>
                      </div>
                      <div className="text-xs text-[var(--text-muted)] mt-0.5">{cfg.descriptionVi}</div>

                      {/* Connection status for Live mode */}
                      {mode === 'live' && isSelected && (
                        <div className={cn(
                          'flex items-center gap-1 mt-2 text-xs',
                          canUseLiveData ? 'text-emerald-400' : 'text-red-400'
                        )}>
                          {canUseLiveData ? (
                            <>
                              <Wifi className="w-3 h-3" />
                              <span>Đã kết nối server</span>
                            </>
                          ) : (
                            <>
                              <AlertTriangle className="w-3 h-3" />
                              <span>{state.errorMessage || 'Không thể kết nối server'}</span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  retryConnection();
                                }}
                                className="ml-2 text-[var(--accent-cyan)] hover:underline"
                              >
                                Thử lại
                              </button>
                            </>
                          )}
                        </div>
                      )}

                      {/* Notice for Demo mode */}
                      {mode === 'demo' && (
                        <div className="flex items-center gap-1 mt-2 text-xs text-amber-400/70">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Dữ liệu giả lập, không phải thật</span>
                        </div>
                      )}
                      
                      {/* LIVE blocked notice */}
                      {mode === 'live' && !liveAllowed && liveBlockers.length > 0 && (
                        <div className="flex items-start gap-1 mt-2 text-xs text-red-400">
                          <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <span>LIVE blocked: {liveBlockers[0]}</span>
                        </div>
                      )}
                    </div>

                    {/* Selected Check */}
                    {isSelected && (
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className={cfg.color}
                      >
                        <Check className="w-4 h-4" />
                      </motion.span>
                    )}
                  </motion.button>
                );
              })}

              {/* Divider */}
              <div className="my-2 border-t border-[var(--border-subtle)]" />

              {/* Footer Info */}
              <div className="px-3 py-2 text-xs text-[var(--text-muted)]">
                <div className="flex items-center justify-between">
                  <span>Connection:</span>
                  <span className="flex items-center gap-1.5">
                    <span
                      className={cn('w-1.5 h-1.5 rounded-full', connStatus.color)}
                    />
                    {connStatus.label}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span>Last sync:</span>
                  <span className="font-mono">
                    {state.lastSyncTime
                      ? new Date(state.lastSyncTime).toLocaleTimeString()
                      : 'Never'}
                  </span>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// TRANSITION OVERLAY
// ============================================================================

export function DataModeTransitionOverlay() {
  const { state } = useDataModeSafe();
  const config = modeConfig[state.mode];

  return (
    <AnimatePresence>
      {state.isTransitioning && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className={cn(
            'fixed inset-0 z-[9999] pointer-events-none',
            'flex items-center justify-center',
            'bg-black/30 backdrop-blur-sm'
          )}
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 1.1, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={cn(
              'flex flex-col items-center gap-4 p-8 rounded-2xl',
              'bg-[var(--bg-secondary)]/95 backdrop-blur-xl',
              'border border-[var(--border-subtle)]',
              'shadow-2xl'
            )}
          >
            {/* Animated Logo */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className={cn(
                'w-14 h-14 rounded-xl flex items-center justify-center',
                'bg-gradient-to-br from-[var(--accent-cyan)] to-[var(--accent-amber)]',
                'shadow-lg shadow-cyan-500/20'
              )}
            >
              <Zap className="w-7 h-7 text-[var(--bg-primary)]" />
            </motion.div>

            {/* Progress Bar */}
            <div className="w-56 h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-[var(--accent-cyan)] to-[var(--accent-amber)] rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: `${state.transitionProgress}%` }}
                transition={{ duration: 0.05 }}
              />
            </div>

            {/* Label */}
            <div className="text-center">
              <span className="text-sm text-[var(--text-secondary)]">Switching to </span>
              <span className={cn('text-sm font-bold', config.color)}>{config.label}</span>
              <span className="text-sm text-[var(--text-secondary)]"> mode...</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ============================================================================
// INLINE STATUS BADGE (For use in other components)
// ============================================================================

export interface DataModeStatusBadgeProps {
  className?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export function DataModeStatusBadge({
  className,
  showLabel = true,
  size = 'md',
}: DataModeStatusBadgeProps) {
  const { state } = useDataModeSafe();
  const config = modeConfig[state.mode];

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full',
        size === 'sm' ? 'px-2 py-0.5' : 'px-2.5 py-1',
        config.bgColor,
        'border',
        config.borderColor,
        className
      )}
    >
      <span className={config.color}>{config.icon}</span>
      {showLabel && (
        <span
          className={cn(
            'font-mono font-bold',
            size === 'sm' ? 'text-[10px]' : 'text-xs',
            config.color
          )}
        >
          {config.label}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// CONNECTION BANNER (For header when disconnected)
// ============================================================================

export interface ConnectionBannerProps {
  className?: string;
}

export function ConnectionBanner({ className }: ConnectionBannerProps) {
  const { state, retryConnection, setMode, shouldShowError } = useDataModeSafe();

  // Only show when in live mode and has error
  if (state.mode === 'demo') return null;
  if (!shouldShowError) return null;

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      className={cn(
        'bg-red-500/10 border-b border-red-500/30',
        'px-4 py-2 flex items-center justify-between gap-4',
        className
      )}
    >
      <div className="flex items-center gap-2 text-sm text-red-400">
        <WifiOff className="w-4 h-4" />
        <span>
          <strong>Chế độ Live:</strong>{' '}
          {state.errorMessage || 'Không thể kết nối server. Dữ liệu không khả dụng.'}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={retryConnection}
          className="px-3 py-1 text-xs font-medium text-red-400 hover:bg-red-500/20 rounded-lg transition-colors flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" />
          Thử lại
        </button>
        <button
          onClick={() => setMode('demo')}
          className="px-3 py-1 text-xs font-medium bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg transition-colors"
        >
          Chuyển sang Demo
        </button>
      </div>
    </motion.div>
  );
}
