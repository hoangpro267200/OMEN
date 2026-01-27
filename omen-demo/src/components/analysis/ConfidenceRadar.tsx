import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Card } from '../common/Card';
import { ChartContainer } from '../charts/ChartContainer';
import type { ConfidenceBreakdown } from '../../types/omen';
import { cn } from '../../lib/utils';

interface ConfidenceRadarProps {
  breakdown: ConfidenceBreakdown;
  overall: number;
  className?: string;
}

const AXIS_LABELS: Record<keyof ConfidenceBreakdown, string> = {
  liquidity: 'Thanh khoản',
  geographic: 'Địa lý',
  semantic: 'Ngữ nghĩa',
  anomaly: 'Bất thường',
  market_depth: 'Độ sâu TTr',
  source_reliability: 'Nguồn',
};

export function ConfidenceRadar({ breakdown, overall, className }: ConfidenceRadarProps) {
  const data = (Object.keys(breakdown) as (keyof ConfidenceBreakdown)[]).map((k) => ({
    axis: AXIS_LABELS[k],
    value: Math.round(breakdown[k] * 100),
    fullMark: 100,
  }));

  return (
    <Card className={cn('p-6 flex flex-col', className)} hover={false}>
      <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-3">
        Sự suy giảm niềm tin
      </div>
      <ChartContainer height={260} minHeight={200} className="w-full min-w-[200px] flex-shrink-0">
        {({ width, height }) => (
          <ResponsiveContainer width={width} height={height}>
            <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
            <defs>
              <linearGradient id="radarFillGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity={0.4} />
                <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <PolarGrid stroke="var(--border-subtle)" />
            <PolarAngleAxis
              dataKey="axis"
              tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
              tickLine={false}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name="Confidence"
              dataKey="value"
              stroke="var(--accent-cyan)"
              strokeWidth={2}
              fill="url(#radarFillGradient)"
              fillOpacity={1}
              dot={{ r: 4, fill: 'var(--accent-cyan)' }}
              isAnimationActive
              animationBegin={0}
              animationDuration={800}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-overlay)',
                border: '1px solid var(--border-default)',
                borderRadius: 8,
              }}
              labelStyle={{ color: 'var(--text-primary)' }}
              formatter={(value: number | undefined) => [
                `${value != null ? value : 0}%`,
                'Điểm',
              ]}
            />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </ChartContainer>
      <div className="text-center mt-2 pt-2 border-t border-[var(--border-subtle)]">
        <span className="text-lg font-bold font-mono text-[var(--accent-cyan)]">
          Tổng thể {(overall * 100).toFixed(0)}%
        </span>
      </div>
    </Card>
  );
}
