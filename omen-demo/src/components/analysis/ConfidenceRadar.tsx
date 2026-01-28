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
  breakdown: ConfidenceBreakdown | null;
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
  const hasBreakdown = breakdown != null;

  if (!hasBreakdown || !breakdown) {
    return (
      <Card className={cn('p-6 flex flex-col', className)} hover={false}>
        <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-3">
          Sự tin cậy
        </div>
        <div className="flex flex-col items-center justify-center h-48">
          <div className="relative w-32 h-32">
            <svg className="w-full h-full" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" fill="none" stroke="var(--bg-hover)" strokeWidth="8" />
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="var(--accent-cyan)"
                strokeWidth="8"
                strokeDasharray={`${Math.min(1, Math.max(0, overall)) * 251.2} 251.2`}
                strokeLinecap="round"
                transform="rotate(-90 50 50)"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-[var(--text-primary)]">
                {Math.round(overall * 100)}%
              </span>
            </div>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-4 text-center">
            Chi tiết độ tin cậy không khả dụng.
            <br />
            Hiển thị điểm tổng hợp.
          </p>
        </div>
      </Card>
    );
  }

  const data = (Object.keys(breakdown) as (keyof ConfidenceBreakdown)[]).map((k) => ({
    axis: AXIS_LABELS[k],
    value: Math.round(breakdown[k] * 100),
    fullMark: 100,
  }));

  return (
    <Card className={cn('p-6 flex flex-col', className)} hover={false}>
      <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-3">
        Sự tin cậy — Chi tiết
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
