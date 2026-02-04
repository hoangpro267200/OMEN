/**
 * Mock Data Generators - Realistic demo data for OMEN
 * 
 * These generators create realistic-looking data for demo mode
 * that mimics the structure and patterns of real API responses.
 */

// ============================================================================
// TYPES (matching API contracts)
// ============================================================================

export interface Signal {
  signal_id: string;
  title: string;
  description?: string;
  probability: number;
  probability_source: string;
  probability_momentum?: number;
  confidence_score: number;
  confidence_level: 'LOW' | 'MEDIUM' | 'HIGH';
  confidence_breakdown?: {
    liquidity: number;
    geographic: number;
    source_reliability: number;
  };
  status: 'ACTIVE' | 'MONITORING' | 'CANDIDATE' | 'ARCHIVED';
  category: string;
  subcategory?: string;
  domain: string;
  signal_type: string;
  severity: number;
  severity_label: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  geographic?: {
    regions: string[];
    chokepoints: string[];
  };
  temporal?: {
    event_horizon: string;
    signal_freshness: string;
  };
  evidence?: Array<{
    source: string;
    source_type: string;
    value: string;
    url?: string;
  }>;
  explanation_steps?: ExplanationStep[];
  trace_id?: string;
  observed_at: string;
  generated_at: string;
  source_market?: string;
  market_url?: string;
  affected_routes?: string[];
  affected_chokepoints?: string[];
  affected_systems?: string[];
  expected_onset_hours?: number;
  expected_duration_hours?: number;
  metrics?: Array<{
    name: string;
    current_value: number;
    projected_value: number;
    unit: string;
    direction: 'up' | 'down' | 'stable';
    has_uncertainty?: boolean;
    uncertainty_low?: number;
    uncertainty_high?: number;
    has_evidence?: boolean;
  }>;
  probability_history?: number[];
  detailed_explanation?: string;
  summary?: string;
  has_confidence_breakdown?: boolean;
  probability_is_fallback?: boolean;
}

export interface ExplanationStep {
  step_id: number;
  rule_name: string;
  rule_version: string;
  status: 'passed' | 'failed' | 'skipped';
  reasoning: string;
  confidence_contribution: number;
  processing_time_ms: number;
  input_summary?: Record<string, unknown>;
  output_summary?: Record<string, unknown>;
}

export interface SignalListResponse {
  signals: Signal[];
  total: number;
  limit: number;
  offset: number;
}

export interface PipelineStats {
  events_received: number;
  events_validated: number;
  events_rejected: number;
  events_translated?: number;
  signals_generated: number;
  validation_rate: number;
  average_confidence: number;
  processing_time_p50_ms: number;
  processing_time_p99_ms: number;
  active_signals: number;
  critical_alerts: number;
}

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
  validation_rate?: number;
  events_translated?: number;
}

export interface DataSource {
  id: string;
  name: string;
  status: 'healthy' | 'warning' | 'error' | 'mock';
  latency: number;
  type: 'real' | 'mock';
  lastUpdate?: string;
  eventsPerHour?: number;
}

export interface ActivityItem {
  id: string;
  type: 'signal_emitted' | 'signal_ingested' | 'reconcile_completed' | 'error' | 'info';
  message: string;
  timestamp: string;
  signal_id?: string;
  status_code?: number;
}

// ============================================================================
// SEED DATA
// ============================================================================

const SIGNAL_TITLES = [
  'Suez Canal disruption risk - vessel congestion',
  'Panama Canal water levels below critical threshold',
  'China-Taiwan military tensions escalation',
  'Red Sea shipping route closure risk',
  'Singapore port congestion surge expected',
  'Oil price spike above $100/barrel probability',
  'European natural gas shortage winter 2026',
  'US West Coast port strike likelihood',
  'Malacca Strait piracy risk elevated',
  'Baltic Sea shipping corridor disruption',
  'China x India military clash potential',
  'Mediterranean drought impact on shipping',
  'Arctic shipping route opening acceleration',
  'South China Sea territorial dispute escalation',
  'Global semiconductor shortage continuation',
];

