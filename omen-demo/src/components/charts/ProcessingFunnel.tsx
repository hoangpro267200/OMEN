import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell, LabelList } from 'recharts';
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

/** Tooltip khi không có số: chỉ ghi ngắn "Đã dịch —" tránh tràn */
const TRANSLATED_NA_LABEL = 'Đã dịch —';

/** Stage colors from design system (CSS variables) */
const STAGE_FILLS: Record<string, string> = {
  'Raw events': 'var(--accent-blue)',
  Validated: 'var(--accent-green)',
  Translated: 'var(--accent-amber)',
  Signals: 'var(--status-late)',
};

interface FunnelItem {
  stage: string;
  value: number | null;
  fill: string;
}

interface ProcessingFunnelProps {
  data: FunnelItem[];
  className?: string;
}

export function ProcessingFunnel({ data, className }: ProcessingFunnelProps) {
  const displayData = useMemo(
    () =>
      (data ?? []).map((d) => {
        const val = d?.value != null ? Number(d.value) : 0;
        const fill = STAGE_FILLS[d?.stage ?? ''] ?? d?.fill ?? 'var(--text-muted)';
        const isTranslatedNa = d?.stage === 'Translated' && (d?.value == null || (typeof d.value === 'number' && Number.isNaN(d.value)));
        return {
          ...d,
          value: val,
          fill,
          stageLabel: STAGE_LABELS[d?.stage ?? ''] ?? d?.stage ?? '',
          valueForBar: val,
          valueLabel: isTranslatedNa ? '—' : val.toLocaleString(),
        };
      }),
    [data]
  );
  const firstVal = data[0]?.value;
  const total = firstVal != null && typeof firstVal === 'number' && firstVal > 0 ? firstVal : 1;

  return (
    <Card
      className={cn('overflow-hidden', className)}
      hover={false}
      style={{
        background: `linear-gradient(165deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%)`,
        border: '1px solid var(--border-subtle)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.35)',
      }}
    >
      <div className="p-5">
        <div className="text-xs font-semibold uppercase tracking-wider text-[var(--accent-amber)] mb-4">
          Quy trình xử lý
        </div>
        <div
          className="rounded-xl p-4"
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <ChartContainer height={160} minHeight={160} className="w-full min-w-[200px]">
            {({ width, height }) => (
              <ResponsiveContainer width={width} height={height}>
                <BarChart
                  data={displayData}
                  layout="vertical"
                  margin={{ left: 0, right: 52 }}
                >
                  <XAxis type="number" hide domain={[0, 'auto']} />
                  <YAxis
                    type="category"
                    dataKey="stageLabel"
                    tick={{ fill: 'var(--accent-amber)', fontSize: 13, fontWeight: 600 }}
                    width={100}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(28, 32, 40, 0.98)',
                      border: '1px solid rgba(253, 224, 71, 0.35)',
                      borderRadius: 8,
                      color: '#fde047',
                      boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
                    }}
                    labelStyle={{ color: '#fde047', fontWeight: 600 }}
                    itemStyle={{ color: '#fde047' }}
                    formatter={(value, _n, props) => {
                      const p = props?.payload as
                        | (FunnelItem & { stageLabel: string; valueForBar: number; value?: number }) | undefined;
                      if (!p) return ['—', ''];
                      const rawVal = p.value;
                      const isTranslatedNa =
                        p.stage === 'Translated' &&
                        (rawVal == null || (typeof rawVal === 'number' && Number.isNaN(rawVal)));
                      if (isTranslatedNa) {
                        return ['—', TRANSLATED_NA_LABEL];
                      }
                      const v = Number(value ?? p.valueForBar ?? 0);
                      const isFirst = data?.[0] && p.stage === data[0].stage;
                      const pct = isFirst ? '100' : ((v / total) * 100).toFixed(1);
                      return [`${v.toLocaleString()} (${pct}%)`, p.stageLabel ?? ''];
                    }}
                  />
                  <Bar dataKey="valueForBar" radius={[0, 8, 8, 0]} maxBarSize={36} minPointSize={6}>
                    <LabelList
                      dataKey="valueLabel"
                      position="right"
                      style={{ fill: 'var(--accent-amber)', fontSize: 12, fontWeight: 600 }}
                    />
                    {displayData.map((entry) => (
                      <Cell
                        key={entry.stage}
                        fill={entry.fill}
                        stroke="var(--border-active)"
                        strokeWidth={1}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartContainer>
        </div>
      </div>
    </Card>
  );
}
