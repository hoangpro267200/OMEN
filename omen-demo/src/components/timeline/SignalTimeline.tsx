/**
 * SignalTimeline - Signal history and probability change visualization
 * 
 * Features:
 * - Timeline view of signal changes
 * - Probability trend chart
 * - Status change indicators
 * - Expandable events
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  FileText,
  Zap,
  RefreshCw,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// ============================================================================
// TYPES
// ============================================================================

export type TimelineEventType =
  | 'created'
  | 'probability_change'
  | 'status_change'
  | 'confidence_change'
  | 'validation'
  | 'alert'
  | 'note';

export interface TimelineEvent {
  id: string;
  timestamp: string;
  type: TimelineEventType;
  title: string;
  description?: string;
  changes?: {
    field: string;
    before: unknown;
    after: unknown;
  }[];
  metadata?: Record<string, unknown>;
}

export interface SignalTimelineProps {
  /** Signal ID */
  signalId: string;
  /** Timeline events */
  events?: TimelineEvent[];
  /** Show probability mini-chart */
  showChart?: boolean;
  /** Maximum events to display */
  maxEvents?: number;
  /** Callback for refresh */
  onRefresh?: () => void;
  /** Loading state */
  isLoading?: boolean;
  /** Additional class names */
  className?: string;
}

// ============================================================================
// MOCK DATA
// ============================================================================

