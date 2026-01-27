import { ImpactMetricCard } from './ImpactMetricCard';
import type { ProcessedImpactMetric } from '../../types/omen';
import { cn } from '../../lib/utils';

interface ImpactMetricsGridProps {
  metrics: ProcessedImpactMetric[];
  className?: string;
}

export function ImpactMetricsGrid({ metrics, className }: ImpactMetricsGridProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4',
        className
      )}
    >
      {metrics.map((m, i) => (
        <ImpactMetricCard key={m.name} metric={m} index={i} />
      ))}
    </div>
  );
}
