/**
 * StatusBar - Neural Command Center bottom status bar
 * Features: Data source health indicators, system metrics, version info
 * 
 * Fetches REAL data from backend APIs:
 * - /health/sources - Data source health status
 * - /api/ui/overview - Pipeline metrics (signals count, hot path status)
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import { StatusIndicator, type StatusType } from '../ui/StatusIndicator';
import { useDataModeSafe } from '../../context/DataModeContext';
import { OMEN_API_BASE } from '../../lib/apiBase';

interface DataSourceStatus {
  name: string;
  status: StatusType;
  latency?: number;
}

interface SourceHealthResponse {
  overall_status: string;
  total_sources: number;
  healthy_count: number;
  degraded_count: number;
  unhealthy_count: number;
  unknown_count: number;
  sources: Record<string, {
    status: string;
    latency_ms: number | null;
    last_check: string | null;
    error: string | null;
  }>;
  checked_at: string;
}

interface OverviewResponse {
  signals_today: number;
  hot_path_ok: number;
  hot_path_pct: string;
}

// Default sources for demo mode or when API is unavailable
const DEFAULT_SOURCES: DataSourceStatus[] = [
  { name: 'Polymarket', status: 'mock' },
  { name: 'AIS', status: 'mock' },
  { name: 'Weather', status: 'mock' },
  { name: 'News', status: 'mock' },
  { name: 'Stock', status: 'mock' },
  { name: 'Freight', status: 'mock' },
];

function mapHealthStatus(status: string): StatusType {
  switch (status.toLowerCase()) {
    case 'healthy':
      return 'healthy';
    case 'degraded':
      return 'warning';
    case 'unhealthy':
    case 'error':
      return 'error';
    default:
      return 'mock';
  }
}

export interface StatusBarProps {
  version?: string;
  className?: string;
}

export function StatusBar({
  version = '1.0.0',
  className,
}: StatusBarProps) {
  const { isLive, canUseLiveData } = useDataModeSafe();
  
  // All state declarations grouped together
  const [dataSources, setDataSources] = useState<DataSourceStatus[]>(DEFAULT_SOURCES);
  const [signalsCount, setSignalsCount] = useState<number>(0);
  const [hotPathOk, setHotPathOk] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  
  // Use refs for error counts to avoid re-triggering callbacks
  const errorCountRef = useRef(0);
  const overviewErrorCountRef = useRef(0);
  
  // AbortController refs for proper cleanup
  const healthAbortRef = useRef<AbortController | null>(null);
  const overviewAbortRef = useRef<AbortController | null>(null);
  
  // Fetch data source health from /health/sources (public endpoint, no auth needed)
  const fetchSourceHealth = useCallback(async () => {
    // Abort any previous request
    if (healthAbortRef.current) {
      healthAbortRef.current.abort();
    }
    
    // Create new controller for this request
    const controller = new AbortController();
    healthAbortRef.current = controller;
    
    try {
      const baseUrl = OMEN_API_BASE.replace(/\/api\/v1\/?$/, '');
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch(`${baseUrl}/health/sources`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`Health API error: ${response.status}`);
      }
      
      const data: SourceHealthResponse = await response.json();
      
      // Convert API response to DataSourceStatus array
      const sources: DataSourceStatus[] = Object.entries(data.sources).map(([name, info]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1), // Capitalize
        status: mapHealthStatus(info.status),
        latency: info.latency_ms ?? undefined,
      }));
      
      // If no sources, show defaults
      if (sources.length === 0) {
        setDataSources(DEFAULT_SOURCES);
      } else {
        setDataSources(sources);
      }
      setLastError(null);
      errorCountRef.current = 0;
    } catch (err) {
      // Ignore abort errors - they're expected during cleanup
      if ((err as Error).name === 'AbortError') {
        return;
      }
      errorCountRef.current += 1;
      // Only log first 3 errors to avoid console spam
      if (errorCountRef.current <= 3) {
        console.warn('[StatusBar] Failed to fetch source health:', (err as Error).message);
      }
      setLastError((err as Error).message);
      // Keep showing last known data or defaults
    }
  }, []);
  
  // Fetch overview stats from /api/v1/ui/overview
  const fetchOverviewStats = useCallback(async () => {
    // Abort any previous request
    if (overviewAbortRef.current) {
      overviewAbortRef.current.abort();
    }
    
    // Create new controller for this request
    const controller = new AbortController();
    overviewAbortRef.current = controller;
    
    try {
      const apiKey = import.meta.env.VITE_API_KEY || 'dev-test-key';
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      // OMEN_API_BASE is http://localhost:8000/api/v1, so /ui/overview becomes /api/v1/ui/overview
      const response = await fetch(`${OMEN_API_BASE.replace(/\/$/, '')}/ui/overview`, {
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`Overview API error: ${response.status}`);
      }
      
      const data: OverviewResponse = await response.json();
      setSignalsCount(data.signals_today ?? 0);
      setHotPathOk(data.hot_path_ok ?? 0);
      overviewErrorCountRef.current = 0;
    } catch (err) {
      // Ignore abort errors - they're expected during cleanup
      if ((err as Error).name === 'AbortError') {
        return;
      }
      overviewErrorCountRef.current += 1;
      // Only log first 3 errors
      if (overviewErrorCountRef.current <= 3) {
        console.warn('[StatusBar] Failed to fetch overview:', (err as Error).message);
      }
      // Keep showing last known data
    }
  }, []);

  // Fetch data periodically
  useEffect(() => {
    let isMounted = true;
    let interval: ReturnType<typeof setInterval> | null = null;
    
    // Only fetch in live mode when backend is available
    if (!isLive || !canUseLiveData) {
      setDataSources(DEFAULT_SOURCES);
      setSignalsCount(0);
      setHotPathOk(0);
      errorCountRef.current = 0;
      overviewErrorCountRef.current = 0;
      return;
    }

    setIsLoading(true);
    
    // Initial fetch with safeguard
    const doFetch = async () => {
      if (!isMounted) return;
      try {
        await Promise.all([fetchSourceHealth(), fetchOverviewStats()]);
      } catch {
        // Errors are handled in individual functions
      }
      if (isMounted) setIsLoading(false);
    };
    
    doFetch();

    // Poll every 10 seconds only if still in live mode
    interval = setInterval(() => {
      if (isMounted && isLive && canUseLiveData) {
        fetchSourceHealth();
        fetchOverviewStats();
      }
    }, 10000);

    return () => {
      isMounted = false;
      if (interval) clearInterval(interval);
      // Abort any in-flight requests on cleanup
      if (healthAbortRef.current) {
        healthAbortRef.current.abort();
        healthAbortRef.current = null;
      }
      if (overviewAbortRef.current) {
        overviewAbortRef.current.abort();
        overviewAbortRef.current = null;
      }
    };
  }, [isLive, canUseLiveData, fetchSourceHealth, fetchOverviewStats]);

  // Determine hot path status from count
  const hotPathStatus: 'ok' | 'degraded' | 'error' = 
    hotPathOk > 0 ? 'ok' : (signalsCount > 0 ? 'degraded' : (lastError ? 'error' : 'ok'));

  return (
    <motion.footer
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.3 }}
      className={cn(
        'fixed bottom-0 left-16 right-0 z-30 h-8 flex items-center justify-between px-4',
        'bg-bg-secondary/95 backdrop-blur-sm border-t border-border-subtle',
        'text-xs font-mono',
        className
      )}
    >
      {/* Left: Data source status indicators - with proper spacing */}
      <div className="flex items-center gap-3 min-w-0">
        {dataSources.map(({ name, status, latency }) => (
          <div 
            key={name} 
            className="flex items-center gap-1.5 shrink-0"
            title={latency ? `${name}: ${latency}ms` : name}
          >
            <StatusIndicator status={status} size="xs" pulse={status === 'healthy'} />
            <span className="text-text-muted whitespace-nowrap">{name}</span>
          </div>
        ))}
        {isLoading && (
          <span className="text-text-muted animate-pulse">...</span>
        )}
      </div>

      {/* Right: System info */}
      <div className="flex items-center gap-4 shrink-0 ml-4">
        {/* Mode indicator */}
        <div className="flex items-center gap-1.5">
          <span className={cn(
            'px-1.5 py-0.5 rounded text-[10px] font-medium',
            isLive ? 'bg-status-success/20 text-status-success' : 'bg-accent-cyan/20 text-accent-cyan'
          )}>
            {isLive ? 'LIVE' : 'DEMO'}
          </span>
        </div>

        {/* Signals count */}
        <div className="flex items-center gap-1.5">
          <span className="text-text-muted">Signals:</span>
          <span className="text-status-success tabular-nums">{signalsCount.toLocaleString()}</span>
        </div>

        {/* Hot Path status */}
        <div className="flex items-center gap-1.5">
          <span className="text-text-muted">Hot Path:</span>
          <span className={cn(
            hotPathStatus === 'ok' && 'text-status-success',
            hotPathStatus === 'degraded' && 'text-status-warning',
            hotPathStatus === 'error' && 'text-status-error'
          )}>
            {hotPathStatus === 'ok' ? 'OK' : hotPathStatus === 'degraded' ? 'WARN' : 'ERR'}
          </span>
        </div>

        {/* Version */}
        <span className="text-text-muted">v{version}</span>
      </div>
    </motion.footer>
  );
}
