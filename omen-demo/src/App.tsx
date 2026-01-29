/**
 * OMEN Dashboard — live backend integration with mock fallback.
 */
import { useState, useMemo, useEffect, lazy, Suspense } from 'react';
import { motion } from 'framer-motion';

import { Header } from './components/Layout/Header';
import { Sidebar } from './components/Layout/Sidebar';
import { MainPanel } from './components/Layout/MainPanel';
import { BottomPanel } from './components/Layout/BottomPanel';
import { KPIStatsRow } from './components/dashboard/KPIStatsRow';
import { ProbabilityGauge } from './components/analysis/ProbabilityGauge';
import { ConfidenceRadar } from './components/analysis/ConfidenceRadar';
import { ImpactMetricsGrid } from './components/analysis/ImpactMetricsGrid';
import { ExplanationChain } from './components/analysis/ExplanationChain';
import { ProbabilityChart } from './components/charts/ProbabilityChart';
import { SeverityDonut } from './components/charts/SeverityDonut';
import { ProcessingFunnel } from './components/charts/ProcessingFunnel';
import { ImpactProjectionChart } from './components/charts/ImpactProjectionChart';
import { ActivityFeed } from './components/dashboard/ActivityFeed';
import { Card } from './components/common/Card';
import {
  SignalMetadataRow,
  SignalSummaryCard,
  SignalDetailedExplanation,
  SignalOnsetDuration,
  SignalBadges,
  SignalSourceMarket,
  SignalAffectedSystems,
} from './components/SignalDetail/SignalDetailBlocks';

import {
  useProcessLiveSignals,
  useSystemStats,
  useActivityFeed,
} from './hooks/useOmenApi';
import { useRealtimePrices } from './hooks/useRealtimePrices';
import { useDataSource } from './hooks/useDataSource';

import { DataSourceBanner } from './components/common/DataSourceBanner';
import { EmptyState } from './components/common/EmptyState';
import { DataCompletenessIndicator } from './components/common/DataCompletenessIndicator';
import { PipelineDebugPanel } from './components/debug/PipelineDebugPanel';

import { systemStats, activityFeed } from './data/mockSignals';
import { last24hProbabilityHistory } from './data/mockTimeSeries';
import type { SystemStats } from './types/omen';

const WorldMap = lazy(() =>
  import('./components/visualization/WorldMap').then((m) => ({ default: m.WorldMap }))
);

