/**
 * Mock RiskCast Risk Assessment Data for Demo UI
 * 
 * Shows risk scoring, alerts, and order assessments.
 */

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'negligible';
export type AlertPriority = 'P1' | 'P2' | 'P3' | 'P4';

export interface RiskFactor {
  factor_name: string;
  score: number;
  weight: number;
  reasoning: string;
}

export interface RiskAssessment {
  assessment_id: string;
  signal_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  factors: RiskFactor[];
  weighted_score: number;
  estimated_impact_usd: number | null;
  affected_orders: string[];
  affected_routes: string[];
  alert_priority: AlertPriority;
  alert_generated: boolean;
  alert_message: string | null;
  assessed_at: string;
  model_version: string;
}

export interface OrderRisk {
  order_id: string;
  origin: string;
  destination: string;
  cargo_type: string;
  value_usd: number;
  assessment: RiskAssessment;
}

export interface ShippingEvent {
  event_id: string;
  event_type: 'port_delay' | 'route_disruption' | 'capacity_change' | 'weather_alert' | 'strike';
  location: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  details: Record<string, unknown>;
  assessment: RiskAssessment;
  created_at: string;
}

export interface Alert {
  alert_id: string;
  signal_id: string;
  priority: AlertPriority;
  message: string;
  created_at: string;
  acknowledged: boolean;
}

// =============================================================================
// MOCK DATA: Risk Assessments from OMEN Signals
// =============================================================================

export const mockRiskAssessments: RiskAssessment[] = [
  {
    assessment_id: 'assess-001abc',
    signal_id: 'OMEN-DEMO001ABCD',
    risk_score: 78.5,
    risk_level: 'high',
    confidence: 0.85,
    factors: [
      {
        factor_name: 'probability_factor',
        score: 0.78,
        weight: 0.3,
        reasoning: 'Market probability 78.0%',
      },
      {
        factor_name: 'keyword_severity',
        score: 0.85,
        weight: 0.3,
        reasoning: 'Event severity from keywords: attack, disruption',
      },
      {
        factor_name: 'geographic_exposure',
        score: 0.9,
        weight: 0.25,
        reasoning: 'Chokepoint multiplier: 1.5x (Bab el-Mandeb)',
      },
      {
        factor_name: 'confidence_factor',
        score: 0.85,
        weight: 0.15,
        reasoning: 'Signal confidence: 0.85',
      },
    ],
    weighted_score: 0.8365,
    estimated_impact_usd: 2500000,
    affected_orders: ['ORD-2026-001234', 'ORD-2026-001235'],
    affected_routes: ['bab_el_mandeb', 'suez_canal', 'red_sea'],
    alert_priority: 'P2',
    alert_generated: true,
    alert_message: '[P2] Risk Alert: Red Sea Shipping Lane Disruption - Risk Score: 78.5/100 (high)',
    assessed_at: '2026-02-02T10:30:00Z',
    model_version: 'riskcast-v1.0',
  },
  {
    assessment_id: 'assess-002xyz',
    signal_id: 'OMEN-DEMO002WXYZ',
    risk_score: 52.3,
    risk_level: 'medium',
    confidence: 0.72,
    factors: [
      {
        factor_name: 'probability_factor',
        score: 0.65,
        weight: 0.3,
        reasoning: 'Market probability 65.0%',
      },
      {
        factor_name: 'keyword_severity',
        score: 0.5,
        weight: 0.3,
        reasoning: 'Event severity from keywords: congestion, delay',
      },
      {
        factor_name: 'geographic_exposure',
        score: 0.6,
        weight: 0.25,
        reasoning: 'Chokepoint multiplier: 1.3x (Panama Canal)',
      },
      {
        factor_name: 'confidence_factor',
        score: 0.72,
        weight: 0.15,
        reasoning: 'Signal confidence: 0.72',
      },
    ],
    weighted_score: 0.5875,
    estimated_impact_usd: 85000,
    affected_orders: ['ORD-2026-001238'],
    affected_routes: ['panama_canal'],
    alert_priority: 'P3',
    alert_generated: false,
    alert_message: null,
    assessed_at: '2026-02-02T10:35:00Z',
    model_version: 'riskcast-v1.0',
  },
  {
    assessment_id: 'assess-003pqr',
    signal_id: 'OMEN-DEMO003PQRS',
    risk_score: 85.2,
    risk_level: 'critical',
    confidence: 0.88,
    factors: [
      {
        factor_name: 'probability_factor',
        score: 0.82,
        weight: 0.3,
        reasoning: 'Market probability 82.0%',
      },
      {
        factor_name: 'keyword_severity',
        score: 0.9,
        weight: 0.3,
        reasoning: 'Event severity from keywords: shutdown, typhoon',
      },
      {
        factor_name: 'geographic_exposure',
        score: 0.75,
        weight: 0.25,
        reasoning: 'Major port: Shanghai',
      },
      {
        factor_name: 'confidence_factor',
        score: 0.88,
        weight: 0.15,
        reasoning: 'Signal confidence: 0.88',
      },
    ],
    weighted_score: 0.8435,
    estimated_impact_usd: 4200000,
    affected_orders: ['ORD-2026-001234', 'ORD-2026-001239', 'ORD-2026-001240'],
    affected_routes: ['shanghai_port', 'yangtze_delta'],
    alert_priority: 'P1',
    alert_generated: true,
    alert_message: '[P1] CRITICAL: Shanghai Port - Typhoon Warning Level 3 - Risk Score: 85.2/100',
    assessed_at: '2026-02-02T10:40:00Z',
    model_version: 'riskcast-v1.0',
  },
];

