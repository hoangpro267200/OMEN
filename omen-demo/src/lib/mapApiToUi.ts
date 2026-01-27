/**
 * Maps API response types to UI component types.
 * Bridge between backend and frontend.
 */

import type {
  ProcessedSignal,
  ProcessedRoute,
  ProcessedImpactMetric,
  Chokepoint,
  ProcessedExplanationStep,
  ConfidenceBreakdown,
  SystemStats,
  ActivityFeedItem,
} from '../types/omen';

/** API signal response (backend FullProcessedSignalResponse) */
export interface ApiSignalResponse {
  signal_id: string;
  event_id: string;
  title: string;
  summary?: string;
  probability: number;
  probability_history: number[];
  probability_momentum: string;
  confidence_level: string;
  confidence_score: number;
  confidence_breakdown: ConfidenceBreakdown;
  severity: number;
  severity_label: string;
  is_actionable: boolean;
  urgency: string;
  metrics: Array<{
    name: string;
    value: number;
    unit: string;
    uncertainty?: { lower: number; upper: number };
    baseline?: number;
    projection?: number[];
    evidence_source?: string;
  }>;
  affected_routes: Array<{
    route_id: string;
    route_name: string;
    origin: { lat: number; lng: number; name: string };
    destination: { lat: number; lng: number; name: string };
    waypoints: Array<{ lat: number; lng: number; name: string }>;
    status: string;
    impact_severity: number;
    delay_days: number;
  }>;
  affected_chokepoints: Array<{ name: string; lat: number; lng: number; risk_level: string }>;
  explanation_steps: Array<{
    step_id: number;
    rule_name: string;
    rule_version: string;
    status: string;
    reasoning: string;
    confidence_contribution: number;
    processing_time_ms?: number;
  }>;
  generated_at: string;
  source_market?: string;
  market_url?: string;
}

/** API system stats */
export interface ApiSystemStats {
  active_signals: number;
  critical_alerts: number;
  avg_confidence: number;
  total_risk_exposure: number;
  events_processed: number;
  events_validated: number;
  signals_generated: number;
  events_rejected: number;
  validation_rate?: number;
  system_latency_ms: number;
  events_per_minute: number;
  uptime_seconds: number;
  memory_usage_mb?: number;
  cpu_percent?: number;
  polymarket_status?: string;
  polymarket_events_per_min?: number;
}

/** API activity item */
export interface ApiActivityItem {
  id: string;
  type: 'signal' | 'validation' | 'rule' | 'alert' | 'source' | 'error';
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

const ROUTE_STATUS_MAP: Record<string, ProcessedRoute['status']> = {
  BLOCKED: 'BLOCKED',
  DELAYED: 'DELAYED',
  ALTERNATIVE: 'ALTERNATIVE',
  OPEN: 'NORMAL',
  NORMAL: 'NORMAL',
};

export function mapApiSignalToUi(api: ApiSignalResponse): ProcessedSignal {
  return {
    signal_id: api.signal_id,
    title: api.title,
    probability: api.probability,
    probability_history: api.probability_history ?? [],
    probability_momentum: (api.probability_momentum as ProcessedSignal['probability_momentum']) || 'STABLE',
    confidence_level: (api.confidence_level as ProcessedSignal['confidence_level']) || 'MEDIUM',
    confidence_score: api.confidence_score,
    confidence_breakdown: api.confidence_breakdown,
    severity: api.severity,
    severity_label: api.severity_label,
    is_actionable: api.is_actionable,
    urgency: api.urgency,
    metrics: (api.metrics ?? []).map((m): ProcessedImpactMetric => ({
      name: m.name,
      value: m.value,
      unit: m.unit,
      uncertainty: m.uncertainty ?? { lower: m.value * 0.8, upper: m.value * 1.2 },
      baseline: m.baseline ?? 0,
      projection: m.projection ?? [],
      evidence_source: m.evidence_source ?? '',
    })),
    affected_routes: (api.affected_routes ?? []).map((r): ProcessedRoute => ({
      route_id: r.route_id,
      route_name: r.route_name,
      origin: r.origin,
      destination: r.destination,
      waypoints: r.waypoints ?? [],
      status: ROUTE_STATUS_MAP[r.status] ?? 'NORMAL',
      impact_severity: r.impact_severity,
      delay_days: r.delay_days ?? 0,
    })),
    affected_chokepoints: (api.affected_chokepoints ?? []).map((c): Chokepoint => ({
      name: c.name,
      lat: c.lat,
      lng: c.lng,
      risk_level: (c.risk_level as Chokepoint['risk_level']) || 'MEDIUM',
    })),
    explanation_steps: (api.explanation_steps ?? []).map((s): ProcessedExplanationStep => ({
      step_id: s.step_id,
      rule_name: s.rule_name,
      rule_version: s.rule_version,
      status: (s.status as ProcessedExplanationStep['status']) || 'passed',
      reasoning: s.reasoning,
      confidence_contribution: s.confidence_contribution,
      processing_time_ms: s.processing_time_ms ?? 0,
    })),
    generated_at: typeof api.generated_at === 'string' ? api.generated_at : new Date(api.generated_at).toISOString(),
  };
}

export function mapApiStatsToUi(api: ApiSystemStats): SystemStats {
  return {
    active_signals: api.active_signals,
    critical_alerts: api.critical_alerts,
    avg_confidence: api.avg_confidence,
    total_risk_exposure: api.total_risk_exposure,
    events_processed: api.events_processed,
    events_validated: api.events_validated,
    signals_generated: api.signals_generated,
    events_rejected: api.events_rejected,
    system_latency_ms: api.system_latency_ms,
    events_per_second: Math.round((api.events_per_minute ?? 0) / 60),
    uptime_percent: api.uptime_seconds > 0 ? 99.97 : 100,
  };
}

const ACTIVITY_TYPE_MAP: Record<string, ActivityFeedItem['type']> = {
  signal: 'signal',
  validation: 'validation',
  rule: 'validation',
  alert: 'alert',
  source: 'source',
  error: 'alert',
  translation: 'translation',
};

export function mapApiActivityToUi(api: ApiActivityItem): ActivityFeedItem {
  const now = Date.now();
  const ts = new Date(api.timestamp).getTime();
  const diffMins = Math.floor((now - ts) / 60000);
  const timeAgo =
    diffMins < 1 ? 'vừa xong' : diffMins < 60 ? `${diffMins} phút trước` : `${Math.floor(diffMins / 60)} giờ trước`;
  return {
    type: ACTIVITY_TYPE_MAP[api.type] ?? 'source',
    message: api.message,
    time: timeAgo,
  };
}
