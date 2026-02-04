/**
 * AuditTrail - Complete audit log visualization
 * 
 * Features:
 * - Timeline view of all changes
 * - Filtering by action type, user, date
 * - Expandable details
 * - Export functionality
 * - Real-time updates
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock,
  User,
  Shield,
  FileText,
  ChevronDown,
  ChevronRight,
  Filter,
  Download,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  Search,
  Calendar,
  ExternalLink,
  Copy,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// ============================================================================
// TYPES
// ============================================================================

export type AuditAction =
  | 'created'
  | 'updated'
  | 'deleted'
  | 'validated'
  | 'rejected'
  | 'emitted'
  | 'archived'
  | 'restored'
  | 'exported';

export type AuditLevel = 'info' | 'success' | 'warning' | 'error';

export interface AuditEntry {
  id: string;
  timestamp: string;
  action: AuditAction;
  level: AuditLevel;
  entityType: 'signal' | 'source' | 'rule' | 'partition' | 'system';
  entityId: string;
  entityName?: string;
  actor: {
    type: 'system' | 'user' | 'rule' | 'api';
    name: string;
    id?: string;
  };
  description: string;
  details?: Record<string, unknown>;
  changes?: {
    field: string;
    before: unknown;
    after: unknown;
  }[];
  metadata?: {
    ip?: string;
    userAgent?: string;
    traceId?: string;
    duration_ms?: number;
  };
}

export interface AuditTrailProps {
  /** Audit entries to display */
  entries?: AuditEntry[];
  /** Entity ID to filter by */
  entityId?: string;
  /** Entity type to filter by */
  entityType?: string;
  /** Show filters */
  showFilters?: boolean;
  /** Show export button */
  showExport?: boolean;
  /** Max entries to display */
  maxEntries?: number;
  /** Callback for refresh */
  onRefresh?: () => void;
  /** Loading state */
  isLoading?: boolean;
  /** Additional class names */
  className?: string;
}

// ============================================================================
// MOCK DATA GENERATOR
// ============================================================================

function generateMockAuditEntries(count: number = 20): AuditEntry[] {
  const actions: AuditAction[] = ['created', 'updated', 'validated', 'emitted', 'rejected', 'archived'];
  const levels: AuditLevel[] = ['info', 'success', 'warning', 'error'];
  const entityTypes: AuditEntry['entityType'][] = ['signal', 'source', 'rule', 'partition'];
  const actors = [
    { type: 'system' as const, name: 'OMEN Pipeline' },
    { type: 'rule' as const, name: 'liquidity_validator', id: 'rule-001' },
    { type: 'rule' as const, name: 'anomaly_detector', id: 'rule-002' },
    { type: 'system' as const, name: 'Signal Emitter' },
    { type: 'api' as const, name: 'Polymarket Ingest' },
  ];

  return Array.from({ length: count }, (_, i) => {
    const action = actions[Math.floor(Math.random() * actions.length)];
    const entityType = entityTypes[Math.floor(Math.random() * entityTypes.length)];
    
    let level: AuditLevel = 'info';
    if (action === 'validated' || action === 'emitted') level = 'success';
    if (action === 'rejected') level = 'warning';
    if (action === 'deleted') level = 'error';

    return {
      id: `audit-${i + 1}`,
      timestamp: new Date(Date.now() - i * 300000 - Math.random() * 60000).toISOString(),
      action,
      level,
      entityType,
      entityId: `OMEN-${entityType.toUpperCase()}-${String(Math.floor(Math.random() * 1000)).padStart(3, '0')}`,
      entityName: entityType === 'signal' ? 'China-India Military Clash Risk' : undefined,
      actor: actors[Math.floor(Math.random() * actors.length)],
      description: getActionDescription(action, entityType),
      details: {
        rule_version: '2.1.0',
        processing_time_ms: Math.floor(Math.random() * 200) + 50,
      },
      changes: action === 'updated' ? [
        { field: 'confidence_score', before: 0.45, after: 0.57 },
        { field: 'status', before: 'CANDIDATE', after: 'MONITORING' },
      ] : undefined,
      metadata: {
        traceId: `trace-${Math.random().toString(36).slice(2, 10)}`,
        duration_ms: Math.floor(Math.random() * 200) + 20,
      },
    };
  });
}

function getActionDescription(action: AuditAction, entityType: string): string {
  const descriptions: Record<AuditAction, string> = {
    created: `New ${entityType} created and added to pipeline`,
    updated: `${entityType} properties updated after validation`,
    deleted: `${entityType} permanently removed from system`,
    validated: `${entityType} passed all validation rules`,
    rejected: `${entityType} rejected due to validation failure`,
    emitted: `${entityType} emitted to downstream consumers`,
    archived: `${entityType} moved to archive`,
    restored: `${entityType} restored from archive`,
    exported: `${entityType} exported to external system`,
  };
  return descriptions[action];
}