function App() {
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);
  const [useLiveData, setUseLiveData] = useState(true);

  const {
    data: liveSignals,
    isLoading: signalsLoading,
    error: signalsError,
    dataUpdatedAt,
    refetch: refetchLiveSignals,
  } = useProcessLiveSignals({ enabled: useLiveData });

  const lastFetchTime = dataUpdatedAt ? new Date(dataUpdatedAt) : null;
  const { data: signals, source: dataSource } = useDataSource(
    useLiveData ? liveSignals : undefined,
    useLiveData ? signalsLoading : false,
    useLiveData ? (signalsError ?? null) : null,
    useLiveData ? lastFetchTime : null
  );

  const { data: liveStats } = useSystemStats();
  const { data: liveActivity } = useActivityFeed(20);

  const signalIds = useMemo(() => signals.map((s) => s.signal_id), [signals]);
  const realtimeStatus = useRealtimePrices(signalIds);

  const stats: SystemStats = useMemo(() => {
    if (dataSource.type === 'demo') return systemStats;
    if (liveStats) return liveStats;
    return {
      active_signals: 0,
      critical_alerts: 0,
      avg_confidence: 0,
      total_risk_exposure: 0,
      events_processed: 0,
      events_validated: 0,
      signals_generated: 0,
      events_rejected: 0,
      system_latency_ms: 0,
      events_per_second: 0,
      uptime_percent: 0,
      validation_rate: undefined,
      events_translated: undefined,
      _unavailable: true,
    };
  }, [dataSource.type, liveStats]);

  const activity = useMemo(() => {
    if (dataSource.type === 'demo') return activityFeed;
    if (liveActivity && liveActivity.length > 0) return liveActivity;
    return [];
  }, [dataSource.type, liveActivity]);

  const selectedSignal = useMemo(() => {
    if (selectedSignalId) {
      const s = signals.find((s) => s.signal_id === selectedSignalId);
      if (s) return s;
    }
    return signals[0] ?? null;
  }, [selectedSignalId, signals]);

  useEffect(() => {
    if (signals.length > 0 && !selectedSignalId) {
      setSelectedSignalId(signals[0].signal_id);
    }
  }, [signals, selectedSignalId]);

  const probabilityChartData = useMemo(() => {
    if (!selectedSignal?.probability_history?.length) return [];
    return last24hProbabilityHistory(selectedSignal.probability_history);
  }, [selectedSignal]);

  const histMin = selectedSignal?.probability_history?.length
    ? Math.min(...selectedSignal.probability_history)
    : 0;
  const histMax = selectedSignal?.probability_history?.length
    ? Math.max(...selectedSignal.probability_history)
    : 1;

  const severityDistribution = useMemo(() => {
    const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
    signals.forEach((s) => {
      if (s.severity >= 0.75) counts.Critical++;
      else if (s.severity >= 0.5) counts.High++;
      else if (s.severity >= 0.25) counts.Medium++;
      else counts.Low++;
    });
    return [
      { name: 'Critical', value: counts.Critical, fill: '#ef4444' },
      { name: 'High', value: counts.High, fill: '#f97316' },
      { name: 'Medium', value: counts.Medium, fill: '#f59e0b' },
      { name: 'Low', value: counts.Low, fill: '#10b981' },
    ];
  }, [signals]);

  const funnelData = useMemo(() => {
    const translated =
      stats.events_translated != null ? stats.events_translated : null;
    return [
      { stage: 'Raw events', value: stats.events_processed, fill: '#3b82f6' },
      { stage: 'Validated', value: stats.events_validated, fill: '#06b6d4' },
      { stage: 'Translated', value: translated, fill: '#10b981' },
      { stage: 'Signals', value: stats.signals_generated, fill: '#8b5cf6' },
    ];
  }, [stats]);

  if (signalsLoading && (!signals || signals.length === 0)) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[var(--text-secondary)]">Đang tải dữ liệu từ Polymarket...</p>
          {useLiveData && (
            <p className="text-[var(--text-muted)] text-sm mt-2">
              Lần đầu có thể mất 30–90 giây (fetch + xử lý pipeline).
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 flex flex-col bg-[var(--bg-base)] text-[var(--text-primary)]">
      <Header
        systemStatus="OPERATIONAL"
        isLive={dataSource.type === 'live'}
        connectionStatus={signalsError ? 'disconnected' : 'connected'}
        latencyMs={stats.system_latency_ms}
        dataSource={dataSource}
        signalsCount={dataSource.type === 'live' ? (stats.signals_generated ?? signals.length) : undefined}
      />

      <div className="flex-1 flex min-h-0 overflow-hidden pt-16 pb-12">
        <Sidebar
          signals={signals}
          selectedSignalId={selectedSignalId}
          onSelectSignal={setSelectedSignalId}
          totalSignalsCount={dataSource.type === 'live' ? (stats.signals_generated ?? signals.length) : signals.length}
        />

        <MainPanel>
          <div className="flex-1 min-h-0 overflow-y-auto overflow-thin-scroll p-6 pb-12 space-y-6 bg-[var(--bg-primary)]">
            {dataSource.type !== 'live' ? (
              <DataSourceBanner
                source={dataSource}
                onRetry={useLiveData && signalsError ? () => refetchLiveSignals() : undefined}
              />
            ) : null}
            {realtimeStatus.error ? (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm"
              >
                Real-time: {realtimeStatus.error}
              </motion.div>
            ) : null}

            {signals.length === 0 && !signalsLoading ? (
              <EmptyState message={dataSource.message} onLoadDemo={() => setUseLiveData(false)} />
            ) : null}

            {signals.length > 0 ? (
              <>
            <KPIStatsRow stats={stats} />

            {selectedSignal && (
              <>
                <Card className="p-4 space-y-3" hover={false}>
                  <SignalMetadataRow signal={selectedSignal} />
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <SignalBadges
                      domain={selectedSignal.domain}
                      category={selectedSignal.category}
                      subcategory={selectedSignal.subcategory}
                    />
                    <SignalOnsetDuration
                      expected_onset_hours={selectedSignal.expected_onset_hours}
                      expected_duration_hours={selectedSignal.expected_duration_hours}
                    />
                    <SignalSourceMarket
                      source_market={selectedSignal.source_market}
                      market_url={selectedSignal.market_url}
                    />
                  </div>
                </Card>
                <DataCompletenessIndicator
                  fields={[
                    { name: 'Probability', hasData: selectedSignal.probability != null, importance: 'critical' },
                    { name: 'Confidence', hasData: selectedSignal.confidence_score != null, importance: 'critical' },
                    { name: 'Confidence Breakdown', hasData: !!(selectedSignal.has_confidence_breakdown ?? selectedSignal.confidence_breakdown != null), importance: 'important' },
                    { name: 'Uncertainty', hasData: (selectedSignal.metrics ?? []).some((m) => m.has_uncertainty), importance: 'important' },
                    { name: 'Evidence', hasData: (selectedSignal.metrics ?? []).some((m) => m.has_evidence), importance: 'important' },
                    { name: 'Routes', hasData: (selectedSignal.affected_routes?.length ?? 0) > 0, importance: 'optional' },
                    { name: 'Chokepoints', hasData: (selectedSignal.affected_chokepoints?.length ?? 0) > 0, importance: 'optional' },
                    { name: 'History', hasData: (selectedSignal.probability_history?.length ?? 0) > 0, importance: 'optional' },
                  ]}
                />
              </>
            )}

            {selectedSignal && (
              <SignalSummaryCard summary={selectedSignal.summary} />
            )}

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              <div className="lg:col-span-4">
                {selectedSignal && (
                  <ProbabilityGauge
                    probability={selectedSignal.probability}
                    momentum={selectedSignal.probability_momentum}
                    historyMin={histMin}
                    historyMax={histMax}
                    isCritical={selectedSignal.severity_label === 'CRITICAL'}
                    isFallback={!!selectedSignal.probability_is_fallback}
                  />
                )}
              </div>
              <div className="lg:col-span-4">
                {selectedSignal && (
                  <ConfidenceRadar
                    breakdown={selectedSignal.confidence_breakdown}
                    overall={selectedSignal.confidence_score}
                  />
                )}
              </div>
              <div className="lg:col-span-4">
                <SeverityDonut data={severityDistribution} />
              </div>
            </div>

            {probabilityChartData.length > 0 && <ProbabilityChart data={probabilityChartData} />}

            {selectedSignal && selectedSignal.metrics?.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                  Chỉ số tác động
                </h2>
                <ImpactMetricsGrid metrics={selectedSignal.metrics} />
                <ImpactProjectionChart metrics={selectedSignal.metrics} />
              </div>
            )}

            {selectedSignal && (selectedSignal.affected_systems?.length ?? 0) > 0 && (
              <SignalAffectedSystems affected_systems={selectedSignal.affected_systems} />
            )}

            {selectedSignal &&
              (selectedSignal.affected_routes?.length > 0 ||
                selectedSignal.affected_chokepoints?.length > 0) && (
                <Suspense
                  fallback={
                    <Card className="p-6 min-h-[320px] flex items-center justify-center text-[var(--text-tertiary)]">
                      Đang tải bản đồ…
                    </Card>
                  }
                >
                  <WorldMap
                    routes={selectedSignal.affected_routes ?? []}
                    chokepoints={selectedSignal.affected_chokepoints ?? []}
                  />
                </Suspense>
              )}

            {selectedSignal && (
              <SignalDetailedExplanation detailed_explanation={selectedSignal.detailed_explanation} />
            )}

            {selectedSignal && selectedSignal.explanation_steps?.length > 0 && (
              <ExplanationChain
                steps={selectedSignal.explanation_steps}
                traceId={selectedSignal.trace_id}
              />
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-1">
                <ProcessingFunnel data={funnelData} />
              </div>
              <div className="lg:col-span-2">
                <ActivityFeed items={activity} />
              </div>
            </div>
              </>
            ) : null}
          </div>
        </MainPanel>
      </div>

      <PipelineDebugPanel />
      <BottomPanel stats={stats} />
    </div>
  );
}

export default App;