// =============================================================================
// MOCK DATA: Order Risk Assessments
// =============================================================================

export const mockOrderRisks: OrderRisk[] = [
  {
    order_id: 'ORD-2026-001234',
    origin: 'Shanghai',
    destination: 'Rotterdam',
    cargo_type: 'Electronics',
    value_usd: 2500000,
    assessment: {
      assessment_id: 'order-assess-001',
      signal_id: 'order-ORD-2026-001234',
      risk_score: 65.5,
      risk_level: 'high',
      confidence: 0.75,
      factors: [
        {
          factor_name: 'route_risk',
          score: 0.7,
          weight: 0.5,
          reasoning: 'Route Shanghai → Rotterdam passes through Red Sea',
        },
        {
          factor_name: 'value_exposure',
          score: 0.8,
          weight: 0.3,
          reasoning: 'Order value: $2,500,000.00 (high value cargo)',
        },
        {
          factor_name: 'cargo_sensitivity',
          score: 0.6,
          weight: 0.2,
          reasoning: 'Cargo type: Electronics (moderate sensitivity)',
        },
      ],
      weighted_score: 0.71,
      estimated_impact_usd: 1625000,
      affected_orders: ['ORD-2026-001234'],
      affected_routes: ['Shanghai → Rotterdam'],
      alert_priority: 'P2',
      alert_generated: true,
      alert_message: 'Order ORD-2026-001234: Risk score 65.5 - Route exposed to Red Sea disruption',
      assessed_at: '2026-02-02T09:00:00Z',
      model_version: 'riskcast-v1.0',
    },
  },
  {
    order_id: 'ORD-2026-001235',
    origin: 'Shenzhen',
    destination: 'Los Angeles',
    cargo_type: 'Consumer Goods',
    value_usd: 850000,
    assessment: {
      assessment_id: 'order-assess-002',
      signal_id: 'order-ORD-2026-001235',
      risk_score: 45.2,
      risk_level: 'medium',
      confidence: 0.75,
      factors: [
        {
          factor_name: 'route_risk',
          score: 0.5,
          weight: 0.5,
          reasoning: 'Route Shenzhen → LA (Transpacific, lower risk)',
        },
        {
          factor_name: 'value_exposure',
          score: 0.4,
          weight: 0.3,
          reasoning: 'Order value: $850,000.00',
        },
        {
          factor_name: 'cargo_sensitivity',
          score: 0.4,
          weight: 0.2,
          reasoning: 'Cargo type: Consumer Goods',
        },
      ],
      weighted_score: 0.45,
      estimated_impact_usd: 382500,
      affected_orders: ['ORD-2026-001235'],
      affected_routes: ['Shenzhen → Los Angeles'],
      alert_priority: 'P3',
      alert_generated: false,
      alert_message: null,
      assessed_at: '2026-02-02T09:05:00Z',
      model_version: 'riskcast-v1.0',
    },
  },
];

// =============================================================================
// MOCK DATA: Shipping Events
// =============================================================================

export const mockShippingEvents: ShippingEvent[] = [
  {
    event_id: 'ship-evt-001',
    event_type: 'route_disruption',
    location: 'Red Sea - Bab el-Mandeb',
    severity: 'critical',
    details: {
      cause: 'Security threat - Houthi attacks',
      reroute_required: true,
      additional_days: 10,
      vessels_affected: 45,
    },
    assessment: mockRiskAssessments[0],
    created_at: '2026-02-02T08:00:00Z',
  },
  {
    event_id: 'ship-evt-002',
    event_type: 'port_delay',
    location: 'Port of Shanghai',
    severity: 'high',
    details: {
      delay_hours: 48,
      cause: 'Typhoon warning Level 3',
      vessels_waiting: 35,
    },
    assessment: mockRiskAssessments[2],
    created_at: '2026-02-02T06:00:00Z',
  },
  {
    event_id: 'ship-evt-003',
    event_type: 'capacity_change',
    location: 'Suez Canal',
    severity: 'medium',
    details: {
      capacity_reduction_pct: 25,
      duration_days: 7,
      reason: 'Vessel grounding cleanup',
    },
    assessment: mockRiskAssessments[1],
    created_at: '2026-02-02T04:00:00Z',
  },
];

