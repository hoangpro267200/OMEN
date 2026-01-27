import type { OmenSignal } from '../types/omen';

export const mockSignal: OmenSignal = {
  signal_id: 'OMEN-RS2024-001',
  event_id: 'polymarket-redsea-001',
  title: 'Red Sea shipping disruption due to Houthi attacks',
  current_probability: 0.75,
  probability_momentum: 'INCREASING',
  confidence_level: 'HIGH',
  confidence_score: 0.82,
  severity: 0.75,
  severity_label: 'High',
  is_actionable: true,
  urgency: 'HIGH',
  key_metrics: [
    {
      name: 'transit_time_increase',
      value: 7.5,
      unit: 'days',
      uncertainty: { lower: 5.3, upper: 9.8 },
      evidence_source: 'Drewry Maritime Research Q1 2024',
    },
    {
      name: 'fuel_consumption_increase',
      value: 22.5,
      unit: '%',
      uncertainty: { lower: 19.1, upper: 25.9 },
      evidence_source: "Lloyd's List Intelligence 2024",
    },
    {
      name: 'freight_rate_pressure',
      value: 56.3,
      unit: '%',
      uncertainty: { lower: 28.1, upper: 112.5 },
      evidence_source: 'Freightos Baltic Index',
    },
  ],
  affected_routes: [
    {
      route_id: 'ASIA-EU-SUEZ',
      route_name: 'Asia to Europe (via Suez)',
      origin_region: 'East Asia',
      destination_region: 'Northern Europe',
      impact_severity: 0.75,
      status: 'blocked',
    },
    {
      route_id: 'ASIA-EU-CAPE',
      route_name: 'Asia to Europe (via Cape of Good Hope)',
      origin_region: 'East Asia',
      destination_region: 'Northern Europe',
      impact_severity: 0.4,
      status: 'alternative',
    },
  ],
  explanation_chain: {
    trace_id: 'trace-abc-123',
    total_steps: 3,
    steps: [
      {
        step_id: 1,
        rule_name: 'liquidity_validation',
        rule_version: '1.0.0',
        status: 'passed',
        reasoning:
          'Sufficient liquidity: $75,000 >= $1,000 threshold',
        confidence_contribution: 0.3,
      },
      {
        step_id: 2,
        rule_name: 'geographic_relevance',
        rule_version: '2.0.0',
        status: 'passed',
        reasoning:
          'Relevant to 2 chokepoints: Red Sea, Suez Canal',
        confidence_contribution: 0.25,
      },
      {
        step_id: 3,
        rule_name: 'red_sea_disruption_logistics',
        rule_version: '2.0.0',
        status: 'passed',
        reasoning:
          '75% probability triggers rerouting via Cape of Good Hope, adding ~7.5 days transit time',
        confidence_contribution: 0.45,
      },
    ],
  },
};
