import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts';
import { useMemo } from 'react';
import { Card } from '../common/Card';
import { ChartContainer } from './ChartContainer';
import { cn } from '../../lib/utils';

const STAGE_LABELS: Record<string, string> = {
  'Raw events': 'Sự kiện thô',
  Validated: 'Đã xác thực',
  Translated: 'Đã dịch',
  Signals: 'Tín hiệu',
};

interface FunnelItem {
  stage: string;
  value: number;
  fill: string;
}

interface ProcessingFunnelProps {
  data: FunnelItem[];
  className?: string;
}

export function ProcessingFunnel({ data, className }: ProcessingFunnelProps) {
  const displayData = useMemo(
    () => data.map((d) => ({ ...d, stageLabel: STAGE_LABELS[d.stage] ?? d.stage })),
    [data]
  );
  return (
    <Card className={cn('p-6', className)} hover={false}>
      <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-4">
        Quy trình xử lý
      </div>
      <ChartContainer height={160} minHeight={160} className="w-full min-w-[200px]">
        {({ width, height }) => (
          <ResponsiveContainer width={width} height={height}>
            <BarChart data={displayData} layout="vertical" margin={{ left: 0, right: 24 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="stageLabel"
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                width={88}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 8,
                }}
                formatter={(value, _n, props) => {
                  const v = Number(value ?? 0);
                  const total = data[0]?.value ?? 1;
                  const p = props?.payload as (FunnelItem & { stageLabel: string }) | undefined;
                  const isFirst = p?.stage === data[0]?.stage;
                  const pct = isFirst ? '100' : (((v / total) * 100).toFixed(1));
                  return [v.toLocaleString() + ' (' + pct + '%)', p?.stageLabel ?? ''];
                }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={28}>
                {displayData.map((entry) => (
                  <Cell key={entry.stage} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartContainer>
    </Card>
  );
}
