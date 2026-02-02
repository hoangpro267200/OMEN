/**
 * PrioritySignals - Neural Command Center high priority signals table
 * Features: Status badges, probability/confidence display, row interactions
 */
import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { StatusIndicator } from '../ui/StatusIndicator';
import { MiniGauge } from '../ui/Gauge';

export interface PrioritySignal {
  id: string;
  title: string;
  status: 'active' | 'monitoring' | 'candidate';
  probability: number;
  confidence: number;
  category: string;
  timeAgo: string;
}

const STATUS_CONFIG = {
  active: {
    label: 'ACTIVE',
    className: 'bg-status-error/20 text-status-error border-status-error/30',
    indicatorStatus: 'error' as const,
  },
  monitoring: {
    label: 'WATCH',
    className: 'bg-status-warning/20 text-status-warning border-status-warning/30',
    indicatorStatus: 'warning' as const,
  },
  candidate: {
    label: 'LOW',
    className: 'bg-text-muted/20 text-text-muted border-text-muted/30',
    indicatorStatus: 'inactive' as const,
  },
};

// Sample data - in production this would come from the API
const SAMPLE_SIGNALS: PrioritySignal[] = [
  {
    id: 'OMEN-ABC123',
    title: 'Suez Canal Disruption Risk',
    status: 'active',
    probability: 0.68,
    confidence: 0.78,
    category: 'SHIPPING',
    timeAgo: '2m ago',
  },
  {
    id: 'OMEN-9C4860',
    title: 'China x India Military Clash',
    status: 'monitoring',
    probability: 0.175,
    confidence: 0.57,
    category: 'GEOPOLITICAL',
    timeAgo: '5m ago',
  },
  {
    id: 'OMEN-DEF456',
    title: 'Panama Canal Water Levels',
    status: 'monitoring',
    probability: 0.42,
    confidence: 0.65,
    category: 'INFRASTRUCTURE',
    timeAgo: '8m ago',
  },
  {
    id: 'OMEN-GHI789',
    title: 'Red Sea Shipping Disruption',
    status: 'active',
    probability: 0.55,
    confidence: 0.72,
    category: 'SHIPPING',
    timeAgo: '12m ago',
  },
  {
    id: 'OMEN-JKL012',
    title: 'Taiwan Strait Tension',
    status: 'candidate',
    probability: 0.15,
    confidence: 0.45,
    category: 'GEOPOLITICAL',
    timeAgo: '18m ago',
  },
];

export interface PrioritySignalsProps {
  signals?: PrioritySignal[];
  onSignalClick?: (signal: PrioritySignal) => void;
  maxItems?: number;
  className?: string;
}

export function PrioritySignals({
  signals = SAMPLE_SIGNALS,
  onSignalClick,
  maxItems = 5,
  className,
}: PrioritySignalsProps) {
  const displaySignals = signals.slice(0, maxItems);

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full">
        <thead>
          <tr className="text-left text-xs text-text-muted border-b border-border-subtle">
            <th className="pb-3 font-medium font-mono">Status</th>
            <th className="pb-3 font-medium font-mono">Signal</th>
            <th className="pb-3 font-medium font-mono text-right">Probability</th>
            <th className="pb-3 font-medium font-mono text-right">Confidence</th>
            <th className="pb-3 font-medium font-mono text-right">Category</th>
            <th className="pb-3 font-medium font-mono text-right">Time</th>
            <th className="pb-3 w-8"></th>
          </tr>
        </thead>
        <tbody>
          {displaySignals.map((signal, index) => {
            const status = STATUS_CONFIG[signal.status];
            return (
              <motion.tr
                key={signal.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05, duration: 0.2 }}
                onClick={() => onSignalClick?.(signal)}
                className="border-b border-border-subtle/50 hover:bg-bg-tertiary/30 transition-colors cursor-pointer group"
              >
                {/* Status */}
                <td className="py-3 pr-4">
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono border',
                      status.className
                    )}
                  >
                    <StatusIndicator
                      status={status.indicatorStatus}
                      size="xs"
                      pulse={signal.status === 'active'}
                    />
                    {status.label}
                  </span>
                </td>

                {/* Signal info */}
                <td className="py-3 pr-4">
                  <div>
                    <p className="text-sm font-medium text-text-primary group-hover:text-accent-cyan transition-colors">
                      {signal.title}
                    </p>
                    <p className="text-xs text-text-muted font-mono">{signal.id}</p>
                  </div>
                </td>

                {/* Probability */}
                <td className="py-3 pr-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <MiniGauge
                      value={signal.probability * 100}
                      size={24}
                      color={signal.probability >= 0.5 ? 'error' : signal.probability >= 0.3 ? 'warning' : 'success'}
                    />
                    <span className="font-mono text-accent-cyan">
                      {(signal.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </td>

                {/* Confidence */}
                <td className="py-3 pr-4 text-right">
                  <span
                    className={cn(
                      'font-mono',
                      signal.confidence >= 0.7
                        ? 'text-status-success'
                        : signal.confidence >= 0.5
                        ? 'text-status-warning'
                        : 'text-status-error'
                    )}
                  >
                    {signal.confidence.toFixed(2)}
                  </span>
                </td>

                {/* Category */}
                <td className="py-3 pr-4 text-right">
                  <span className="px-2 py-1 rounded text-xs font-mono bg-bg-tertiary text-text-secondary border border-border-subtle">
                    {signal.category}
                  </span>
                </td>

                {/* Time */}
                <td className="py-3 pr-4 text-right text-xs text-text-muted font-mono">
                  {signal.timeAgo}
                </td>

                {/* Arrow */}
                <td className="py-3">
                  <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-accent-cyan transition-colors" />
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
