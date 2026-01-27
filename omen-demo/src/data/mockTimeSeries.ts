/**
 * Mock time-series for charts (probability history, impact projections, etc.)
 */

export interface TimePoint {
  time: string;
  value: number;
  lower?: number;
  upper?: number;
}

export function last24hProbabilityHistory(history: number[]): TimePoint[] {
  const now = Date.now();
  const step = (24 * 60 * 60 * 1000) / Math.max(1, history.length - 1);
  return history.map((v, i) => ({
    time: new Date(now - (history.length - 1 - i) * step).toISOString(),
    value: v * 100,
    lower: Math.max(0, v * 100 - 5),
    upper: Math.min(100, v * 100 + 5),
  }));
}

export function impactProjectionData(
  baseName: string,
  projection: number[],
  dayCount = 30
): { day: number; value: number; name: string }[] {
  const step = dayCount / Math.max(1, projection.length - 1);
  return projection.map((v, i) => ({
    day: Math.round(i * step),
    value: v,
    name: baseName,
  }));
}

export const severityDistribution = [
  { name: 'Critical', value: 3, fill: '#ef4444' },
  { name: 'High', value: 4, fill: '#f97316' },
  { name: 'Medium', value: 3, fill: '#f59e0b' },
  { name: 'Low', value: 2, fill: '#10b981' },
];

export const processingFunnelData = [
  { stage: 'Raw events', value: 1247, fill: '#3b82f6' },
  { stage: 'Validated', value: 892, fill: '#06b6d4' },
  { stage: 'Translated', value: 654, fill: '#10b981' },
  { stage: 'Signals', value: 127, fill: '#8b5cf6' },
];

export const geographicRiskData = [
  { region: 'Middle East', risk: 92, severity: 'CRITICAL' },
  { region: 'Asia', risk: 65, severity: 'HIGH' },
  { region: 'Europe', risk: 48, severity: 'MEDIUM' },
  { region: 'Americas', risk: 35, severity: 'LOW' },
];
