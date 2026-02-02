/**
 * RulePerformance - Neural Command Center validation rule performance display
 * Features: Animated progress bars, rejection reasons breakdown
 */
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import { ProgressBar } from '../ui/ProgressBar';

interface Rule {
  name: string;
  passRate: number;
  avgTime: string;
}

interface RejectionReason {
  reason: string;
  percentage: number;
  color: string;
}

const DEFAULT_RULES: Rule[] = [
  { name: 'Liquidity Validation', passRate: 95, avgTime: '12ms' },
  { name: 'Anomaly Detection', passRate: 98, avgTime: '28ms' },
  { name: 'Semantic Relevance', passRate: 45, avgTime: '45ms' },
  { name: 'Geographic Relevance', passRate: 72, avgTime: '18ms' },
];

const DEFAULT_REJECTIONS: RejectionReason[] = [
  { reason: 'Low Liquidity', percentage: 45, color: 'bg-status-error' },
  { reason: 'Irrelevant Content', percentage: 35, color: 'bg-status-warning' },
  { reason: 'Anomaly Detected', percentage: 15, color: 'bg-accent-amber' },
  { reason: 'No Geographic Match', percentage: 5, color: 'bg-text-muted' },
];

export interface RulePerformanceProps {
  rules?: Rule[];
  rejections?: RejectionReason[];
  className?: string;
}

export function RulePerformance({
  rules = DEFAULT_RULES,
  rejections = DEFAULT_REJECTIONS,
  className,
}: RulePerformanceProps) {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Rule Pass Rates */}
      <div className="space-y-4">
        {rules.map((rule, index) => (
          <motion.div
            key={rule.name}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="space-y-2"
          >
            <div className="flex justify-between text-sm">
              <span className="text-text-primary">{rule.name}</span>
              <span className="text-text-muted font-mono">{rule.avgTime}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <ProgressBar value={rule.passRate} variant="dynamic" size="md" glow />
              </div>
              <span className="text-sm font-mono w-12 text-right text-text-secondary">
                {rule.passRate}%
              </span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Rejection Breakdown */}
      <div className="pt-4 border-t border-border-subtle">
        <h3 className="text-xs font-heading text-text-muted mb-3 uppercase tracking-wider">
          Rejection Reasons
        </h3>
        <div className="space-y-2">
          {rejections.map((item, index) => (
            <motion.div
              key={item.reason}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 + index * 0.1 }}
              className="flex items-center justify-between text-sm"
            >
              <div className="flex items-center gap-2">
                <span className={cn('w-2 h-2 rounded-full', item.color)} />
                <span className="text-text-secondary">{item.reason}</span>
              </div>
              <span className="font-mono text-text-muted">{item.percentage}%</span>
            </motion.div>
          ))}
        </div>

        {/* Visual breakdown bar */}
        <div className="mt-4 h-3 rounded-full overflow-hidden flex">
          {rejections.map((item) => (
            <motion.div
              key={item.reason}
              className={cn(item.color)}
              initial={{ width: 0 }}
              animate={{ width: `${item.percentage}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