// ============================================================================
// COMPONENT
// ============================================================================

export function AuditTrail({
  entries: propEntries,
  entityId,
  entityType,
  showFilters = true,
  showExport = true,
  maxEntries = 50,
  onRefresh,
  isLoading = false,
  className,
}: AuditTrailProps) {
  // State
  const [selectedActions, setSelectedActions] = useState<AuditAction[]>([]);
  const [selectedLevels, setSelectedLevels] = useState<AuditLevel[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState<string | null>(null);

  // Use mock data if no entries provided
  const entries = useMemo(() => {
    return propEntries || generateMockAuditEntries(maxEntries);
  }, [propEntries, maxEntries]);

  // Filter entries
  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      // Filter by entity
      if (entityId && entry.entityId !== entityId) return false;
      if (entityType && entry.entityType !== entityType) return false;

      // Filter by action
      if (selectedActions.length > 0 && !selectedActions.includes(entry.action)) return false;

      // Filter by level
      if (selectedLevels.length > 0 && !selectedLevels.includes(entry.level)) return false;

      // Filter by search
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const searchable = [
          entry.entityId,
          entry.entityName,
          entry.description,
          entry.actor.name,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        if (!searchable.includes(query)) return false;
      }

      return true;
    });
  }, [entries, entityId, entityType, selectedActions, selectedLevels, searchQuery]);

  // Toggle entry expansion
  const toggleExpanded = (id: string) => {
    setExpandedEntries((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Copy to clipboard
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  // Export
  const handleExport = () => {
    const json = JSON.stringify(filteredEntries, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-trail-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[var(--accent-cyan)]/10">
            <Shield className="w-5 h-5 text-[var(--accent-cyan)]" />
          </div>
          <div>
            <h3 className="font-semibold text-[var(--text-primary)]">Audit Trail</h3>
            <p className="text-xs text-[var(--text-muted)]">
              {filteredEntries.length} entries
              {entityId && ` for ${entityId}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className={cn(
                'p-2 rounded-lg transition-colors',
                'hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]',
                isLoading && 'animate-spin'
              )}
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
          {showExport && (
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)] text-sm transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-[var(--bg-tertiary)]/50">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search entries..."
              className="w-full pl-10 pr-4 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--accent-cyan)]"
            />
          </div>

          {/* Action Filter */}
          <FilterDropdown
            label="Action"
            icon={<Filter className="w-4 h-4" />}
            options={['created', 'updated', 'validated', 'rejected', 'emitted', 'archived']}
            selected={selectedActions}
            onChange={setSelectedActions as (v: string[]) => void}
          />

          {/* Level Filter */}
          <FilterDropdown
            label="Level"
            icon={<AlertTriangle className="w-4 h-4" />}
            options={['info', 'success', 'warning', 'error']}
            selected={selectedLevels}
            onChange={setSelectedLevels as (v: string[]) => void}
          />
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        {/* Timeline Line */}
        <div className="absolute left-6 top-0 bottom-0 w-px bg-[var(--border-subtle)]" />

        {/* Entries */}
        <div className="space-y-3">
          {filteredEntries.length === 0 ? (
            <div className="text-center py-12 text-[var(--text-muted)]">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No audit entries found</p>
            </div>
          ) : (
            filteredEntries.map((entry, idx) => (
              <AuditEntryRow
                key={entry.id}
                entry={entry}
                isExpanded={expandedEntries.has(entry.id)}
                onToggle={() => toggleExpanded(entry.id)}
                onCopy={handleCopy}
                copied={copied}
                index={idx}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// FILTER DROPDOWN
// ============================================================================

interface FilterDropdownProps {
  label: string;
  icon: React.ReactNode;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

function FilterDropdown({ label, icon, options, selected, onChange }: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
          selected.length > 0
            ? 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)]'
            : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
        )}
      >
        {icon}
        {label}
        {selected.length > 0 && (
          <span className="px-1.5 py-0.5 rounded bg-[var(--accent-cyan)] text-black text-[10px] font-bold">
            {selected.length}
          </span>
        )}
        <ChevronDown className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full left-0 mt-1 z-50 min-w-[150px] rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-subtle)] shadow-xl overflow-hidden"
            >
              {options.map((option) => (
                <button
                  key={option}
                  onClick={() => toggleOption(option)}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors',
                    selected.includes(option)
                      ? 'bg-[var(--accent-cyan)]/10 text-[var(--accent-cyan)]'
                      : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
                  )}
                >
                  <div
                    className={cn(
                      'w-4 h-4 rounded border flex items-center justify-center',
                      selected.includes(option)
                        ? 'bg-[var(--accent-cyan)] border-[var(--accent-cyan)]'
                        : 'border-[var(--border-default)]'
                    )}
                  >
                    {selected.includes(option) && <CheckCircle className="w-3 h-3 text-black" />}
                  </div>
                  <span className="capitalize">{option}</span>
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// AUDIT ENTRY ROW
// ============================================================================

interface AuditEntryRowProps {
  entry: AuditEntry;
  isExpanded: boolean;
  onToggle: () => void;
  onCopy: (text: string, id: string) => void;
  copied: string | null;
  index: number;
}

function AuditEntryRow({ entry, isExpanded, onToggle, onCopy, copied, index }: AuditEntryRowProps) {
  const levelConfig = {
    info: { icon: Info, color: 'text-[var(--text-muted)]', bg: 'bg-[var(--bg-tertiary)]' },
    success: { icon: CheckCircle, color: 'text-[var(--status-success)]', bg: 'bg-[var(--status-success)]/10' },
    warning: { icon: AlertTriangle, color: 'text-[var(--accent-amber)]', bg: 'bg-[var(--accent-amber)]/10' },
    error: { icon: XCircle, color: 'text-[var(--status-error)]', bg: 'bg-[var(--status-error)]/10' },
  };

  const config = levelConfig[entry.level];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.02 }}
      className="relative pl-12"
    >
      {/* Timeline Dot */}
      <div
        className={cn(
          'absolute left-4 top-4 w-5 h-5 rounded-full flex items-center justify-center border-2 border-[var(--bg-primary)]',
          config.bg
        )}
      >
        <Icon className={cn('w-3 h-3', config.color)} />
      </div>

      {/* Card */}
      <div
        className={cn(
          'rounded-lg border transition-all cursor-pointer',
          'bg-[var(--bg-secondary)] border-[var(--border-subtle)]',
          isExpanded && 'ring-1 ring-[var(--accent-cyan)]/50'
        )}
        onClick={onToggle}
      >
        {/* Header */}
        <div className="flex items-center gap-3 p-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn('px-2 py-0.5 rounded text-[10px] font-medium uppercase', config.bg, config.color)}>
                {entry.action}
              </span>
              <span className="text-xs text-[var(--text-muted)]">{entry.entityType}</span>
            </div>
            <p className="text-sm text-[var(--text-primary)] truncate">{entry.description}</p>
          </div>

          <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
            <div className="flex items-center gap-1">
              <User className="w-3 h-3" />
              <span>{entry.actor.name}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>{new Date(entry.timestamp).toLocaleTimeString()}</span>
            </div>
            <ChevronRight className={cn('w-4 h-4 transition-transform', isExpanded && 'rotate-90')} />
          </div>
        </div>

        {/* Expanded Details */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="px-3 pb-3 pt-0 space-y-3 border-t border-[var(--border-subtle)]">
                {/* Entity Info */}
                <div className="flex items-center justify-between p-2 rounded bg-[var(--bg-tertiary)]/50 mt-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[var(--text-muted)]" />
                    <span className="font-mono text-sm text-[var(--accent-cyan)]">{entry.entityId}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onCopy(entry.entityId, entry.id);
                    }}
                    className="p-1 rounded hover:bg-[var(--bg-tertiary)]"
                  >
                    {copied === entry.id ? (
                      <CheckCircle className="w-4 h-4 text-[var(--status-success)]" />
                    ) : (
                      <Copy className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                  </button>
                </div>

                {/* Changes */}
                {entry.changes && entry.changes.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs text-[var(--text-muted)] font-medium">Changes</div>
                    {entry.changes.map((change, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <span className="text-[var(--text-muted)]">{change.field}:</span>
                        <span className="text-[var(--status-error)] line-through">{String(change.before)}</span>
                        <span className="text-[var(--text-muted)]">→</span>
                        <span className="text-[var(--status-success)]">{String(change.after)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Metadata */}
                {entry.metadata && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {entry.metadata.traceId && (
                      <div className="flex items-center gap-1 text-[var(--text-muted)]">
                        <span>Trace:</span>
                        <code className="text-[var(--accent-cyan)]">{entry.metadata.traceId}</code>
                      </div>
                    )}
                    {entry.metadata.duration_ms && (
                      <div className="flex items-center gap-1 text-[var(--text-muted)]">
                        <span>Duration:</span>
                        <span className="text-[var(--status-success)]">{entry.metadata.duration_ms}ms</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Timestamp */}
                <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                  <Calendar className="w-3 h-3" />
                  <span>{new Date(entry.timestamp).toLocaleString()}</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default AuditTrail;