function generateMockTimelineEvents(signalId: string, count: number = 15): TimelineEvent[] {
  const types: TimelineEventType[] = [
    'probability_change',
    'probability_change',
    'status_change',
    'confidence_change',
    'validation',
    'alert',
  ];

  const events: TimelineEvent[] = [
    {
      id: `event-0`,
      timestamp: new Date(Date.now() - count * 3600000).toISOString(),
      type: 'created',
      title: 'Signal Created',
      description: `Signal ${signalId} was created and added to monitoring queue`,
      metadata: { source: 'Polymarket', initialProbability: 0.12 },
    },
  ];

  let currentProb = 0.12;
  let currentStatus = 'CANDIDATE';

  for (let i = 1; i < count; i++) {
    const type = types[Math.floor(Math.random() * types.length)];
    const timestamp = new Date(Date.now() - (count - i) * 3600000 + Math.random() * 1800000).toISOString();

    switch (type) {
      case 'probability_change': {
        const delta = (Math.random() - 0.5) * 0.1;
        const newProb = Math.max(0.01, Math.min(0.99, currentProb + delta));
        events.push({
          id: `event-${i}`,
          timestamp,
          type,
          title: 'Probability Updated',
          description: `Market probability ${delta > 0 ? 'increased' : 'decreased'} by ${Math.abs(delta * 100).toFixed(1)}%`,
          changes: [{ field: 'probability', before: currentProb, after: newProb }],
        });
        currentProb = newProb;
        break;
      }
      case 'status_change': {
        const statuses = ['CANDIDATE', 'MONITORING', 'ACTIVE'];
        const newStatus = statuses[Math.floor(Math.random() * statuses.length)];
        if (newStatus !== currentStatus) {
          events.push({
            id: `event-${i}`,
            timestamp,
            type,
            title: 'Status Changed',
            description: `Signal status transitioned based on validation rules`,
            changes: [{ field: 'status', before: currentStatus, after: newStatus }],
          });
          currentStatus = newStatus;
        }
        break;
      }
      case 'confidence_change': {
        const oldConf = 0.4 + Math.random() * 0.3;
        const newConf = oldConf + (Math.random() - 0.5) * 0.2;
        events.push({
          id: `event-${i}`,
          timestamp,
          type,
          title: 'Confidence Recalculated',
          description: 'Confidence score updated after new market data',
          changes: [{ field: 'confidence_score', before: oldConf, after: newConf }],
        });
        break;
      }
      case 'validation': {
        events.push({
          id: `event-${i}`,
          timestamp,
          type,
          title: 'Validation Passed',
          description: 'Signal passed periodic re-validation',
          metadata: { rule: 'liquidity_validator', version: '2.1.0' },
        });
        break;
      }
      case 'alert': {
        events.push({
          id: `event-${i}`,
          timestamp,
          type,
          title: 'Alert Triggered',
          description: 'Anomaly detected in market activity',
          metadata: { severity: 'medium', threshold: 0.15 },
        });
        break;
      }
    }
  }

  return events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

// ============================================================================
// COMPONENT
// ============================================================================

export function SignalTimeline({
  signalId,
  events: propEvents,
  showChart = true,
  maxEvents = 20,
  onRefresh,
  isLoading = false,
  className,
}: SignalTimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  // Use mock data if no events provided
  const events = useMemo(() => {
    const data = propEvents || generateMockTimelineEvents(signalId, maxEvents);
    return data.slice(0, maxEvents);
  }, [propEvents, signalId, maxEvents]);

  // Extract probability history for mini-chart
  const probabilityHistory = useMemo(() => {
    const history: { timestamp: string; value: number }[] = [];
    
    events
      .filter((e) => e.type === 'probability_change' || e.type === 'created')
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .forEach((e) => {
        if (e.type === 'created' && e.metadata?.initialProbability) {
          history.push({ timestamp: e.timestamp, value: e.metadata.initialProbability as number });
        } else if (e.changes) {
          const change = e.changes.find((c) => c.field === 'probability');
          if (change) {
            history.push({ timestamp: e.timestamp, value: change.after as number });
          }
        }
      });

    return history;
  }, [events]);

  // Toggle event expansion
  const toggleExpanded = (id: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Event type config
  const typeConfig: Record<TimelineEventType, { icon: React.ComponentType<{ className?: string }>; color: string; bg: string }> = {
    created: { icon: Zap, color: 'text-[var(--accent-cyan)]', bg: 'bg-[var(--accent-cyan)]/10' },
    probability_change: { icon: Activity, color: 'text-[var(--accent-amber)]', bg: 'bg-[var(--accent-amber)]/10' },
    status_change: { icon: RefreshCw, color: 'text-[var(--text-muted)]', bg: 'bg-[var(--bg-tertiary)]' },
    confidence_change: { icon: TrendingUp, color: 'text-[var(--status-success)]', bg: 'bg-[var(--status-success)]/10' },
    validation: { icon: CheckCircle, color: 'text-[var(--status-success)]', bg: 'bg-[var(--status-success)]/10' },
    alert: { icon: AlertTriangle, color: 'text-[var(--status-error)]', bg: 'bg-[var(--status-error)]/10' },
    note: { icon: FileText, color: 'text-[var(--text-muted)]', bg: 'bg-[var(--bg-tertiary)]' },
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[var(--accent-cyan)]/10">
            <Clock className="w-5 h-5 text-[var(--accent-cyan)]" />
          </div>
          <div>
            <h3 className="font-semibold text-[var(--text-primary)]">Signal Timeline</h3>
            <p className="text-xs text-[var(--text-muted)]">{events.length} events</p>
          </div>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className={cn(
              'p-2 rounded-lg transition-colors',
              'hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]',
              isLoading && 'animate-spin'
            )}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Mini Probability Chart */}
      {showChart && probabilityHistory.length > 1 && (
        <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]/50 border border-[var(--border-subtle)]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-[var(--text-muted)]">Probability Trend</span>
            <span className="text-sm font-mono text-[var(--accent-cyan)]">
              {(probabilityHistory[probabilityHistory.length - 1]?.value * 100).toFixed(1)}%
            </span>
          </div>
          <MiniChart data={probabilityHistory} />
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        {/* Timeline Line */}
        <div className="absolute left-6 top-0 bottom-0 w-px bg-[var(--border-subtle)]" />

        {/* Events */}
        <div className="space-y-3">
          {events.length === 0 ? (
            <div className="text-center py-12 text-[var(--text-muted)]">
              <Clock className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No timeline events</p>
            </div>
          ) : (
            events.map((event, idx) => {
              const config = typeConfig[event.type];
              const Icon = config.icon;
              const isExpanded = expandedEvents.has(event.id);

              return (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.03 }}
                  className="relative pl-12"
                >
                  {/* Timeline Dot */}
                  <div
                    className={cn(
                      'absolute left-4 top-3 w-5 h-5 rounded-full flex items-center justify-center border-2 border-[var(--bg-primary)]',
                      config.bg
                    )}
                  >
                    <Icon className={cn('w-3 h-3', config.color)} />
                  </div>

                  {/* Event Card */}
                  <div
                    className={cn(
                      'rounded-lg border transition-all cursor-pointer',
                      'bg-[var(--bg-secondary)] border-[var(--border-subtle)]',
                      isExpanded && 'ring-1 ring-[var(--accent-cyan)]/50'
                    )}
                    onClick={() => toggleExpanded(event.id)}
                  >
                    <div className="flex items-center gap-3 p-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-[var(--text-primary)]">{event.title}</span>
                          {event.changes && (
                            <ChangeIndicator changes={event.changes} />
                          )}
                        </div>
                        {event.description && (
                          <p className="text-sm text-[var(--text-muted)] truncate">{event.description}</p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                        <span>{formatTimeAgo(event.timestamp)}</span>
                        <ChevronRight className={cn('w-4 h-4 transition-transform', isExpanded && 'rotate-90')} />
                      </div>
                    </div>

                    {/* Expanded Details */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-3 pb-3 pt-0 space-y-2 border-t border-[var(--border-subtle)]">
                            {/* Changes */}
                            {event.changes && event.changes.length > 0 && (
                              <div className="space-y-1 mt-3">
                                {event.changes.map((change, idx) => (
                                  <div key={idx} className="flex items-center gap-2 text-sm">
                                    <span className="text-[var(--text-muted)] capitalize">{change.field.replace(/_/g, ' ')}:</span>
                                    <span className="text-[var(--status-error)] font-mono">{formatValue(change.before)}</span>
                                    <span className="text-[var(--text-muted)]">→</span>
                                    <span className="text-[var(--status-success)] font-mono">{formatValue(change.after)}</span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Metadata */}
                            {event.metadata && Object.keys(event.metadata).length > 0 && (
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                {Object.entries(event.metadata).map(([key, value]) => (
                                  <div key={key} className="flex items-center gap-1">
                                    <span className="text-[var(--text-muted)] capitalize">{key.replace(/_/g, ' ')}:</span>
                                    <span className="text-[var(--text-secondary)]">{formatValue(value)}</span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Timestamp */}
                            <div className="text-xs text-[var(--text-muted)]">
                              {new Date(event.timestamp).toLocaleString()}
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

function MiniChart({ data }: { data: { timestamp: string; value: number }[] }) {
  const width = 300;
  const height = 60;
  const padding = 4;

  const values = data.map((d) => d.value);
  const min = Math.min(...values) * 0.9;
  const max = Math.max(...values) * 1.1;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - padding * 2);
    const y = height - padding - ((d.value - min) / (max - min)) * (height - padding * 2);
    return `${x},${y}`;
  }).join(' ');

  const trend = values[values.length - 1] > values[0] ? 'up' : values[values.length - 1] < values[0] ? 'down' : 'stable';

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={trend === 'up' ? 'var(--status-success)' : trend === 'down' ? 'var(--status-error)' : 'var(--accent-cyan)'} stopOpacity="0.3" />
          <stop offset="100%" stopColor={trend === 'up' ? 'var(--status-success)' : trend === 'down' ? 'var(--status-error)' : 'var(--accent-cyan)'} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`${padding},${height - padding} ${points} ${width - padding},${height - padding}`}
        fill="url(#chartGradient)"
      />
      <polyline
        points={points}
        fill="none"
        stroke={trend === 'up' ? 'var(--status-success)' : trend === 'down' ? 'var(--status-error)' : 'var(--accent-cyan)'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChangeIndicator({ changes }: { changes: { field: string; before: unknown; after: unknown }[] }) {
  const probChange = changes.find((c) => c.field === 'probability');
  if (!probChange) return null;

  const before = Number(probChange.before);
  const after = Number(probChange.after);
  const delta = after - before;

  if (delta > 0) {
    return (
      <span className="flex items-center gap-0.5 text-[var(--status-error)] text-xs">
        <TrendingUp className="w-3 h-3" />
        +{(delta * 100).toFixed(1)}%
      </span>
    );
  } else if (delta < 0) {
    return (
      <span className="flex items-center gap-0.5 text-[var(--status-success)] text-xs">
        <TrendingDown className="w-3 h-3" />
        {(delta * 100).toFixed(1)}%
      </span>
    );
  }

  return (
    <span className="flex items-center gap-0.5 text-[var(--text-muted)] text-xs">
      <Minus className="w-3 h-3" />
      0%
    </span>
  );
}

function formatValue(value: unknown): string {
  if (typeof value === 'number') {
    if (value < 1 && value > 0) {
      return `${(value * 100).toFixed(1)}%`;
    }
    return value.toFixed(2);
  }
  return String(value);
}

function formatTimeAgo(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

// ============================================================================
// EXPORTS
// ============================================================================

export default SignalTimeline;
