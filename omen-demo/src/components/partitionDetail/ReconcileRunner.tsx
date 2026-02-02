import type { ReactNode } from 'react';

export type ReconcileState = 'idle' | 'running' | 'success';

export interface ReconcileRunnerProps {
  state: ReconcileState;
  onRunReconcile: () => void;
  ledgerCount: number;
  riskcastCount: number;
  missingCount: number;
  missingSignalIds: string[];
  replayedAcks: Record<string, string>;
  replayedCount: number;
  durationMs?: number;
  canReconcile: boolean;
  reconcileDisabledReason?: string;
  children: ReactNode;
}

/**
 * Handles reconcile flow state; children render UI (CompletenessGauge).
 * Parent manages state (idle → running → success) and calls onRunReconcile.
 */
export function ReconcileRunner({
  state: _state,
  onRunReconcile: _onRunReconcile,
  ledgerCount: _ledgerCount,
  riskcastCount: _riskcastCount,
  missingCount: _missingCount,
  missingSignalIds: _missingSignalIds,
  replayedAcks: _replayedAcks,
  replayedCount: _replayedCount,
  canReconcile: _canReconcile,
  reconcileDisabledReason: _reconcileDisabledReason,
  children,
}: ReconcileRunnerProps) {
  return <>{children}</>;
}
