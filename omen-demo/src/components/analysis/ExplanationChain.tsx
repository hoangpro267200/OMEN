import { motion } from 'framer-motion';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card } from '../common/Card';
import type { ProcessedExplanationStep } from '../../types/omen';
import { cn } from '../../lib/utils';

interface ExplanationChainProps {
  steps: ProcessedExplanationStep[];
  traceId?: string;
  className?: string;
}

const statusIcon = (status: string) => {
  switch (status) {
    case 'passed':
      return <CheckCircle className="w-5 h-5 text-[var(--accent-green)] shrink-0" />;
    case 'failed':
      return <XCircle className="w-5 h-5 text-[var(--accent-red)] shrink-0" />;
    default:
      return <Loader2 className="w-5 h-5 text-[var(--accent-yellow)] shrink-0 animate-spin" />;
  }
};

export function ExplanationChain({ steps, traceId, className }: ExplanationChainProps) {
  return (
    <Card className={cn('p-6', className)} hover={false}>
      <div className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)] mb-4">
        Chuỗi giải thích
        {traceId && (
          <span className="font-mono text-[var(--text-muted)] ml-2">Trace: {traceId}</span>
        )}
      </div>
      <div className="space-y-0">
        {steps.map((step, i) => (
            <motion.div
              key={step.step_id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className="relative pl-8 pb-6 last:pb-0"
            >
              {i < steps.length - 1 && (
                <div
                  className="absolute left-[15px] top-8 bottom-0 w-0.5 bg-[var(--border-subtle)]"
                  aria-hidden
                />
              )}
              <div className="absolute left-0 top-0.5 flex items-center justify-center w-6 h-6 rounded-full bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] text-xs font-mono text-[var(--text-secondary)]">
                {step.step_id}
              </div>
              <div className="flex items-start gap-3">
                <div className="mt-0.5">{statusIcon(step.status)}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-[var(--text-primary)]">
                      {step.rule_name}
                    </span>
                    <span className="text-xs text-[var(--text-muted)] font-mono">
                      v{step.rule_version}
                    </span>
                    <span className="text-xs text-[var(--text-tertiary)] font-mono">
                      {step.processing_time_ms.toFixed(1)} ms
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">{step.reasoning}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden max-w-[120px]">
                      <motion.div
                        className="h-full bg-[var(--accent-cyan)] rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${step.confidence_contribution * 100}%` }}
                        transition={{ delay: 0.3 + i * 0.05, duration: 0.4 }}
                      />
                    </div>
                    <span className="text-xs text-[var(--text-muted)]">
                      Đóng góp {(step.confidence_contribution * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
        ))}
      </div>
    </Card>
  );
}
