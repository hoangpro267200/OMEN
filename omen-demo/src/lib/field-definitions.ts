/**
 * Field Definitions Registry - Semantic definitions for all OMEN data fields
 * 
 * This registry provides comprehensive metadata for every data field in the system:
 * - What it means (semantic definition)
 * - Where it comes from (source)
 * - How it's calculated (formula/rule)
 * - What's normal (thresholds)
 * - Quality indicators
 * 
 * Used by ExplainPopover to provide "Explain This" functionality.
 */

// ============================================================================
// TYPES
// ============================================================================

export interface FieldSource {
  /** Source system name */
  system: string;
  /** API endpoint if applicable */
  endpoint?: string;
  /** Link to documentation */
  documentation?: string;
}

export interface FieldComputation {
  /** Rule/function name that computes this */
  rule: string;
  /** Version of the rule */
  version: string;
  /** Human-readable formula */
  formula?: string;
}

export interface QualityIndicator {
  /** Metric name */
  metric: string;
  /** Threshold for acceptable quality */
  threshold: number;
  /** Description */
  description?: string;
}

export interface FieldDefinition {
  /** Unique field identifier (e.g., 'signal.probability') */
  id: string;
  /** Human-readable label */
  label: string;
  /** Detailed description of what this field represents */
  description: string;
  /** Unit of measurement (e.g., '%', 'ms', 'USD') */
  unit?: string;
  /** Expected/normal range for this field */
  normalRange?: { min: number; max: number; unit?: string };
  /** Human-readable calculation formula */
  formula?: string;
  /** Source system information */
  source: FieldSource;
  /** Computation details if field is derived */
  computedBy?: FieldComputation;
  /** Quality indicators for this field */
  qualityIndicators?: QualityIndicator[];
  /** Related fields */
  relatedFields?: string[];
  /** Example values */
  examples?: string[];
  /** Additional notes */
  notes?: string;
}

// ============================================================================
// FIELD DEFINITIONS REGISTRY
// ============================================================================

