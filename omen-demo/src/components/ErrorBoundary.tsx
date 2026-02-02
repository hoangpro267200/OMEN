/**
 * Error Boundary
 *
 * Catches React errors and displays fallback UI.
 * Provides recovery options.
 */

import { Component, type ErrorInfo, type ReactNode, useState } from 'react'
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react'
import { Button } from './ui/Button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  showDetails?: boolean
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo })
    console.error('Error caught by boundary:', error, errorInfo)
    this.props.onError?.(error, errorInfo)
    this.logError(error, errorInfo)
  }

  logError(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary]', {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
    })
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.handleRetry}
          onGoHome={this.handleGoHome}
          showDetails={this.props.showDetails}
        />
      )
    }
    return this.props.children
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Error Fallback Component
// ═══════════════════════════════════════════════════════════════════════════════

interface ErrorFallbackProps {
  error: Error | null
  errorInfo: ErrorInfo | null
  onRetry: () => void
  onGoHome: () => void
  showDetails?: boolean
}

function ErrorFallback({
  error,
  errorInfo,
  onRetry,
  onGoHome,
  showDetails = false,
}: ErrorFallbackProps) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  return (
    <div className="min-h-[400px] flex items-center justify-center p-8">
      <div className="max-w-md w-full">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-full bg-[var(--accent-red)]/10 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-[var(--accent-red)]" />
          </div>
        </div>
        <h2 className="text-xl font-semibold text-[var(--text-primary)] text-center mb-2">
          Something went wrong
        </h2>
        <p className="text-[var(--text-secondary)] text-center mb-6">
          An unexpected error occurred. You can try again or return to the home page.
        </p>
        {error && (
          <div className="bg-[var(--bg-tertiary)] rounded-[var(--radius-card)] p-4 mb-6">
            <p className="text-sm font-mono text-[var(--accent-red)]">
              {error.message || 'Unknown error'}
            </p>
          </div>
        )}
        <div className="flex gap-3 justify-center mb-6">
          <Button onClick={onRetry} variant="primary">
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </Button>
          <Button onClick={onGoHome} variant="secondary">
            <Home className="w-4 h-4 mr-2" />
            Go Home
          </Button>
        </div>
        {showDetails && errorInfo && (
          <div>
            <button
              type="button"
              onClick={() => setDetailsOpen(!detailsOpen)}
              className="flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] mx-auto"
            >
              <Bug className="w-4 h-4" />
              {detailsOpen ? 'Hide' : 'Show'} technical details
            </button>
            {detailsOpen && (
              <pre className="mt-4 p-4 bg-[var(--bg-tertiary)] rounded-[var(--radius-card)] text-xs font-mono text-[var(--text-muted)] overflow-auto max-h-48">
                {error?.stack}
                {'\n\nComponent Stack:'}
                {errorInfo.componentStack}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Screen-level Error Boundary
// ═══════════════════════════════════════════════════════════════════════════════

export function ScreenErrorBoundary({ children }: { children: ReactNode }) {
  const isDev = (import.meta as { env?: { DEV?: boolean } }).env?.DEV ?? false
  return (
    <ErrorBoundary showDetails={isDev}>
      {children}
    </ErrorBoundary>
  )
}
