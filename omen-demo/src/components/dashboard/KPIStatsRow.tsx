import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Gauge,
  DollarSign,
  Zap,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  XCircle,
  Percent,
} from 'lucide-react';
import { Card } from '../common/Card';
import { AnimatedNumber } from '../common/AnimatedNumber';
import type { SystemStats } from '../../types/omen';
import { cn } from '../../lib/utils';

interface KPIItem {
  label: string;
  value: number | string;
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'flat';
  format?: (n: number) => string;
  suffix?: string;
  accent?: string;
}

interface KPIStatsRowProps {
  stats: SystemStats;
  className?: string;
}

export function KPIStatsRow({ stats, className }: KPIStatsRowProps) {
  const items: KPIItem[] = [
    {
      label: 'Tín hiệu chủ động',
      value: stats.active_signals,
      icon: Activity,
      trend: 'up',
      accent: 'text-[var(--accent-cyan)]',
    },
    {
      label: 'Cảnh báo khẩn cấp',
      value: stats.critical_alerts,
      icon: AlertTriangle,
      trend: 'up',
      accent: 'text-[var(--severity-critical)]',
    },
    {
      label: 'Độ tin cậy trung bình',
      value: stats.avg_confidence,
      icon: Gauge,
      format: (n) => `${(n * 100).toFixed(0)}%`,
      trend: 'flat',
      accent: 'text-[var(--accent-green)]',
    },
    {
      label: 'Mức độ rủi ro',
      value: stats.total_risk_exposure,
      icon: DollarSign,
      format: (n) => (n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${n.toLocaleString()}`),
      trend: 'up',
      accent: 'text-[var(--accent-orange)]',
    },
    {
      label: 'Sự kiện đã xử lý',
      value: stats.events_processed,
      icon: Zap,
      format: (n) => n.toLocaleString(),
      trend: 'up',
    },
    {
      label: 'Sự kiện bị loại',
      value: stats.events_rejected,
      icon: XCircle,
      format: (n) => n.toLocaleString(),
      trend: 'up',
      accent: 'text-[var(--text-muted)]',
    },
    {
      label: 'Tỉ lệ validation',
      value:
        stats.validation_rate != null
          ? stats.validation_rate
          : ('—' as string),
      icon: Percent,
      format: (n) => `${(n * 100).toFixed(0)}%`,
      trend: 'flat',
      accent: 'text-[var(--accent-green)]',
    },
    {
      label: 'Độ trễ',
      value: stats.system_latency_ms,
      icon: Clock,
      suffix: 'ms',
      trend: 'down',
      accent: 'text-[var(--accent-green)]',
    },
  ];

  const TrendIcon = { up: TrendingUp, down: TrendingDown, flat: Minus } as const;

  return (
    <div
      className={cn(
        'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-3',
        className
      )}
    >
      {items.map((item, i) => {
        const Icon = item.icon;
        const Trend = item.trend ? TrendIcon[item.trend] : Minus;
        const isNa = typeof item.value === 'string';
        const numVal = typeof item.value === 'number' ? item.value : 0;
        return (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card className="p-4" hover>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 text-[var(--text-tertiary)]">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="text-xs font-medium truncate">{item.label}</span>
                  </div>
                  <div
                    className={cn(
                      'mt-1 text-lg font-semibold font-mono tabular-nums',
                      item.accent ?? 'text-[var(--text-primary)]'
                    )}
                  >
                    {isNa ? (
                      <span title="Not available">—</span>
                    ) : typeof item.value === 'number' && (item.format || item.suffix) ? (
                      <AnimatedNumber
                        value={numVal}
                        format={item.format}
                        suffix={item.suffix}
                      />
                    ) : (
                      <AnimatedNumber value={numVal} decimals={0} />
                    )}
                  </div>
                </div>
                {item.trend && !isNa && (
                  <Trend
                    className={cn(
                      'w-4 h-4 shrink-0',
                      item.trend === 'up' && 'text-[var(--accent-green)]',
                      item.trend === 'down' && 'text-[var(--accent-red)]',
                      item.trend === 'flat' && 'text-[var(--text-muted)]'
                    )}
                  />
                )}
              </div>
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}
