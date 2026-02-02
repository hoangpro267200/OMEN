import { useMemo } from 'react';
import { OverviewScreen } from './OverviewScreen';
import { useOverviewStats, useDataSourceMode } from '../lib/api/hooks';
import type { OverviewStats } from '../lib/api/contracts';

function mapStatsToKpis(stats: OverviewStats) {
  return {
    signalsToday: stats.signals_today,
    signalsTrend: stats.signals_trend,
    signalsTrendUp: stats.signals_trend_up,
    hotPathOk: stats.hot_path_ok,
    hotPathPct: stats.hot_path_pct,
    duplicates: stats.duplicates,
    duplicatesSub: stats.duplicates_sub,
    partitionsSealed: stats.partitions_sealed,
    partitionsOpen: stats.partitions_open,
    partitionsSub: stats.partitions_sub,
    lastReconcile: stats.last_reconcile,
    lastReconcileStatus: stats.last_reconcile_status,
  };
}

/**
 * Overview route — renders OverviewScreen (hero, KPIs, proof pack, activity).
 * Data from useOverviewStats() only; no direct mock imports.
 */
export function OverviewPage() {
  const [dataSourceMode, setDataSourceMode] = useDataSourceMode();
  const { data: stats, isLoading, error, refetch } = useOverviewStats();
  const state = isLoading ? 'loading' : error ? 'error' : !stats ? 'empty' : 'ready';
  const kpis = useMemo(() => (stats ? mapStatsToKpis(stats) : null), [stats]);
  const activity = stats?.activity_feed ?? [];

  return (
    <OverviewScreen
      state={state}
      kpis={kpis}
      activity={activity}
      errorMessage={error?.message}
      onRetry={() => refetch()}
      onSwitchToDemo={dataSourceMode === 'live' ? () => setDataSourceMode('demo') : undefined}
    />
  );
}
