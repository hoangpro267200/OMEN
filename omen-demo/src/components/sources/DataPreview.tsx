/**
 * DataPreview - Neural Command Center live data preview panel
 * Features: Syntax-highlighted JSON, auto-refresh, copy functionality
 */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, RefreshCw, Check } from 'lucide-react';
import { cn } from '../../lib/utils';

const SAMPLE_DATA: Record<string, object> = {
  polymarket: {
    event_id: 'polymarket-677404',
    title: 'China x India military clash by December 31, 2026?',
    probability: 0.175,
    liquidity: 150000,
    volume: 500000,
    num_traders: 1200,
    last_updated: '2026-01-29T14:32:00Z',
  },
  ais: {
    port_code: 'SGSIN',
    vessels_waiting: 35,
    normal_waiting: 25,
    congestion_ratio: 1.4,
    avg_wait_time_hours: 18.0,
    anomaly_detected: true,
  },
  commodity: {
    asset: 'CRUDE_OIL',
    price_usd: 82.45,
    change_24h: 2.3,
    volatility: 'HIGH',
    supply_disruption_risk: 0.35,
  },
  weather: {
    storm_id: 'WP202601',
    name: 'Typhoon Haiyan',
    category: 4,
    wind_speed_kts: 130,
    affected_ports: ['HKHKG', 'CNSHA'],
    path_confidence: 0.8,
  },
  news: {
    article_id: 'reuters-20260129-001',
    headline: 'Red Sea shipping disruptions continue amid regional tensions',
    source: 'Reuters',
    sentiment: -0.65,
    relevance_score: 0.92,
    entities: ['Suez Canal', 'Houthi', 'shipping'],
  },
  stock: {
    ticker: 'MAERSK.CO',
    price: 1245.5,
    change_pct: -2.3,
    volume: 1200000,
    market_cap: '25.4B',
  },
  freight: {
    route: 'Shanghai-Rotterdam',
    rate_usd: 4500,
    change_week: 12.5,
    capacity_utilization: 0.87,
    eta_days: 35,
  },
  partner: {
    company_id: 'ACME-001',
    risk_score: 0.23,
    financial_health: 'STABLE',
    supply_chain_exposure: ['China', 'Taiwan'],
    last_assessment: '2026-01-15',
  },
};

interface DataPreviewProps {
  sourceId: string | null;
  className?: string;
}

export function DataPreview({ sourceId, className }: DataPreviewProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [copied, setCopied] = useState(false);

  const data = sourceId ? SAMPLE_DATA[sourceId] : null;

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  const handleCopy = () => {
    if (data) {
      navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!sourceId || !data) {
    return (
      <div className="h-[200px] flex items-center justify-center text-text-muted">
        Select a source to preview live data
      </div>
    );
  }

  // Syntax highlight JSON
  const highlightJson = (json: string): string => {
    return json
      .replace(/"([^"]+)":/g, '<span class="text-accent-amber">"$1"</span>:')
      .replace(/: "([^"]+)"/g, ': <span class="text-status-success">"$1"</span>')
      .replace(/: (\d+\.?\d*)/g, ': <span class="text-accent-cyan">$1</span>')
      .replace(/: (true|false)/g, ': <span class="text-status-warning">$1</span>')
      .replace(/: (null)/g, ': <span class="text-text-muted">$1</span>');
  };

  const jsonLines = JSON.stringify(data, null, 2).split('\n');

  return (
    <div className={cn('space-y-3', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-text-muted">
          Sample data from <span className="text-accent-cyan font-mono">{sourceId}</span>
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors"
            title="Refresh"
          >
            <RefreshCw
              className={cn('w-4 h-4 text-text-muted', isRefreshing && 'animate-spin')}
            />
          </button>
          <button
            onClick={handleCopy}
            className="p-2 rounded-lg hover:bg-bg-tertiary transition-colors"
            title="Copy to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-status-success" />
            ) : (
              <Copy className="w-4 h-4 text-text-muted" />
            )}
          </button>
        </div>
      </div>

      {/* JSON Preview */}
      <motion.div
        key={sourceId}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="relative"
      >
        <pre className="p-4 rounded-lg bg-bg-primary overflow-auto max-h-[300px] text-sm font-mono border border-border-subtle">
          <code className="text-text-secondary">
            {jsonLines.map((line, i) => (
              <div key={i} className="flex">
                <span className="w-8 text-text-muted select-none text-right pr-3">{i + 1}</span>
                <span dangerouslySetInnerHTML={{ __html: highlightJson(line) }} />
              </div>
            ))}
          </code>
        </pre>

        {/* Refresh overlay */}
        {isRefreshing && (
          <div className="absolute inset-0 bg-bg-primary/80 flex items-center justify-center rounded-lg">
            <RefreshCw className="w-6 h-6 text-accent-cyan animate-spin" />
          </div>
        )}
      </motion.div>
    </div>
  );
}
