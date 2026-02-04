/**
 * SignalDeepDive - Signal 360 View
 * 
 * Complete signal analysis screen featuring:
 * - Signal overview with key metrics
 * - Probability gauge and confidence breakdown
 * - Geographic & temporal context
 * - Data lineage visualization
 * - Explanation chain (audit trail)
 * - Raw JSON viewer
 * 
 * Uses unified data hooks for seamless demo/live mode switching.
 */

import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  ExternalLink,
  Share2,
  Download,
  Bell,
  CheckCircle,
  AlertTriangle,
  Clock,
  MapPin,
  Calendar,
  Zap,
  Shield,
  FileText,
  Truck,
  GitBranch,
  Code,
  Activity,
  Copy,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useSignalDetail } from '../hooks/useSignalData';
import { useDataMode } from '../context/DataModeContext';

// Components
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { ExplainPopover } from '../components/ui/ExplainPopover';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ProgressBar } from '../components/ui/ProgressBar';
import { LineageGraph, LineageDetailPanel, type LineageNodeData } from '../components/lineage';

// ============================================================================
// TYPES
// ============================================================================

type TabId = 'evidence' | 'lineage' | 'history' | 'raw';

interface ExplanationStep {
  step_id: number;
  rule_name: string;
  rule_version?: string;
  input_summary?: Record<string, unknown>;
  output_summary?: Record<string, unknown>;
  reasoning?: string;
  confidence_contribution?: number;
  duration_ms?: number;
  status?: 'PASSED' | 'FAILED' | 'SKIPPED';
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export interface SignalDeepDiveProps {
  className?: string;
}

export function SignalDeepDive({ className }: SignalDeepDiveProps) {
  const { signalId } = useParams<{ signalId: string }>();
  const navigate = useNavigate();
  const { state: dataMode } = useDataModeSafe();

  // Fetch signal data using unified hook (works in demo AND live mode)
  const {
    data: signal,
    isLoading,
    isError,
    error,
    dataSource,
    refetch,
  } = useSignalDetail(signalId);

  // Local state
  const [activeTab, setActiveTab] = useState<TabId>('evidence');
  const [selectedLineageNode, setSelectedLineageNode] = useState<{
    id: string;
    data: LineageNodeData;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  // Copy handler
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // -------------------------------------------------------------------------
  // Loading State
  // -------------------------------------------------------------------------

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <LoadingSpinner size="lg" />
          <p className="text-[var(--text-muted)]">Loading signal details...</p>
          <p className="text-xs text-[var(--text-muted)]">ID: {signalId}</p>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Error State
  // -------------------------------------------------------------------------

  if (isError || !signal) {
    return (
      <div className="p-6">
        <ErrorState
          title="Signal Not Found"
          message={error?.message || `Could not load signal ${signalId}`}
          type="not-found"
          action={{
            label: 'Retry',
            onClick: () => refetch(),
          }}
          secondaryAction={{
            label: 'Go Back',
            onClick: () => navigate(-1),
          }}
          showHomeLink
          errorDetails={error?.stack}
        />
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className={cn('p-6 space-y-6', className)}>
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5 text-[var(--text-muted)]" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-display font-bold text-[var(--text-primary)] tracking-tight">
                Signal Analysis
              </h1>
              {/* Data Source Badge */}
              <span
                className={cn(
                  'px-2 py-0.5 rounded text-[10px] font-mono',
                  dataSource === 'live'
                    ? 'bg-[var(--status-success)]/20 text-[var(--status-success)]'
                    : 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)]'
                )}
              >
                {dataSource.toUpperCase()}
              </span>
            </div>
            <p className="text-[var(--accent-cyan)] font-mono text-sm flex items-center gap-2">
              {signal.signal_id}
              <button
                onClick={() => handleCopy(signal.signal_id)}
                className="p-0.5 rounded hover:bg-[var(--bg-tertiary)]"
                title="Copy ID"
              >
                {copied ? (
                  <CheckCircle className="w-3 h-3 text-[var(--status-success)]" />
                ) : (
                  <Copy className="w-3 h-3 text-[var(--text-muted)]" />
                )}
              </button>
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors text-[var(--text-muted)]"
            title="Subscribe to updates"
          >
            <Bell className="w-5 h-5" />
          </button>
          <button
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors text-[var(--text-muted)]"
            title="Share signal"
          >
            <Share2 className="w-5 h-5" />
          </button>
          <button
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors text-[var(--text-muted)]"
            title="Download"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>
      </motion.div>

      {/* Top Row - Overview and Gauges */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Signal Overview */}
        <div className="lg:col-span-5">
          <GlassCard className="p-6 h-full" delay={0.1}>
            <div className="flex items-center justify-between mb-4">
              <GlassCardTitle>Signal Overview</GlassCardTitle>
              <StatusBadge status={signal.status} />
            </div>

            <h2 className="text-lg font-medium text-[var(--text-primary)] mb-4">{signal.title}</h2>

            {signal.description && (
              <p className="text-sm text-[var(--text-muted)] mb-4">{signal.description}</p>
            )}

            <div className="flex items-center gap-3 mb-4">
              <span className="px-2 py-1 rounded text-xs font-mono bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-subtle)]">
                {signal.category}
              </span>
              {signal.signal_type && (
                <span className="px-2 py-1 rounded text-xs font-mono bg-[var(--bg-tertiary)] text-[var(--text-muted)]">
                  {signal.signal_type}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm pt-4 border-t border-[var(--border-subtle)]">
              <div>
                <span className="text-[var(--text-muted)]">Observed</span>
                <p className="text-[var(--text-primary)] font-mono">
                  {new Date(signal.observed_at).toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-[var(--text-muted)]">Generated</span>
                <p className="text-[var(--text-primary)] font-mono">
                  {new Date(signal.generated_at).toLocaleString()}
                </p>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Probability Gauge */}
        <div className="lg:col-span-3">
          <GlassCard className="p-6 h-full flex flex-col items-center justify-center" delay={0.15}>
            <GlassCardTitle className="self-start mb-4">Probability</GlassCardTitle>
            <ExplainPopover
              fieldId="signal.probability"
              value={signal.probability}
              context={{
                eventTime: signal.observed_at,
                computeTime: signal.generated_at,
              }}
            >
              <div className="relative w-36 h-36">
                <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="var(--bg-tertiary)"
                    strokeWidth="8"
                  />
                  <motion.circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke={
                      signal.probability >= 0.7
                        ? 'var(--status-error)'
                        : signal.probability >= 0.5
                        ? 'var(--accent-amber)'
                        : 'var(--accent-cyan)'
                    }
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray="283"
                    initial={{ strokeDashoffset: 283 }}
                    animate={{ strokeDashoffset: 283 - signal.probability * 283 }}
                    transition={{ duration: 1, type: 'spring', stiffness: 50 }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold font-mono tabular-nums text-[var(--text-primary)]">
                    {(signal.probability * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </ExplainPopover>
          </GlassCard>
        </div>

        {/* Confidence Breakdown */}
        <div className="lg:col-span-4">
          <GlassCard className="p-6 h-full" delay={0.2}>
            <GlassCardTitle>Confidence Breakdown</GlassCardTitle>
            <div className="mt-4 space-y-4">
              {/* Overall Score */}
              <ExplainPopover
                fieldId="signal.confidence_score"
                value={signal.confidence_score}
                context={{
                  computeTime: signal.generated_at,
                  ruleVersion: signal.ruleset_version,
                  quality: signal.confidence_score,
                }}
              >
                <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-tertiary)]/50">
                  <span className="text-sm text-[var(--text-muted)]">Overall Score</span>
                  <span
                    className={cn(
                      'text-2xl font-bold font-mono',
                      signal.confidence_score >= 0.7
                        ? 'text-[var(--status-success)]'
                        : signal.confidence_score >= 0.4
                        ? 'text-[var(--accent-amber)]'
                        : 'text-[var(--status-error)]'
                    )}
                  >
                    {signal.confidence_score.toFixed(2)}
                  </span>
                </div>
              </ExplainPopover>

              {/* Breakdown */}
              {signal.confidence_factors && (
                <div className="space-y-3 pt-4 border-t border-[var(--border-subtle)]">
                  {Object.entries(signal.confidence_factors).map(([key, value]) => (
                    <div key={key} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-[var(--text-muted)] capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="font-mono text-[var(--text-secondary)]">
                          {typeof value === 'number' ? value.toFixed(2) : String(value)}
                        </span>
                      </div>
                      <ProgressBar
                        value={typeof value === 'number' ? value * 100 : 0}
                        variant="cyan"
                        size="sm"
                      />
                    </div>
                  ))}
                </div>
              )}

              {/* Level Badge */}
              <div className="text-center pt-2">
                <span
                  className={cn(
                    'px-3 py-1 rounded-full text-xs font-medium',
                    signal.confidence_level === 'HIGH'
                      ? 'bg-[var(--status-success)]/20 text-[var(--status-success)]'
                      : signal.confidence_level === 'MEDIUM'
                      ? 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)]'
                      : 'bg-[var(--status-error)]/20 text-[var(--status-error)]'
                  )}
                >
                  {signal.confidence_level} CONFIDENCE
                </span>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Geographic & Temporal Context */}
      <GlassCard className="p-6" delay={0.25}>
        <GlassCardTitle icon={<MapPin className="w-4 h-4" />}>Context</GlassCardTitle>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Geographic */}
          <div>
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-3">
              <MapPin className="w-3 h-3" />
              Geographic
            </div>
            {signal.geographic?.regions && signal.geographic.regions.length > 0 && (
              <div className="mb-3">
                <div className="text-[10px] text-[var(--text-muted)] mb-2">REGIONS</div>
                <div className="flex flex-wrap gap-2">
                  {signal.geographic.regions.map((region: string) => (
                    <span
                      key={region}
                      className="px-3 py-1 rounded-full bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)] text-sm"
                    >
                      {region}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {signal.geographic?.chokepoints && signal.geographic.chokepoints.length > 0 && (
              <div>
                <div className="text-[10px] text-[var(--text-muted)] mb-2">CHOKEPOINTS</div>
                <div className="flex flex-wrap gap-2">
                  {signal.geographic.chokepoints.map((cp: string) => (
                    <span
                      key={cp}
                      className="px-3 py-1 rounded-full bg-[var(--status-error)]/20 text-[var(--status-error)] text-sm flex items-center gap-1"
                    >
                      <AlertTriangle className="w-3 h-3" />
                      {cp}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Temporal */}
          <div>
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-3">
              <Calendar className="w-3 h-3" />
              Temporal
            </div>
            <div className="space-y-3 text-sm">
              {signal.temporal?.event_horizon && (
                <div className="flex justify-between p-2 rounded bg-[var(--bg-tertiary)]/50">
                  <span className="text-[var(--text-muted)]">Event Horizon</span>
                  <span className="text-[var(--text-primary)] font-mono">
                    {new Date(signal.temporal.event_horizon).toLocaleDateString()}
                  </span>
                </div>
              )}
              {signal.temporal?.signal_freshness && (
                <div className="flex justify-between p-2 rounded bg-[var(--bg-tertiary)]/50">
                  <span className="text-[var(--text-muted)]">Freshness</span>
                  <span className="text-[var(--accent-cyan)] font-mono">
                    {signal.temporal.signal_freshness}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Tabs */}
      <div className="border-b border-[var(--border-subtle)]">
        <div className="flex gap-1">
          {(
            [
              { id: 'evidence', label: 'Evidence Chain', icon: <Shield className="w-4 h-4" /> },
              { id: 'lineage', label: 'Data Lineage', icon: <GitBranch className="w-4 h-4" /> },
              { id: 'history', label: 'History', icon: <Clock className="w-4 h-4" /> },
              { id: 'raw', label: 'Raw Data', icon: <Code className="w-4 h-4" /> },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
                activeTab === tab.id
                  ? 'text-[var(--accent-cyan)] border-[var(--accent-cyan)] bg-[var(--accent-cyan)]/5'
                  : 'text-[var(--text-muted)] border-transparent hover:text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="min-h-[400px]"
        >
          {/* Evidence Tab */}
          {activeTab === 'evidence' && (
            <GlassCard className="p-6">
              <ExplanationChainDisplay steps={signal.explanation_chain?.steps || []} />
            </GlassCard>
          )}

          {/* Lineage Tab */}
          {activeTab === 'lineage' && (
            <div className="relative">
              <GlassCard className="p-4">
                <LineageGraph
                  signalId={signal.signal_id}
                  signalData={signal}
                  onNodeClick={(id, data) => setSelectedLineageNode({ id, data })}
                  className="h-[450px]"
                />
              </GlassCard>
              <LineageDetailPanel
                nodeId={selectedLineageNode?.id || null}
                nodeData={selectedLineageNode?.data || null}
                onClose={() => setSelectedLineageNode(null)}
              />
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <GlassCard className="p-6">
              <div className="text-center text-[var(--text-muted)] py-16">
                <Activity className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="text-lg mb-2">Signal History</p>
                <p className="text-sm">Historical changes and probability trends will be displayed here.</p>
              </div>
            </GlassCard>
          )}

          {/* Raw Tab */}
          {activeTab === 'raw' && (
            <GlassCard className="p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-[var(--text-muted)] font-mono">signal.json</span>
                <button
                  onClick={() => handleCopy(JSON.stringify(signal, null, 2))}
                  className="flex items-center gap-1 px-2 py-1 rounded text-xs text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)]"
                >
                  <Copy className="w-3 h-3" />
                  Copy
                </button>
              </div>
              <pre className="text-xs font-mono text-[var(--text-secondary)] overflow-auto max-h-[500px] p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-subtle)]">
                {JSON.stringify(signal, null, 2)}
              </pre>
            </GlassCard>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Evidence Sources */}
      {signal.evidence && signal.evidence.length > 0 && (
        <GlassCard className="p-6" delay={0.5}>
          <GlassCardTitle icon={<FileText className="w-4 h-4" />}>Evidence Sources</GlassCardTitle>
          <div className="mt-4 space-y-3">
            {signal.evidence.map((ev: { source: string; source_type: string; value?: string; url?: string }, idx: number) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-[var(--bg-tertiary)]/30 border border-[var(--border-subtle)]"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-[var(--text-primary)]">{ev.source}</span>
                  <span className="text-xs text-[var(--text-muted)]">{ev.source_type}</span>
                </div>
                {ev.value && (
                  <p className="text-sm text-[var(--text-secondary)] mb-2">{ev.value}</p>
                )}
                {ev.url && (
                  <a
                    href={ev.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-[var(--accent-cyan)] hover:underline"
                  >
                    View Source <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  );
}

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    ACTIVE: {
      bg: 'bg-[var(--status-success)]/20',
      text: 'text-[var(--status-success)]',
      icon: <Zap className="w-3 h-3" />,
    },
    MONITORING: {
      bg: 'bg-[var(--accent-amber)]/20',
      text: 'text-[var(--accent-amber)]',
      icon: <Clock className="w-3 h-3" />,
    },
    CANDIDATE: {
      bg: 'bg-[var(--text-muted)]/20',
      text: 'text-[var(--text-muted)]',
      icon: <Shield className="w-3 h-3" />,
    },
    DEGRADED: {
      bg: 'bg-[var(--status-error)]/20',
      text: 'text-[var(--status-error)]',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
    ARCHIVED: {
      bg: 'bg-[var(--text-muted)]/20',
      text: 'text-[var(--text-muted)]',
      icon: <FileText className="w-3 h-3" />,
    },
  };

  const { bg, text, icon } = config[status] || config.CANDIDATE;

  return (
    <span className={cn('flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium', bg, text)}>
      {icon}
      {status}
    </span>
  );
}

function ExplanationChainDisplay({ steps }: { steps: ExplanationStep[] }) {
  if (!steps || steps.length === 0) {
    return (
      <div className="text-center text-[var(--text-muted)] py-12">
        <Shield className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p>No explanation chain available</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-4 mb-4 p-3 bg-[var(--bg-tertiary)]/50 rounded-lg">
        <div>
          <span className="text-xs text-[var(--text-muted)]">Total Steps</span>
          <p className="font-mono text-[var(--text-primary)]">{steps.length}</p>
        </div>
        <div>
          <span className="text-xs text-[var(--text-muted)]">Total Time</span>
          <p className="font-mono text-[var(--status-success)]">
            {steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0)}ms
          </p>
        </div>
      </div>

      {/* Steps */}
      {steps.map((step, index) => (
        <motion.div
          key={step.step_id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.05 }}
          className="p-4 rounded-lg bg-[var(--bg-tertiary)]/30 border border-[var(--border-subtle)]"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border',
                  step.status === 'PASSED' || !step.status
                    ? 'bg-[var(--status-success)]/20 text-[var(--status-success)] border-[var(--status-success)]'
                    : step.status === 'FAILED'
                    ? 'bg-[var(--status-error)]/20 text-[var(--status-error)] border-[var(--status-error)]'
                    : 'bg-[var(--text-muted)]/20 text-[var(--text-muted)] border-[var(--text-muted)]'
                )}
              >
                {step.step_id}
              </div>
              <div>
                <h4 className="font-medium text-[var(--text-primary)] flex items-center gap-2">
                  {step.rule_name}
                  {step.rule_version && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-[var(--bg-tertiary)] text-[var(--text-muted)] rounded">
                      v{step.rule_version}
                    </span>
                  )}
                </h4>
                {step.reasoning && (
                  <p className="text-sm text-[var(--text-muted)]">{step.reasoning}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              {step.confidence_contribution !== undefined && (
                <div className="text-right">
                  <span className="text-xs text-[var(--text-muted)]">Contribution</span>
                  <p className="font-mono text-[var(--accent-cyan)]">
                    +{(step.confidence_contribution * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {step.duration_ms !== undefined && (
                <div className="text-right">
                  <span className="text-xs text-[var(--text-muted)]">Duration</span>
                  <p className="font-mono text-[var(--text-secondary)]">{step.duration_ms}ms</p>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default SignalDeepDive;
