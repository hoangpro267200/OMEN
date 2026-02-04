/**
 * Signal Data Hooks - Unified hooks for signal-related data
 *
 * These hooks automatically switch between live API and mock data
 * based on the current DataMode context. Updated for correct backend endpoints.
 */

import { useUnifiedData, createUnifiedDataHook, type UseUnifiedDataResult } from './useUnifiedData';
import {
  generateMockSignals,
  generateMockSignalDetail,
  generateMockPipelineStats,
  generateMockSystemStats,
  generateMockDataSources,
  generateMockActivityFeed,
  type Signal,
  type SignalListResponse,
  type PipelineStats,
  type SystemStats,
  type DataSource,
  type ActivityItem,
} from '../data/mockGenerators';
import { OMEN_API_BASE } from '../lib/apiBase';

// ============================================================================
// API BASE URL - Uses the full backend URL
// ============================================================================

const API_BASE = OMEN_API_BASE;

// API Key from environment variable
const API_KEY = import.meta.env.VITE_API_KEY || '';

// Debug: Log API configuration on load
console.log('[useSignalData] API_BASE:', API_BASE);
console.log('[useSignalData] API_KEY present:', API_KEY ? 'yes' : 'NO');

// ============================================================================
// FETCH HELPERS
// ============================================================================

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  // Build headers with API key
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
  };
  
  // Add X-API-Key header if available
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    // Network error - backend might not be running
    throw new Error(`Không thể kết nối đến server: ${(err as Error).message}`);
  }
  
  // Check content type to avoid parsing HTML as JSON
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('text/html')) {
    throw new Error('Server trả về HTML thay vì JSON. Backend có thể chưa chạy hoặc URL sai.');
  }
  
  // Handle 401 Unauthorized specifically
  if (response.status === 401) {
    throw new Error('Thiếu hoặc sai API key. Kiểm tra VITE_API_KEY trong file .env');
  }
  
  if (!response.ok) {
    // Try to parse error message from JSON response
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.message) {
        errorMessage = errorData.message;
      } else if (errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail);
      }
    } catch {
      // Ignore JSON parse errors for error responses
    }
    
    // Create error with status code for retry logic
    const error = new Error(errorMessage) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  
  return response.json();
}

// ============================================================================
// SIGNALS LIST HOOK
// ============================================================================

export interface UseSignalsOptions {
  limit?: number;
  offset?: number;
  filter?: string;
  category?: string;
  status?: string;
  enabled?: boolean;
}

export function useSignals(options: UseSignalsOptions = {}): UseUnifiedDataResult<SignalListResponse> {
  const { limit = 20, offset = 0, filter, category, status, enabled = true } = options;
  
  return useUnifiedData({
    queryKey: ['signals', 'list', { limit, offset, filter, category, status }],
    liveFetcher: async () => {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      params.set('offset', String(offset));
      params.set('mode', 'live'); // Always request LIVE signals when in live mode
      if (filter) params.set('filter', filter);
      if (category) params.set('category', category);
      if (status) params.set('status', status);
      
      // Fetch signals from API
      const response = await fetchJson<SignalListResponse>(`/signals?${params}`);
      
      // If no signals returned in LIVE mode, trigger generation
      if (response.signals.length === 0) {
        console.log('[useSignals] No LIVE signals found, triggering generation...');
        try {
          const baseUrl = API_BASE.replace(/\/api\/v1\/?$/, '');
          const genResponse = await fetch(`${baseUrl}/api/v1/signals/generate`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(API_KEY && { 'X-API-Key': API_KEY }),
            },
          });
          if (genResponse.ok) {
            // Re-fetch signals after generation
            return await fetchJson<SignalListResponse>(`/signals?${params}`);
          }
        } catch (e) {
          console.warn('[useSignals] Signal generation failed:', e);
        }
      }
      
      return response;
    },
    mockData: () => generateMockSignals(limit),
    staleTime: 10000,
    refetchInterval: 5000,
    enabled,
  });
}

// ============================================================================
// SIGNAL DETAIL HOOK
// ============================================================================

export interface UseSignalDetailOptions {
  enabled?: boolean;
  onSuccess?: (data: Signal) => void;
  onError?: (error: Error) => void;
}

