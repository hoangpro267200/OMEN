/**
 * Query State Component
 *
 * Handles loading, error, and empty states for queries.
 */

import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { AlertCircle, RefreshCw, Inbox } from 'lucide-react'
import { Button } from './Button'

interface QueryStateProps<T> {
  query: UseQueryResult<T, Error>
  children: (data: T) => ReactNode
  loadingComponent?: ReactNode
  errorComponent?: ReactNode
  emptyComponent?: ReactNode
  isEmpty?: (data: T) => boolean
}

export function QueryState<T>({
  query,
  children,
  loadingComponent,
  errorComponent,
  emptyComponent,
  isEmpty,
}: QueryStateProps<T>) {
  if (query.isLoading) {
    return loadingComponent ?? <LoadingSkeleton />
  }

  if (query.isError) {
    return (
      errorComponent ?? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      )
    )
  }

  if (query.data && isEmpty?.(query.data)) {
    return emptyComponent ?? <QueryEmptyState />
  }

  if (query.data) {
    return <>{children(query.data)}</>
  }

  return null
}

// ═══════════════════════════════════════════════════════════════════════════════
// State Components
// ═══════════════════════════════════════════════════════════════════════════════

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-4">
      <div className="h-4 bg-[var(--bg-tertiary)] rounded w-3/4" />
      <div className="h-4 bg-[var(--bg-tertiary)] rounded w-1/2" />
      <div className="h-4 bg-[var(--bg-tertiary)] rounded w-5/6" />
    </div>
  )
}

interface ErrorStateProps {
  error: Error
  onRetry?: () => void
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-12 h-12 rounded-full bg-[var(--accent-red)]/10 flex items-center justify-center mb-4">
        <AlertCircle className="w-6 h-6 text-[var(--accent-red)]" />
      </div>
      <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
        Failed to load data
      </h3>
      <p className="text-sm text-[var(--text-secondary)] mb-4">
        {error.message || 'An unexpected error occurred'}
      </p>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary" className="text-xs px-3 py-1.5">
          <RefreshCw className="w-4 h-4 mr-2" />
          Try Again
        </Button>
      )}
    </div>
  )
}

export function QueryEmptyState({
  title = 'No data',
  description = 'No items to display',
  action,
}: {
  title?: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-12 h-12 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center mb-4">
        <Inbox className="w-6 h-6 text-[var(--text-muted)]" />
      </div>
      <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
        {title}
      </h3>
      <p className="text-sm text-[var(--text-secondary)] mb-4">
        {description}
      </p>
      {action}
    </div>
  )
}
