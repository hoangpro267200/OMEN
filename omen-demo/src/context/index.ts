/**
 * OMEN Context - Centralized export for all React contexts
 */

// Demo Mode (Presentation mode for investor demos)
export { DemoModeProvider, useDemoModeContext } from './DemoModeContext';
export type { DemoModeContextValue } from './DemoModeContext';

// Data Mode (Live / Demo / Hybrid data switching)
export {
  DataModeProvider,
  useDataMode,
  useDataModeSafe,
  useIsDataMode,
  useConnectionStatus,
  useDataRefreshListener,
  useModeChangeListener,
} from './DataModeContext';

export type {
  DataMode,
  ConnectionStatus,
  DataModeState,
  DataModeConfig,
  DataModeContextValue,
  DataModeProviderProps,
} from './DataModeContext';
