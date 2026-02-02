/**
 * SourceCard - Neural Command Center data source health card
 * Features: Status indicator, latency bar, metrics display
 */
import { motion } from 'framer-motion';
import { Activity, Database } from 'lucide-react';
import { cn } from '../../lib/utils';
import { StatusIndicator, type StatusType } from '../ui/StatusIndicator';
import { ProgressBar } from '../ui/ProgressBar';
import type { DataSource } from './SourceConstellation';

// Extended source info with metrics
interface SourceMetrics {
  eventsPerHour: number;
  itemCount: string;
}

const SOURCE_METRICS: Record<string, SourceMetrics> = {
  polymarket: { eventsPerHour: 850, itemCount: '150 markets' },
  ais: { eventsPerHour: 2000, itemCount: '45 ports' },
  commodity: { eventsPerHour: 12, itemCount: '8 assets' },
  weather: { eventsPerHour: 24, itemCount: '3 alerts' },
  news: { eventsPerHour: 200, itemCount: '50 articles' },
  stock: { eventsPerHour: 100, itemCount: '25 tickers' },
  freight: { eventsPerHour: 0, itemCount: 'Mock data' },
  partner: { eventsPerHour: 15, itemCount: '8 companies' },
};

interface SourceCardProps {
  source: DataSource;
  isSelected: boolean;
  onClick: () => void;
  delay?: number;
  className?: string;
}

export function SourceCard({
  source,
  isSelected,
  onClick,
  delay = 0,
  className,
}: SourceCardProps) {
  const metrics = SOURCE_METRICS[source.id] || { eventsPerHour: 0, itemCount: 'N/A' };
  const latencyPercent = Math.min((source.latency / 1000) * 100, 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      onClick={onClick}
      className={cn(
        'p-4 rounded-xl cursor-pointer transition-all duration-300',
        'border bg-bg-tertiary/30',
        isSelected
          ? 'border-accent-cyan shadow-glow-cyan'
          : 'border-border-subtle hover:border-border-active hover:bg-bg-tertiary/50',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-heading font-medium text-text-primary">{source.name}</h3>
        <StatusIndicator status={source.status as StatusType} size="sm" />
      </div>

      {/* Latency Bar */}
      <div className="space-y-1 mb-3">
        <div className="flex justify-between text-xs">
          <span className="text-text-muted">Latency</span>
          <span className="font-mono text-text-secondary">
            {source.type === 'mock' ? 'N/A' : `${source.latency}ms`}
          </span>
        </div>
        <ProgressBar
          value={source.type === 'mock' ? 0 : latencyPercent}
          variant={latencyPercent > 70 ? 'warning' : 'cyan'}
          size="sm"
          animated={false}
        />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1 text-text-muted">
          <Activity className="w-3 h-3" />
          <span>{metrics.eventsPerHour}/hr</span>
        </div>
        <div className="flex items-center gap-1 text-text-muted">
          <Database className="w-3 h-3" />
          <span>{metrics.itemCount}</span>
        </div>
      </div>

      {/* Type Badge */}
      <div className="mt-3 pt-3 border-t border-border-subtle">
        <span
          className={cn(
            'text-xs px-2 py-0.5 rounded-full',
            source.type === 'real'
              ? 'bg-status-success/20 text-status-success'
              : 'bg-text-muted/20 text-text-muted'
          )}
        >
          {source.type === 'real' ? '● LIVE' : '○ MOCK'}
        </span>
      </div>
    </motion.div>
  );
}
