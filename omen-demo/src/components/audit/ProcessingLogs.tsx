/**
 * ProcessingLogs - Real-time processing logs viewer
 * 
 * Features:
 * - Live log streaming display
 * - Log level filtering (DEBUG, INFO, WARN, ERROR)
 * - Search/filter logs
 * - Auto-scroll to bottom
 * - Copy log entries
 * - Export functionality
 */

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal,
  Search,
  Filter,
  Download,
  Trash2,
  Pause,
  Play,
  ChevronDown,
  Copy,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  Bug,
  RefreshCw,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// ============================================================================
// TYPES
// ============================================================================

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  source: string;
  message: string;
  details?: Record<string, unknown>;
  traceId?: string;
  duration_ms?: number;
}

export interface ProcessingLogsProps {
  /** Log entries to display */
  logs?: LogEntry[];
  /** Maximum logs to keep in memory */
  maxLogs?: number;
  /** Auto-scroll to new logs */
  autoScroll?: boolean;
  /** Show filters */
  showFilters?: boolean;
  /** Show export button */
  showExport?: boolean;
  /** Additional class names */
  className?: string;
  /** Height of the log container */
  height?: string | number;
}

// ============================================================================
// MOCK DATA GENERATOR
// ============================================================================

const LOG_SOURCES = [
  'polymarket.ingest',
  'pipeline.validator',
  'pipeline.enricher',
  'pipeline.classifier',
  'signal.emitter',
  'ledger.writer',
  'health.monitor',
];

const LOG_MESSAGES: Record<LogLevel, string[]> = {
  DEBUG: [
    'Processing batch of 50 events',
    'Cache hit for rule configuration',
    'WebSocket connection stable',
    'Fetching market data for token_id=0x...',
  ],
  INFO: [
    'Signal OMEN-001 validated successfully',
    'Partition p-2026-02 reconciliation complete',
    'Connected to Polymarket CLOB API',
    'Rule liquidity_validator v2.1.0 loaded',
    'Emitted 3 signals to downstream consumers',
  ],
  WARN: [
    'High latency detected: 450ms (threshold: 200ms)',
    'Rate limit approaching: 85% of quota used',
    'Retry attempt 2/3 for source polymarket',
    'Memory usage above 80%',
  ],
  ERROR: [
    'Failed to fetch market data: timeout after 5000ms',
    'Validation rule threw exception: NaN confidence',
    'WebSocket disconnected unexpectedly',
    'Database write failed: connection refused',
  ],
};

function generateMockLogs(count: number = 100): LogEntry[] {
  const levels: LogLevel[] = ['DEBUG', 'INFO', 'INFO', 'INFO', 'WARN', 'ERROR'];
  
  return Array.from({ length: count }, (_, i) => {
    const level = levels[Math.floor(Math.random() * levels.length)];
    const messages = LOG_MESSAGES[level];
    
    return {
      id: `log-${i + 1}`,
      timestamp: new Date(Date.now() - (count - i) * 1000 - Math.random() * 500).toISOString(),
      level,
      source: LOG_SOURCES[Math.floor(Math.random() * LOG_SOURCES.length)],
      message: messages[Math.floor(Math.random() * messages.length)],
      traceId: Math.random() > 0.5 ? `trace-${Math.random().toString(36).slice(2, 10)}` : undefined,
      duration_ms: Math.random() > 0.7 ? Math.floor(Math.random() * 500) + 10 : undefined,
    };
  });
}

// ============================================================================
// COMPONENT
// ============================================================================

