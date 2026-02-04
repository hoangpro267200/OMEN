/**
 * ScreenErrorBoundary - Enhanced error boundary for screens/routes
 * 
 * Features:
 * - Catches render errors
 * - Shows friendly error UI
 * - Auto-retry with countdown
 * - Error reporting
 * - Recovery actions
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  RefreshCw,
  Home,
  Bug,
  Copy,
  CheckCircle,
  ChevronDown,
  Send,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// ============================================================================
// TYPES
// ============================================================================

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Fallback component to render on error */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** Called when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Enable auto-retry */
  autoRetry?: boolean;
  /** Auto-retry delay in seconds */
  autoRetryDelay?: number;
  /** Maximum auto-retry attempts */
  maxRetries?: number;
  /** Show technical details */
  showDetails?: boolean;
  /** Component name for logging */
  componentName?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  retryCount: number;
  retryCountdown: number | null;
  copied: boolean;
  showDetails: boolean;
}

// ============================================================================
// ERROR BOUNDARY CLASS
// ============================================================================

export class ScreenErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryTimer: NodeJS.Timeout | null = null;
  private countdownTimer: NodeJS.Timeout | null = null;

  static defaultProps = {
    autoRetry: true,
    autoRetryDelay: 5,
    maxRetries: 3,
    showDetails: true,
    componentName: 'Screen',
  };

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
      retryCountdown: null,
      copied: false,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Call onError callback
    this.props.onError?.(error, errorInfo);

    // Log error
    console.error(`[${this.props.componentName}] Error caught:`, error, errorInfo);

    // Start auto-retry if enabled
    if (this.props.autoRetry && this.state.retryCount < (this.props.maxRetries || 3)) {
      this.startAutoRetry();
    }
  }

  componentWillUnmount() {
    this.clearTimers();
  }

  clearTimers = () => {
    if (this.retryTimer) clearTimeout(this.retryTimer);
    if (this.countdownTimer) clearInterval(this.countdownTimer);
  };

  startAutoRetry = () => {
    const delay = this.props.autoRetryDelay || 5;
    this.setState({ retryCountdown: delay });

    this.countdownTimer = setInterval(() => {
      this.setState((prev) => {
        if (prev.retryCountdown === null || prev.retryCountdown <= 1) {
          return { retryCountdown: null };
        }
        return { retryCountdown: prev.retryCountdown - 1 };
      });
    }, 1000);

    this.retryTimer = setTimeout(() => {
      this.handleRetry();
    }, delay * 1000);
  };

  cancelAutoRetry = () => {
    this.clearTimers();
    this.setState({ retryCountdown: null });
  };

  handleRetry = () => {
    this.clearTimers();
    this.setState((prev) => ({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: prev.retryCount + 1,
      retryCountdown: null,
    }));
  };

  handleReset = () => {
    this.clearTimers();
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
      retryCountdown: null,
    });
  };

  handleCopyError = () => {
    const { error, errorInfo } = this.state;
    const errorText = `
Error: ${error?.message}
Stack: ${error?.stack}
Component Stack: ${errorInfo?.componentStack}
    `.trim();

    navigator.clipboard.writeText(errorText);
    this.setState({ copied: true });
    setTimeout(() => this.setState({ copied: false }), 2000);
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    const { children, fallback, showDetails: propShowDetails, componentName, maxRetries } = this.props;
    const { hasError, error, errorInfo, retryCount, retryCountdown, copied, showDetails } = this.state;

    if (hasError) {
      // Custom fallback
      if (fallback) {
        if (typeof fallback === 'function') {
          return fallback(error!, this.handleReset);
        }
        return fallback;
      }

      // Default error UI
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-lg w-full"
          >
            <div className="text-center mb-6">
              {/* Icon */}
              <motion.div
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200 }}
                className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[var(--status-error)]/10 border border-[var(--status-error)]/20 mb-4"
              >
                <AlertTriangle className="w-8 h-8 text-[var(--status-error)]" />
              </motion.div>

              {/* Title */}
              <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">
                Something went wrong
              </h2>

              {/* Message */}
              <p className="text-[var(--text-muted)]">
                {error?.message || `An error occurred in ${componentName}`}
              </p>

              {/* Retry info */}
              {retryCountdown !== null && (
                <p className="text-sm text-[var(--accent-cyan)] mt-2">
                  Auto-retrying in {retryCountdown}s...
                  <button
                    onClick={this.cancelAutoRetry}
                    className="ml-2 underline hover:no-underline"
                  >
                    Cancel
                  </button>
                </p>
              )}

              {/* Retry count */}
              {retryCount > 0 && (
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Retry attempt {retryCount}/{maxRetries}
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-center gap-3 mb-6">
              <button
                onClick={this.handleRetry}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-cyan)] text-black font-medium hover:bg-[var(--accent-cyan)]/90 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>

              <a
                href="/"
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition-colors"
              >
                <Home className="w-4 h-4" />
                Go Home
              </a>
            </div>

            {/* Technical Details */}
            {propShowDetails && (
              <div className="rounded-xl border border-[var(--border-subtle)] overflow-hidden">
                <button
                  onClick={this.toggleDetails}
                  className="w-full flex items-center justify-between px-4 py-3 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] transition-colors"
                >
                  <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                    <Bug className="w-4 h-4" />
                    Technical Details
                  </div>
                  <ChevronDown
                    className={cn(
                      'w-4 h-4 text-[var(--text-muted)] transition-transform',
                      showDetails && 'rotate-180'
                    )}
                  />
                </button>

                {showDetails && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="p-4 bg-[var(--bg-primary)] border-t border-[var(--border-subtle)]"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-[var(--text-muted)]">Error Stack</span>
                      <button
                        onClick={this.handleCopyError}
                        className="flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                      >
                        {copied ? (
                          <>
                            <CheckCircle className="w-3 h-3 text-[var(--status-success)]" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>

                    <pre className="text-xs font-mono text-[var(--status-error)] bg-[var(--bg-secondary)] p-3 rounded-lg overflow-auto max-h-[200px]">
                      {error?.stack || 'No stack trace available'}
                    </pre>

                    {errorInfo?.componentStack && (
                      <>
                        <div className="text-xs text-[var(--text-muted)] mt-3 mb-2">
                          Component Stack
                        </div>
                        <pre className="text-xs font-mono text-[var(--text-muted)] bg-[var(--bg-secondary)] p-3 rounded-lg overflow-auto max-h-[100px]">
                          {errorInfo.componentStack}
                        </pre>
                      </>
                    )}

                    {/* Report button */}
                    <button
                      onClick={() => {
                        console.log('Report error:', { error, errorInfo });
                        // TODO: Integrate with error reporting service
                      }}
                      className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:bg-[var(--bg-elevated)] text-sm transition-colors"
                    >
                      <Send className="w-4 h-4" />
                      Report Issue
                    </button>
                  </motion.div>
                )}
              </div>
            )}
          </motion.div>
        </div>
      );
    }

    return children;
  }
}

// ============================================================================
// FUNCTIONAL WRAPPER
// ============================================================================

export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options?: Omit<ErrorBoundaryProps, 'children'>
): React.FC<P> {
  return function WithErrorBoundary(props: P) {
    return (
      <ScreenErrorBoundary {...options}>
        <WrappedComponent {...props} />
      </ScreenErrorBoundary>
    );
  };
}

// ============================================================================
// EXPORTS
// ============================================================================

export default ScreenErrorBoundary;
