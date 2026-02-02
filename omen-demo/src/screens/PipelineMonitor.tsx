/**
 * PipelineMonitor - Neural Command Center signal processing pipeline view
 * Features: Animated pipeline flow, validation breakdown, signal inspector
 */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { GitBranch, BarChart2, Search } from 'lucide-react';
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { AnimatedPipeline } from '../components/pipeline/AnimatedPipeline';
import { RulePerformance } from '../components/pipeline/RulePerformance';
import { SignalInspector } from '../components/pipeline/SignalInspector';
import { cn } from '../lib/utils';

export interface PipelineMonitorProps {
  className?: string;
}

export function PipelineMonitor({ className }: PipelineMonitorProps) {
  const [selectedSignal, setSelectedSignal] = useState<string | null>('OMEN-9C4860E23B54');

  return (
    <div className={cn('p-6 space-y-6', className)}>
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
          Signal Processing Pipeline
        </h1>
        <p className="text-text-muted text-sm mt-1 font-body">
          Real-time visualization of signal validation and enrichment
        </p>
      </motion.div>

      {/* Main Pipeline Animation */}
      <GlassCard className="p-6" delay={0.1}>
        <GlassCardTitle icon={<GitBranch className="w-4 h-4" />}>
          Live Pipeline Visualization
        </GlassCardTitle>
        <div className="mt-4 h-[220px]">
          <AnimatedPipeline onSelectSignal={setSelectedSignal} />
        </div>
      </GlassCard>

      {/* Analytics Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Validation Sankey (simplified as rule performance) */}
        <GlassCard className="p-4" delay={0.2}>
          <GlassCardTitle icon={<BarChart2 className="w-4 h-4" />}>
            Validation Breakdown
          </GlassCardTitle>
          <div className="mt-4">
            <ValidationFunnel />
          </div>
        </GlassCard>

        {/* Rule Performance */}
        <GlassCard className="p-4" delay={0.25}>
          <GlassCardTitle>Rule Performance</GlassCardTitle>
          <div className="mt-4">
            <RulePerformance />
          </div>
        </GlassCard>
      </div>

      {/* Signal Inspector */}
      <GlassCard className="p-4" delay={0.3}>
        <GlassCardTitle icon={<Search className="w-4 h-4" />}>
          Signal Inspector
        </GlassCardTitle>
        <div className="mt-4">
          <SignalInspector signalId={selectedSignal} />
        </div>
      </GlassCard>
    </div>
  );
}

// Simple validation funnel visualization
function ValidationFunnel() {
  const stages = [
    { name: 'Raw Events', value: 1250, color: 'bg-accent-cyan', width: 100 },
    { name: 'After Liquidity', value: 980, color: 'bg-accent-cyan', width: 78 },
    { name: 'After Anomaly', value: 850, color: 'bg-status-success', width: 68 },
    { name: 'After Semantic', value: 520, color: 'bg-status-success', width: 42 },
    { name: 'Signals', value: 47, color: 'bg-accent-amber', width: 4 },
  ];

  return (
    <div className="space-y-3">
      {stages.map((stage, index) => (
        <motion.div
          key={stage.name}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
          className="space-y-1"
        >
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">{stage.name}</span>
            <span className="font-mono text-text-primary">{stage.value.toLocaleString()}</span>
          </div>
          <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
            <motion.div
              className={cn('h-full rounded-full', stage.color)}
              initial={{ width: 0 }}
              animate={{ width: `${stage.width}%` }}
              transition={{ duration: 0.8, delay: index * 0.1, ease: 'easeOut' }}
            />
          </div>
        </motion.div>
      ))}

      {/* Conversion metrics */}
      <div className="pt-4 mt-4 border-t border-border-subtle grid grid-cols-3 gap-4 text-center">
        <div>
          <p className="text-lg font-display font-bold text-accent-cyan">41.6%</p>
          <p className="text-xs text-text-muted">Pass Rate</p>
        </div>
        <div>
          <p className="text-lg font-display font-bold text-status-success">3.8%</p>
          <p className="text-xs text-text-muted">Signal Rate</p>
        </div>
        <div>
          <p className="text-lg font-display font-bold text-status-error">58.4%</p>
          <p className="text-xs text-text-muted">Rejected</p>
        </div>
      </div>
    </div>
  );
}

export default PipelineMonitor;