// =============================================================================
// MOCK DATA: Active Alerts
// =============================================================================

export const mockAlerts: Alert[] = [
  {
    alert_id: 'alert-001',
    signal_id: 'OMEN-DEMO003PQRS',
    priority: 'P1',
    message: '[P1] CRITICAL: Shanghai Port - Typhoon Warning Level 3 - Immediate action required',
    created_at: '2026-02-02T10:40:00Z',
    acknowledged: false,
  },
  {
    alert_id: 'alert-002',
    signal_id: 'OMEN-DEMO001ABCD',
    priority: 'P2',
    message: '[P2] Red Sea Shipping Disruption - Risk Score: 78.5/100 - Reroute recommended',
    created_at: '2026-02-02T10:30:00Z',
    acknowledged: false,
  },
  {
    alert_id: 'alert-003',
    signal_id: 'order-ORD-2026-001234',
    priority: 'P2',
    message: '[P2] Order ORD-2026-001234 ($2.5M) exposed to Red Sea route disruption',
    created_at: '2026-02-02T09:00:00Z',
    acknowledged: true,
  },
];

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

export function getRiskLevelColor(level: RiskLevel): string {
  switch (level) {
    case 'critical':
      return '#dc2626'; // red-600
    case 'high':
      return '#ea580c'; // orange-600
    case 'medium':
      return '#ca8a04'; // yellow-600
    case 'low':
      return '#16a34a'; // green-600
    case 'negligible':
      return '#6b7280'; // gray-500
    default:
      return '#6b7280';
  }
}

export function getAlertPriorityColor(priority: AlertPriority): string {
  switch (priority) {
    case 'P1':
      return '#dc2626'; // red-600
    case 'P2':
      return '#ea580c'; // orange-600
    case 'P3':
      return '#ca8a04'; // yellow-600
    case 'P4':
      return '#6b7280'; // gray-500
    default:
      return '#6b7280';
  }
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

// =============================================================================
// MOCK API FUNCTIONS (for demo mode)
// =============================================================================

/** Simulate API call to get risk assessments */
export async function mockGetRiskAssessments(): Promise<RiskAssessment[]> {
  await new Promise((r) => setTimeout(r, 300));
  return mockRiskAssessments;
}

/** Simulate API call to assess order risk */
export async function mockAssessOrderRisk(order: {
  order_id: string;
  origin: string;
  destination: string;
  cargo_type: string;
  value_usd: number;
}): Promise<RiskAssessment> {
  await new Promise((r) => setTimeout(r, 400));
  
  // Find existing or generate new
  const existing = mockOrderRisks.find((o) => o.order_id === order.order_id);
  if (existing) return existing.assessment;
  
  // Generate mock assessment
  const baseRisk = 
    (order.origin.toLowerCase().includes('shanghai') ? 0.2 : 0) +
    (order.destination.toLowerCase().includes('rotterdam') ? 0.1 : 0) +
    (order.value_usd > 1000000 ? 0.15 : 0.05);
  
  const riskScore = Math.min(100, baseRisk * 100 + Math.random() * 20);
  const riskLevel: RiskLevel = 
    riskScore >= 80 ? 'critical' :
    riskScore >= 60 ? 'high' :
    riskScore >= 40 ? 'medium' :
    riskScore >= 20 ? 'low' : 'negligible';
  
  return {
    assessment_id: `order-assess-${Date.now()}`,
    signal_id: `order-${order.order_id}`,
    risk_score: Math.round(riskScore * 10) / 10,
    risk_level: riskLevel,
    confidence: 0.75,
    factors: [
      {
        factor_name: 'route_risk',
        score: baseRisk,
        weight: 0.5,
        reasoning: `Route ${order.origin} → ${order.destination}`,
      },
    ],
    weighted_score: baseRisk,
    estimated_impact_usd: order.value_usd * baseRisk,
    affected_orders: [order.order_id],
    affected_routes: [`${order.origin} → ${order.destination}`],
    alert_priority: riskScore >= 60 ? 'P2' : 'P3',
    alert_generated: riskScore >= 50,
    alert_message: riskScore >= 50 ? `Order ${order.order_id}: Risk score ${riskScore.toFixed(1)}` : null,
    assessed_at: new Date().toISOString(),
    model_version: 'riskcast-v1.0',
  };
}

/** Simulate API call to get alerts */
export async function mockGetAlerts(): Promise<Alert[]> {
  await new Promise((r) => setTimeout(r, 200));
  return mockAlerts;
}
