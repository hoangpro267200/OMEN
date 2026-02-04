/**
 * DataModeContext - Data Mode System
 * 
 * Provides clear switching between Live and Demo data modes.
 * 
 * Features:
 * - 2 modes: live (real API only) or demo (mock data only)
 * - NO auto-fallback: Live mode shows errors when API fails, NEVER fake data
 * - Connection health monitoring
 * - React 18 transitions for non-blocking updates
 * - Persistent mode preference
 * 
 * IMPORTANT: Live mode = REAL DATA ONLY. If API fails, show error, never mock data.
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useTransition,
  useMemo,
  useRef,
  type ReactNode,
} from 'react';

// ============================================================================
// TYPES
// ============================================================================

/** Only 2 modes - Live (real API) or Demo (mock data). No hybrid. */
export type DataMode = 'live' | 'demo';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

export interface DataModeState {
  /** Current data mode */
  mode: DataMode;
  /** Whether a mode transition is in progress */
  isTransitioning: boolean;
  /** Transition progress 0-100 */
  transitionProgress: number;
  /** Last successful data sync time */
  lastSyncTime: Date | null;
  /** Current connection status to backend */
  connectionStatus: ConnectionStatus;
  /** Last error if any */
  error: Error | null;
  /** Number of consecutive connection failures */
  failureCount: number;
  /** Error message for display */
  errorMessage: string | null;
  
  // === BACKEND-AUTHORITATIVE LIVE MODE STATUS ===
  /** Whether backend allows LIVE mode */
  liveAllowed: boolean;
  /** Reasons why LIVE mode is blocked (from backend) */
  liveBlockers: string[];
  /** Last time LIVE mode status was checked */
  liveStatusCheckedAt: Date | null;
  /** Message from backend about LIVE mode status */
  liveStatusMessage: string | null;
}

export interface DataModeConfig {
  /** Show transition animation */
  animateTransition: boolean;
  /** Preserve scroll position on mode switch */
  preserveScrollPosition: boolean;
  /** Cache duration in ms */
  cacheDuration: number;
  /** Health check interval in ms */
  healthCheckInterval: number;
  /** Health check endpoint */
  healthCheckEndpoint: string;
}

export interface DataModeContextValue {
  state: DataModeState;
  config: DataModeConfig;

  // Actions
  setMode: (mode: DataMode) => Promise<void>;
  toggleMode: () => Promise<void>;
  refreshData: () => void;
  retryConnection: () => Promise<void>;
  /** Check if LIVE mode is allowed by the backend */
  checkLiveModeStatus: () => Promise<void>;

  // Computed helpers - STRICT: no hybrid, no fallback
  isLive: boolean;
  isDemo: boolean;
  /** True only when in Live mode AND connected to API */
  canUseLiveData: boolean;
  /** True ONLY in Demo mode - Live mode NEVER uses mock data */
  shouldUseMockData: boolean;
  /** True when in Live mode but API is not available - should show error */
  shouldShowError: boolean;
  /** True if LIVE mode is allowed by backend (all data sources are real) */
  liveAllowed: boolean;
  /** List of blockers preventing LIVE mode */
  liveBlockers: string[];
}

// ============================================================================
// DEFAULT VALUES
// ============================================================================

const defaultState: DataModeState = {
  mode: 'demo', // Default to demo - user must explicitly switch to live
  isTransitioning: false,
  transitionProgress: 0,
  lastSyncTime: null,
  connectionStatus: 'disconnected',
  error: null,
  failureCount: 0,
  errorMessage: null,
  
  // LIVE mode status - default to blocked until verified
  liveAllowed: false,
  liveBlockers: ['Checking backend status...'],
  liveStatusCheckedAt: null,
  liveStatusMessage: null,
};

// Get backend base URL and API key from environment
const BACKEND_BASE = import.meta.env?.VITE_API_BASE || 'http://localhost:8000';
const BACKEND_API_KEY = import.meta.env?.VITE_API_KEY || '';

// Helper to create headers with API key
const getAuthHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (BACKEND_API_KEY) headers['X-API-Key'] = BACKEND_API_KEY;
  return headers;
};

