import { motion } from 'framer-motion';
import { Card } from '../common/Card';
import { ProbabilityBar } from './ProbabilityBar';
import { MetricCard } from './MetricCard';
import { BadgeRow } from './BadgeRow';
import type { OmenSignal } from '../../types/omen';

interface SignalCardProps {
  signal: OmenSignal;
}

export function SignalCard({ signal }: SignalCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card glow className="p-6 md:p-8">
        <div className="mb-6">
          <div className="text-xs text-zinc-500 font-mono mb-1">
            {signal.signal_id}
          </div>
          <h3 className="text-xl font-semibold text-white leading-tight">
            {signal.title}
          </h3>
        </div>

        <div className="mb-6">
          <ProbabilityBar
            probability={signal.current_probability}
            momentum={signal.probability_momentum}
          />
        </div>

        <div className="mb-6">
          <BadgeRow
            confidenceLevel={signal.confidence_level}
            severityLabel={signal.severity_label}
            isActionable={signal.is_actionable}
            urgency={signal.urgency}
          />
        </div>

        <div>
          <div className="text-sm font-medium text-zinc-400 mb-3">
            Impact metrics
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {signal.key_metrics.map((m, i) => (
              <MetricCard key={m.name} metric={m} delay={i * 0.1} />
            ))}
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
