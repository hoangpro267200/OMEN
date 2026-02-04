/**
 * CommandCenter - Neural Command Center main dashboard
 * The primary view for OMEN Signal Intelligence Engine
 * Features: Global map, system status, KPIs, activity feed, priority signals
 * 
 * Uses unified data hooks for real-time data in both Live and Demo modes.
 */
import { motion } from 'framer-motion';
import { Activity, Shield, Zap, Clock, Globe, AlertTriangle } from 'lucide-react';
import { Suspense, lazy, Component, type ReactNode, useMemo, useEffect, useState } from 'react';
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { MetricCard } from '../components/ui/MetricCard';
import { SystemStatus } from '../components/dashboard/SystemStatus';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { PrioritySignals } from '../components/dashboard/PrioritySignals';
import { ProgressBar } from '../components/ui/ProgressBar';
import { cn } from '../lib/utils';
import { usePipelineStats, useDataSources } from '../hooks/useSignalData';
import { useDataModeSafe } from '../context/DataModeContext';
import { formatDistanceToNow } from 'date-fns';

// Lazy load GlobalMap to prevent crashes
const GlobalMap = lazy(() => import('../components/dashboard/GlobalMap').then(m => ({ default: m.GlobalMap })));

// Error boundary for map
class MapErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-full text-text-muted">
          <div className="text-center">
            <Globe className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Map unavailable</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export interface CommandCenterProps {
  className?: string;
}

