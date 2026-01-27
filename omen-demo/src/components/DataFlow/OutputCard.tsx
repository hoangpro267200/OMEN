import { motion } from 'framer-motion';
import { Send } from 'lucide-react';
import { Card } from '../common/Card';

interface OutputCardProps {
  active: boolean;
  hasResult: boolean;
}

export function OutputCard({ active, hasResult }: OutputCardProps) {
  const highlight = active || hasResult;
  const colorClass = hasResult ? 'text-emerald-400' : 'text-zinc-400';

  return (
    <motion.div
      initial={{ opacity: 0.6, scale: 0.98 }}
      animate={{
        opacity: highlight ? 1 : 0.7,
        scale: highlight ? 1 : 0.98,
        boxShadow: hasResult
          ? '0 0 40px rgba(16, 185, 129, 0.2)'
          : active
            ? '0 0 40px rgba(59, 130, 246, 0.15)'
            : 'none',
      }}
      transition={{ duration: 0.3 }}
    >
      <Card glow={highlight} className="p-6 min-w-[160px] text-center">
        <Send className={`w-10 h-10 mx-auto mb-3 ${colorClass}`} />
        <div className="text-sm font-medium text-white">Output</div>
        <div className="text-xs text-zinc-500 mt-1">
          {hasResult ? 'OMEN signals' : 'Risk signals'}
        </div>
      </Card>
    </motion.div>
  );
}
