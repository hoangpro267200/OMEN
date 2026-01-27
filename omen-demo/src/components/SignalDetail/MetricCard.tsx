import { motion } from 'framer-motion';
import { AnimatedNumber } from '../common/AnimatedNumber';
import type { ImpactMetric } from '../../types/omen';

interface MetricCardProps {
  metric: ImpactMetric;
  delay?: number;
}

export function MetricCard({ metric, delay = 0 }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="p-4 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 transition-colors"
    >
      <div className="text-xs text-zinc-500 uppercase tracking-wider">
        {metric.name.replace(/_/g, ' ')}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <AnimatedNumber
          value={metric.value}
          className="text-2xl font-bold text-white"
        />
        <span className="text-zinc-400">{metric.unit}</span>
      </div>
      {metric.uncertainty != null && (
        <div className="mt-1 text-xs text-zinc-500">
          Range: {metric.uncertainty.lower} - {metric.uncertainty.upper}{' '}
          {metric.unit}
        </div>
      )}
      {metric.evidence_source != null && (
        <div className="mt-2 text-xs text-blue-400 truncate" title={metric.evidence_source}>
          Evidence: {metric.evidence_source}
        </div>
      )}
    </motion.div>
  );
}
