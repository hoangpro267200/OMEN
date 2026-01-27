import { motion } from 'framer-motion';
import { CheckCircle, XCircle } from 'lucide-react';
import type { ExplanationStep as StepType } from '../../types/omen';

interface ExplanationStepProps {
  step: StepType;
  index: number;
  isLast: boolean;
}

export function ExplanationStep({ step, index, isLast }: ExplanationStepProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.2 }}
      className="relative pl-8"
    >
      {!isLast && (
        <div className="absolute left-3 top-8 w-0.5 h-full bg-white/10 min-h-[24px]" />
      )}
      <div className="absolute left-0 top-1">
        {step.status === 'passed' ? (
          <CheckCircle className="w-6 h-6 text-emerald-500" />
        ) : (
          <XCircle className="w-6 h-6 text-red-500" />
        )}
      </div>
      <div className="pb-6">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{step.rule_name}</span>
          <span className="text-xs text-zinc-500">v{step.rule_version}</span>
        </div>
        <p className="mt-1 text-sm text-zinc-400">{step.reasoning}</p>
      </div>
    </motion.div>
  );
}