export const FIELD_DEFINITIONS: Record<string, FieldDefinition> = {
  // ===========================================================================
  // SIGNAL FIELDS
  // ===========================================================================

  'signal.probability': {
    id: 'signal.probability',
    label: 'Probability',
    description:
      'The market-implied probability that this event will occur. Derived from prediction market prices where probability equals the YES token price divided by the total of YES and NO prices.',
    unit: '%',
    normalRange: { min: 1, max: 99, unit: '%' },
    formula: 'YES_price / (YES_price + NO_price) × 100',
    source: {
      system: 'Polymarket',
      endpoint: '/v1/markets/{market_id}',
      documentation: 'https://docs.polymarket.com/#markets',
    },
    qualityIndicators: [
      { metric: 'liquidity_depth', threshold: 10000, description: 'Minimum USD liquidity' },
      { metric: 'trade_count', threshold: 100, description: 'Minimum number of trades' },
    ],
    relatedFields: ['signal.probability_momentum', 'signal.probability_history'],
    examples: ['17.5%', '82.3%', '50.0%'],
    notes: 'Probabilities near 50% indicate high uncertainty. Extreme values (>90% or <10%) should be treated with caution.',
  },

  'signal.probability_momentum': {
    id: 'signal.probability_momentum',
    label: 'Probability Momentum',
    description:
      'The rate of change in probability over the last 24 hours. Positive values indicate increasing probability, negative values indicate decreasing.',
    unit: '%/day',
    normalRange: { min: -10, max: 10, unit: '%/day' },
    formula: '(current_probability - probability_24h_ago)',
    source: {
      system: 'OMEN Pipeline',
      endpoint: '/api/v1/signals/{signal_id}',
    },
    computedBy: {
      rule: 'momentum_calculator',
      version: '1.2.0',
    },
    examples: ['+2.5%', '-1.8%', '0.0%'],
  },

  'signal.confidence_score': {
    id: 'signal.confidence_score',
    label: 'Confidence Score',
    description:
      "OMEN's confidence in the signal quality and reliability. This is a weighted average of multiple factors: market liquidity (30%), anomaly detection (30%), and semantic relevance (40%). Higher scores indicate more reliable signals.",
    unit: 'score',
    normalRange: { min: 0, max: 1 },
    formula: '(liquidity_score × 0.3) + (anomaly_score × 0.3) + (semantic_score × 0.4)',
    source: {
      system: 'OMEN Pipeline',
      endpoint: '/api/v1/signals/{signal_id}',
    },
    computedBy: {
      rule: 'confidence_aggregator',
      version: '2.1.0',
      formula: 'weighted_average([liquidity, anomaly, semantic], [0.3, 0.3, 0.4])',
    },
    qualityIndicators: [
      { metric: 'liquidity_score', threshold: 0.3, description: 'Market liquidity quality' },
      { metric: 'anomaly_score', threshold: 0.5, description: 'Anomaly detection pass' },
      { metric: 'semantic_score', threshold: 0.6, description: 'Relevance to supply chain' },
    ],
    relatedFields: ['signal.confidence_breakdown'],
    examples: ['0.85 (HIGH)', '0.57 (MEDIUM)', '0.32 (LOW)'],
    notes: 'Scores above 0.7 are considered HIGH confidence, 0.4-0.7 MEDIUM, below 0.4 LOW.',
  },

  'signal.confidence_breakdown.liquidity': {
    id: 'signal.confidence_breakdown.liquidity',
    label: 'Liquidity Score',
    description:
      'Component score measuring market liquidity depth. Higher liquidity indicates more reliable price signals as manipulation becomes harder.',
    unit: 'score',
    normalRange: { min: 0, max: 1 },
    formula: 'min(1, ln(liquidity_usd + 1) / ln(100000))',
    source: {
      system: 'OMEN Pipeline',
    },
    computedBy: {
      rule: 'liquidity_validator',
      version: '2.1.0',
    },
  },

  'signal.confidence_breakdown.geographic': {
    id: 'signal.confidence_breakdown.geographic',
    label: 'Geographic Relevance',
    description:
      'Score indicating how relevant this signal is to supply chain geography (chokepoints, routes, regions).',
    unit: 'score',
    normalRange: { min: 0, max: 1 },
    source: {
      system: 'OMEN Pipeline',
    },
    computedBy: {
      rule: 'geographic_enricher',
      version: '1.5.0',
    },
  },

  'signal.confidence_breakdown.source_reliability': {
    id: 'signal.confidence_breakdown.source_reliability',
    label: 'Source Reliability',
    description:
      'Historical reliability score of the data source. Based on past accuracy and market integrity.',
    unit: 'score',
    normalRange: { min: 0, max: 1 },
    source: {
      system: 'OMEN Source Registry',
    },
  },

  'signal.liquidity': {
    id: 'signal.liquidity',
    label: 'Market Liquidity',
    description:
      'Total USD value available for trading in the prediction market order book. Higher liquidity = more reliable price signal and harder to manipulate.',
    unit: 'USD',
    normalRange: { min: 10000, max: 1000000 },
    source: {
      system: 'Polymarket CLOB API',
      endpoint: '/v1/orderbook/{token_id}',
      documentation: 'https://docs.polymarket.com/#orderbook',
    },
    qualityIndicators: [
      { metric: 'bid_depth', threshold: 5000, description: 'Minimum bid liquidity' },
      { metric: 'ask_depth', threshold: 5000, description: 'Minimum ask liquidity' },
    ],
    examples: ['$150,000', '$2,500,000', '$45,000'],
  },

  'signal.status': {
    id: 'signal.status',
    label: 'Signal Status',
    description:
      'Current lifecycle stage of the signal. ACTIVE = validated and actionable; MONITORING = being tracked; CANDIDATE = under evaluation; ARCHIVED = no longer relevant.',
    source: {
      system: 'OMEN Pipeline',
    },
    computedBy: {
      rule: 'status_classifier',
      version: '1.5.0',
    },
    examples: ['ACTIVE', 'MONITORING', 'CANDIDATE', 'ARCHIVED'],
  },

  'signal.severity': {
    id: 'signal.severity',
    label: 'Severity Score',
    description:
      'Numeric severity score indicating potential impact. Derived from probability, affected routes, and historical impact analysis.',
    unit: 'score',
    normalRange: { min: 0, max: 1 },
    formula: 'probability × impact_factor × urgency_factor',
    source: {
      system: 'OMEN Pipeline',
    },
    computedBy: {
      rule: 'severity_calculator',
      version: '1.3.0',
    },
  },

  'signal.severity_label': {
    id: 'signal.severity_label',
    label: 'Severity Level',
    description:
      'Categorical severity classification. CRITICAL = immediate action required; HIGH = urgent attention; MEDIUM = monitor closely; LOW = informational.',
    source: {
      system: 'OMEN Pipeline',
    },
    computedBy: {
      rule: 'severity_classifier',
      version: '1.3.0',
    },
    examples: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
    notes: 'CRITICAL: severity >= 0.75, HIGH: 0.5-0.75, MEDIUM: 0.25-0.5, LOW: < 0.25',
  },

  // ===========================================================================
  // PIPELINE FIELDS
  // ===========================================================================

  'pipeline.events_received': {
    id: 'pipeline.events_received',
    label: 'Events Received',
    description:
      'Total number of raw events received from all data sources before any validation or filtering.',
    unit: 'count',
    source: {
      system: 'OMEN Pipeline',
      endpoint: '/api/v1/signals/stats',
    },
  },

  'pipeline.events_validated': {
    id: 'pipeline.events_validated',
    label: 'Events Validated',
    description:
      'Number of events that passed all validation rules (liquidity, anomaly detection, semantic relevance).',
    unit: 'count',
    source: {
      system: 'OMEN Pipeline',
    },
    relatedFields: ['pipeline.events_received', 'pipeline.validation_rate'],
  },

  'pipeline.validation_rate': {
    id: 'pipeline.validation_rate',
    label: 'Validation Rate',
    description:
      'Percentage of incoming events that pass all validation rules. A low rate indicates strict filtering or low-quality input data.',
    unit: '%',
    normalRange: { min: 20, max: 60 },
    formula: '(events_validated / events_received) × 100',
    source: {
      system: 'OMEN Pipeline',
      endpoint: '/api/v1/signals/stats',
    },
    notes: 'Typical range is 30-50%. Rates below 20% may indicate data quality issues.',
  },

  'pipeline.signals_generated': {
    id: 'pipeline.signals_generated',
    label: 'Signals Generated',
    description:
      'Number of validated events that were promoted to signals after enrichment and classification.',
    unit: 'count',
    source: {
      system: 'OMEN Pipeline',
    },
  },

  'pipeline.processing_time': {
    id: 'pipeline.processing_time',
    label: 'Processing Time',
    description:
      'Time taken to process an event through all pipeline stages: ingest → validate → enrich → emit.',
    unit: 'ms',
    normalRange: { min: 50, max: 200 },
    source: {
      system: 'OMEN Pipeline',
    },
    notes: 'P50 should be under 100ms, P99 under 300ms for acceptable performance.',
  },

  // ===========================================================================
  // SOURCE FIELDS
  // ===========================================================================

  'source.status': {
    id: 'source.status',
    label: 'Source Status',
    description:
      'Current health status of the data source connection. healthy = normal; degraded = partial; error = unavailable; mock = using simulated data.',
    source: {
      system: 'OMEN Health Monitor',
      endpoint: '/health/sources',
    },
    examples: ['healthy', 'degraded', 'error', 'mock'],
  },

  'source.latency': {
    id: 'source.latency',
    label: 'Source Latency',
    description:
      'Round-trip time to fetch data from this source, including network latency and source processing time.',
    unit: 'ms',
    normalRange: { min: 50, max: 500 },
    source: {
      system: 'OMEN Health Monitor',
    },
    notes: 'Latency above 500ms may indicate connectivity issues.',
  },

  'source.events_per_hour': {
    id: 'source.events_per_hour',
    label: 'Events/Hour',
    description: 'Number of events received from this source in the last hour.',
    unit: 'events/hr',
    source: {
      system: 'OMEN Metrics',
    },
  },

  // ===========================================================================
  // SYSTEM FIELDS
  // ===========================================================================

  'system.latency_ms': {
    id: 'system.latency_ms',
    label: 'System Latency',
    description:
      'End-to-end processing latency from event reception to signal emission (P50 percentile).',
    unit: 'ms',
    normalRange: { min: 50, max: 200 },
    source: {
      system: 'OMEN Metrics',
      endpoint: '/api/v1/system/stats',
    },
  },

  'system.uptime_percent': {
    id: 'system.uptime_percent',
    label: 'Uptime',
    description: 'System availability percentage over the monitoring period.',
    unit: '%',
    normalRange: { min: 99, max: 100 },
    source: {
      system: 'OMEN Metrics',
    },
    notes: 'Target SLA is 99.9% uptime.',
  },
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get field definition by ID
 */
export function getFieldDefinition(fieldId: string): FieldDefinition | null {
  return FIELD_DEFINITIONS[fieldId] ?? null;
}

/**
 * Get field definition with fallback for unknown fields
 */
export function getFieldDefinitionWithFallback(
  fieldId: string | undefined | null,
  fallback: Partial<FieldDefinition> = {}
): FieldDefinition {
  // Handle undefined/null fieldId
  if (!fieldId) {
    return {
      id: 'unknown',
      label: fallback.label ?? 'Unknown Field',
      description: fallback.description ?? 'No description available.',
      source: fallback.source ?? { system: 'OMEN' },
      ...fallback,
    };
  }

  const definition = FIELD_DEFINITIONS[fieldId];
  
  if (definition) {
    return { ...definition, ...fallback };
  }
  
  // Create a minimal definition for unknown fields
  return {
    id: fieldId,
    label: fieldId.split('.').pop()?.replace(/_/g, ' ') ?? fieldId,
    description: fallback.description ?? 'No description available for this field.',
    source: fallback.source ?? { system: 'OMEN' },
    ...fallback,
  };
}

/**
 * Search field definitions
 */
export function searchFieldDefinitions(query: string): FieldDefinition[] {
  const lowerQuery = query.toLowerCase();
  
  return Object.values(FIELD_DEFINITIONS).filter(
    (def) =>
      def.id.toLowerCase().includes(lowerQuery) ||
      def.label.toLowerCase().includes(lowerQuery) ||
      def.description.toLowerCase().includes(lowerQuery)
  );
}

/**
 * Get all field definitions for a category (e.g., 'signal', 'pipeline')
 */
export function getFieldDefinitionsByCategory(category: string): FieldDefinition[] {
  return Object.values(FIELD_DEFINITIONS).filter((def) =>
    def.id.startsWith(`${category}.`)
  );
}
