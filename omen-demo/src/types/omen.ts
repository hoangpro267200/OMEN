export interface ImpactMetric {
  name: string;
  value: number;
  unit: string;
  uncertainty?: { lower: number; upper: number };
  evidence_source?: string;
}

export interface AffectedRoute {
  route_id: string;
  route_name: string;
  origin_region: string;
  destination_region: string;
  impact_severity: number;
  status?: 'blocked' | 'alternative' | 'affected';
}

export interface ExplanationStep {
  step_id: number;
  rule_name: string;
  rule_version: string;
  status: 'passed' | 'failed';
  reasoning: string;
  confidence_contribution: number;
}

export interface ExplanationChain {
  trace_id: string;
  total_steps: number;
  steps: ExplanationStep[];
}

export interface OmenSignal {
  signal_id: string;
  event_id: string;
  title: string;
  current_probability: number;
  probability_momentum: 'INCREASING' | 'DECREASING' | 'STABLE';
  confidence_level: 'LOW' | 'MEDIUM' | 'HIGH';
  confidence_score: number;
  severity: number;
  severity_label: string;
  is_actionable: boolean;
  urgency: string;
  key_metrics: ImpactMetric[];
  affected_routes: AffectedRoute[];
  explanation_chain: ExplanationChain;
}

/* --- Enterprise dashboard types (ProcessedSignal) --- */

export interface LatLng {
  lat: number;
  lng: number;
  name: string;
}

export interface ProcessedImpactMetric {
  name: string;
  value: number;
  unit: string;
  uncertainty: { lower: number; upper: number };
  baseline: number;
  projection: number[];
  evidence_source: string;
}

export interface ProcessedRoute {
  route_id: string;
  route_name: string;
  origin: LatLng;
  destination: LatLng;
  waypoints: LatLng[];
  status: 'BLOCKED' | 'DELAYED' | 'ALTERNATIVE' | 'NORMAL';
  impact_severity: number;
  delay_days: number;
}

export interface Chokepoint {
  name: string;
  lat: number;
  lng: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface ProcessedExplanationStep {
  step_id: number;
  rule_name: string;
  rule_version: string;
  status: 'passed' | 'failed' | 'processing';
  reasoning: string;
  confidence_contribution: number;
  processing_time_ms: number;
}

export interface ConfidenceBreakdown {
  liquidity: number;
  geographic: number;
  semantic: number;
  anomaly: number;
  market_depth: number;
  source_reliability: number;
}

export interface ProcessedSignal {
  signal_id: string;
  title: string;
  probability: number;
  probability_history: number[];
  probability_momentum: 'INCREASING' | 'DECREASING' | 'STABLE';
  confidence_level: 'LOW' | 'MEDIUM' | 'HIGH';
  confidence_score: number;
  confidence_breakdown: ConfidenceBreakdown;
  severity: number;
  severity_label: string;
  is_actionable: boolean;
  urgency: string;
  metrics: ProcessedImpactMetric[];
  affected_routes: ProcessedRoute[];
  affected_chokepoints: Chokepoint[];
  explanation_steps: ProcessedExplanationStep[];
  generated_at: string;
}

export type SeverityLabel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface SystemStats {
  active_signals: number;
  critical_alerts: number;
  avg_confidence: number;
  total_risk_exposure: number;
  events_processed: number;
  events_validated: number;
  signals_generated: number;
  events_rejected: number;
  system_latency_ms: number;
  events_per_second: number;
  uptime_percent: number;
}

export interface ActivityFeedItem {
  type: 'signal' | 'validation' | 'translation' | 'alert' | 'source';
  message: string;
  time: string;
}
