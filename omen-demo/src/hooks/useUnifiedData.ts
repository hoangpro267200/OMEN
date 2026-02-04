/**
 * useUnifiedData - Universal data fetching hook with STRICT mode awareness
 * 
 * This hook switches between live API data and mock data based on DataMode:
 * - LIVE mode: ONLY real API data. If API fails, return error. NEVER mock data.
 * - DEMO mode: ONLY mock data. API is not called.
 * 
 * IMPORTANT: NO HYBRID MODE. NO AUTO-FALLBACK TO MOCK DATA.
 * If you're in Live mode and API is down, you get an error, not fake data.
 */

import { useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo } from 'react';
import { useDataModeSafe, useDataRefreshListener } from '../context/DataModeContext';

// ============================================================================
// TYPES
// ============================================================================

export interface UseUnifiedDataOptions<TData, TMockData = TData> {
  /** Unique query key for caching */
  queryKey: readonly unknown[];
  /** Function to fetch live data */
  liveFetcher: () => Promise<TData>;
  /** Mock data - static value or generator function */
  mockData: TMockData | (() => TMockData);
  /** Optional transform to convert mock data to live data shape */
  mockTransform?: (mock: TMockData) => TData;
  /** Stale time in ms (default: 30s) */
  staleTime?: number;
  /** Refetch interval for live mode (false to disable) */
  refetchInterval?: number | false;
  /** Whether query is enabled */
  enabled?: boolean;
  /** Number of retries for live fetcher */
  retry?: number;
  /** Retry delay in ms */
  retryDelay?: number;
  /** Callback on successful fetch */
  onSuccess?: (data: TData) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseUnifiedDataResult<TData> {
  /** The data (from live API or mock) */
  data: TData | undefined;
  /** Whether initial loading is in progress */
  isLoading: boolean;
  /** Whether currently fetching (initial or refetch) */
  isFetching: boolean;
  /** Whether an error occurred */
  isError: boolean;
  /** Error object if any */
  error: Error | null;
  /** Manual refetch function */
  refetch: () => void;
  /** Data source indicator */
  dataSource: 'live' | 'mock' | 'cache';
  /** Whether data is stale */
  isStale: boolean;
  /** Last update timestamp */
  dataUpdatedAt: number | undefined;
}

// ============================================================================
// HOOK
// ============================================================================

export function useUnifiedData<TData, TMockData = TData>({
  queryKey,
  liveFetcher,
  mockData,
  mockTransform,
  staleTime = 30000,
  refetchInterval = false,
  enabled = true,
  retry = 2,
  retryDelay = 1000,
  onSuccess,
  onError,
}: UseUnifiedDataOptions<TData, TMockData>): UseUnifiedDataResult<TData> {
  // Use safe version to handle edge cases during error recovery or HMR
  const { state, isDemo, isLive, shouldUseMockData, shouldShowError, canUseLiveData } = useDataModeSafe();
  const queryClient = useQueryClient();

  // -------------------------------------------------------------------------
  // STRICT LOGIC: Live mode = fetch from API, Demo mode = use mock data
  // -------------------------------------------------------------------------
  
  // Only fetch live data when in Live mode AND connection is available
  const shouldFetchLive = enabled && isLive && canUseLiveData;

  // -------------------------------------------------------------------------
  // Live Query - only runs in Live mode when connected
  // -------------------------------------------------------------------------
  
  const liveQuery = useQuery({
    queryKey: [...queryKey, 'live'],
    queryFn: liveFetcher,
    enabled: shouldFetchLive,
    staleTime,
    refetchInterval: shouldFetchLive ? refetchInterval : false,
    // Don't retry for 404 errors - resource doesn't exist
    retry: (failureCount, error) => {
      const err = error as Error & { status?: number };
      // Never retry 404 (Not Found) or 401 (Unauthorized) errors
      if (err.status === 404 || err.status === 401 || err.status === 403) {
        return false;
      }
      // Otherwise, retry up to the configured amount
      return failureCount < retry;
    },
    retryDelay,
  });

  // Call success/error callbacks
  useEffect(() => {
    if (liveQuery.isSuccess && liveQuery.data && onSuccess) {
      onSuccess(liveQuery.data);
    }
  }, [liveQuery.isSuccess, liveQuery.data, onSuccess]);

  useEffect(() => {
    if (liveQuery.isError && liveQuery.error && onError) {
      onError(liveQuery.error);
    }
  }, [liveQuery.isError, liveQuery.error, onError]);

  // -------------------------------------------------------------------------
  // Mock Data (Memoized) - ONLY used in Demo mode
  // -------------------------------------------------------------------------
  
  const getMockData = useCallback((): TData => {
    const raw = typeof mockData === 'function' ? (mockData as () => TMockData)() : mockData;
    return mockTransform ? mockTransform(raw) : (raw as unknown as TData);
  }, [mockData, mockTransform]);

  const memoizedMockData = useMemo(() => {
    // STRICT: Only generate mock data in Demo mode
    if (!isDemo) return undefined;
    return getMockData();
  }, [isDemo, getMockData]);

  // -------------------------------------------------------------------------
  // Listen for global refresh events
  // -------------------------------------------------------------------------
  
  const handleRefresh = useCallback(() => {
    if (isLive) {
      queryClient.invalidateQueries({ queryKey: [...queryKey, 'live'] });
    }
  }, [queryClient, queryKey, isLive]);

  useDataRefreshListener(handleRefresh);

  // -------------------------------------------------------------------------
  // Invalidate cache on mode change
  // -------------------------------------------------------------------------
  
  useEffect(() => {
    // When switching to live mode and connected, invalidate to get fresh data
    if (shouldFetchLive) {
      queryClient.invalidateQueries({ queryKey: [...queryKey, 'live'] });
    }
  }, [state.mode, queryClient, queryKey, shouldFetchLive]);

  // -------------------------------------------------------------------------
  // Result - STRICT: No fallback to mock data in Live mode
  // -------------------------------------------------------------------------
  
  // DEMO MODE: Return mock data
  if (isDemo || shouldUseMockData) {
    // Ensure mock data is generated even if memoizedMockData failed
    const mockResult = memoizedMockData ?? getMockData();
    return {
      data: mockResult,
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      refetch: () => {
        // For mock data, this is a no-op
      },
      dataSource: 'mock' as const,
      isStale: false,
      dataUpdatedAt: Date.now(),
    };
  }

  // LIVE MODE: Return API data or error - NEVER mock data
  // If shouldShowError is true (not connected), we return an error state
  if (shouldShowError) {
    return {
      data: undefined,
      isLoading: false,
      isFetching: false,
      isError: true,
      error: new Error(state.errorMessage || 'Không thể kết nối đến server. Vui lòng kiểm tra backend.'),
      refetch: () => {
        queryClient.invalidateQueries({ queryKey: [...queryKey, 'live'] });
      },
      dataSource: 'live',
      isStale: true,
      dataUpdatedAt: undefined,
    };
  }

  // Live mode and connected - return query result
  return {
    data: liveQuery.data,
    isLoading: liveQuery.isLoading,
    isFetching: liveQuery.isFetching,
    isError: liveQuery.isError,
    error: liveQuery.error as Error | null,
    refetch: liveQuery.refetch,
    dataSource: liveQuery.isFetched ? 'live' : 'cache',
    isStale: liveQuery.isStale,
    dataUpdatedAt: liveQuery.dataUpdatedAt,
  };
}

// ============================================================================
// UTILITY: Create typed hook factory
// ============================================================================

/**
 * Factory to create typed unified data hooks with consistent options
 */
export function createUnifiedDataHook<TParams, TData, TMockData = TData>(
  config: {
    getQueryKey: (params: TParams) => readonly unknown[];
    liveFetcher: (params: TParams) => Promise<TData>;
    mockGenerator: (params: TParams) => TMockData;
    mockTransform?: (mock: TMockData) => TData;
    defaultStaleTime?: number;
    defaultRefetchInterval?: number | false;
  }
) {
  return function useGeneratedHook(
    params: TParams,
    options?: Partial<Pick<UseUnifiedDataOptions<TData, TMockData>, 
      'enabled' | 'staleTime' | 'refetchInterval' | 'onSuccess' | 'onError'
    >>
  ): UseUnifiedDataResult<TData> {
    return useUnifiedData({
      queryKey: config.getQueryKey(params),
      liveFetcher: () => config.liveFetcher(params),
      mockData: () => config.mockGenerator(params),
      mockTransform: config.mockTransform,
      staleTime: options?.staleTime ?? config.defaultStaleTime ?? 30000,
      refetchInterval: options?.refetchInterval ?? config.defaultRefetchInterval ?? false,
      enabled: options?.enabled ?? true,
      onSuccess: options?.onSuccess,
      onError: options?.onError,
    });
  };
}
