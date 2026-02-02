/**
 * SignalDeepDive - Neural Command Center signal analysis screen
 * Features: Probability gauge, confidence radar, explanation chain, impact hints
 */
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ExternalLink, MapPin, Truck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { Gauge, ConfidenceGauge } from '../components/ui/Gauge';
import { ProgressBar } from '../components/ui/ProgressBar';
import { cn } from '../lib/utils';

// Mock signal data for demonstration
const MOCK_SIGNAL = {
  id: 'OMEN-9C4860E23B54',
  title: 'China x India Military Clash by December 31, 2026',
  probability: 0.175,
  confidence: 0.57,
  status: 'monitoring' as const,
  category: 'GEOPOLITICAL',
  type: 'geopolitical_conflict',
  observedAt: '2 hours ago',
  source: 'Polymarket',
  sourceType: 'Prediction Market',
  liquidity: 150000,
  traders: 1200,
  marketUrl: 'https://polymarket.com/event/...',
  regions: ['China', 'India'],
  nearbyChokepoints: ['Malacca Strait'],
  domains: ['logistics', 'shipping', 'energy'],
  direction: 'negative' as const,
  affectedAssets: ['ports', 'vessels', 'shipping routes'],
  confidenceBreakdown: {
    liquidity: 0.16,
    geographic: 0.70,
    reliability: 0.85,
  },
  explanationSteps: [
    {
      id: 1,
      name: 'Ingestion',
      status: 'passed' as const,
      duration: '10ms',
      input: { event_id: 'polymarket-677404', source: 'polymarket' },
      output: { raw_event: '...', input_hash: '7f8a9b0c1d2e3f4a' },
      reasoning: 'Raw event received and normalized successfully.',
    },
    {
      id: 2,
      name: 'Liquidity Validation',
      status: 'passed' as const,
      duration: '45ms',
      score: 0.95,
      input: { liquidity_usd: 150000, min_threshold: 1000 },
      output: { score: 0.95, status: 'PASSED' },
      reasoning: 'Liquidity $150,000 exceeds minimum threshold of $1,000.',
    },
    {
      id: 3,
      name: 'Anomaly Detection',
      status: 'passed' as const,
      duration: '30ms',
      score: 0.85,
      input: { probability: 0.175, num_traders: 1200 },
      output: { risk_score: 0.15, status: 'PASSED' },
      reasoning: 'No anomalies detected. Probability within normal range.',
    },
    {
      id: 4,
      name: 'Semantic Relevance',
      status: 'passed' as const,
      duration: '60ms',
      score: 0.80,
      input: { title: 'China x India military clash...', keywords: ['military', 'clash'] },
      output: { category: 'GEOPOLITICAL', relevance_score: 0.80 },
      reasoning: 'Matched geopolitical risk category with high relevance.',
    },
  ],
};

export interface SignalDeepDiveProps {
  className?: string;
}

