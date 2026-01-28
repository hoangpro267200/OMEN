/**
 * Tests to verify UI displays only real data.
 * Phase 6: DEMO vs LIVE labels, no fabricated uncertainty.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '../App';
import { ImpactMetricCard } from '../components/analysis/ImpactMetricCard';
import type { ProcessedImpactMetric, ProcessedSignal } from '../types/omen';
import {
  useProcessLiveSignals,
  useSystemStats,
  useActivityFeed,
} from '../hooks/useOmenApi';
import { useDataSource } from '../hooks/useDataSource';

const mockLiveSignals: ProcessedSignal[] = [
  {
    signal_id: 'OMEN-TEST-001',
    title: 'Test signal',
    probability: 0.75,
    probability_history: [0.7, 0.72, 0.74, 0.75],
    probability_momentum: 'STABLE',
    confidence_level: 'HIGH',
    confidence_score: 0.82,
    confidence_breakdown: { liquidity: 0.85, geographic: 0.9, semantic: 0.8, anomaly: 0.8, market_depth: 0.8, source_reliability: 0.85 },
    has_confidence_breakdown: true,
    severity: 0.7,
    severity_label: 'HIGH',
    is_actionable: true,
    urgency: 'HIGH',
    metrics: [
      {
        name: 'transit_time',
        value: 7.5,
        unit: 'days',
        uncertainty: { lower: 5.3, upper: 9.8 },
        baseline: 0,
        projection: [],
        evidence_source: null,
        has_uncertainty: true,
        has_projection: false,
        has_evidence: false,
      },
    ],
    affected_routes: [],
    affected_chokepoints: [],
    explanation_steps: [],
    generated_at: new Date().toISOString(),
  },
];

vi.mock('../hooks/useOmenApi', () => ({
  useProcessLiveSignals: vi.fn(),
  useSystemStats: vi.fn(),
  useActivityFeed: vi.fn(),
  useProcessSignals: vi.fn(() => ({ mutate: vi.fn() })),
  useProcessSingleSignal: vi.fn(() => ({ mutate: vi.fn() })),
  useLiveEvents: vi.fn(() => ({ data: [] })),
  useProcessEvents: vi.fn(() => ({ mutate: vi.fn() })),
  useProcessSingleEvent: vi.fn(() => ({ mutate: vi.fn() })),
  useSearchEvents: vi.fn(() => ({ data: [] })),
}));

vi.mock('../hooks/useDataSource', () => ({
  useDataSource: vi.fn(),
}));

vi.mock('../hooks/useRealtimePrices', () => ({
  useRealtimePrices: vi.fn(() => ({ error: null })),
  useRealtimeStatus: vi.fn(() => ({ connected: true, error: null })),
}));

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );
}

describe('Data Integrity', () => {
  beforeEach(() => {
    vi.mocked(useProcessLiveSignals).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      dataUpdatedAt: null,
    } as unknown as ReturnType<typeof useProcessLiveSignals>);
    vi.mocked(useSystemStats).mockReturnValue({ data: null } as unknown as ReturnType<typeof useSystemStats>);
    vi.mocked(useActivityFeed).mockReturnValue({ data: [] } as unknown as ReturnType<typeof useActivityFeed>);
  });

  it('should show DEMO label when using mock/demo data', async () => {
    vi.mocked(useDataSource).mockReturnValue({
      data: [],
      source: {
        type: 'demo',
        source: 'Demo data',
        timestamp: null,
        signalCount: 0,
        isStale: false,
        message: 'Đang hiển thị dữ liệu demo.',
      },
    });
    renderApp();
    await waitFor(() => {
      const matches = screen.getAllByText(/DỮ LIỆU DEMO|DEMO/i);
      expect(matches.length).toBeGreaterThan(0);
      expect(matches[0]).toBeInTheDocument();
    });
  });

  it('should show LIVE label only with real data', async () => {
    vi.mocked(useDataSource).mockReturnValue({
      data: mockLiveSignals,
      source: {
        type: 'live',
        source: 'Polymarket via OMEN',
        timestamp: new Date().toISOString(),
        signalCount: 1,
        isStale: false,
        message: '1 tín hiệu từ Polymarket',
      },
    });
    renderApp();
    await waitFor(() => {
      const matches = screen.getAllByText(/TRỰC TIẾP|LIVE/i);
      expect(matches.length).toBeGreaterThan(0);
      expect(matches[0]).toBeInTheDocument();
    });
  });

  it('should not display uncertainty when not provided by API', () => {
    const metricWithoutUncertainty: ProcessedImpactMetric = {
      name: 'transit_time',
      value: 7.5,
      unit: 'days',
      uncertainty: null,
      baseline: 0,
      projection: [],
      evidence_source: null,
      has_uncertainty: false,
      has_projection: false,
      has_evidence: false,
    };
    render(<ImpactMetricCard metric={metricWithoutUncertainty} />);
    expect(screen.getByText(/Độ không chắc chắn: Không có dữ liệu/i)).toBeInTheDocument();
    expect(screen.queryByText(/5\.3.*9\.8/)).not.toBeInTheDocument();
  });

  it('should show methodology when provided', () => {
    const metricWithMethodology: ProcessedImpactMetric = {
      name: 'transit_time',
      value: 7.5,
      unit: 'days',
      uncertainty: null,
      baseline: 0,
      projection: [],
      evidence_source: null,
      methodology_name: 'red_sea_transit_time_impact',
      methodology_version: '2.0.0',
      has_uncertainty: false,
      has_projection: false,
      has_evidence: false,
    };
    render(<ImpactMetricCard metric={metricWithMethodology} />);
    expect(screen.getByText(/Phương pháp: red_sea_transit_time_impact v2\.0\.0/)).toBeInTheDocument();
  });
});
