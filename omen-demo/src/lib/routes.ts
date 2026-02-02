/**
 * Route paths and config for OMEN Signal Intelligence Engine
 * Neural Command Center navigation
 */

export const ROUTES = {
  overview: '/',
  pipeline: '/pipeline',
  sources: '/sources',
  partitions: '/partitions',
  signals: '/signals',
  ingestDemo: '/ingest-demo',
  ledgerProof: '/ledger-proof',
} as const;

export type RouteId = keyof typeof ROUTES;

export const ROUTE_LABELS: Record<RouteId, string> = {
  overview: 'Command Center',
  pipeline: 'Pipeline',
  sources: 'Data Sources',
  partitions: 'Partitions',
  signals: 'Signal Monitor',
  ingestDemo: 'Ingest Demo',
  ledgerProof: 'Ledger',
};
