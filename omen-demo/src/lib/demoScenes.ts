/**
 * Demo Mode — scene definitions for scripted presentation.
 * Order: Overview → Ingest Demo → Partitions → Partition Detail → Ledger Proof → Signals.
 */

export type DemoActionType = 'click' | 'input' | 'wait' | 'highlight';

export interface DemoAction {
  type: DemoActionType;
  target?: string; // data-demo-target value or id (optional for 'wait')
  value?: string; // for type "input"
  delay: number; // ms after previous action
}

export interface DemoScene {
  id: number;
  title: string;
  route: string;
  duration: string;
  script: string;
  actions: DemoAction[];
}

export const DEMO_SCENES: DemoScene[] = [
  {
    id: 1,
    title: 'Overview',
    route: '/',
    duration: '30s',
    script: "Show pipeline flow, KPIs, and proof cards. Emphasize 'ledger first, hot path second.'",
    actions: [
      { type: 'highlight', target: 'pipeline-diagram', delay: 1000 },
      { type: 'highlight', target: 'kpi-grid', delay: 3000 },
      { type: 'highlight', target: 'proof-cards', delay: 5000 },
    ],
  },
  {
    id: 2,
    title: 'Ingest Demo',
    route: '/ingest-demo',
    duration: '40s',
    script: 'Send 1 request → 200. Send 5 duplicates → all 409 with SAME ack_id.',
    actions: [
      { type: 'wait', delay: 1000 },
      { type: 'click', target: 'send-one-button', delay: 2000 },
      { type: 'wait', delay: 1500 },
      { type: 'highlight', target: 'counter-200', delay: 500 },
      { type: 'highlight', target: 'ack-id-display', delay: 1000 },
      { type: 'click', target: 'send-duplicates-button', delay: 2000 },
      { type: 'wait', delay: 3000 },
      { type: 'highlight', target: 'counter-409', delay: 500 },
      { type: 'highlight', target: 'request-log', delay: 1000 },
    ],
  },
  {
    id: 3,
    title: 'Partitions',
    route: '/partitions',
    duration: '15s',
    script: 'Show partition list. Point out SEALED vs OPEN, MAIN vs LATE.',
    actions: [
      { type: 'highlight', target: 'partition-2026-01-28', delay: 1000 },
      { type: 'highlight', target: 'badge-sealed', delay: 2000 },
      { type: 'highlight', target: 'badge-late', delay: 3000 },
    ],
  },
  {
    id: 4,
    title: 'Partition Detail - Reconcile',
    route: '/partitions/2026-01-28',
    duration: '45s',
    script: "Show 10 vs 8, highlight missing. Run reconcile → 10 vs 10. 'No lost signals.'",
    actions: [
      { type: 'wait', delay: 1000 },
      { type: 'highlight', target: 'completeness-gauge', delay: 1000 },
      { type: 'highlight', target: 'ledger-count', delay: 1500 },
      { type: 'highlight', target: 'processed-count', delay: 1500 },
      { type: 'highlight', target: 'missing-count', delay: 1500 },
      { type: 'highlight', target: 'missing-ids-list', delay: 2000 },
      { type: 'click', target: 'run-reconcile-button', delay: 3000 },
      { type: 'wait', delay: 2000 },
      { type: 'highlight', target: 'reconcile-success', delay: 1000 },
    ],
  },
  {
    id: 5,
    title: 'Ledger Proof',
    route: '/ledger-proof',
    duration: '30s',
    script: 'Show WAL frame structure. Run crash-tail demo → 2 valid records.',
    actions: [
      { type: 'highlight', target: 'frame-diagram', delay: 1000 },
      { type: 'click', target: 'simulate-crash-button', delay: 2000 },
      { type: 'wait', delay: 1500 },
      { type: 'click', target: 'run-read-button', delay: 1500 },
      { type: 'wait', delay: 2000 },
      { type: 'highlight', target: 'proof-result', delay: 1000 },
    ],
  },
  {
    id: 6,
    title: 'Signals Browser',
    route: '/signals',
    duration: '20s',
    script: 'Search for late signal. Show envelope details, trace journey.',
    actions: [
      { type: 'input', target: 'search-input', value: 'OMEN-DEMO008LATE', delay: 1000 },
      { type: 'wait', delay: 1000 },
      { type: 'click', target: 'signal-row-OMEN-DEMO008LATE', delay: 1500 },
      { type: 'wait', delay: 500 },
      { type: 'highlight', target: 'signal-drawer', delay: 1000 },
    ],
  },
];

export const DEMO_SCENE_COUNT = DEMO_SCENES.length;
export const TOTAL_DEMO_DURATION = '3 minutes';

/** Route order for syncing location with scene index */
export const DEMO_SCENE_ROUTES = DEMO_SCENES.map((s) => s.route);

/** Find scene index by path (exact or base match for dynamic routes like /partitions/:id) */
export function getSceneIndexForPath(pathname: string): number {
  const exact = DEMO_SCENE_ROUTES.indexOf(pathname);
  if (exact >= 0) return exact;
  if (pathname.startsWith('/partitions/') && pathname !== '/partitions') return 3; // Partition Detail
  return 0;
}