const defaultConfig: DataModeConfig = {
  animateTransition: true,
  preserveScrollPosition: true,
  cacheDuration: 30000,
  healthCheckInterval: 15000, // Check every 15s when in live mode
  healthCheckEndpoint: `${BACKEND_BASE}/health/`,
};

// ============================================================================
// STORAGE
// ============================================================================

const STORAGE_KEY = 'omen.dataMode';

function loadPersistedMode(): DataMode {
  if (typeof window === 'undefined') return 'demo';
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    // Accept 'live' or 'demo' from localStorage
    if (raw === 'live' || raw === 'demo') {
      return raw;
    }
  } catch {
    // Ignore storage errors
  }
  return 'demo';
}

function persistMode(mode: DataMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // Ignore storage errors
  }
}

// ============================================================================
// CONTEXT
// ============================================================================

const DataModeContext = createContext<DataModeContextValue | null>(null);

// ============================================================================
// PROVIDER
// ============================================================================

export interface DataModeProviderProps {
  children: ReactNode;
  initialMode?: DataMode;
  config?: Partial<DataModeConfig>;
}

export function DataModeProvider({
  children,
  initialMode,
  config: configOverrides = {},
}: DataModeProviderProps) {
  const [state, setState] = useState<DataModeState>(() => ({
    ...defaultState,
    mode: initialMode ?? loadPersistedMode(),
  }));

  const config = useMemo<DataModeConfig>(
    () => ({
      ...defaultConfig,
      ...configOverrides,
    }),
    [configOverrides]
  );

  const [isPending, startTransition] = useTransition();

  // AbortController refs for proper cleanup
  const connectionAbortRef = useRef<AbortController | null>(null);
  const liveStatusAbortRef = useRef<AbortController | null>(null);

  // -------------------------------------------------------------------------
  // Connection Health Check
  // -------------------------------------------------------------------------

  const checkConnection = useCallback(async (): Promise<boolean> => {
    // In demo mode, no need to check connection
    if (state.mode === 'demo') {
      setState((prev) => ({
        ...prev,
        connectionStatus: 'disconnected',
        error: null,
        errorMessage: null,
      }));
      return false;
    }

    // Abort any previous connection check
    if (connectionAbortRef.current) {
      connectionAbortRef.current.abort();
    }

    // Create new controller for this request
    const controller = new AbortController();
    connectionAbortRef.current = controller;

    // In live mode - check API health
    setState((prev) => ({ ...prev, connectionStatus: 'connecting' }));

    try {
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(config.healthCheckEndpoint, {
        method: 'GET',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        setState((prev) => ({
          ...prev,
          connectionStatus: 'connected',
          error: null,
          errorMessage: null,
          lastSyncTime: new Date(),
          failureCount: 0,
        }));
        return true;
      } else {
        throw new Error(`API returned status ${response.status}`);
      }
    } catch (error) {
      const err = error as Error;
      
      // Ignore abort errors - they're expected during cleanup/cancellation
      if (err.name === 'AbortError') {
        return false;
      }
      
      const newFailureCount = state.failureCount + 1;
      
      // Build user-friendly error message
      let errorMessage = 'Không thể kết nối đến server';
      if (err.message.includes('fetch')) {
        errorMessage = 'Server không phản hồi. Kiểm tra backend đang chạy.';
      } else if (err.message.includes('status')) {
        errorMessage = `Server lỗi: ${err.message}`;
      }

      setState((prev) => ({
        ...prev,
        connectionStatus: 'error',
        error: err,
        errorMessage,
        failureCount: newFailureCount,
      }));

      // NO AUTO-FALLBACK: Live mode stays in Live mode, shows error
      // User must manually switch to Demo if they want mock data
      console.warn(
        `[DataMode] API connection failed (attempt ${newFailureCount}): ${errorMessage}`
      );

      return false;
    }
  }, [state.mode, state.failureCount, config]);

  // -------------------------------------------------------------------------
  // LIVE Mode Status Check (Backend-Authoritative)
  // -------------------------------------------------------------------------
  
  const checkLiveModeStatus = useCallback(async () => {
    // Abort any previous status check
    if (liveStatusAbortRef.current) {
      liveStatusAbortRef.current.abort();
    }

    // Create new controller for this request
    const controller = new AbortController();
    liveStatusAbortRef.current = controller;

    try {
      // First try the dedicated live-mode status endpoint (requires auth)
      let response = await fetch(`${BACKEND_BASE}/api/v1/live-mode/status`, {
        method: 'GET',
        headers: getAuthHeaders(),
        signal: controller.signal,
      });
      
      if (response.ok) {
        const data = await response.json();
        const isAllowed = data.can_go_live === true || data.live_allowed === true;
        const blockers = data.blockers || [];
        setState((prev) => ({
          ...prev,
          liveAllowed: isAllowed,
          liveBlockers: blockers,
          liveStatusCheckedAt: new Date(),
          liveStatusMessage: data.message,
        }));
        console.log('[DataMode] LIVE status from backend:', isAllowed ? '✅ ALLOWED' : '❌ BLOCKED', 
          'blockers:', blockers.length > 0 ? blockers : '(none)');
        return;
      }
      
      // Fallback: check /health/sources endpoint (public, no auth)
      response = await fetch(`${BACKEND_BASE}/health/sources`, {
        method: 'GET',
        signal: controller.signal,
      });
      
      if (response.ok) {
        const data = await response.json();
        // If we have healthy sources, allow LIVE mode
        const healthyCount = data.healthy_count ?? 0;
        const totalSources = data.total_sources ?? 0;
        const isAllowed = healthyCount > 0 || totalSources === 0; // Allow if no sources registered yet
        const blockers: string[] = [];
        
        if (!isAllowed) {
          blockers.push('No healthy data sources available');
        }
        
        setState((prev) => ({
          ...prev,
          liveAllowed: isAllowed,
          liveBlockers: blockers,
          liveStatusCheckedAt: new Date(),
          liveStatusMessage: isAllowed ? 'Backend available - LIVE mode allowed' : 'No healthy sources',
        }));
        console.log('[DataMode] LIVE status from /health/sources:', isAllowed ? '✅ ALLOWED' : '❌ BLOCKED');
        return;
      }
      
      // Both endpoints unavailable - check basic health (public)
      response = await fetch(`${BACKEND_BASE}/health/`, {
        method: 'GET',
        signal: controller.signal,
      });
      
      if (response.ok) {
        // Backend is healthy, allow LIVE mode
        setState((prev) => ({
          ...prev,
          liveAllowed: true,
          liveBlockers: [],
          liveStatusCheckedAt: new Date(),
          liveStatusMessage: 'Backend available',
        }));
        console.log('[DataMode] LIVE status from /health/: ✅ ALLOWED');
        return;
      }
      
      // Backend unavailable - block LIVE mode
      setState((prev) => ({
        ...prev,
        liveAllowed: false,
        liveBlockers: ['Cannot reach backend to verify LIVE mode status'],
        liveStatusCheckedAt: new Date(),
        liveStatusMessage: 'Backend unavailable',
      }));
    } catch (error) {
      const err = error as Error;
      // Ignore abort errors - they're expected during cleanup
      if (err.name === 'AbortError') {
        return;
      }
      console.error('[DataMode] Failed to check LIVE mode status:', error);
      setState((prev) => ({
        ...prev,
        liveAllowed: false,
        liveBlockers: ['Cannot reach backend to verify LIVE mode status'],
        liveStatusCheckedAt: new Date(),
        liveStatusMessage: 'Backend connection failed',
      }));
    }
  }, []);
  
  // Check LIVE mode status on mount
  useEffect(() => {
    checkLiveModeStatus();
    // Re-check every 60 seconds
    const interval = setInterval(checkLiveModeStatus, 60000);
    return () => {
      clearInterval(interval);
      // Abort any in-flight request on cleanup
      if (liveStatusAbortRef.current) {
        liveStatusAbortRef.current.abort();
        liveStatusAbortRef.current = null;
      }
    };
  }, [checkLiveModeStatus]);

  // Health check on mount and interval
  useEffect(() => {
    if (state.mode === 'demo') return;

    checkConnection();
    const interval = setInterval(checkConnection, config.healthCheckInterval);

    return () => {
      clearInterval(interval);
      // Abort any in-flight request on cleanup
      if (connectionAbortRef.current) {
        connectionAbortRef.current.abort();
        connectionAbortRef.current = null;
      }
    };
  }, [state.mode, config.healthCheckInterval, checkConnection]);

  // -------------------------------------------------------------------------
  // Mode Transition with Animation
  // -------------------------------------------------------------------------

  const setMode = useCallback(
    async (newMode: DataMode) => {
      if (newMode === state.mode) return;

      // BACKEND-AUTHORITATIVE: Block switch to LIVE if not allowed
      if (newMode === 'live' && !state.liveAllowed) {
        console.warn('[DataMode] LIVE mode blocked by backend:', state.liveBlockers);
        setState((prev) => ({
          ...prev,
          errorMessage: `LIVE mode unavailable: ${state.liveBlockers[0] || 'Data sources not ready'}`,
        }));
        // Refresh LIVE status in case it changed
        await checkLiveModeStatus();
        return;
      }

      // Preserve scroll position if configured
      const scrollY = config.preserveScrollPosition ? window.scrollY : 0;

      // Start transition
      setState((prev) => ({
        ...prev,
        isTransitioning: true,
        transitionProgress: 0,
      }));

      // Animate progress
      if (config.animateTransition) {
        for (let i = 0; i <= 100; i += 10) {
          await new Promise((resolve) => setTimeout(resolve, 25));
          setState((prev) => ({ ...prev, transitionProgress: i }));
        }
      }

      // Apply new mode with React 18 transition
      startTransition(() => {
        setState((prev) => ({
          ...prev,
          mode: newMode,
          isTransitioning: false,
          transitionProgress: 100,
          // Reset states based on new mode
          connectionStatus: newMode === 'demo' ? 'disconnected' : 'connecting',
          error: null,
          errorMessage: null,
          failureCount: 0,
        }));
      });

      // Persist preference
      persistMode(newMode);

      // Restore scroll position
      if (config.preserveScrollPosition) {
        requestAnimationFrame(() => {
          window.scrollTo(0, scrollY);
        });
      }

      // When switching to LIVE mode
      if (newMode === 'live') {
        // First, establish connection to verify backend is available
        console.log('[DataMode] Switching to LIVE mode, checking connection...');
        
        try {
          const healthResponse = await fetch(config.healthCheckEndpoint, { method: 'GET' });
          if (healthResponse.ok) {
            setState((prev) => ({
              ...prev,
              connectionStatus: 'connected',
              error: null,
              errorMessage: null,
              lastSyncTime: new Date(),
              failureCount: 0,
            }));
            console.log('[DataMode] Backend connection established');
            
            // Generate LIVE signals from all real data sources
            // Use the new /signals/generate endpoint for comprehensive generation
            console.log('[DataMode] Triggering LIVE signal generation...');
            const baseUrl = BACKEND_BASE;
            const apiKey = BACKEND_API_KEY;
            
            // Call the signal generator endpoint (triggers background generator)
            try {
              const genResponse = await fetch(`${baseUrl}/api/v1/signals/generate`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  ...(apiKey && { 'X-API-Key': apiKey }),
                },
              });
              
              if (genResponse.ok) {
                const data = await genResponse.json();
                console.log('[DataMode] LIVE signals generated:', data.signals_created, 'from sources:', data.sources);
              } else {
                console.warn('[DataMode] Signal generation returned:', genResponse.status);
                // Fallback to live-data/generate
                const fallbackResponse = await fetch(`${baseUrl}/api/v1/live-data/generate`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    ...(apiKey && { 'X-API-Key': apiKey }),
                  },
                });
                if (fallbackResponse.ok) {
                  const fallbackData = await fallbackResponse.json();
                  console.log('[DataMode] Fallback live signals generated:', fallbackData.signals_created);
                }
              }
            } catch (genError) {
              console.warn('[DataMode] Signal generation error:', genError);
            }
          } else {
            console.warn('[DataMode] Backend health check failed:', healthResponse.status);
          }
        } catch (error) {
          console.warn('[DataMode] Error establishing connection:', error);
        }
      }

      // Trigger data refresh
      window.dispatchEvent(new CustomEvent('omen:data-mode-changed', { detail: { mode: newMode } }));
    },
    [state.mode, state.liveAllowed, state.liveBlockers, config.animateTransition, config.preserveScrollPosition, config.healthCheckEndpoint, checkLiveModeStatus]
  );

  const toggleMode = useCallback(async () => {
    // Simple toggle: live <-> demo, no hybrid
    const nextMode: DataMode = state.mode === 'live' ? 'demo' : 'live';
    await setMode(nextMode);
  }, [state.mode, setMode]);

  const refreshData = useCallback(() => {
    window.dispatchEvent(new CustomEvent('omen:refresh-data'));
  }, []);

  const retryConnection = useCallback(async () => {
    setState((prev) => ({ ...prev, failureCount: 0 }));
    await checkConnection();
  }, [checkConnection]);

  // -------------------------------------------------------------------------
  // Computed Values - STRICT MODE LOGIC
  // -------------------------------------------------------------------------

  const value = useMemo<DataModeContextValue>(() => {
    const isLive = state.mode === 'live';
    const isDemo = state.mode === 'demo';
    
    // Can use live data ONLY when in live mode AND connected
    const canUseLiveData = isLive && state.connectionStatus === 'connected';
    
    // STRICT: Mock data ONLY in demo mode. Never in live mode.
    const shouldUseMockData = isDemo;
    
    // Show error when in Live mode but API is not available
    const shouldShowError = isLive && state.connectionStatus !== 'connected' && state.connectionStatus !== 'connecting';

    return {
      state,
      config,
      setMode,
      toggleMode,
      refreshData,
      retryConnection,
      checkLiveModeStatus,
      isLive,
      isDemo,
      canUseLiveData,
      shouldUseMockData,
      shouldShowError,
      liveAllowed: state.liveAllowed,
      liveBlockers: state.liveBlockers,
    };
  }, [state, config, setMode, toggleMode, refreshData, retryConnection, checkLiveModeStatus]);

  return <DataModeContext.Provider value={value}>{children}</DataModeContext.Provider>;
}

