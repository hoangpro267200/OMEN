import { motion } from 'framer-motion';
import { Layers } from 'lucide-react';
import { Card } from '../common/Card';

interface ProcessingCardProps {
  active: boolean;
  stage: number;
}

const stages = ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4'];

export function ProcessingCard({ active, stage }: ProcessingCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0.6, scale: 0.98 }}
      animate={{
        opacity: active ? 1 : 0.7,
        scale: active ? 1 : 0.98,
        boxShadow: active ? '0 0 40px rgba(59, 130, 246, 0.2)' : 'none',
      }}
      transition={{ duration: 0.3 }}
    >
      <Card glow={active} className="p-6 min-w-[180px] text-center">
        <Layers className="w-10 h-10 mx-auto mb-3 text-amber-400" />
        <div className="text-sm font-medium text-white">Processing</div>
        <div className="text-xs text-zinc-500 mt-1">
          {stage > 0 ? stages[stage - 1] : '—'}
        </div>
      </Card>
    </motion.div>
  );
}
