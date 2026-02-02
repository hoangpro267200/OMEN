import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronLeft } from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { CollapsibleSection } from '../components/partitionDetail/CollapsibleSection';
import { CompletenessGauge } from '../components/partitionDetail/CompletenessGauge';
import { ManifestPanel } from '../components/partitionDetail/ManifestPanel';
import { ReconcileHistoryTable } from '../components/partitionDetail/ReconcileHistoryTable';
import { HighwaterTracker } from '../components/partitionDetail/HighwaterTracker';
import { ROUTES } from '../lib/routes';
import { playSuccess } from '../lib/soundFx';
import type { ReconcileState } from '../components/partitionDetail/ReconcileRunner';
import type { PartitionDetailData } from '../data/partitionDetailMock';

const pageVariants = {
  initial: { opacity: 0, x: 8 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -8 },
};
const pageTransition = { duration: 0.15, ease: 'easeOut' as const };

function formatLastReconcile(iso: string | null): string {
  if (!iso) return 'Never';
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffM = Math.floor(diffMs / 60000);
    if (diffM < 60) return `${diffM}m ago`;
    const diffH = Math.floor(diffM / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return d.toLocaleDateString();
  } catch {
    return iso ?? '—';
  }
}

export interface PartitionDetailScreenProps {
  partitionDate: string;
  detail: PartitionDetailData | null;
  isLoading?: boolean;
  errorMessage?: string | null;
  onRunReconcile: () => void;
  isReconciling?: boolean;
}

/**
 * Partition Detail — "money screen": completeness gauge, Run Reconcile, three collapsible zones.
 * Data from props (usePartitionDetail + usePartitionDiff); reconcile via onRunReconcile.
 */
