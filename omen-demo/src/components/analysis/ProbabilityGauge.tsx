import { motion } from 'framer-motion';
import { Card } from '../common/Card';
import { AnimatedNumber } from '../common/AnimatedNumber';
import { cn } from '../../lib/utils';

interface ProbabilityGaugeProps {
  probability: number;
  momentum: 'INCREASING' | 'DECREASING' | 'STABLE';
  historyMin?: number;
  historyMax?: number;
  isCritical?: boolean;
  className?: string;
}

const MOMENTUM_CONFIG = {
  INCREASING: { label: 'TĂNG DẦN', className: 'bg-[var(--danger)]/20 text-[var(--danger)]' },
  DECREASING: { label: 'GIẢM', className: 'bg-[var(--success)]/20 text-[var(--success)]' },
  STABLE: { label: 'ỔN ĐỊNH', className: 'bg-[var(--text-muted)]/20 text-[var(--text-tertiary)]' },
};

export function ProbabilityGauge({
  probability,
  momentum,
  historyMin: _historyMin = 0,
  historyMax: _historyMax = 1,
  isCritical,
  className,
}: ProbabilityGaugeProps) {
  const pct = probability * 100;
  const config = MOMENTUM_CONFIG[momentum];

  return (
    <Card
      className={cn(
        'p-6 flex flex-col items-center justify-center min-h-[240px]',
        isCritical && 'ring-1 ring-[var(--severity-critical)]/50 pulse-critical',
        className
      )}
      hover={false}
    >
      <svg className="absolute inset-0 w-full h-full rounded-xl overflow-visible" aria-hidden>
        <defs>
          <linearGradient id="prob-gauge-ok" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--accent-cyan)" />
            <stop offset="100%" stopColor="var(--accent-blue)" />
          </linearGradient>
          <linearGradient id="prob-gauge-warn" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--accent-yellow)" />
            <stop offset="100%" stopColor="var(--accent-orange)" />
          </linearGradient>
          <linearGradient id="prob-gauge-danger" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--accent-orange)" />
            <stop offset="100%" stopColor="var(--severity-critical)" />
          </linearGradient>
        </defs>
      </svg>
      <div className="relative flex flex-col items-center">
        <div className="relative w-40 h-40">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="var(--bg-tertiary)"
              strokeWidth="8"
            />
            <motion.circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke={pct >= 70 ? 'var(--severity-critical)' : pct >= 50 ? 'var(--accent-orange)' : 'var(--accent-cyan)'}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray="283"
              initial={{ strokeDashoffset: 283 }}
              animate={{ strokeDashoffset: 100 - (pct / 100) * 283 }}
              transition={{ duration: 1, type: 'spring', stiffness: 50 }}
            />
          </svg>
        </div>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold font-mono tabular-nums text-[var(--text-primary)]">
            <AnimatedNumber value={pct} decimals={0} suffix="%" />
          </span>
          <motion.span
            className={cn(
              'mt-1 text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded',
              config.className
            )}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {config.label}
          </motion.span>
        </div>
      </div>
    </Card>
  );
}
