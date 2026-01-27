import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Card } from '../common/Card';
import { ChartContainer } from './ChartContainer';
import { cn } from '../../lib/utils';

const SEVERITY_LABELS: Record<string, string> = {
  Critical: 'Phê bình',
  High: 'Cao',
  Medium: 'Trung bình',
  Low: 'Thấp',
};

interface DonutItem {
  name: string;
  value: number;
  fill: string;
}

interface SeverityDonutProps {
  data: DonutItem[];
  className?: string;
}

export function SeverityDonut({ data, className }: SeverityDonutProps) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const displayData = data.map((d) => ({ ...d, displayName: SEVERITY_LABELS[d.name] ?? d.name }));

  return (
    <Card className={cn('p-6', className)} hover={false}>
      <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-4">
        Phân bố mức độ nghiêm trọng
      </div>
      <div className="w-full min-w-[200px] relative" style={{ height: 192, minHeight: 192 }}>
        <ChartContainer height={192} minHeight={192} className="w-full h-full">
          {({ width, height }) => (
            <ResponsiveContainer width={width} height={height}>
              <PieChart>
                <Pie
                  data={displayData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="value"
                  nameKey="displayName"
                >
                  {displayData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} stroke="var(--bg-secondary)" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 8,
                  }}
                  formatter={(value: number | undefined, _name: string | undefined, props: { payload?: DonutItem }) => {
                    const v = value ?? 0;
                    const label = props?.payload ? (SEVERITY_LABELS[props.payload.name] ?? props.payload.name) : '';
                    return [v, `${label} (${total ? ((v / total) * 100).toFixed(0) : 0}%)`];
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 10 }}
                  formatter={(value) => <span style={{ color: 'var(--text-secondary)' }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartContainer>
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          aria-hidden
        >
          <span className="text-2xl font-bold font-mono text-[var(--text-primary)]">{total}</span>
        </div>
      </div>
    </Card>
  );
}