const CATEGORIES = ['GEOPOLITICAL', 'CLIMATE', 'INFRASTRUCTURE', 'ECONOMIC', 'SECURITY'];
const DOMAINS = ['shipping', 'logistics', 'energy', 'commodities', 'trade'];
const REGIONS = ['asia-pacific', 'europe', 'middle-east', 'americas', 'africa'];
const CHOKEPOINTS = [
  'suez_canal',
  'panama_canal',
  'malacca_strait',
  'strait_of_hormuz',
  'bosphorus',
  'gibraltar',
];

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function randomId(prefix = 'OMEN'): string {
  const chars = 'ABCDEF0123456789';
  let id = '';
  for (let i = 0; i < 12; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return `${prefix}-${id}`;
}

function randomFrom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function randomInt(min: number, max: number): number {
  return Math.floor(randomBetween(min, max));
}

function generateProbabilityHistory(current: number, length = 24): number[] {
  const history: number[] = [];
  let value = current + randomBetween(-0.1, 0.1);
  
  for (let i = 0; i < length; i++) {
    value = Math.max(0.01, Math.min(0.99, value + randomBetween(-0.05, 0.05)));
    history.push(value);
  }
  
  // Ensure last value is close to current
  history[history.length - 1] = current;
  return history;
}

function severityFromProbability(probability: number): { severity: number; label: Signal['severity_label'] } {
  if (probability >= 0.75) return { severity: 0.9, label: 'CRITICAL' };
  if (probability >= 0.5) return { severity: 0.7, label: 'HIGH' };
  if (probability >= 0.25) return { severity: 0.4, label: 'MEDIUM' };
  return { severity: 0.2, label: 'LOW' };
}

function confidenceLevelFromScore(score: number): Signal['confidence_level'] {
  if (score >= 0.7) return 'HIGH';
  if (score >= 0.4) return 'MEDIUM';
  return 'LOW';
}

// ============================================================================
// GENERATORS
// ============================================================================

/**
 * Generate a single realistic signal
 */
export function generateMockSignal(index: number = 0, overrides: Partial<Signal> = {}): Signal {
  const title = SIGNAL_TITLES[index % SIGNAL_TITLES.length];
  const probability = randomBetween(0.1, 0.85);
  const confidence = randomBetween(0.35, 0.9);
  const { severity, label: severityLabel } = severityFromProbability(probability);
  const category = randomFrom(CATEGORIES);
  const domain = randomFrom(DOMAINS);
  
  const now = new Date();
  const observedAt = new Date(now.getTime() - randomInt(1, 24) * 3600000);
  
  return {
    signal_id: randomId(),
    title,
    description: `Market signal tracking: ${title.toLowerCase()}`,
    probability,
    probability_source: 'polymarket',
    probability_momentum: randomBetween(-0.05, 0.05),
    confidence_score: confidence,
    confidence_level: confidenceLevelFromScore(confidence),
    confidence_breakdown: {
      liquidity: randomBetween(0.1, 0.95),
      geographic: randomBetween(0.5, 0.95),
      source_reliability: randomBetween(0.7, 0.95),
    },
    status: randomFrom(['ACTIVE', 'MONITORING', 'CANDIDATE']),
    category,
    subcategory: `${category.toLowerCase()}_risk`,
    domain,
    signal_type: `${domain}_disruption`,
    severity,
    severity_label: severityLabel,
    geographic: {
      regions: [randomFrom(REGIONS), randomFrom(REGIONS)].filter((v, i, a) => a.indexOf(v) === i),
      chokepoints: [randomFrom(CHOKEPOINTS)],
    },
    temporal: {
      event_horizon: new Date(now.getTime() + randomInt(7, 365) * 86400000).toISOString(),
      signal_freshness: 'current',
    },
    evidence: [
      {
        source: 'polymarket',
        source_type: 'prediction_market',
        value: `$${randomInt(50, 500)}K liquidity, ${randomInt(500, 5000)} traders`,
        url: 'https://polymarket.com/event/example',
      },
    ],
    explanation_steps: generateExplanationSteps(),
    trace_id: randomId('trace'),
    observed_at: observedAt.toISOString(),
    generated_at: now.toISOString(),
    source_market: 'Polymarket',
    market_url: 'https://polymarket.com/event/example',
    affected_routes: ['Asia-Europe', 'Trans-Pacific'].slice(0, randomInt(1, 3)),
    affected_chokepoints: [randomFrom(CHOKEPOINTS)],
    affected_systems: ['shipping', 'logistics', 'supply-chain'].slice(0, randomInt(1, 4)),
    expected_onset_hours: randomInt(24, 720),
    expected_duration_hours: randomInt(48, 2160),
    metrics: [
      {
        name: 'Shipping Delay',
        current_value: randomInt(0, 5),
        projected_value: randomInt(5, 20),
        unit: 'days',
        direction: 'up',
        has_uncertainty: true,
        uncertainty_low: randomInt(3, 10),
        uncertainty_high: randomInt(15, 30),
        has_evidence: true,
      },
      {
        name: 'Cost Impact',
        current_value: randomInt(0, 10),
        projected_value: randomInt(10, 50),
        unit: '%',
        direction: 'up',
        has_uncertainty: true,
        uncertainty_low: randomInt(5, 20),
        uncertainty_high: randomInt(30, 80),
        has_evidence: true,
      },
    ],
    probability_history: generateProbabilityHistory(probability),
    detailed_explanation: `This signal was generated from prediction market data indicating elevated probability of ${title.toLowerCase()}. The market shows significant trading activity with confidence derived from liquidity depth and historical reliability.`,
    summary: `Elevated risk detected: ${title}. Probability ${(probability * 100).toFixed(1)}% with ${confidenceLevelFromScore(confidence)} confidence.`,
    has_confidence_breakdown: true,
    probability_is_fallback: false,
    ...overrides,
  };
}

/**
 * Generate explanation chain steps
 */
export function generateExplanationSteps(): ExplanationStep[] {
  return [
    {
      step_id: 1,
      rule_name: 'ingestion',
      rule_version: '1.0.0',
      status: 'passed',
      reasoning: 'Raw event received and normalized successfully from Polymarket API.',
      confidence_contribution: 0.1,
      processing_time_ms: randomBetween(5, 15),
      input_summary: { source: 'polymarket', event_type: 'market_update' },
      output_summary: { normalized: true, schema_valid: true },
    },
    {
      step_id: 2,
      rule_name: 'liquidity_validation',
      rule_version: '2.1.0',
      status: 'passed',
      reasoning: `Liquidity $${randomInt(100, 500)}K exceeds minimum threshold of $1,000.`,
      confidence_contribution: 0.25,
      processing_time_ms: randomBetween(30, 60),
      input_summary: { liquidity_usd: randomInt(100000, 500000), min_threshold: 1000 },
      output_summary: { score: randomBetween(0.7, 0.95), status: 'PASSED' },
    },
    {
      step_id: 3,
      rule_name: 'anomaly_detection',
      rule_version: '1.5.0',
      status: 'passed',
      reasoning: 'No anomalies detected. Probability within expected range for market type.',
      confidence_contribution: 0.2,
      processing_time_ms: randomBetween(20, 40),
      input_summary: { probability: randomBetween(0.1, 0.8), historical_mean: 0.3 },
      output_summary: { risk_score: randomBetween(0.05, 0.2), status: 'PASSED' },
    },
    {
      step_id: 4,
      rule_name: 'semantic_relevance',
      rule_version: '3.0.0',
      status: 'passed',
      reasoning: 'Matched supply chain risk category with high relevance score.',
      confidence_contribution: 0.25,
      processing_time_ms: randomBetween(40, 80),
      input_summary: { title_embedding: '[vector]', category_match: 0.85 },
      output_summary: { category: 'GEOPOLITICAL', relevance: 0.82 },
    },
    {
      step_id: 5,
      rule_name: 'geographic_enrichment',
      rule_version: '2.0.0',
      status: 'passed',
      reasoning: 'Geographic context added. Identified affected shipping routes and chokepoints.',
      confidence_contribution: 0.2,
      processing_time_ms: randomBetween(30, 60),
      input_summary: { regions: ['asia', 'middle-east'], keywords: ['shipping', 'route'] },
      output_summary: { routes_affected: 3, chokepoints: ['malacca_strait'] },
    },
  ];
}

/**
 * Generate a list of signals
 */
export function generateMockSignals(count: number = 10): SignalListResponse {
  const signals: Signal[] = [];
  
  for (let i = 0; i < count; i++) {
    signals.push(generateMockSignal(i));
  }
  
  // Sort by severity (critical first)
  signals.sort((a, b) => b.severity - a.severity);
  
  return {
    signals,
    total: count,
    limit: count,
    offset: 0,
  };
}

/**
 * Generate signal detail by ID
 */
export function generateMockSignalDetail(signalId: string): Signal {
  // Use signalId to seed consistent data
  const index = signalId.charCodeAt(signalId.length - 1) % SIGNAL_TITLES.length;
  return generateMockSignal(index, { signal_id: signalId });
}

/**
 * Generate pipeline statistics
 */
export function generateMockPipelineStats(): PipelineStats {
  const received = randomInt(1000, 2000);
  const validated = Math.floor(received * randomBetween(0.35, 0.5));
  const rejected = received - validated;
  const translated = Math.floor(validated * randomBetween(0.9, 0.98));
  const signals = Math.floor(translated * randomBetween(0.05, 0.15));
  
  return {
    events_received: received,
    events_validated: validated,
    events_rejected: rejected,
    events_translated: translated,
    signals_generated: signals,
    validation_rate: (validated / received) * 100,
    average_confidence: randomBetween(0.55, 0.75),
    processing_time_p50_ms: randomInt(60, 120),
    processing_time_p99_ms: randomInt(200, 400),
    active_signals: signals,
    critical_alerts: Math.floor(signals * randomBetween(0.05, 0.15)),
  };
}

/**
 * Generate system statistics
 */
export function generateMockSystemStats(): SystemStats {
  const pipelineStats = generateMockPipelineStats();
  
  return {
    active_signals: pipelineStats.signals_generated,
    critical_alerts: pipelineStats.critical_alerts,
    avg_confidence: pipelineStats.average_confidence,
    total_risk_exposure: randomBetween(0.3, 0.7),
    events_processed: pipelineStats.events_received,
    events_validated: pipelineStats.events_validated,
    signals_generated: pipelineStats.signals_generated,
    events_rejected: pipelineStats.events_rejected,
    system_latency_ms: pipelineStats.processing_time_p50_ms,
    events_per_second: randomBetween(5, 20),
    uptime_percent: randomBetween(99.5, 99.99),
    validation_rate: pipelineStats.validation_rate / 100,
    events_translated: pipelineStats.events_translated,
  };
}

/**
 * Generate data sources
 */
export function generateMockDataSources(): DataSource[] {
  return [
    { id: 'polymarket', name: 'Polymarket', status: 'healthy', latency: randomInt(80, 150), type: 'real', eventsPerHour: randomInt(500, 1000) },
    { id: 'ais', name: 'AIS Marine', status: 'healthy', latency: randomInt(300, 600), type: 'real', eventsPerHour: randomInt(200, 500) },
    { id: 'commodity', name: 'Commodity', status: 'healthy', latency: randomInt(150, 300), type: 'real', eventsPerHour: randomInt(100, 300) },
    { id: 'weather', name: 'Weather', status: 'warning', latency: randomInt(600, 1000), type: 'real', eventsPerHour: randomInt(50, 150) },
    { id: 'news', name: 'News', status: 'healthy', latency: randomInt(100, 200), type: 'real', eventsPerHour: randomInt(300, 600) },
    { id: 'stock', name: 'Stock', status: 'healthy', latency: randomInt(80, 150), type: 'real', eventsPerHour: randomInt(400, 800) },
    { id: 'freight', name: 'Freight', status: 'mock', latency: 0, type: 'mock', eventsPerHour: 0 },
    { id: 'partner', name: 'Partner Risk', status: 'healthy', latency: randomInt(150, 300), type: 'real', eventsPerHour: randomInt(100, 200) },
  ];
}

/**
 * Generate activity feed
 */
export function generateMockActivityFeed(count: number = 20): ActivityItem[] {
  const items: ActivityItem[] = [];
  const now = Date.now();
  
  for (let i = 0; i < count; i++) {
    const type = randomFrom(['signal_emitted', 'signal_ingested', 'reconcile_completed', 'info'] as const);
    const timestamp = new Date(now - i * randomInt(30000, 300000)).toISOString();
    
    let message: string;
    let signal_id: string | undefined;
    let status_code: number | undefined;
    
    switch (type) {
      case 'signal_emitted':
        signal_id = randomId();
        message = `Signal ${signal_id.slice(0, 16)} emitted`;
        break;
      case 'signal_ingested':
        signal_id = randomId();
        status_code = Math.random() > 0.2 ? 200 : 409;
        message = status_code === 200 
          ? `Ingested ${signal_id.slice(0, 16)}` 
          : `Duplicate rejected: ${signal_id.slice(0, 16)}`;
        break;
      case 'reconcile_completed':
        message = `Partition ${new Date(now - i * 86400000).toISOString().slice(0, 10)} reconciled`;
        break;
      default:
        message = 'System health check passed';
    }
    
    items.push({
      id: `${timestamp}-${i}`,
      type,
      message,
      timestamp,
      signal_id,
      status_code,
    });
  }
  
  return items;
}
