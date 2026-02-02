/**
 * Route paths and config for OMEN demo shell.
 */

export const ROUTES = {
  overview: '/',
  partitions: '/partitions',
  signals: '/signals',
  ingestDemo: '/ingest-demo',
  ledgerProof: '/ledger-proof',
} as const;

export type RouteId = keyof typeof ROUTES;

export const ROUTE_LABELS: Record<RouteId, string> = {
  overview: 'Overview',
  partitions: 'Partitions',
  signals: 'Signals',
  ingestDemo: 'Ingest Demo',
  ledgerProof: 'Ledger Proof',
};
