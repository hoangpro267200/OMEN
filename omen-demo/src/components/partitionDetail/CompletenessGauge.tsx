import { motion } from 'framer-motion';
import { Check, Loader2, Play } from 'lucide-react';
import { cn } from '../../lib/utils';
import { DURATION, TRANSITION } from '../../lib/animationConstants';
import { MissingSignalsList } from './MissingSignalsList';
import type { ReconcileState } from './ReconcileRunner';

export interface CompletenessGaugeProps {
  ledgerCount: number;
  riskcastCount: number;
  missingCount: number;
  missingSignalIds: string[];
  replayedAcks: Record<string, string>;
  replayedCount: number;
  reconcileState: ReconcileState;
  onRunReconcile: () => void;
  canReconcile: boolean;
  reconcileDisabledReason?: string;
  durationMs?: number;
  className?: string;
}

/**
 * Hero: Ledger vs RiskCast completeness bars, missing list, Run Reconcile, success state.
 */
export function CompletenessGauge({
  ledgerCount,
  riskcastCount,
  missingCount,
  missingSignalIds,
  replayedAcks,
  replayedCount,
  reconcileState,
  onRunReconcile,
  canReconcile,
  reconcileDisabledReason,
  durationMs = 1200,
  className = '',
}: CompletenessGaugeProps) {
  const riskcastPct = ledgerCount > 0 ? Math.round((riskcastCount / ledgerCount) * 100) : 0;
  const missingPct = ledgerCount > 0 ? Math.round((missingCount / ledgerCount) * 100) : 0;

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6 md:p-8',
        className
      )}
    >
      <h2 className="mb-6 text-center font-mono text-sm font-medium uppercase tracking-wider text-[var(--text-muted)]">
        Completeness Check
      </h2>

      {/* Ledger bar — always 100% */}
      <div className="mb-6">
        <div className="mb-1 font-mono text-xs text-[var(--text-muted)]">
          Ledger (Source of Truth)
        </div>
        <div className="h-6 overflow-hidden rounded-[var(--radius-button)] bg-[var(--bg-tertiary)] border border-[var(--border-subtle)]">
          <motion.div
            className="h-full rounded-[var(--radius-button)] bg-[var(--accent-green)]"
            initial={{ width: 0 }}
            animate={{ width: '100%' }}
            transition={{ duration: DURATION.progress / 1000, delay: 0, ease: 'easeOut' }}
          />
        </div>
        <div className="mt-1 font-mono text-sm text-[var(--text-secondary)]">
          {ledgerCount} signals
        </div>
      </div>

      {/* RiskCast bar */}
      <div className="mb-6">
        <div className="mb-1 font-mono text-xs text-[var(--text-muted)]">
          RiskCast (Processed)
        </div>
        <div className="h-6 overflow-hidden rounded-[var(--radius-button)] bg-[var(--bg-tertiary)] border border-[var(--border-subtle)]">
          <motion.div
            className="h-full rounded-[var(--radius-button)] bg-[var(--accent-blue)]"
            initial={{ width: 0 }}
            animate={{ width: `${riskcastPct}%` }}
            transition={{ duration: DURATION.progress / 1000, delay: 0.1, ease: 'easeOut' }}
          />
        </div>
        <div className="mt-1 font-mono text-sm text-[var(--text-secondary)]">
          {riskcastCount} signals ({riskcastPct}%)
        </div>
      </div>

      {/* Missing bar */}
      <div className="mb-6">
        <div className="mb-1 font-mono text-xs text-[var(--text-muted)]">
          Missing
        </div>
        <div className="h-6 overflow-hidden rounded-[var(--radius-button)] bg-[var(--bg-tertiary)] border border-[var(--border-subtle)]">
          <motion.div
            className="h-full rounded-[var(--radius-button)] bg-[var(--accent-amber)]"
            initial={{ width: 0 }}
            animate={{ width: `${missingPct}%` }}
            transition={{ duration: DURATION.progress / 1000, delay: 0.2, ease: 'easeOut' }}
          />
        </div>
        <div className="mt-1 font-mono text-sm text-[var(--text-secondary)]">
          {missingCount} signals
        </div>
      </div>

      {/* Missing Signal IDs list */}
      {missingSignalIds.length > 0 && (
        <div className="mb-6">
          <MissingSignalsList signalIds={missingSignalIds} />
        </div>
      )}

      {/* Run Reconcile button */}
      <div className="mb-6 flex justify-center">
        <button
          type="button"
          data-demo-target="run-reconcile-button"
          onClick={onRunReconcile}
          disabled={!canReconcile || reconcileState === 'running'}
          title={!canReconcile ? reconcileDisabledReason : undefined}
          className={cn(
            'inline-flex items-center gap-2 rounded-[var(--radius-button)] border px-6 py-3 font-mono text-sm font-medium transition-colors',
            canReconcile && reconcileState !== 'running'
              ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)] text-white hover:opacity-90'
              : 'cursor-not-allowed border-[var(--border-subtle)] bg-[var(--bg-tertiary)] text-[var(--text-muted)]'
          )}
        >
          {reconcileState === 'running' ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Reconciling…
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run Reconcile
            </>
          )}
        </button>
      </div>

      {/* Success state */}
      {reconcileState === 'success' && replayedCount > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="rounded-[var(--radius-card)] border border-[var(--status-completed)]/50 bg-[var(--status-completed)]/10 p-4"
        >
          <div className="flex items-center gap-2 font-mono text-sm font-medium text-[var(--status-completed)]">
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={TRANSITION.bounce}
            >
              <Check className="h-5 w-5" />
            </motion.span>
            Reconcile Complete
          </div>
          <p className="mt-2 font-mono text-sm text-[var(--text-secondary)]">
            Replayed {replayedCount} signal{replayedCount !== 1 ? 's' : ''} in {(durationMs / 1000).toFixed(1)}s
          </p>
          {Object.entries(replayedAcks).length > 0 && (
            <ul className="mt-2 space-y-1 font-mono text-xs text-[var(--text-muted)]">
              {Object.entries(replayedAcks).map(([id, ack]) => (
                <li key={id}>
                  • {id} → ack_id: {ack}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 font-mono text-xs text-[var(--text-muted)]">
            Ledger: {ledgerCount} → RiskCast: {ledgerCount} → Missing: 0
          </p>
        </motion.div>
      )}
    </motion.section>
  );
}
