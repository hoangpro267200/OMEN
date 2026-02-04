/**
 * Interactive panel showing rejected and passed events.
 * Uses /api/v1/debug/rejections and /api/v1/debug/passed.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronUp, Filter, Check, X } from 'lucide-react';
import { OMEN_API_BASE } from '../../lib/apiBase';

const API_BASE = OMEN_API_BASE;
const API_KEY = import.meta.env.VITE_API_KEY || '';

// Helper to create headers with API key
const getHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_KEY) headers['X-API-Key'] = API_KEY;
  return headers;
};

interface RejectionRecord {
  event_id: string;
  stage: string;
  reason: string;
  timestamp: string;
  title?: string;
  probability?: number;
  liquidity?: number;
  keywords_found?: string[];
  rule_name?: string;
}

interface PassedRecord {
  signal_id: string;
  event_id: string;
  timestamp: string;
  title: string;
  probability: number;
  confidence: number;
  severity: string;
  metrics_count: number;
}

interface PipelineStats {
  total_processed: number;
  total_rejected: number;
  total_passed: number;
  pass_rate: number;
  by_stage: Record<string, { count: number; percentage: number }>;
  top_rejection_reasons: { reason: string; count: number }[];
}

function TabButton({
  active,
  onClick,
  children,
  count,
  color,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  count?: number;
  color?: 'red' | 'green';
}) {
  return (
    <button
      onClick={onClick}
      className={
        active
          ? 'border-b-2 border-[var(--accent-cyan)] bg-[var(--bg-elevated)] px-4 py-2 text-sm font-medium'
          : 'px-4 py-2 text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)]'
      }
    >
      {children}
      {count !== undefined && (
        <span
          className={`ml-2 rounded px-1.5 py-0.5 text-xs ${
            color === 'red'
              ? 'bg-red-500/20 text-red-400'
              : color === 'green'
                ? 'bg-green-500/20 text-green-400'
                : 'bg-[var(--bg-hover)]'
          }`}
        >
          {count}
        </span>
      )}
    </button>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color?: 'red' | 'green';
}) {
  return (
    <div className="rounded-lg bg-[var(--bg-elevated)] p-3">
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <p
        className={`text-xl font-bold ${
          color === 'red'
            ? 'text-red-400'
            : color === 'green'
              ? 'text-green-400'
              : 'text-[var(--text-primary)]'
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function StatsView({ stats }: { stats: PipelineStats }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Processed" value={stats.total_processed} />
        <StatCard label="Rejected" value={stats.total_rejected} color="red" />
        <StatCard label="Passed" value={stats.total_passed} color="green" />
        <StatCard
          label="Pass Rate"
          value={`${(stats.pass_rate * 100).toFixed(1)}%`}
          color={stats.pass_rate > 0.1 ? 'green' : 'red'}
        />
      </div>
      <div>
        <h4 className="mb-2 text-sm font-medium">Rejections by Stage</h4>
        <div className="space-y-1">
          {Object.entries(stats.by_stage).map(([stage, data]) => (
            <div key={stage} className="flex items-center gap-2">
              <span className="w-24 text-xs text-[var(--text-muted)]">{stage}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--bg-hover)]">
                <div
                  className="h-full bg-red-500/50"
                  style={{ width: `${data.percentage * 100}%` }}
                />
              </div>
              <span className="w-12 text-right text-xs">{data.count}</span>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h4 className="mb-2 text-sm font-medium">Top Rejection Reasons</h4>
        <div className="space-y-1">
          {(stats.top_rejection_reasons || []).slice(0, 5).map((item, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="max-w-[80%] truncate text-[var(--text-secondary)]">
                {item.reason}
              </span>
              <span className="text-[var(--text-muted)]">{item.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RejectionCard({ rejection }: { rejection: RejectionRecord }) {
  const [expanded, setExpanded] = useState(false);
  const stageColors: Record<string, string> = {
    validation: 'bg-yellow-500/20 text-yellow-400',
    translation: 'bg-orange-500/20 text-orange-400',
    generation: 'bg-red-500/20 text-red-400',
  };
  return (
    <div
      className="cursor-pointer rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3 transition-colors hover:border-[var(--border-default)]"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={`rounded px-1.5 py-0.5 text-xs ${stageColors[rejection.stage] ?? 'bg-gray-500/20'}`}
            >
              {rejection.stage}
            </span>
            {rejection.rule_name && (
              <span className="text-xs text-[var(--text-muted)]">{rejection.rule_name}</span>
            )}
          </div>
          <p className="truncate text-sm">{rejection.title || rejection.event_id}</p>
          <p className="mt-1 text-xs text-red-400">{rejection.reason}</p>
        </div>
        <X className="h-4 w-4 flex-shrink-0 text-red-400" />
      </div>
      {expanded && (
        <div className="mt-3 space-y-1 border-t border-[var(--border-subtle)] pt-3 text-xs">
          <div className="flex justify-between">
            <span className="text-[var(--text-muted)]">Event ID:</span>
            <span className="font-mono">{rejection.event_id}</span>
          </div>
          {rejection.probability !== undefined && (
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Probability:</span>
              <span>{(rejection.probability * 100).toFixed(1)}%</span>
            </div>
          )}
          {rejection.liquidity !== undefined && (
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Liquidity:</span>
              <span>${rejection.liquidity.toLocaleString()}</span>
            </div>
          )}
          {rejection.keywords_found && rejection.keywords_found.length > 0 && (
            <div>
              <span className="text-[var(--text-muted)]">Keywords:</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {rejection.keywords_found.map((kw) => (
                  <span
                    key={kw}
                    className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px]"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RejectedView({
  rejections,
  selectedStage,
  onStageSelect,
  stats,
}: {
  rejections: RejectionRecord[];
  selectedStage: string | null;
  onStageSelect: (stage: string | null) => void;
  stats: PipelineStats | null;
}) {
  const stages = ['validation', 'translation', 'generation'];
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button
          onClick={() => onStageSelect(null)}
          className={`rounded px-2 py-1 text-xs ${
            !selectedStage ? 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]' : 'bg-[var(--bg-hover)]'
          }`}
        >
          All
        </button>
        {stages.map((stage) => (
          <button
            key={stage}
            onClick={() => onStageSelect(stage)}
            className={`rounded px-2 py-1 text-xs ${
              selectedStage === stage
                ? 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]'
                : 'bg-[var(--bg-hover)]'
            }`}
          >
            {stage} ({stats?.by_stage[stage]?.count ?? 0})
          </button>
        ))}
      </div>
      <div className="space-y-2">
        {rejections.length === 0 ? (
          <p className="py-4 text-center text-sm text-[var(--text-muted)]">
            No rejections recorded yet
          </p>
        ) : (
          rejections.map((r, i) => <RejectionCard key={`${r.event_id}-${i}`} rejection={r} />)
        )}
      </div>
    </div>
  );
}

function PassedCard({ record }: { record: PassedRecord }) {
  const severityColors: Record<string, string> = {
    HIGH: 'text-red-400',
    MEDIUM: 'text-yellow-400',
    LOW: 'text-green-400',
  };
  return (
    <div className="rounded-lg border border-green-500/20 bg-[var(--bg-elevated)] p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="rounded bg-green-500/20 px-1.5 py-0.5 text-xs text-green-400">
              {record.signal_id}
            </span>
            <span
              className={`text-xs ${severityColors[record.severity] ?? ''}`}
            >
              {record.severity}
            </span>
          </div>
          <p className="truncate text-sm">{record.title}</p>
          <div className="mt-1 flex gap-4 text-xs text-[var(--text-muted)]">
            <span>P: {(record.probability * 100).toFixed(0)}%</span>
            <span>C: {(record.confidence * 100).toFixed(0)}%</span>
            <span>{record.metrics_count} metrics</span>
          </div>
        </div>
        <Check className="h-4 w-4 flex-shrink-0 text-green-400" />
      </div>
    </div>
  );
}

function PassedView({ passed }: { passed: PassedRecord[] }) {
  return (
    <div className="space-y-2">
      {passed.length === 0 ? (
        <p className="py-4 text-center text-sm text-[var(--text-muted)]">
          No signals generated yet
        </p>
      ) : (
        passed.map((p, i) => <PassedCard key={`${p.signal_id}-${i}`} record={p} />)
      )}
    </div>
  );
}

export function PipelineDebugPanel() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'stats' | 'rejected' | 'passed'>('stats');
  const [selectedStage, setSelectedStage] = useState<string | null>(null);

  const { data: rejectionsData } = useQuery({
    queryKey: ['debug-rejections', selectedStage],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '100' });
      if (selectedStage) params.set('stage', selectedStage);
      const res = await fetch(`${API_BASE}/debug/rejections?${params}`, { headers: getHeaders() });
      return res.json();
    },
    refetchInterval: 10000,
  });

  const { data: passedData } = useQuery({
    queryKey: ['debug-passed'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/debug/passed?limit=100`, { headers: getHeaders() });
      return res.json();
    },
    refetchInterval: 10000,
  });

  const stats: PipelineStats | null = rejectionsData?.statistics ?? null;
  const rejections: RejectionRecord[] = rejectionsData?.rejections ?? [];
  const passed: PassedRecord[] = passedData?.passed ?? [];

  return (
    <div className="fixed bottom-16 left-4 right-4 z-40">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-2 rounded-t-lg border border-[var(--border-default)] bg-[var(--bg-elevated)] px-4 py-2 transition-colors hover:bg-[var(--bg-hover)]"
      >
        <Filter className="h-4 w-4" />
        <span className="text-sm font-medium">Pipeline Debug</span>
        {stats && (
          <span className="text-xs text-[var(--text-muted)]">
            {stats.total_passed}/{stats.total_processed} passed (
            {(stats.pass_rate * 100).toFixed(1)}%)
          </span>
        )}
        {isExpanded ? (
          <ChevronDown className="ml-auto h-4 w-4" />
        ) : (
          <ChevronUp className="ml-auto h-4 w-4" />
        )}
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="max-h-[320px] overflow-hidden rounded-b-lg border border-t-0 border-[var(--border-default)] bg-[var(--bg-surface)]"
          >
            <div className="flex border-b border-[var(--border-subtle)]">
              <TabButton active={activeTab === 'stats'} onClick={() => setActiveTab('stats')}>
                📊 Statistics
              </TabButton>
              <TabButton
                active={activeTab === 'rejected'}
                onClick={() => setActiveTab('rejected')}
                count={stats?.total_rejected}
                color="red"
              >
                ❌ Rejected
              </TabButton>
              <TabButton
                active={activeTab === 'passed'}
                onClick={() => setActiveTab('passed')}
                count={stats?.total_passed}
                color="green"
              >
                ✅ Passed
              </TabButton>
            </div>
            <div className="max-h-80 overflow-y-auto p-4">
              {activeTab === 'stats' && stats && <StatsView stats={stats} />}
              {activeTab === 'rejected' && (
                <RejectedView
                  rejections={rejections}
                  selectedStage={selectedStage}
                  onStageSelect={setSelectedStage}
                  stats={stats}
                />
              )}
              {activeTab === 'passed' && <PassedView passed={passed} />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