export function ProcessingLogs({
  logs: propLogs,
  maxLogs = 500,
  autoScroll: initialAutoScroll = true,
  showFilters = true,
  showExport = true,
  className,
  height = 400,
}: ProcessingLogsProps) {
  // State
  const [selectedLevels, setSelectedLevels] = useState<LogLevel[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [autoScroll, setAutoScroll] = useState(initialAutoScroll);
  const [isPaused, setIsPaused] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Use mock data if no logs provided
  const logs = useMemo(() => {
    const data = propLogs || generateMockLogs(100);
    return data.slice(-maxLogs);
  }, [propLogs, maxLogs]);

  // Filter logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      // Filter by level
      if (selectedLevels.length > 0 && !selectedLevels.includes(log.level)) return false;

      // Filter by search
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const searchable = [log.message, log.source, log.traceId].filter(Boolean).join(' ').toLowerCase();
        if (!searchable.includes(query)) return false;
      }

      return true;
    });
  }, [logs, selectedLevels, searchQuery]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && !isPaused && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll, isPaused]);

  // Copy log entry
  const handleCopy = (log: LogEntry) => {
    const text = `[${log.timestamp}] [${log.level}] [${log.source}] ${log.message}`;
    navigator.clipboard.writeText(text);
    setCopied(log.id);
    setTimeout(() => setCopied(null), 2000);
  };

  // Export logs
  const handleExport = () => {
    const text = filteredLogs
      .map((log) => `[${log.timestamp}] [${log.level}] [${log.source}] ${log.message}`)
      .join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `processing-logs-${new Date().toISOString().slice(0, 10)}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Clear logs (just filter out)
  const handleClear = () => {
    setSearchQuery('');
    setSelectedLevels([]);
  };

  // Level config
  const levelConfig: Record<LogLevel, { icon: React.ComponentType<{ className?: string }>; color: string; bg: string }> = {
    DEBUG: { icon: Bug, color: 'text-[var(--text-muted)]', bg: 'bg-[var(--bg-tertiary)]' },
    INFO: { icon: Info, color: 'text-[var(--accent-cyan)]', bg: 'bg-[var(--accent-cyan)]/10' },
    WARN: { icon: AlertTriangle, color: 'text-[var(--accent-amber)]', bg: 'bg-[var(--accent-amber)]/10' },
    ERROR: { icon: XCircle, color: 'text-[var(--status-error)]', bg: 'bg-[var(--status-error)]/10' },
  };

  return (
    <div className={cn('flex flex-col rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]/50">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-[var(--accent-cyan)]" />
          <span className="font-semibold text-[var(--text-primary)]">Processing Logs</span>
          <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] text-xs text-[var(--text-muted)] font-mono">
            {filteredLogs.length} entries
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Pause/Resume */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={cn(
              'p-2 rounded-lg transition-colors',
              isPaused
                ? 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]'
                : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]'
            )}
            title={isPaused ? 'Resume' : 'Pause'}
          >
            {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>

          {/* Auto-scroll toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={cn(
              'p-2 rounded-lg transition-colors',
              autoScroll
                ? 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]'
                : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]'
            )}
            title={autoScroll ? 'Disable auto-scroll' : 'Enable auto-scroll'}
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {/* Clear */}
          <button
            onClick={handleClear}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]"
            title="Clear filters"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          {/* Export */}
          {showExport && (
            <button
              onClick={handleExport}
              className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]"
              title="Export logs"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="flex items-center gap-3 px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--bg-primary)]/50">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter logs..."
              className="w-full pl-10 pr-4 py-1.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--accent-cyan)]"
            />
          </div>

          {/* Level Filters */}
          <div className="flex items-center gap-1">
            {(['DEBUG', 'INFO', 'WARN', 'ERROR'] as LogLevel[]).map((level) => {
              const config = levelConfig[level];
              const isSelected = selectedLevels.includes(level);
              return (
                <button
                  key={level}
                  onClick={() => {
                    if (isSelected) {
                      setSelectedLevels(selectedLevels.filter((l) => l !== level));
                    } else {
                      setSelectedLevels([...selectedLevels, level]);
                    }
                  }}
                  className={cn(
                    'px-2 py-1 rounded text-xs font-mono transition-colors',
                    isSelected ? cn(config.bg, config.color) : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]'
                  )}
                >
                  {level}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Log Container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto overflow-x-hidden font-mono text-xs"
        style={{ height: typeof height === 'number' ? `${height}px` : height }}
      >
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[var(--text-muted)]">
            <div className="text-center">
              <Terminal className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No logs to display</p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {filteredLogs.map((log, idx) => {
              const config = levelConfig[log.level];
              const Icon = config.icon;
              
              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(idx * 0.01, 0.5) }}
                  className={cn(
                    'flex items-start gap-2 px-4 py-2 hover:bg-[var(--bg-tertiary)]/30 group cursor-pointer',
                    log.level === 'ERROR' && 'bg-[var(--status-error)]/5'
                  )}
                  onClick={() => handleCopy(log)}
                >
                  {/* Timestamp */}
                  <span className="text-[var(--text-muted)] shrink-0 w-[85px]">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>

                  {/* Level Badge */}
                  <span className={cn('shrink-0 px-1.5 py-0.5 rounded font-semibold', config.bg, config.color)}>
                    {log.level.padEnd(5)}
                  </span>

                  {/* Source */}
                  <span className="text-[var(--accent-cyan)] shrink-0 w-[150px] truncate">{log.source}</span>

                  {/* Message */}
                  <span className="flex-1 text-[var(--text-secondary)] break-all">{log.message}</span>

                  {/* Duration */}
                  {log.duration_ms && (
                    <span className="shrink-0 text-[var(--text-muted)]">{log.duration_ms}ms</span>
                  )}

                  {/* Copy indicator */}
                  <span className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    {copied === log.id ? (
                      <CheckCircle className="w-4 h-4 text-[var(--status-success)]" />
                    ) : (
                      <Copy className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                  </span>
                </motion.div>
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-[var(--border-subtle)] bg-[var(--bg-tertiary)]/50 text-xs text-[var(--text-muted)]">
        <span>
          {isPaused ? '⏸ Paused' : '● Live'}
          {autoScroll && ' • Auto-scroll enabled'}
        </span>
        <span>Click to copy log entry</span>
      </div>
    </div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default ProcessingLogs;
