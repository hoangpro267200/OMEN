/**
 * SourcesObservatory - Neural Command Center data sources monitoring
 * Features: Constellation view, source cards, live data preview
 */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Radio, Grid } from 'lucide-react';
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { SourceConstellation, type DataSource } from '../components/sources/SourceConstellation';
import { SourceCard } from '../components/sources/SourceCard';
import { DataPreview } from '../components/sources/DataPreview';
import { cn } from '../lib/utils';

const DEFAULT_SOURCES: DataSource[] = [
  { id: 'polymarket', name: 'Polymarket', status: 'healthy', latency: 120, type: 'real' },
  { id: 'ais', name: 'AIS Marine', status: 'healthy', latency: 450, type: 'real' },
  { id: 'commodity', name: 'Commodity', status: 'healthy', latency: 200, type: 'real' },
  { id: 'weather', name: 'Weather', status: 'warning', latency: 800, type: 'real' },
  { id: 'news', name: 'News', status: 'healthy', latency: 150, type: 'real' },
  { id: 'stock', name: 'Stock', status: 'healthy', latency: 180, type: 'real' },
  { id: 'freight', name: 'Freight', status: 'mock', latency: 0, type: 'mock' },
  { id: 'partner', name: 'Partner Risk', status: 'healthy', latency: 220, type: 'real' },
];

export interface SourcesObservatoryProps {
  className?: string;
}

export function SourcesObservatory({ className }: SourcesObservatoryProps) {
  const [selectedSource, setSelectedSource] = useState<string | null>('polymarket');
  const [sources] = useState<DataSource[]>(DEFAULT_SOURCES);

  // Calculate summary stats
  const healthySources = sources.filter((s) => s.status === 'healthy').length;
  const totalSources = sources.length;
  const avgLatency = Math.round(
    sources.filter((s) => s.type === 'real').reduce((sum, s) => sum + s.latency, 0) /
      sources.filter((s) => s.type === 'real').length
  );

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
            Data Sources Observatory
          </h1>
          <p className="text-text-muted text-sm mt-1 font-body">
            Monitor all {totalSources} intelligence sources feeding into OMEN
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-text-muted">Active:</span>
            <span className="font-mono text-status-success">
              {healthySources}/{totalSources}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-muted">Avg Latency:</span>
            <span className="font-mono text-accent-cyan">{avgLatency}ms</span>
          </div>
        </div>
      </motion.div>

      {/* Constellation View */}
      <GlassCard className="p-6" delay={0.1}>
        <GlassCardTitle icon={<Radio className="w-4 h-4" />}>
          Source Constellation
        </GlassCardTitle>
        <div className="mt-4">
          <SourceConstellation
            sources={sources}
            selectedSource={selectedSource}
            onSelectSource={setSelectedSource}
          />
        </div>
      </GlassCard>

      {/* Source Cards Grid */}
      <GlassCard className="p-6" delay={0.2}>
        <GlassCardTitle icon={<Grid className="w-4 h-4" />}>
          Source Status
        </GlassCardTitle>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {sources.map((source, index) => (
            <SourceCard
              key={source.id}
              source={source}
              isSelected={selectedSource === source.id}
              onClick={() => setSelectedSource(source.id)}
              delay={0.25 + index * 0.05}
            />
          ))}
        </div>
      </GlassCard>

      {/* Data Preview */}
      <GlassCard className="p-6" delay={0.5}>
        <GlassCardTitle>Live Data Preview</GlassCardTitle>
        <div className="mt-4">
          <DataPreview sourceId={selectedSource} />
        </div>
      </GlassCard>
    </div>
  );
}

export default SourcesObservatory;
