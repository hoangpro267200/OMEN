import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { Card } from '../common/Card';
import { ChartContainer } from './ChartContainer';
import type { ProcessedImpactMetric } from '../../types/omen';
import { cn } from '../../lib/utils';

const METRIC_COLORS: Record<string, string> = {
  transit_time_increase: 'var(--accent-cyan)',
  fuel_consumption_increase: 'var(--accent-orange)',
  freight_rate_pressure: 'var(--accent-purple)',
  insurance_premium_increase: 'var(--accent-red)',
};

const METRIC_LABELS: Record<string, string> = {
  transit_time_increase: 'Di chuyển',
  fuel_consumption_increase: 'Nhiên liệu',
  freight_rate_pressure: 'Cước phí',
  insurance_premium_increase: 'Bảo hiểm',
};

interface ImpactProjectionChartProps {
  metrics: ProcessedImpactMetric[];
  className?: string;
}

export function ImpactProjectionChart({ metrics, className }: ImpactProjectionChartProps) {
  const days = metrics[0]?.projection?.length ?? 7;
  const chartData = Array.from({ length: days }, (_, i) => {
    const point: Record<string, number | string> = { day: i };
    metrics.forEach((m) => {
      point[METRIC_LABELS[m.name] ?? m.name] = m.projection?.[i] ?? 0;
    });
    return point;
  });

  return (
    <Card className={cn('p-6', className)} hover={false}>
      <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-4">
        Dự báo tác động (% thay đổi)
      </div>
      <ChartContainer height={224} minHeight={224} className="w-full min-w-[200px]">
        {({ width, height }) => (
          <ResponsiveContainer width={width} height={height}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
              <XAxis
                dataKey="day"
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                tickFormatter={(d) => `Ngày ${d}`}
              />
              <YAxis
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                tickFormatter={(v) => v + '%'}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 8,
                }}
                labelFormatter={(d) => `Ngày ${d}`}
                formatter={(value: number | undefined) => [(value != null ? value.toFixed(1) : '') + '%', '']}
              />
              <Legend
                wrapperStyle={{ fontSize: 10 }}
                formatter={(value) => <span style={{ color: 'var(--text-secondary)' }}>{value}</span>}
              />
              {metrics.slice(0, 4).map((m) => {
                const key = METRIC_LABELS[m.name] ?? m.name;
                const color = METRIC_COLORS[m.name] ?? 'var(--accent-blue)';
                return (
                  <Line
                    key={m.name}
                    type="monotone"
                    dataKey={key}
                    stroke={color}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        )}
      </ChartContainer>
    </Card>
  );
}
