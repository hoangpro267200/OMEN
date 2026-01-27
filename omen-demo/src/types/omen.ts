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
