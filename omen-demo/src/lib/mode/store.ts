/**
 * Data Source mode store — demo vs live. Persisted to localStorage.
 * Data Source = which data provider (demo | live). Not the same as Demo Mode (presentation overlay).
 */

import * as React from 'react';

const STORAGE_KEY = 'omen.dataSourceMode';

export type DataSourceMode = 'demo' | 'live';

function loadMode(): DataSourceMode {
  if (typeof window === 'undefined') return 'demo';
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'demo' || raw === 'live') return raw;
  } catch {
    // ignore
  }
  return 'demo';
}

function saveMode(mode: DataSourceMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // ignore
  }
}

let currentMode: DataSourceMode = loadMode();
const listeners: Set<() => void> = new Set();

function getMode(): DataSourceMode {
  return currentMode;
}

function setDataSourceMode(mode: DataSourceMode): void {
  if (currentMode === mode) return;
  currentMode = mode;
  saveMode(mode);
  listeners.forEach((fn) => fn());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export { getMode as getDataSourceMode, setDataSourceMode, subscribe };

export function isLive(): boolean {
  return getMode() === 'live';
}

export function isDemo(): boolean {
  return getMode() === 'demo';
}

// React hook — re-renders when mode changes. Use this in components.
export function useDataSourceMode(): [DataSourceMode, (mode: DataSourceMode) => void] {
  const [mode, setMode] = React.useState<DataSourceMode>(currentMode);
  React.useEffect(() => {
    setMode(currentMode);
    return subscribe(() => setMode(getMode()));
  }, []);
  return [
    mode,
    (m: DataSourceMode) => {
      setDataSourceMode(m);
      setMode(m);
    },
  ];
}