// ============================================================================
// HOOK
// ============================================================================

/**
 * Default context value for when provider is not available.
 * This allows hooks to work during error recovery or HMR.
 */
const defaultContextValue: DataModeContextValue = {
  state: defaultState,
  config: defaultConfig,
  setMode: async () => {},
  toggleMode: async () => {},
  refreshData: () => {},
  retryConnection: async () => {},
  checkLiveModeStatus: async () => {},
  isLive: false,
  isDemo: true,
  canUseLiveData: false,
  shouldUseMockData: true,
  shouldShowError: false,
  liveAllowed: false,
  liveBlockers: [],
};

/**
 * Safe hook that returns a default value when context is unavailable.
 * Use this in hooks that might be called during error recovery.
 */
export function useDataModeSafe(): DataModeContextValue {
  const context = useContext(DataModeContext);
  return context ?? defaultContextValue;
}

/**
 * Main hook for accessing DataMode context.
 * Throws if used outside DataModeProvider.
 */
export function useDataMode(): DataModeContextValue {
  const context = useContext(DataModeContext);
  if (!context) {
    // In development, log a warning instead of throwing to aid debugging
    if (import.meta.env?.DEV) {
      console.warn(
        '[useDataMode] Context not available. This usually happens during error recovery or HMR. ' +
        'Using default demo mode values. Make sure DataModeProvider wraps your component tree.'
      );
      return defaultContextValue;
    }
    throw new Error('useDataMode must be used within DataModeProvider');
  }
  return context;
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Hook to check if currently in a specific mode
 */
export function useIsDataMode(mode: DataMode): boolean {
  const { state } = useDataModeSafe();
  return state.mode === mode;
}

/**
 * Hook to get connection status
 */
export function useConnectionStatus(): ConnectionStatus {
  const { state } = useDataModeSafe();
  return state.connectionStatus;
}

/**
 * Hook to listen for data refresh events
 */
export function useDataRefreshListener(callback: () => void): void {
  useEffect(() => {
    const handler = () => callback();
    window.addEventListener('omen:refresh-data', handler);
    return () => window.removeEventListener('omen:refresh-data', handler);
  }, [callback]);
}

/**
 * Hook to listen for mode change events
 */
export function useModeChangeListener(callback: (mode: DataMode) => void): void {
  useEffect(() => {
    const handler = (event: CustomEvent<{ mode: DataMode }>) => {
      callback(event.detail.mode);
    };
    window.addEventListener('omen:data-mode-changed', handler as EventListener);
    return () => window.removeEventListener('omen:data-mode-changed', handler as EventListener);
  }, [callback]);
}
