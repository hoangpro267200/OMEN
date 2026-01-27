import { motion } from 'framer-motion';

interface ProbabilityBarProps {
  probability: number;
  momentum: 'INCREASING' | 'DECREASING' | 'STABLE';
}

export function ProbabilityBar({ probability, momentum }: ProbabilityBarProps) {
  const color =
    probability > 0.7
      ? 'bg-red-500'
      : probability > 0.4
        ? 'bg-amber-500'
        : 'bg-emerald-500';

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-400">Probability</span>
        <span className="text-white font-mono">
          {(probability * 100).toFixed(0)}%
        </span>
      </div>
      <div className="h-3 bg-white/10 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${color} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width: `${probability * 100}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </div>
      <div className="flex items-center gap-1 text-xs text-zinc-500">
        {momentum === 'INCREASING' && (
          <span className="text-red-400">↑ Increasing</span>
        )}
        {momentum === 'DECREASING' && (
          <span className="text-emerald-400">↓ Decreasing</span>
        )}
        {momentum === 'STABLE' && <span>→ Stable</span>}
      </div>
    </div>
  );
}
