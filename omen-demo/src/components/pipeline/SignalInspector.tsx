/**
 * SignalInspector - Neural Command Center signal processing trace viewer
 * Features: Step-by-step processing trace, expandable details, timing info
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, Clock, ChevronDown, Copy } from 'lucide-react';
import { cn } from '../../lib/utils';
import { ProgressBar } from '../ui/ProgressBar';

interface ProcessingStep {
  id: number;
  name: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  reasoning: string;
  score?: number;
}

const MOCK_STEPS: ProcessingStep[] = [
  {
    id: 1,
    name: 'Ingestion',
    status: 'passed',
    duration: '10ms',
    input: { event_id: 'polymarket-677404', source: 'polymarket' },
    output: { raw_event: '...', input_hash: '7f8a9b0c1d2e3f4a' },
    reasoning: 'Raw event received and normalized successfully.',
  },
  {
    id: 2,
    name: 'Liquidity Validation',
    status: 'passed',
    duration: '45ms',
    input: { liquidity_usd: 150000, min_threshold: 1000 },
    output: { score: 0.95, status: 'PASSED' },
    reasoning: 'Liquidity $150,000 exceeds minimum threshold of $1,000.',
    score: 0.95,
  },
  {
    id: 3,
    name: 'Anomaly Detection',
    status: 'passed',
    duration: '30ms',
    input: { probability: 0.175, num_traders: 1200 },
    output: { risk_score: 0.15, status: 'PASSED' },
    reasoning: 'No anomalies detected. Probability within normal range.',
    score: 0.85,
  },
  {
    id: 4,
    name: 'Semantic Relevance',
    status: 'passed',
    duration: '60ms',
    input: { title: 'China x India military clash...', keywords: ['military', 'clash'] },
    output: { category: 'GEOPOLITICAL', relevance_score: 0.8 },
    reasoning: 'Matched geopolitical risk category with high relevance.',
    score: 0.8,
  },
  {
    id: 5,
    name: 'Enrichment',
    status: 'passed',
    duration: '55ms',
    input: { regions: ['china', 'india'], category: 'GEOPOLITICAL' },
    output: { affected_routes: 3, confidence_boost: 0.05 },
    reasoning: 'Geographic context added. Identified 3 affected shipping routes.',
    score: 0.9,
  },
];

export interface SignalInspectorProps {
  signalId?: string | null;
  steps?: ProcessingStep[];
  className?: string;
}

export function SignalInspector({
  signalId = 'OMEN-9C4860E23B54',
  steps = MOCK_STEPS,
  className,
}: SignalInspectorProps) {
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  if (!signalId) {
    return (
      <div className="h-[200px] flex items-center justify-center text-text-muted">
        <p>Select a signal from the pipeline to inspect processing details</p>
      </div>
    );
  }

  const totalTime = steps.reduce((sum, s) => sum + parseInt(s.duration), 0);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Signal Header */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary/50 border border-border-subtle">
        <div>
          <span className="text-xs text-text-muted block">Signal ID</span>
          <p className="font-mono text-accent-cyan">{signalId}</p>
        </div>
        <div>
          <span className="text-xs text-text-muted block">Trace ID</span>
          <p className="font-mono text-text-secondary">9c4860e23b540dc5</p>
        </div>
        <div>
          <span className="text-xs text-text-muted block">Total Time</span>
          <p className="font-mono text-status-success">{totalTime}ms</p>
        </div>
        <button
          className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors"
          title="Copy trace ID"
        >
          <Copy className="w-4 h-4 text-text-muted" />
        </button>
      </div>

      {/* Progress Timeline */}
      <div className="flex items-center justify-between px-4 py-2">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <motion.div
              className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold',
                step.status === 'passed' &&
                  'bg-status-success/20 text-status-success border border-status-success',
                step.status === 'failed' &&
                  'bg-status-error/20 text-status-error border border-status-error',
                step.status === 'skipped' &&
                  'bg-text-muted/20 text-text-muted border border-text-muted'
              )}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: index * 0.1 }}
            >
              {step.id}
            </motion.div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'w-12 h-0.5 mx-1',
                  step.status === 'passed' ? 'bg-status-success' : 'bg-text-muted/30'
                )}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Details */}
      <div className="space-y-2">
        {steps.map((step) => (
          <motion.div
            key={step.id}
            className="border border-border-subtle rounded-lg overflow-hidden"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Step Header */}
            <button
              onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
              className="w-full flex items-center justify-between p-3 hover:bg-bg-tertiary/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                {step.status === 'passed' ? (
                  <CheckCircle className="w-5 h-5 text-status-success" />
                ) : (
                  <XCircle className="w-5 h-5 text-status-error" />
                )}
                <span className="font-medium text-text-primary">
                  Step {step.id}: {step.name}
                </span>
              </div>
              <div className="flex items-center gap-4">
                {step.score !== undefined && (
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent-cyan transition-all"
                        style={{ width: `${step.score * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-text-muted">{step.score}</span>
                  </div>
                )}
                <span className="text-xs font-mono text-text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {step.duration}
                </span>
                <ChevronDown
                  className={cn(
                    'w-4 h-4 text-text-muted transition-transform',
                    expandedStep === step.id && 'rotate-180'
                  )}
                />
              </div>
            </button>

            {/* Expanded Content */}
            <AnimatePresence>
              {expandedStep === step.id && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-border-subtle"
                >
                  <div className="p-4 space-y-4 bg-bg-tertiary/20">
                    {/* Input/Output Grid */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h4 className="text-xs font-heading text-text-muted mb-2">INPUT</h4>
                        <pre className="text-xs font-mono bg-bg-primary p-3 rounded-lg overflow-auto max-h-24 text-text-secondary">
                          {JSON.stringify(step.input, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <h4 className="text-xs font-heading text-text-muted mb-2">OUTPUT</h4>
                        <pre className="text-xs font-mono bg-bg-primary p-3 rounded-lg overflow-auto max-h-24 text-text-secondary">
                          {JSON.stringify(step.output, null, 2)}
                        </pre>
                      </div>
                    </div>

                    {/* Reasoning */}
                    <div>
                      <h4 className="text-xs font-heading text-text-muted mb-2">REASONING</h4>
                      <p className="text-sm text-text-secondary italic bg-bg-primary/50 p-3 rounded-lg">
                        &ldquo;{step.reasoning}&rdquo;
                      </p>
                    </div>

                    {/* Score bar if present */}
                    {step.score !== undefined && (
                      <div>
                        <h4 className="text-xs font-heading text-text-muted mb-2">SCORE</h4>
                        <ProgressBar
                          value={step.score * 100}
                          variant="cyan"
                          showValue
                          glow
                        />
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
