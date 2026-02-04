/**
 * ErrorState - Unified error display component
 * 
 * Used for:
 * - 404 Not Found
 * - API errors (especially Live mode connection failures)
 * - Failed data loads
 * - Network errors
 */

import React from 'react';
import { AlertTriangle, RefreshCw, ArrowLeft, Home, Bug, WifiOff, FileQuestion } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useDataModeSafe } from '../../context/DataModeContext';

// ============================================================================
// TYPES
// ============================================================================

export interface ErrorStateProps {
  /** Error title */
  title?: string;
  /** Error message / description */
  message?: string;
  /** Error type for icon selection */
  type?: 'error' | 'not-found' | 'network' | 'empty' | 'api-unavailable';
  /** Primary action button */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Secondary action button */
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  /** Show home link */
  showHomeLink?: boolean;
  /** Technical error details (for developers) */
  errorDetails?: string;
  /** Additional class names */
  className?: string;
  /** Compact mode */
  compact?: boolean;
  /** Show switch to demo button */
  showSwitchToDemo?: boolean;
}

// ============================================================================
// CONFIG
// ============================================================================

const typeConfig = {
  error: {
    icon: AlertTriangle,
    iconColor: 'text-[var(--status-error)]',
    bgColor: 'bg-[var(--status-error)]/10',
    borderColor: 'border-[var(--status-error)]/20',
  },
  'not-found': {
    icon: FileQuestion,
    iconColor: 'text-[var(--accent-amber)]',
    bgColor: 'bg-[var(--accent-amber)]/10',
    borderColor: 'border-[var(--accent-amber)]/20',
  },
  network: {
    icon: WifiOff,
    iconColor: 'text-[var(--accent-cyan)]',
    bgColor: 'bg-[var(--accent-cyan)]/10',
    borderColor: 'border-[var(--accent-cyan)]/20',
  },
  empty: {
    icon: FileQuestion,
    iconColor: 'text-[var(--text-muted)]',
    bgColor: 'bg-[var(--bg-tertiary)]',
    borderColor: 'border-[var(--border-subtle)]',
  },
  'api-unavailable': {
    icon: AlertTriangle, // Changed from Database to AlertTriangle for consistency
    iconColor: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/20',
  },
};

// ============================================================================
// COMPONENT
// ============================================================================

export function ErrorState({
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
  type = 'error',
  action,
  secondaryAction,
  showHomeLink = false,
  errorDetails,
  className,
  compact = false,
  showSwitchToDemo = false,
}: ErrorStateProps) {
  const config = typeConfig[type];
  const Icon = config.icon;
  const { setMode, isLive } = useDataModeSafe();

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center animate-fade-in',
        compact ? 'py-8 px-4' : 'min-h-[40vh] py-12 px-6',
        className
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex items-center justify-center rounded-2xl border',
          compact ? 'w-14 h-14 mb-4' : 'w-20 h-20 mb-6',
          config.bgColor,
          config.borderColor
        )}
      >
        <Icon className={cn(compact ? 'w-7 h-7' : 'w-10 h-10', config.iconColor)} />
      </div>

      {/* Title */}
      <h2 className={cn('font-bold text-[var(--text-primary)]', compact ? 'text-lg mb-2' : 'text-2xl mb-3')}>
        {title}
      </h2>

      {/* Message */}
      <p
        className={cn(
          'text-[var(--text-muted)] max-w-md',
          compact ? 'text-sm mb-4' : 'text-base mb-6'
        )}
      >
        {message}
      </p>

      {/* Actions */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        {action && (
          <button
            onClick={action.onClick}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
              'bg-[var(--accent-cyan)] text-black hover:bg-[var(--accent-cyan)]/90',
              compact ? 'text-sm' : 'text-base'
            )}
          >
            <RefreshCw className="w-4 h-4" />
            {action.label}
          </button>
        )}

        {secondaryAction && (
          <button
            onClick={secondaryAction.onClick}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
              'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]',
              compact ? 'text-sm' : 'text-base'
            )}
          >
            <ArrowLeft className="w-4 h-4" />
            {secondaryAction.label}
          </button>
        )}

        {/* Switch to Demo button - only show in Live mode */}
        {showSwitchToDemo && isLive && (
          <button
            onClick={() => setMode('demo')}
            className={cn(
              'px-4 py-2 rounded-lg font-medium transition-all',
              'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 border border-amber-500/30',
              compact ? 'text-sm' : 'text-base'
            )}
          >
            ⚗ Chuyển sang Demo
          </button>
        )}
      </div>

      {/* Home Link */}
      {showHomeLink && (
        <a
          href="/"
          className="mt-4 flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-[var(--accent-cyan)] transition-colors"
        >
          <Home className="w-4 h-4" />
          Return to Home
        </a>
      )}

      {/* Error Details (Developer Info) */}
      {errorDetails && (
        <details className="mt-6 w-full max-w-md text-left">
          <summary className="cursor-pointer text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] flex items-center gap-1">
            <Bug className="w-3 h-3" />
            Technical Details
          </summary>
          <pre className="mt-2 p-3 rounded-lg bg-[var(--bg-tertiary)] text-xs font-mono text-[var(--text-muted)] overflow-auto max-h-32">
            {errorDetails}
          </pre>
        </details>
      )}
    </div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default ErrorState;