export function SignalDeepDive({ className }: SignalDeepDiveProps) {
  const { signalId: _signalId } = useParams();
  const signal = MOCK_SIGNAL; // TODO: In production, fetch based on signalId

  return (
    <div className={cn('p-6 space-y-6', className)}>
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-4"
      >
        <Link
          to="/signals"
          className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-text-muted" />
        </Link>
        <div>
          <h1 className="text-xl font-display font-bold text-text-primary tracking-tight">
            Signal Analysis
          </h1>
          <p className="text-accent-cyan font-mono text-sm">{signal.id}</p>
        </div>
      </motion.div>

      {/* Top Row - Overview and Gauges */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Signal Overview */}
        <div className="lg:col-span-5">
          <GlassCard className="p-6 h-full" delay={0.1}>
            <GlassCardTitle>Signal Overview</GlassCardTitle>
            <div className="mt-4 space-y-4">
              <h2 className="text-lg font-medium text-text-primary">{signal.title}</h2>

              <div className="flex items-center gap-3">
                <span
                  className={cn(
                    'px-2 py-1 rounded text-xs font-mono border',
                    signal.status === 'monitoring'
                      ? 'bg-status-warning/20 text-status-warning border-status-warning/30'
                      : 'bg-status-error/20 text-status-error border-status-error/30'
                  )}
                >
                  {signal.status === 'monitoring' ? 'WATCHING' : 'ACTIVE'}
                </span>
                <span className="px-2 py-1 rounded text-xs font-mono bg-bg-tertiary text-text-secondary border border-border-subtle">
                  {signal.category}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-text-muted">Observed</span>
                  <p className="text-text-primary font-mono">{signal.observedAt}</p>
                </div>
                <div>
                  <span className="text-text-muted">Type</span>
                  <p className="text-text-primary font-mono">{signal.type}</p>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Probability Gauge */}
        <div className="lg:col-span-3">
          <GlassCard
            className="p-6 h-full flex flex-col items-center justify-center"
            delay={0.15}
          >
            <GlassCardTitle className="self-start mb-4">Probability</GlassCardTitle>
            <Gauge
              value={signal.probability}
              max={1}
              size={140}
              variant="dynamic"
              format="percent"
              label="PROBABILITY"
            />
          </GlassCard>
        </div>

        {/* Confidence Breakdown */}
        <div className="lg:col-span-4">
          <GlassCard className="p-6 h-full" delay={0.2}>
            <GlassCardTitle>Confidence Breakdown</GlassCardTitle>
            <div className="mt-4 space-y-4">
              <ConfidenceGauge confidence={signal.confidence} size={100} />

              <div className="space-y-3 pt-4 border-t border-border-subtle">
                {Object.entries(signal.confidenceBreakdown).map(([key, value]) => (
                  <div key={key} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-text-muted capitalize">{key}</span>
                      <span className="font-mono text-text-secondary">
                        {value.toFixed(2)}
                      </span>
                    </div>
                    <ProgressBar value={value * 100} variant="cyan" size="sm" />
                  </div>
                ))}
              </div>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Geographic Context */}
      <GlassCard className="p-6" delay={0.25}>
        <GlassCardTitle icon={<MapPin className="w-4 h-4" />}>
          Geographic Context
        </GlassCardTitle>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h4 className="text-xs text-text-muted mb-2">REGIONS</h4>
            <div className="flex flex-wrap gap-2">
              {signal.regions.map((region) => (
                <span
                  key={region}
                  className="px-3 py-1 rounded-full bg-accent-cyan/20 text-accent-cyan text-sm"
                >
                  {region}
                </span>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs text-text-muted mb-2">NEARBY CHOKEPOINTS</h4>
            <div className="flex flex-wrap gap-2">
              {signal.nearbyChokepoints.map((cp) => (
                <span
                  key={cp}
                  className="px-3 py-1 rounded-full bg-status-warning/20 text-status-warning text-sm"
                >
                  {cp}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-center p-4 bg-bg-tertiary/50 rounded-lg text-text-muted text-sm">
            Map visualization would appear here
          </div>
        </div>
      </GlassCard>

      {/* Explanation Chain */}
      <GlassCard className="p-6" delay={0.3}>
        <GlassCardTitle>Explanation Chain (Audit Trail)</GlassCardTitle>
        <div className="mt-4">
          <div className="flex items-center gap-4 mb-4 p-3 bg-bg-tertiary/50 rounded-lg">
            <div>
              <span className="text-xs text-text-muted">Trace ID</span>
              <p className="font-mono text-text-secondary">9c4860e23b540dc5</p>
            </div>
            <div>
              <span className="text-xs text-text-muted">Total Processing</span>
              <p className="font-mono text-status-success">145ms</p>
            </div>
          </div>

          <div className="space-y-3">
            {signal.explanationSteps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.35 + index * 0.1 }}
                className="p-4 rounded-lg bg-bg-tertiary/30 border border-border-subtle"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold',
                        step.status === 'passed'
                          ? 'bg-status-success/20 text-status-success border border-status-success'
                          : 'bg-status-error/20 text-status-error border border-status-error'
                      )}
                    >
                      {step.id}
                    </div>
                    <div>
                      <h4 className="font-medium text-text-primary">{step.name}</h4>
                      <p className="text-sm text-text-muted">{step.reasoning}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {step.score && (
                      <div className="text-right">
                        <span className="text-xs text-text-muted">Score</span>
                        <p className="font-mono text-accent-cyan">{step.score}</p>
                      </div>
                    )}
                    <div className="text-right">
                      <span className="text-xs text-text-muted">Duration</span>
                      <p className="font-mono text-text-secondary">{step.duration}</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </GlassCard>

      {/* Bottom Row - Evidence & Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evidence */}
        <GlassCard className="p-6" delay={0.5}>
          <GlassCardTitle>Evidence</GlassCardTitle>
          <div className="mt-4 space-y-4">
            <div>
              <span className="text-xs text-text-muted">Source</span>
              <p className="text-text-primary">{signal.source}</p>
            </div>
            <div>
              <span className="text-xs text-text-muted">Type</span>
              <p className="text-text-secondary">{signal.sourceType}</p>
            </div>
            <div className="p-3 bg-bg-tertiary/50 rounded-lg text-sm text-text-secondary">
              &ldquo;${signal.liquidity.toLocaleString()} liquidity, {signal.traders.toLocaleString()}{' '}
              traders&rdquo;
            </div>
            <a
              href={signal.marketUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-accent-cyan hover:underline text-sm"
            >
              View on {signal.source}
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </GlassCard>

        {/* Impact Hints */}
        <GlassCard className="p-6" delay={0.55}>
          <GlassCardTitle>Impact Hints</GlassCardTitle>
          <div className="mt-4 space-y-4">
            <div>
              <h4 className="text-xs text-text-muted mb-2">AFFECTED DOMAINS</h4>
              <div className="flex flex-wrap gap-2">
                {signal.domains.map((domain) => (
                  <span
                    key={domain}
                    className="px-3 py-1 rounded-full bg-accent-cyan/20 text-accent-cyan text-sm flex items-center gap-1"
                  >
                    <Truck className="w-3 h-3" />
                    {domain}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-xs text-text-muted mb-2">DIRECTION</h4>
              <span
                className={cn(
                  'text-lg',
                  signal.direction === 'negative' ? 'text-status-error' : 'text-status-success'
                )}
              >
                {signal.direction === 'negative' ? '📉 Negative' : '📈 Positive'}
              </span>
            </div>

            <div>
              <h4 className="text-xs text-text-muted mb-2">AFFECTED ASSETS</h4>
              <p className="text-text-secondary">{signal.affectedAssets.join(', ')}</p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

export default SignalDeepDive;