export function useSignalDetail(
  signalId: string | undefined,
  options: UseSignalDetailOptions = {}
): UseUnifiedDataResult<Signal> {
  const { enabled = true, onSuccess, onError } = options;
  
  return useUnifiedData({
    queryKey: ['signals', 'detail', signalId],
    liveFetcher: async () => {
      if (!signalId) throw new Error('Signal ID required');
      return fetchJson<Signal>(`/signals/${signalId}`);
    },
    mockData: () => generateMockSignalDetail(signalId ?? 'OMEN-MOCK-001'),
    staleTime: 30000,
    enabled: enabled && !!signalId,
    onSuccess,
    onError,
  });
}

// ============================================================================
// PIPELINE STATS HOOK
// ============================================================================

export interface UsePipelineStatsOptions {
  enabled?: boolean;
  refetchInterval?: number | false;
}

export function usePipelineStats(
  options: UsePipelineStatsOptions = {}
): UseUnifiedDataResult<PipelineStats> {
  const { enabled = true, refetchInterval = 3000 } = options;
  
  return useUnifiedData({
    queryKey: ['pipeline', 'stats'],
    liveFetcher: async () => fetchJson<PipelineStats>('/signals/stats'),
    mockData: generateMockPipelineStats,
    staleTime: 5000,
    refetchInterval,
    enabled,
  });
}

// ============================================================================
// SYSTEM STATS HOOK
// ============================================================================

export interface UseSystemStatsOptions {
  enabled?: boolean;
  refetchInterval?: number | false;
}

export function useSystemStats(
  options: UseSystemStatsOptions = {}
): UseUnifiedDataResult<SystemStats> {
  const { enabled = true, refetchInterval = 5000 } = options;
  
  return useUnifiedData({
    queryKey: ['system', 'stats'],
    liveFetcher: async () => fetchJson<SystemStats>('/stats'),
    mockData: generateMockSystemStats,
    staleTime: 5000,
    refetchInterval,
    enabled,
  });
}

// ============================================================================
// DATA SOURCES HOOK
// ============================================================================

export interface UseDataSourcesOptions {
  enabled?: boolean;
}

// Response type from backend health/sources API (public, no auth required)
interface HealthSourceInfo {
  status: string;
  latency_ms: number | null;
  last_check: string | null;
  error: string | null;
}

interface HealthSourcesResponse {
  overall_status: string;
  total_sources: number;
  healthy_count: number;
  degraded_count: number;
  unhealthy_count: number;
  unknown_count: number;
  sources: Record<string, HealthSourceInfo>;
  checked_at: string;
  cache_age_seconds: number;
}

