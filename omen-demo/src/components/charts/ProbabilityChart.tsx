import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Card } from '../common/Card';
import { ChartContainer } from './ChartContainer';
import { format, parseISO } from 'date-fns';
import type { TimePoint } from '../../data/mockTimeSeries';
import { cn } from '../../lib/utils';

interface ProbabilityChartProps {
  data: TimePoint[];
  className?: string;
}

export function ProbabilityChart({ data, className }: ProbabilityChartProps) {
  return (
    <Card className={cn('p-6', className)} hover={false}>
      <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-4">
        Diễn biến xác suất (24h)
      </div>
      <ChartContainer height={192} minHeight={192} className="w-full min-w-[200px]">
        {({ width, height }) => (
          <ResponsiveContainer width={width} height={height}>
            <AreaChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
              <defs>
                <linearGradient id="probArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
              <XAxis
                dataKey="time"
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                tickFormatter={(t) => {
                  try {
                    return format(parseISO(t), 'HH:mm');
                  } catch {
                    return t;
                  }
                }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                tickFormatter={(v) => v + '%'}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 8,
                }}
                labelFormatter={(t) => {
                  try {
                    return format(parseISO(t), 'PPp');
                  } catch {
                    return t;
                  }
                }}
                formatter={(value: number | undefined) => [(value != null ? value.toFixed(1) : 0) + '%', 'Xác suất']}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="var(--accent-cyan)"
                fill="url(#probArea)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </ChartContainer>
    </Card>
  );
}