export function CommandCenter({ className }: CommandCenterProps) {
  // Fetch real data using unified hooks
  const { data: pipelineStats, isLoading: statsLoading, dataSource } = usePipelineStats();
  const { data: dataSources } = useDataSources();
  const { state: dataModeState } = useDataModeSafe();
  
  // Track last update time
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());
  
  useEffect(() => {
    if (pipelineStats) {
      setLastUpdateTime(new Date());
    }
  }, [pipelineStats]);
  
  // Compute derived metrics with safe defaults
  const metrics = useMemo(() => {
    // Default values - always return these to prevent undefined errors
    const defaults = {
      signalsToday: 0,
      validationRate: 0,
      avgConfidence: 0,
      eventsReceived: 0,
      eventsValidated: 0,
      signalsGenerated: 0,
      passRate: 0,
      signalRate: 0,
    };
    
    if (!pipelineStats) {
      return defaults;
    }
    
    // Safely extract values with fallbacks
    const eventsReceived = pipelineStats.events_received ?? 0;
    const eventsValidated = pipelineStats.events_validated ?? 0;
    const signalsGenerated = pipelineStats.signals_generated ?? 0;
    const avgConfidence = pipelineStats.average_confidence ?? 0;
    
    const passRate = eventsReceived > 0 ? (eventsValidated / eventsReceived) * 100 : 0;
    const signalRate = eventsValidated > 0 ? (signalsGenerated / eventsValidated) * 100 : 0;
    
    return {
      signalsToday: signalsGenerated,
      validationRate: passRate,
      avgConfidence: avgConfidence * 100,
      eventsReceived,
      eventsValidated,
      signalsGenerated,
      passRate,
      signalRate,
    };
  }, [pipelineStats]);
  
  // Compute system status from data sources
  const systemStatusProps = useMemo(() => {
    if (!dataSources) {
      return {
        sourcesActive: 0,
        sourcesTotal: 0,
      };
    }
    const active = dataSources.filter(s => s.status === 'healthy' || s.status === 'warning').length;
    return {
      sourcesActive: active,
      sourcesTotal: dataSources.length,
    };
  }, [dataSources]);

  // Format last update time
  const lastUpdateText = useMemo(() => {
    return formatDistanceToNow(lastUpdateTime, { addSuffix: false });
  }, [lastUpdateTime]);

  return (
    <div className={cn('p-6 space-y-6', className)}>
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
            Command Center
          </h1>
          <p className="text-text-muted text-sm mt-1 font-body">
            Real-time signal intelligence overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Data source indicator */}
          <span className={cn(
            'px-2 py-0.5 rounded-full border text-[10px] font-mono font-bold',
            dataSource === 'mock' 
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          )}>
            {dataSource === 'mock' ? '⚗ DEMO' : '● LIVE'}
          </span>
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <Clock className="w-4 h-4" />
            <span className="font-mono">Cập nhật: {lastUpdateText}</span>
          </div>
        </div>
      </motion.div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Signals Today"
          value={metrics.signalsToday}
          previousValue={Math.max(0, metrics.signalsToday - 5)}
          icon={<Activity className="w-5 h-5" />}
          color="cyan"
          delay={0.1}
          loading={statsLoading}
        />
        <MetricCard
          title="Validation Rate"
          value={metrics.validationRate}
          format="percent"
          icon={<Shield className="w-5 h-5" />}
          color="success"
          delay={0.15}
          loading={statsLoading}
        />
        <MetricCard
          title="Avg Confidence"
          value={metrics.avgConfidence / 100}
          format="decimal"
          decimals={2}
          icon={<Zap className="w-5 h-5" />}
          color="amber"
          delay={0.2}
          loading={statsLoading}
        />
        <MetricCard
          title="Processing"
          value={metrics.eventsReceived}
          unit="events/hr"
          icon={<Activity className="w-5 h-5" />}
          color="cyan"
          delay={0.25}
          loading={statsLoading}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Global Map - Large */}
        <div className="lg:col-span-8">
          <GlassCard className="p-4 h-[400px]" delay={0.3}>
            <GlassCardTitle icon={<Globe className="w-4 h-4" />}>
              Global Situation Awareness
            </GlassCardTitle>
            <div className="h-[calc(100%-2rem)] mt-3">
              <MapErrorBoundary>
                <Suspense fallback={
                  <div className="flex items-center justify-center h-full text-text-muted">
                    <div className="animate-pulse">Loading map...</div>
                  </div>
                }>
                  <GlobalMap />
                </Suspense>
              </MapErrorBoundary>
            </div>
          </GlassCard>
        </div>

        {/* Right Column */}
        <div className="lg:col-span-4 space-y-4">
          {/* System Status */}
          <GlassCard className="p-4" delay={0.35}>
            <GlassCardTitle>System Status</GlassCardTitle>
            <div className="mt-3">
              <SystemStatus 
                sourcesActive={systemStatusProps.sourcesActive}
                sourcesTotal={systemStatusProps.sourcesTotal}
                pipelineStatus={dataModeState.connectionStatus === 'connected' ? 'healthy' : 
                               dataModeState.connectionStatus === 'connecting' ? 'warning' : 'error'}
                pipelineDetail={statsLoading ? 'Loading...' : 
                               `Processing ${((metrics.eventsReceived || 0) / 60).toFixed(1)} events/sec`}
              />
            </div>
          </GlassCard>

          {/* Signal Funnel */}
          <GlassCard className="p-4" delay={0.4}>
            <GlassCardTitle>Signal Metrics</GlassCardTitle>
            <div className="mt-4 space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Sự kiện đã nhận được</span>
                  <span className="font-mono text-text-primary">
                    {statsLoading ? '...' : (metrics.eventsReceived || 0).toLocaleString()}
                  </span>
                </div>
                <ProgressBar value={100} variant="cyan" size="sm" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Đã xác thực</span>
                  <span className="font-mono text-text-primary">
                    {statsLoading ? '...' : (metrics.eventsValidated || 0).toLocaleString()}
                  </span>
                </div>
                <ProgressBar 
                  value={metrics.passRate || 0} 
                  variant="success" 
                  size="sm" 
                />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Các tín hiệu được tạo ra</span>
                  <span className="font-mono text-text-primary">
                    {statsLoading ? '...' : (metrics.signalsGenerated || 0).toLocaleString()}
                  </span>
                </div>
                <ProgressBar 
                  value={metrics.signalRate || 0} 
                  variant="amber" 
                  size="sm" 
                />
              </div>

              {/* Conversion Rates */}
              <div className="pt-3 border-t border-border-subtle grid grid-cols-2 gap-4">
                <div className="text-center">
                  <p className="text-xl font-display font-bold text-accent-cyan">
                    {statsLoading ? '...' : `${(metrics.passRate || 0).toFixed(1)}%`}
                  </p>
                  <p className="text-xs text-text-muted">Tỷ lệ đậu</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-display font-bold text-status-success">
                    {statsLoading ? '...' : `${(metrics.signalRate || 0).toFixed(1)}%`}
                  </p>
                  <p className="text-xs text-text-muted">Tốc độ tín hiệu</p>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Priority Signals Table */}
        <div className="lg:col-span-8">
          <GlassCard className="p-4" delay={0.45}>
            <GlassCardTitle icon={<AlertTriangle className="w-4 h-4" />}>
              High Priority Signals
            </GlassCardTitle>
            <div className="mt-3">
              <PrioritySignals />
            </div>
          </GlassCard>
        </div>

        {/* Activity Feed */}
        <div className="lg:col-span-4">
          <GlassCard className="p-4 h-[350px]" delay={0.5}>
            <GlassCardTitle icon={<Zap className="w-4 h-4" />}>
              Live Activity
            </GlassCardTitle>
            <div className="h-[calc(100%-2rem)] mt-3">
              <ActivityFeed maxItems={10} />
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

export default CommandCenter;
// HMR trigger
