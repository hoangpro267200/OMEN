/**
 * Mock data for Overview Dashboard (KPIs, activity feed).
 */

export interface OverviewActivityEvent {
  time: string;
  id: string;
  status: string;
  channel: string;
}

export interface OverviewKpiData {
  signalsToday: number;
  signalsTrend: string;
  signalsTrendUp: boolean;
  hotPathOk: number;
  hotPathPct: string;
  duplicates: number;
  duplicatesSub: string;
  partitionsSealed: number;
  partitionsOpen: number;
  partitionsSub: string;
  lastReconcile: string;
  lastReconcileStatus: string;
}

export const defaultOverviewKpis: OverviewKpiData = {
  signalsToday: 247,
  signalsTrend: '↑ 12%',
  signalsTrendUp: true,
  hotPathOk: 245,
  hotPathPct: '99.2%',
  duplicates: 2,
  duplicatesSub: '(409s)',
  partitionsSealed: 3,
  partitionsOpen: 1,
  partitionsSub: 'sealed/open',
  lastReconcile: '2m ago ✓',
  lastReconcileStatus: 'COMPLETED',
};

export const defaultOverviewActivity: OverviewActivityEvent[] = [
  { time: '10:05:32', id: 'OMEN-DEMO007', status: 'Delivered', channel: 'hot_path' },
  { time: '10:05:30', id: 'OMEN-DEMO006', status: 'Delivered', channel: 'hot_path' },
  { time: '10:05:28', id: 'OMEN-DEMO005', status: 'Duplicate', channel: '409' },
  { time: '10:05:25', id: 'OMEN-DEMO004', status: 'Delivered', channel: 'hot_path' },
  { time: '10:05:22', id: 'OMEN-DEMO003', status: 'Delivered', channel: 'hot_path' },
  { time: '10:05:18', id: 'OMEN-DEMO002', status: 'Duplicate', channel: '409' },
  { time: '10:05:15', id: 'OMEN-DEMO001', status: 'Delivered', channel: 'hot_path' },
];