export function PartitionDetailScreen({
  partitionDate,
  detail,
  isLoading = false,
  errorMessage = null,
  onRunReconcile,
  isReconciling = false,
}: PartitionDetailScreenProps) {
  const [reconcileState, setReconcileState] = useState<ReconcileState>('idle');

  useEffect(() => {
    if (isReconciling) setReconcileState('running');
  }, [isReconciling]);

  useEffect(() => {
    if (!isReconciling && reconcileState === 'running') {
      setReconcileState('success');
      playSuccess();
      const t = setTimeout(() => setReconcileState('idle'), 2000);
      return () => clearTimeout(t);
    }
  }, [isReconciling, reconcileState]);

  const initialData = detail;
  const canReconcile =
    initialData &&
    ((initialData.type === 'MAIN' && initialData.status === 'SEALED') || initialData.type === 'LATE');
  const reconcileDisabledReason =
    initialData?.type === 'MAIN' && initialData?.status === 'OPEN'
      ? 'Main partition must be SEALED'
      : undefined;

  const showLateBadge =
    initialData?.type === 'LATE' && initialData?.status === 'OPEN';

  if (!partitionDate) {
    return (
      <motion.div
        variants={pageVariants}
        initial="initial"
        animate="animate"
        className="min-h-full p-4 md:p-6"
      >
        <p className="text-[var(--text-muted)]">Partition not found.</p>
        <Link to={ROUTES.partitions} className="mt-4 inline-block text-sm text-[var(--accent-blue)]">
          Back to Partitions
        </Link>
      </motion.div>
    );
  }

  if (isLoading && !initialData) {
    return (
      <motion.div
        variants={pageVariants}
        initial="initial"
        animate="animate"
        className="min-h-full p-4 md:p-6"
      >
        <div className="mb-6 h-8 w-48 rounded bg-[var(--bg-tertiary)] skeleton" />
        <div className="h-64 rounded bg-[var(--bg-tertiary)] skeleton" />
      </motion.div>
    );
  }

  if (errorMessage) {
    return (
      <motion.div
        variants={pageVariants}
        initial="initial"
        animate="animate"
        className="min-h-full p-4 md:p-6"
      >
        <p className="text-[var(--accent-red)]">{errorMessage}</p>
        <Link to={ROUTES.partitions} className="mt-4 inline-block text-sm text-[var(--accent-blue)]">
          Back to Partitions
        </Link>
      </motion.div>
    );
  }

  if (!initialData) {
    return (
      <motion.div
        variants={pageVariants}
        initial="initial"
        animate="animate"
        className="min-h-full p-4 md:p-6"
      >
        <p className="text-[var(--text-muted)]">Partition not found.</p>
        <Link to={ROUTES.partitions} className="mt-4 inline-block text-sm text-[var(--accent-blue)]">
          Back to Partitions
        </Link>
      </motion.div>
    );
  }

  const ledgerCount = initialData.ledgerCount;
  const riskcastCount = initialData.riskcastCount;
  const missingCount = initialData.missingSignalIds.length;
  const missingSignalIds = initialData.missingSignalIds;
  const replayedAcks = initialData.replayedAcks;
  const replayedCount = Object.keys(replayedAcks).length;

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      className="min-h-full p-4 md:p-6"
    >
      {/* Header */}
      <header className="mb-6">
        <Link
          to={ROUTES.partitions}
          className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        >
          <ChevronLeft className="h-4 w-4" /> Back to Partitions
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-medium text-[var(--text-primary)]">
              Partition: {partitionDate}
            </h1>
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">
              Complete and immutable. Last reconcile: {formatLastReconcile(initialData.lastReconcileAt)}.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={initialData.type === 'LATE' ? 'LATE' : 'default'}>
              {initialData.type}
            </Badge>
            <Badge variant={initialData.status === 'SEALED' ? 'SEALED' : 'OPEN'}>
              {initialData.status}
            </Badge>
            {showLateBadge && (
              <Badge variant="PARTIAL">Late partition open; may change</Badge>
            )}
            <button
              type="button"
              onClick={onRunReconcile}
              disabled={!canReconcile || reconcileState === 'running' || isReconciling || missingCount === 0}
              title={reconcileDisabledReason}
              className={`inline-flex items-center gap-2 rounded-[var(--radius-button)] border px-4 py-2 font-mono text-sm font-medium transition-colors ${
                canReconcile && reconcileState !== 'running' && missingCount > 0
                  ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)] text-white hover:opacity-90'
                  : 'cursor-not-allowed border-[var(--border-subtle)] bg-[var(--bg-tertiary)] text-[var(--text-muted)]'
              }`}
            >
              Run Reconcile
            </button>
          </div>
        </div>
      </header>

      {/* Hero: Completeness Gauge */}
      <section className="mb-8">
        <CompletenessGauge
          ledgerCount={ledgerCount}
          riskcastCount={riskcastCount}
          missingCount={missingCount}
          missingSignalIds={missingSignalIds}
          replayedAcks={replayedAcks}
          replayedCount={replayedCount}
          reconcileState={reconcileState}
          onRunReconcile={onRunReconcile}
          canReconcile={!!canReconcile}
          reconcileDisabledReason={reconcileDisabledReason}
          durationMs={1200}
        />
      </section>

      {/* Zone 1: Manifest & Segments */}
      <section className="mb-4">
        <CollapsibleSection title="Manifest & Segments" defaultOpen={false}>
          <ManifestPanel
            manifest={initialData.manifest}
            segments={initialData.segments}
          />
        </CollapsibleSection>
      </section>

      {/* Zone 2: Reconcile History */}
      <section className="mb-4">
        <CollapsibleSection title="Reconcile History" defaultOpen={false}>
          <ReconcileHistoryTable entries={initialData.reconcileHistory} />
        </CollapsibleSection>
      </section>

      {/* Zone 3: Highwater Tracker */}
      <section>
        <CollapsibleSection title="Highwater Tracker" defaultOpen={false}>
          <HighwaterTracker highwater={initialData.highwater} />
        </CollapsibleSection>
      </section>
    </motion.div>
  );
}
