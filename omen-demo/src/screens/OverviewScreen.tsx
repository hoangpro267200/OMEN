import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { DURATION } from '../lib/animationConstants';
import { PipelineFlowDiagram } from '../components/widgets/PipelineFlowDiagram';
import { AnimatedPipelineFlow } from '../components/visualization/AnimatedPipelineFlow';
import { ProofCard } from '../components/widgets/ProofCard';
import { OverviewActivityFeed } from '../components/widgets/OverviewActivityFeed';
import { RealtimeActivityFeed } from '../components/widgets/RealtimeActivityFeed';
import { KPICard } from '../components/ui/KPICard';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ROUTES } from '../lib/routes';
import type { OverviewActivityItem } from '../lib/api/contracts';

export type OverviewState = 'loading' | 'empty' | 'error' | 'partial' | 'ready';

/** KPI shape for display (camelCase). Provided by OverviewPage from useOverviewStats(). */
export interface OverviewKpiData {
  signalsToday: number;
  signalsTrend: string;
  signalsTrendUp: boolean;
  hotPathOk: number;
  hotPathPct: string;
  duplicates: number;
  duplicatesSub: string;
  partitionsSealed: number;
  partitionsOpen: number;
  partitionsSub: string;
  lastReconcile: string;
  lastReconcileStatus: string;
}

export interface OverviewScreenProps {
  state?: OverviewState;
  kpis?: OverviewKpiData | null;
  activity?: OverviewActivityItem[];
  errorMessage?: string;
  onRetry?: () => void;
  /** When Live API fails, show "Chuyển sang Demo" and call this on click */
  onSwitchToDemo?: () => void;
}

const pageVariants = {
  initial: { opacity: 0, x: 8 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -8 },
};
const pageTransition = { duration: 0.15, ease: 'easeOut' as const };

/**
 * Overview Dashboard — Hero screen for judges.
 * Hero (PipelineFlowDiagram), KPI grid, Proof Pack, Activity Feed.
 */
export function OverviewScreen({
  state = 'ready',
  kpis = null,
  activity = [],
  errorMessage,
  onRetry,
  onSwitchToDemo,
}: OverviewScreenProps) {
  const isLoading = state === 'loading';
  const isEmpty = state === 'empty';
  const isError = state === 'error';
  const isPartial = state === 'partial';
  const showPartialBadge = isPartial;

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      className="min-h-full p-4 md:p-6"
    >
      {showPartialBadge && (
        <div className="mb-4">
          <Badge variant="PARTIAL">Some partitions open</Badge>
        </div>
      )}

      {isError && errorMessage && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-[var(--accent-red)]/50 bg-[var(--accent-red)]/10 px-4 py-3">
          <p className="min-w-0 flex-1 text-sm text-[var(--accent-red)]">{errorMessage}</p>
          <div className="flex shrink-0 items-center gap-2">
            {onSwitchToDemo && (
              <Button variant="primary" onClick={onSwitchToDemo}>
                Chuyển sang Demo
              </Button>
            )}
            {onRetry && (
              <Button variant="secondary" onClick={onRetry}>
                Thử lại
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Hero: Animated pipeline flow (packets) + static diagram */}
      <section className="mb-6">
        <AnimatedPipelineFlow />
      </section>
      <section className="mb-8">
        <PipelineFlowDiagram />
      </section>

      {/* KPI Grid: 5 cards */}
      <section className="mb-8">
        <h2 className="sr-only">Key metrics</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-28 rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] skeleton"
              />
            ))
          ) : isEmpty ? (
            <div className="col-span-full rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-8 text-center">
              <p className="text-[var(--text-secondary)]">No signals today</p>
              <p className="mt-1 text-sm text-[var(--text-muted)]">
                Run the Ingest Demo to see pipeline activity.
              </p>
              <Link to={ROUTES.ingestDemo} className="mt-4 inline-block">
                <Button variant="primary">Run Ingest Demo</Button>
              </Link>
            </div>
          ) : (
            kpis && (
              <>
                {[
                  { label: 'Signals Today', value: kpis.signalsToday, trend: kpis.signalsTrend, trendUp: kpis.signalsTrendUp, subtitle: undefined },
                  { label: 'Hot Path OK', value: kpis.hotPathOk, subtitle: kpis.hotPathPct },
                  { label: 'Duplicates', value: kpis.duplicates, subtitle: kpis.duplicatesSub },
                  { label: 'Partitions', value: `${kpis.partitionsSealed} / ${kpis.partitionsOpen}`, subtitle: kpis.partitionsSub },
                  { label: 'Last Reconcile', value: kpis.lastReconcile, subtitle: kpis.lastReconcileStatus },
                ].map((item, i) => (
                  <motion.div
                    key={item.label}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: i * (DURATION.stagger / 1000) }}
                  >
                    <KPICard
                      label={item.label}
                      value={item.value}
                      trend={i === 0 ? kpis.signalsTrend : undefined}
                      trendUp={i === 0 ? kpis.signalsTrendUp : undefined}
                      subtitle={item.subtitle}
                      size="hero"
                    />
                  </motion.div>
                ))}
              </>
            )
          )}
        </div>
      </section>

      {/* Proof Pack + Activity */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Proof cards: 3 on desktop, 2 on tablet, 1 on mobile */}
        <section className="lg:col-span-2">
          <h2 className="mb-4 font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Proof Pack
          </h2>
          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="h-48 rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] skeleton"
                />
              ))}
            </div>
          ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <ProofCard
              title="Ledger-first invariant"
              description="Write ledger → then hot path. No hot-only writes."
              snippet={
                <>
                  <span className="text-[var(--text-secondary)]">[4B len][4B crc][payload]</span>
                  <br />
                  <span className="text-[var(--text-muted)]">↓ fsync · POST /ingest</span>
                </>
              }
              actionLabel="View Emitter Code →"
              actionTo={ROUTES.ledgerProof}
            />
            <ProofCard
              title="Crash-tail safe"
              description="Partial frame → truncated. No corrupted records."
              snippet={
                <>
                  Write 3 → Crash → Read 2 ✓
                  <br />
                  <span className="text-[var(--text-muted)]">No corrupted records</span>
                </>
              }
              actionLabel="Run Crash Demo →"
              actionTo={ROUTES.ledgerProof}
            />
            <ProofCard
              title="Idempotent ingest"
              description="1×200, N×409, same ack_id. Duplicates rejected."
              snippet={
                <>
                  POST → 200 ✓
                  <br />
                  <span className="text-[var(--text-muted)]">POST same → 409 (dup)</span>
                </>
              }
              actionLabel="Run Dedupe Demo →"
              actionTo={ROUTES.ingestDemo}
            />
          </div>
          )}
        </section>

        {/* Activity: real-time WebSocket + overview feed */}
        <section className="flex flex-col gap-4">
          <RealtimeActivityFeed />
          {isLoading ? (
            <div className="h-64 rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] skeleton" />
          ) : (
            <OverviewActivityFeed events={activity} maxItems={10} className="h-full" />
          )}
        </section>
      </div>
    </motion.div>
  );
}
