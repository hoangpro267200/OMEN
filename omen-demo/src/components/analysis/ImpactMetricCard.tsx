import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { motion } from 'framer-motion';
import { ExternalLink } from 'lucide-react';
import { Card } from '../common/Card';
import { ChartContainer } from '../charts/ChartContainer';
import { AnimatedNumber } from '../common/AnimatedNumber';
import type { ProcessedImpactMetric } from '../../types/omen';
import { cn } from '../../lib/utils';

const METRIC_LABELS: Record<string, string> = {
  transit_time_increase: 'Thời gian di chuyển',
  fuel_consumption_increase: 'Chi phí nhiên liệu',
  freight_rate_pressure: 'Cước phí vận chuyển',
  insurance_premium_increase: 'Bảo hiểm',
};

interface ImpactMetricCardProps {
  metric: ProcessedImpactMetric;
  index?: number;
  className?: string;
}

export function ImpactMetricCard({ metric, index = 0, className }: ImpactMetricCardProps) {
  const label = METRIC_LABELS[metric.name] ?? metric.name.replace(/_/g, ' ');
  const chartData = useMemo(
    () =>
      metric.projection.map((v, i) => ({
        x: i,
        value: v,
      })),
    [metric]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: (index ?? 0) * 0.06 }}
    >
      <Card className={cn('p-4 flex flex-col', className)}>
        <div className="flex items-start justify-between gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
            {label}
          </span>
          {metric.evidence_source && (
            <a
              href="#"
              className="text-[var(--accent-cyan)] hover:underline flex items-center gap-0.5 text-xs"
              onClick={(e) => e.preventDefault()}
            >
              <ExternalLink className="w-3 h-3" />
              ↗ Nguồn
            </a>
          )}
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold font-mono tabular-nums text-[var(--text-primary)]">
            <AnimatedNumber value={metric.value} decimals={1} />
          </span>
          <span className="text-sm text-[var(--text-muted)]">{metric.unit}</span>
        </div>
        <div className="text-xs text-[var(--text-tertiary)] mt-1">
          Khoảng: {metric.uncertainty.lower.toFixed(1)} – {metric.uncertainty.upper.toFixed(1)} {metric.unit}
        </div>
        <ChartContainer height={48} minHeight={48} className="mt-3 w-full min-w-[120px]">
          {({ width, height }) => (
            <ResponsiveContainer width={width} height={height}>
              <AreaChart data={chartData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                <defs>
                  <linearGradient id={'area-' + metric.name} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="x" hide />
                <YAxis hide domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 6,
                  }}
                  formatter={(value: number | undefined) => [(value != null ? value.toFixed(1) : '') + ' ' + metric.unit, 'Projected']}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="var(--accent-cyan)"
                  fill={'url(#area-' + metric.name + ')'}
                  strokeWidth={1.5}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartContainer>
      </Card>
    </motion.div>
  );
}
