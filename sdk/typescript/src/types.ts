/**
 * OMEN SDK Type Definitions
 *
 * Type-safe interfaces for OMEN API responses.
 */

/**
 * Signal type enumeration
 */
export type SignalType =
  | 'prediction_market'
  | 'news'
  | 'commodity'
  | 'weather'
  | 'ais'
  | 'stock';

/**
 * Confidence level enumeration
 */
export type ConfidenceLevel = 'high' | 'medium' | 'low';

/**
 * Raw signal metrics for a partner.
 *
 * IMPORTANT: This contains SIGNALS only, not risk verdicts.
 * OMEN does not make risk decisions.
 */
export interface PartnerSignalMetrics {
  // Price signals
  price_current: number | null;
  price_open?: number | null;
  price_high?: number | null;
  price_low?: number | null;
  price_close_previous?: number | null;
  price_change_percent: number | null;
  price_change_absolute?: number | null;

  // Volume signals
  volume?: number | null;
  volume_avg_20d?: number | null;
  volume_ratio?: number | null;
  volume_anomaly_zscore?: number | null;

  // Volatility signals
  volatility_20d?: number | null;
  volatility_percentile?: number | null;

  // Trend signals
  trend_1d?: number | null;
  trend_7d?: number | null;
  trend_30d?: number | null;
  trend_ytd?: number | null;

  // Fundamental signals
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  roe?: number | null;
  roa?: number | null;
  debt_to_equity?: number | null;
  market_cap?: number | null;

  // Position signals
  distance_from_52w_high?: number | null;
  distance_from_52w_low?: number | null;

  // Liquidity signals
  liquidity_score?: number | null;
  bid_ask_spread?: number | null;
}

/**
 * Confidence and data quality indicators
 */
export interface PartnerSignalConfidence {
  overall_confidence: number;
  data_completeness: number;
  data_freshness_seconds: number;
  price_data_confidence: number;
  fundamental_data_confidence: number;
  volume_data_confidence: number;
  missing_fields: string[];
  data_source: string;
  data_source_reliability: number;
}

/**
 * Evidence item for audit trail
 */
export interface PartnerSignalEvidence {
  evidence_id: string;
  evidence_type: string;
  title: string;
  description?: string | null;
  raw_value: number;
  normalized_value: number;
  threshold_reference?: number | null;
  source: string;
  observed_at: string;
}

/**
 * Main partner signal response.
 *
 * Contains:
 * - Raw signal metrics (NO verdict)
 * - Confidence scores
 * - Evidence trail
 * - Optional suggestion (with disclaimer)
 */
export interface PartnerSignalResponse {
  // Identity
  symbol: string;
  company_name: string;
  sector: string;
  exchange: string;

  // Signals (NO risk verdict)
  signals: PartnerSignalMetrics;

  // Confidence
  confidence: PartnerSignalConfidence;

  // Evidence
  evidence: PartnerSignalEvidence[];

  // Market context
  market_context?: Record<string, unknown> | null;

  // Optional suggestion (NOT a decision)
  omen_suggestion?: string | null;
  suggestion_confidence?: number | null;
  suggestion_disclaimer: string;

  // Metadata
  signal_id: string;
  timestamp: string;
  omen_version: string;
  schema_version: string;
}

/**
 * Response for multiple partners
 */
export interface PartnerSignalsListResponse {
  timestamp: string;
  total_partners: number;
  market_context: Record<string, unknown>;
  partners: PartnerSignalResponse[];
  aggregated_metrics: Record<string, number>;
  data_quality: Record<string, unknown>;
}

/**
 * Geographic context
 */
export interface GeographicContext {
  locations: string[];
  primary_region?: string | null;
  affected_ports: string[];
  affected_routes: string[];
}

/**
 * Temporal context
 */
export interface TemporalContext {
  event_time?: string | null;
  detected_time: string;
  expected_duration_hours?: number | null;
}

/**
 * Evidence item
 */
export interface EvidenceItem {
  evidence_id: string;
  source: string;
  title: string;
  description?: string | null;
  url?: string | null;
  timestamp: string;
}

/**
 * Core OMEN Signal
 */
export interface OmenSignal {
  signal_id: string;
  source_event_id?: string | null;
  trace_id?: string | null;
  input_event_hash?: string | null;

  // Content
  title: string;
  description?: string | null;

  // Probability
  probability?: number | null;
  confidence_score?: number | null;
  confidence_level?: ConfidenceLevel | null;

  // Classification
  signal_type?: SignalType | null;
  category?: string | null;
  tags: string[];

  // Context
  geographic?: GeographicContext | null;
  temporal?: TemporalContext | null;

  // Evidence
  evidence: EvidenceItem[];

  // Timestamps
  created_at: string;
  updated_at?: string | null;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  items: T[];
  next_cursor?: string | null;
  prev_cursor?: string | null;
  has_more: boolean;
  total_count?: number | null;
  page_size: number;
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy' | 'degraded';
  version: string;
  timestamp: string;
  checks?: Record<string, unknown>;
}

/**
 * Error response
 */
export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}
