/**
 * CommandCenter - Neural Command Center main dashboard
 * The primary view for OMEN Signal Intelligence Engine
 * Features: Global map, system status, KPIs, activity feed, priority signals
 */
import { motion } from 'framer-motion';
import { Activity, Shield, Zap, Clock, Globe, AlertTriangle } from 'lucide-react';
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { MetricCard } from '../components/ui/MetricCard';
import { GlobalMap } from '../components/dashboard/GlobalMap';
import { SystemStatus } from '../components/dashboard/SystemStatus';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { PrioritySignals } from '../components/dashboard/PrioritySignals';
import { ProgressBar } from '../components/ui/ProgressBar';
import { cn } from '../lib/utils';

export interface CommandCenterProps {
  className?: string;
}

export function CommandCenter({ className }: CommandCenterProps) {
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
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <Clock className="w-4 h-4" />
          <span className="font-mono">Last updated: 2 seconds ago</span>
        </div>
      </motion.div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Signals Today"
          value={47}
          previousValue={42}
          icon={<Activity className="w-5 h-5" />}
          color="cyan"
          delay={0.1}
        />
        <MetricCard
          title="Validation Rate"
          value={41.6}
          format="percent"
          icon={<Shield className="w-5 h-5" />}
          color="success"
          delay={0.15}
        />
        <MetricCard
          title="Avg Confidence"
          value={0.62}
          format="decimal"
          decimals={2}
          icon={<Zap className="w-5 h-5" />}
          color="amber"
          delay={0.2}
        />
        <MetricCard
          title="Processing"
          value={1250}
          unit="events/hr"
          icon={<Activity className="w-5 h-5" />}
          color="cyan"
          delay={0.25}
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
              <GlobalMap />
            </div>
          </GlassCard>
        </div>

        {/* Right Column */}
        <div className="lg:col-span-4 space-y-4">
          {/* System Status */}
          <GlassCard className="p-4" delay={0.35}>
            <GlassCardTitle>System Status</GlassCardTitle>
            <div className="mt-3">
              <SystemStatus />
            </div>
          </GlassCard>

          {/* Signal Funnel */}
          <GlassCard className="p-4" delay={0.4}>
            <GlassCardTitle>Signal Metrics</GlassCardTitle>
            <div className="mt-4 space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Events Received</span>
                  <span className="font-mono text-text-primary">1,250</span>
                </div>
                <ProgressBar value={100} variant="cyan" size="sm" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Validated</span>
                  <span className="font-mono text-text-primary">520</span>
                </div>
                <ProgressBar value={41.6} variant="success" size="sm" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Signals Generated</span>
                  <span className="font-mono text-text-primary">47</span>
                </div>
                <ProgressBar value={9} variant="amber" size="sm" />
              </div>

              {/* Conversion Rates */}
              <div className="pt-3 border-t border-border-subtle grid grid-cols-2 gap-4">
                <div className="text-center">
                  <p className="text-xl font-display font-bold text-accent-cyan">41.6%</p>
                  <p className="text-xs text-text-muted">Pass Rate</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-display font-bold text-status-success">9.0%</p>
                  <p className="text-xs text-text-muted">Signal Rate</p>
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