export function useDataSources(
  options: UseDataSourcesOptions = {}
): UseUnifiedDataResult<DataSource[]> {
  const { enabled = true } = options;
  
  return useUnifiedData({
    queryKey: ['sources', 'list'],
    liveFetcher: async () => {
      // Use public health endpoint (no auth required) for source status
      const baseUrl = OMEN_API_BASE.replace(/\/api\/v1\/?$/, '');
      const url = `${baseUrl}/health/sources`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch sources: ${response.statusText}`);
      }
      
      const data: HealthSourcesResponse = await response.json();
      
      // Transform health endpoint response to DataSource[] format
      // sources is a Record<string, SourceInfo>, convert to array
      const sourceEntries = Object.entries(data.sources);
      
      // If no sources registered yet, return default sources for UI display
      if (sourceEntries.length === 0) {
        return [
          { id: 'polymarket', name: 'Polymarket', type: 'polymarket' as const, status: 'offline' as const, latency: 0, lastUpdate: new Date().toISOString(), signalCount: 0, enabled: true },
          { id: 'weather', name: 'Weather', type: 'weather' as const, status: 'offline' as const, latency: 0, lastUpdate: new Date().toISOString(), signalCount: 0, enabled: true },
          { id: 'ais', name: 'AIS', type: 'ais' as const, status: 'offline' as const, latency: 0, lastUpdate: new Date().toISOString(), signalCount: 0, enabled: true },
          { id: 'freight', name: 'Freight', type: 'freight' as const, status: 'offline' as const, latency: 0, lastUpdate: new Date().toISOString(), signalCount: 0, enabled: true },
        ];
      }
      
      return sourceEntries.map(([name, info]) => ({
        id: name.toLowerCase().replace(/\s+/g, '-'),
        name: name,
        type: name.toLowerCase() as DataSource['type'],
        status: info.status === 'healthy' ? 'online' as const : 
                info.status === 'degraded' ? 'degraded' as const : 'offline' as const,
        latency: info.latency_ms ?? 0,
        lastUpdate: info.last_check ?? new Date().toISOString(),
        signalCount: 0, // Not provided by health endpoint
        enabled: true, // Assume enabled if listed in health check
      }));
    },
    mockData: generateMockDataSources,
    staleTime: 30000,
    refetchInterval: 10000,
    enabled,
  });
}

// ============================================================================
// ACTIVITY FEED HOOK
// ============================================================================

export interface UseActivityFeedOptions {
  limit?: number;
  enabled?: boolean;
}

export function useActivityFeed(
  options: UseActivityFeedOptions = {}
): UseUnifiedDataResult<ActivityItem[]> {
  const { limit = 20, enabled = true } = options;
  
  return useUnifiedData({
    queryKey: ['activity', 'feed', limit],
    liveFetcher: async () => {
      const params = new URLSearchParams({ limit: String(limit) });
      return fetchJson<ActivityItem[]>(`/activity?${params}`);
    },
    mockData: () => generateMockActivityFeed(limit),
    staleTime: 5000,
    refetchInterval: 3000,
    enabled,
  });
}

// ============================================================================
// SIGNAL SEARCH HOOK
// ============================================================================

export interface SignalSearchParams {
  query: string;
  limit?: number;
}

export function useSignalSearch(
  params: SignalSearchParams,
  options: { enabled?: boolean } = {}
): UseUnifiedDataResult<SignalListResponse> {
  const { query, limit = 10 } = params;
  const { enabled = true } = options;
  
  return useUnifiedData({
    queryKey: ['signals', 'search', query, limit],
    liveFetcher: async () => {
      const searchParams = new URLSearchParams({
        q: query,
        limit: String(limit),
      });
      return fetchJson<SignalListResponse>(`/signals/search?${searchParams}`);
    },
    mockData: () => {
      // Filter mock signals by query
      const all = generateMockSignals(50);
      const filtered = all.signals.filter(
        (s) =>
          s.title.toLowerCase().includes(query.toLowerCase()) ||
          s.signal_id.toLowerCase().includes(query.toLowerCase()) ||
          s.category.toLowerCase().includes(query.toLowerCase())
      );
      return {
        signals: filtered.slice(0, limit),
        total: filtered.length,
        limit,
        offset: 0,
      };
    },
    staleTime: 10000,
    enabled: enabled && query.length >= 2,
  });
}

// ============================================================================
// EXPLANATION CHAIN HOOK
// ============================================================================

export interface ExplanationChainResponse {
  trace_id: string;
  signal_id: string;
  steps: Signal['explanation_steps'];
  total_processing_ms: number;
  started_at: string;
  completed_at: string;
}

export function useExplanationChain(
  signalId: string | undefined,
  options: { enabled?: boolean } = {}
): UseUnifiedDataResult<ExplanationChainResponse> {
  const { enabled = true } = options;
  
  return useUnifiedData({
    queryKey: ['signals', 'explanation', signalId],
    liveFetcher: async () => {
      if (!signalId) throw new Error('Signal ID required');
      return fetchJson<ExplanationChainResponse>(`/signals/${signalId}/explanation`);
    },
    mockData: () => {
      const signal = generateMockSignalDetail(signalId ?? 'OMEN-MOCK-001');
      const totalMs = signal.explanation_steps?.reduce((sum, s) => sum + s.processing_time_ms, 0) ?? 0;
      
      return {
        trace_id: signal.trace_id ?? 'mock-trace',
        signal_id: signal.signal_id,
        steps: signal.explanation_steps ?? [],
        total_processing_ms: totalMs,
        started_at: signal.observed_at,
        completed_at: signal.generated_at,
      };
    },
    staleTime: 60000,
    enabled: enabled && !!signalId,
  });
}

// ============================================================================
// RE-EXPORT TYPES
// ============================================================================

export type {
  Signal,
  SignalListResponse,
  PipelineStats,
  SystemStats,
  DataSource,
  ActivityItem,
  ExplanationStep,
} from '../data/mockGenerators';
