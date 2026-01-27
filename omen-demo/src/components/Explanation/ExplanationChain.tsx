import { motion } from 'framer-motion';
import { ExplanationStep } from './ExplanationStep';
import { Card } from '../common/Card';
import type { ExplanationChain as ChainType } from '../../types/omen';

interface ExplanationChainProps {
  chain: ChainType;
}

export function ExplanationChain({ chain }: ExplanationChainProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-12"
    >
      <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
        <span className="w-1 h-6 bg-blue-500 rounded-full" />
        Explanation chain
      </h2>
      <Card className="p-6">
        <div className="text-xs text-zinc-500 font-mono mb-4">
          Trace: {chain.trace_id}
        </div>
        <div className="space-y-0">
          {chain.steps.map((step, i) => (
            <ExplanationStep
              key={step.step_id}
              step={step}
              index={i}
              isLast={i === chain.steps.length - 1}
            />
          ))}
        </div>
      </Card>
    </motion.section>
  );
}
