/**
 * OMEN data models — aligned with backend SignalEvent, OmenSignal, API responses.
 * Dual-path signal intelligence pipeline contract.
 */

/* ---------------------------------------------------------------------------
   Enums (match backend)
   --------------------------------------------------------------------------- */

export type SignalType =
  | 'GEOPOLITICAL_CONFLICT'
  | 'GEOPOLITICAL_SANCTIONS'
  | 'GEOPOLITICAL_DIPLOMATIC'
  | 'SUPPLY_CHAIN_DISRUPTION'
  | 'SHIPPING_ROUTE_RISK'
  | 'PORT_OPERATIONS'
  | 'ENERGY_SUPPLY'
  | 'ENERGY_INFRASTRUCTURE'
  | 'LABOR_DISRUPTION'
  | 'CLIMATE_EVENT'
  | 'NATURAL_DISASTER'
  | 'REGULATORY_CHANGE'
  | 'UNCLASSIFIED';

export type SignalStatus =
  | 'CANDIDATE'
  | 'ACTIVE'
  | 'MONITORING'
  | 'DEGRADED'
  | 'RESOLVED'
  | 'INVALIDATED';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type SignalCategory =
  | 'GEOPOLITICAL'
  | 'INFRASTRUCTURE'
  | 'WEATHER'
  | 'ECONOMIC'
  | 'REGULATORY'
  | 'SECURITY'
  | 'OTHER';

/** Ledger/delivery status (SEALED, OPEN, LATE, FAILED, COMPLETED, PARTIAL) */
export type DeliveryStatus =
  | 'SEALED'
  | 'OPEN'
  | 'LATE'
  | 'FAILED'
  | 'COMPLETED'
  | 'PARTIAL';

/* ---------------------------------------------------------------------------
   Nested context (API response shape)
   --------------------------------------------------------------------------- */

export interface GeographicContextResponse {
  regions: string[];
  chokepoints: string[];
}

export interface TemporalContextResponse {
  event_horizon: string | null;
  resolution_date: string | null;
}

export interface EvidenceResponse {
  source: string;
  source_type: string;
  url: string | null;
}

export interface ImpactHintsResponse {
  domains: string[];
  direction: string;
  affected_asset_types: string[];
  keywords: string[];
}

/* ---------------------------------------------------------------------------
   OmenSignal (API SignalResponse — public contract)
   --------------------------------------------------------------------------- */

export interface OmenSignalResponse {
  signal_id: string;
  source_event_id: string;
  signal_type: SignalType | string;
  status: SignalStatus | string;
  impact_hints: ImpactHintsResponse;

  title: string;
  description: string | null;

  probability: number;
  probability_source: string;
  probability_is_estimate: boolean;

  confidence_score: number;
  confidence_level: ConfidenceLevel | string;
  confidence_factors: Record<string, number>;
  confidence_method?: string | null;

  category: SignalCategory | string;
  tags: string[];

  geographic: GeographicContextResponse;
  temporal: TemporalContextResponse;
  evidence: EvidenceResponse[];

  trace_id: string;
  ruleset_version: string;
  source_url: string | null;
  observed_at: string | null;
  generated_at: string;
}

/* ---------------------------------------------------------------------------
   SignalEvent (envelope: hot path + cold path / ledger)
   --------------------------------------------------------------------------- */

export interface SignalEventEnvelope {
  schema_version: string;
  signal_id: string;
  deterministic_trace_id: string;
  input_event_hash: string;
  source_event_id: string;
  ruleset_version: string;
  observed_at: string;
  emitted_at: string;
  ledger_written_at?: string | null;
  signal: OmenSignalResponse;
  ledger_partition?: string | null;
  ledger_sequence?: number | null;
}

/* ---------------------------------------------------------------------------
   API list / stats responses
   --------------------------------------------------------------------------- */

export interface SignalListResponse {
  signals: OmenSignalResponse[];
  total: number;
  processed: number;
  passed: number;
  rejected: number;
  pass_rate: number;
}

export interface PipelineStatsResponse {
  total_processed: number;
  total_passed: number;
  total_rejected: number;
  pass_rate: number;
  rejection_by_stage: Record<string, number>;
  latency_ms: number;
  uptime_seconds: number;
}

/* ---------------------------------------------------------------------------
   Ledger record (integrity)
   --------------------------------------------------------------------------- */

export interface LedgerRecordResponse {
  checksum: string;
  length: number;
  signal: SignalEventEnvelope['signal'];
}
