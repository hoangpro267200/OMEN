/**
 * Query Error Handling
 *
 * Centralized error handling for React Query.
 */

import { QueryCache, QueryClient } from '@tanstack/react-query'
import { keepPreviousData } from '@tanstack/query-core'
import toast from 'react-hot-toast'

// ═══════════════════════════════════════════════════════════════════════════════
// Error Types
// ═══════════════════════════════════════════════════════════════════════════════

export class RequestError extends Error {
  status: number
  code: string
  details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'RequestError'
    this.status = status
    this.code = code
    this.details = details
  }

  static fromResponse(response: Response, body?: { code?: string; message?: string; details?: unknown }): RequestError {
    const code = body?.code ?? `HTTP_${response.status}`
    const message = body?.message ?? response.statusText
    return new RequestError(response.status, code, message, body?.details)
  }

  get isNetworkError(): boolean {
    return this.status === 0
  }

  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isServerError(): boolean {
    return this.status >= 500
  }

  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500
  }
}

export class NetworkError extends Error {
  constructor(message = 'Network error') {
    super(message)
    this.name = 'NetworkError'
  }
}

export class TimeoutError extends Error {
  constructor(message = 'Request timed out') {
    super(message)
    this.name = 'TimeoutError'
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Error Handlers
// ═══════════════════════════════════════════════════════════════════════════════

export function handleQueryError(error: unknown): void {
  console.error('Query error:', error)

  if (error instanceof RequestError) {
    if (error.isNetworkError) {
      toast.error('Network error. Please check your connection.')
    } else if (error.isAuthError) {
      toast.error('Authentication error. Please refresh the page.')
    } else if (error.isServerError) {
      toast.error('Server error. Please try again later.')
    } else {
      toast.error(error.message)
    }
  } else if (error instanceof NetworkError) {
    toast.error('Unable to connect. Please check your network.')
  } else if (error instanceof TimeoutError) {
    toast.error('Request timed out. Please try again.')
  } else if (error instanceof Error) {
    toast.error(error.message)
  } else {
    toast.error('An unexpected error occurred.')
  }
}

export function handleMutationError(error: unknown): void {
  console.error('Mutation error:', error)

  if (error instanceof RequestError) {
    if (error.status === 409) {
      toast('Already processed', { icon: 'ℹ️' })
    } else if (error.isServerError) {
      toast.error('Operation failed. Please try again.')
    } else {
      toast.error(error.message)
    }
  } else {
    toast.error('Operation failed. Please try again.')
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Query Client Configuration
// ═══════════════════════════════════════════════════════════════════════════════

export function createQueryClientWithErrorHandling(): QueryClient {
  const queryCache = new QueryCache({
    onError: (error) => handleQueryError(error),
  })

  return new QueryClient({
    queryCache,
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          if (error instanceof RequestError && error.isClientError) {
            return false
          }
          return failureCount < 3
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        staleTime: 30_000,
        gcTime: 5 * 60 * 1000,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
        placeholderData: keepPreviousData,
      },
      mutations: {
        retry: false,
        onError: handleMutationError,
      },
    },
  })
}
