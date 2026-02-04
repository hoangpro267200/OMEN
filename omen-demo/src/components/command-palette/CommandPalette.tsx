/**
 * CommandPalette - Enterprise-grade command palette (Cmd+K)
 * 
 * Features:
 * - Fuzzy search across all entities (signals, pages, actions)
 * - Search syntax: signal:active confidence:>0.7 category:GEOPOLITICAL
 * - Recent searches with persistence
 * - Keyboard navigation (↑↓ or j/k, Enter, Escape)
 * - Action commands (export, refresh, toggle mode)
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Command } from 'cmdk';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  ArrowRight,
  Clock,
  Zap,
  FileText,
  Download,
  RefreshCw,
  Radio,
  Activity,
  Database,
  Shield,
  Command as CommandIcon,
  Layers,
  GitBranch,
  Terminal,
  X,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useDataModeSafe } from '../../context/DataModeContext';
import { useSignals } from '../../hooks/useSignalData';
import { ROUTES } from '../../lib/routes';

// ============================================================================
// TYPES
// ============================================================================

interface CommandItem {
  id: string;
  type: 'signal' | 'page' | 'action' | 'source' | 'recent';
  label: string;
  description?: string;
  icon?: React.ReactNode;
  shortcut?: string;
  keywords?: string[];
  category?: string;
  confidence?: number;
  onSelect: () => void;
}

interface CommandGroup {
  heading: string;
  items: CommandItem[];
}

// ============================================================================
// SEARCH PARSER
// ============================================================================

interface ParsedSearch {
  text: string;
  filters: Record<string, string>;
}

function parseSearchQuery(query: string): ParsedSearch {
  const filters: Record<string, string> = {};
  let text = query;

  // Parse field:value and field:>value syntax
  const filterRegex = /(\w+):(>|<|>=|<=)?([^\s]+)/g;
  let match;

  while ((match = filterRegex.exec(query)) !== null) {
    const [full, field, operator, value] = match;
    filters[field] = (operator || '') + value;
    text = text.replace(full, '').trim();
  }

  return { text, filters };
}

// ============================================================================
// RECENT SEARCHES
// ============================================================================

const STORAGE_KEY = 'omen-command-palette-recent';
const MAX_RECENT = 5;

function loadRecentSearches(): string[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

function saveRecentSearches(searches: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(searches.slice(0, MAX_RECENT)));
  } catch {
    // Ignore
  }
}

// ============================================================================
// HOOK: useCommandPalette
// ============================================================================

export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K to toggle
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
        return;
      }

      // Escape to close (handled by cmdk too, but we want to be sure)
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  return {
    isOpen,
    setIsOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
  };
}

// ============================================================================
// COMPONENT: CommandPalette
// ============================================================================

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [search, setSearch] = useState('');
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const navigate = useNavigate();
  const { toggleMode, state: dataMode, refreshData } = useDataModeSafe();
  const { data: signalsData } = useSignals({ limit: 100, enabled: isOpen });
  const inputRef = useRef<HTMLInputElement>(null);

  // Load recent searches on mount
  useEffect(() => {
    setRecentSearches(loadRecentSearches());
  }, []);

  // Focus input when opened, clear when closed
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setSearch('');
    }
  }, [isOpen]);

  // Save search to recent
  const saveSearch = useCallback(
    (query: string) => {
      if (!query.trim() || query.length < 3) return;

      const updated = [query, ...recentSearches.filter((s) => s !== query)].slice(0, MAX_RECENT);
      setRecentSearches(updated);
      saveRecentSearches(updated);
    },
    [recentSearches]
  );

  // Navigation helper
  const navigateTo = useCallback(
    (path: string, searchQuery?: string) => {
      if (searchQuery) saveSearch(searchQuery);
      navigate(path);
      onClose();
    },
    [navigate, onClose, saveSearch]
  );

  // Action helper
  const runAction = useCallback(
    (action: () => void, searchQuery?: string) => {
      if (searchQuery) saveSearch(searchQuery);
      action();
      onClose();
    },
    [onClose, saveSearch]
  );

  // Parse search query
  const parsedSearch = useMemo(() => parseSearchQuery(search), [search]);

  // -------------------------------------------------------------------------
  // Build Command Groups
  // -------------------------------------------------------------------------

  const commandGroups = useMemo((): CommandGroup[] => {
    const groups: CommandGroup[] = [];
    const searchLower = parsedSearch.text.toLowerCase();

    // ===================== RECENT SEARCHES =====================
    if (!search && recentSearches.length > 0) {
      groups.push({
        heading: 'Recent Searches',
        items: recentSearches.map((query, i) => ({
          id: `recent-${i}`,
          type: 'recent',
          label: query,
          icon: <Clock className="w-4 h-4" />,
          onSelect: () => setSearch(query),
        })),
      });
    }

    // ===================== SIGNALS =====================
    if (search && signalsData?.signals) {
      const filteredSignals = signalsData.signals
        .filter((signal) => {
          // Text match on title or ID
          const textMatch =
            !parsedSearch.text ||
            signal.title.toLowerCase().includes(searchLower) ||
            signal.signal_id.toLowerCase().includes(searchLower);

          // Filter matches
          let filterMatch = true;

          if (parsedSearch.filters.status) {
            filterMatch =
              filterMatch &&
              signal.status.toLowerCase() === parsedSearch.filters.status.toLowerCase();
          }

          if (parsedSearch.filters.confidence) {
            const filter = parsedSearch.filters.confidence;
            const op = filter.match(/^(>|<|>=|<=)/)?.[0] || '';
            const value = parseFloat(filter.replace(/^(>|<|>=|<=)/, ''));

            if (!isNaN(value)) {
              const score = signal.confidence_score;
              if (op === '>') filterMatch = filterMatch && score > value;
              else if (op === '<') filterMatch = filterMatch && score < value;
              else if (op === '>=') filterMatch = filterMatch && score >= value;
              else if (op === '<=') filterMatch = filterMatch && score <= value;
              else filterMatch = filterMatch && Math.abs(score - value) < 0.05;
            }
          }

          if (parsedSearch.filters.category) {
            filterMatch =
              filterMatch &&
              signal.category.toLowerCase().includes(parsedSearch.filters.category.toLowerCase());
          }

          if (parsedSearch.filters.severity) {
            filterMatch =
              filterMatch &&
              signal.severity_label?.toLowerCase() === parsedSearch.filters.severity.toLowerCase();
          }

          return textMatch && filterMatch;
        })
        .slice(0, 6);

      if (filteredSignals.length > 0) {
        groups.push({
          heading: `Signals (${filteredSignals.length} found)`,
          items: filteredSignals.map((signal) => ({
            id: signal.signal_id,
            type: 'signal',
            label: signal.signal_id,
            description: signal.title,
            icon: <Zap className="w-4 h-4 text-cyan-400" />,
            category: signal.category,
            confidence: signal.confidence_score,
            keywords: [signal.category, signal.status, signal.severity_label || ''],
            onSelect: () => navigateTo(`/signals/${signal.signal_id}`, search),
          })),
        });
      }
    }

    // ===================== PAGES =====================
    const pages: CommandItem[] = [
      {
        id: 'page-command-center',
        type: 'page',
        label: 'Command Center',
        description: 'Main dashboard overview',
        icon: <CommandIcon className="w-4 h-4" />,
        shortcut: '⌘ 1',
        keywords: ['home', 'dashboard', 'overview', 'main'],
        onSelect: () => navigateTo(ROUTES.overview),
      },
      {
        id: 'page-signals',
        type: 'page',
        label: 'Signal Monitor',
        description: 'Browse and filter all signals',
        icon: <Activity className="w-4 h-4" />,
        shortcut: '⌘ 2',
        keywords: ['signals', 'list', 'browse', 'monitor', 'watch'],
        onSelect: () => navigateTo(ROUTES.signals),
      },
      {
        id: 'page-pipeline',
        type: 'page',
        label: 'Pipeline Monitor',
        description: 'Processing pipeline visualization',
        icon: <GitBranch className="w-4 h-4" />,
        shortcut: '⌘ 3',
        keywords: ['pipeline', 'processing', 'validation', 'flow'],
        onSelect: () => navigateTo(ROUTES.pipeline),
      },
      {
        id: 'page-sources',
        type: 'page',
        label: 'Data Sources',
        description: 'Monitor data source health',
        icon: <Database className="w-4 h-4" />,
        shortcut: '⌘ 4',
        keywords: ['sources', 'data', 'connections', 'health', 'api'],
        onSelect: () => navigateTo(ROUTES.sources),
      },
      {
        id: 'page-partitions',
        type: 'page',
        label: 'Partitions',
        description: 'Ledger partitions and reconciliation',
        icon: <Layers className="w-4 h-4" />,
        shortcut: '⌘ 5',
        keywords: ['partitions', 'ledger', 'reconcile', 'audit'],
        onSelect: () => navigateTo(ROUTES.partitions),
      },
      {
        id: 'page-ledger',
        type: 'page',
        label: 'Ledger Proof',
        description: 'WAL framing and crash safety demo',
        icon: <FileText className="w-4 h-4" />,
        shortcut: '⌘ 6',
        keywords: ['ledger', 'proof', 'wal', 'audit', 'crash'],
        onSelect: () => navigateTo(ROUTES.ledgerProof),
      },
      {
        id: 'page-ingest',
        type: 'page',
        label: 'Ingest Demo',
        description: 'Idempotent delivery demonstration',
        icon: <Terminal className="w-4 h-4" />,
        shortcut: '⌘ 7',
        keywords: ['ingest', 'demo', 'idempotent', 'delivery'],
        onSelect: () => navigateTo(ROUTES.ingestDemo),
      },
    ];

    const filteredPages = search
      ? pages.filter(
          (p) =>
            p.label.toLowerCase().includes(searchLower) ||
            p.description?.toLowerCase().includes(searchLower) ||
            p.keywords?.some((k) => k.toLowerCase().includes(searchLower))
        )
      : pages;

    if (filteredPages.length > 0) {
      groups.push({
        heading: 'Pages',
        items: filteredPages,
      });
    }

    // ===================== ACTIONS =====================
    const actions: CommandItem[] = [
      {
        id: 'action-toggle-mode',
        type: 'action',
        label: `Switch to ${dataMode.mode === 'demo' ? 'Live' : 'Demo'} Mode`,
        description: `Currently in ${dataMode.mode.toUpperCase()} mode`,
        icon: <Radio className="w-4 h-4" />,
        keywords: ['mode', 'toggle', 'switch', 'live', 'demo'],
        onSelect: () => runAction(toggleMode),
      },
      {
        id: 'action-refresh',
        type: 'action',
        label: 'Refresh All Data',
        description: 'Force refresh from all sources',
        icon: <RefreshCw className="w-4 h-4" />,
        shortcut: '⌘ R',
        keywords: ['refresh', 'reload', 'fetch', 'update'],
        onSelect: () => runAction(refreshData),
      },
      {
        id: 'action-export-csv',
        type: 'action',
        label: 'Export Signals as CSV',
        description: 'Download all visible signals',
        icon: <Download className="w-4 h-4" />,
        keywords: ['export', 'download', 'csv', 'data'],
        onSelect: () => runAction(() => exportSignalsCSV(signalsData?.signals || [])),
      },
      {
        id: 'action-export-json',
        type: 'action',
        label: 'Export Signals as JSON',
        description: 'Download all visible signals as JSON',
        icon: <Download className="w-4 h-4" />,
        keywords: ['export', 'download', 'json', 'data'],
        onSelect: () => runAction(() => exportSignalsJSON(signalsData?.signals || [])),
      },
    ];

    const filteredActions = search
      ? actions.filter(
          (a) =>
            a.label.toLowerCase().includes(searchLower) ||
            a.description?.toLowerCase().includes(searchLower) ||
            a.keywords?.some((k) => k.toLowerCase().includes(searchLower))
        )
      : actions;

    if (filteredActions.length > 0) {
      groups.push({
        heading: 'Actions',
        items: filteredActions,
      });
    }

    // ===================== SEARCH TIPS =====================
    if (search && search.includes(':') && groups.length <= 1) {
      // Show syntax help when using filters
    }

    return groups;
  }, [
    search,
    parsedSearch,
    recentSearches,
    signalsData,
    dataMode.mode,
    navigateTo,
    runAction,
    toggleMode,
    refreshData,
  ]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Command Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 350 }}
            className="fixed inset-x-4 top-[15%] z-50 mx-auto max-w-2xl sm:inset-x-0"
          >
            <Command
              className={cn(
                'overflow-hidden rounded-2xl',
                'bg-[var(--bg-secondary)]/95 backdrop-blur-xl',
                'border border-[var(--border-subtle)]',
                'shadow-2xl shadow-black/50'
              )}
              shouldFilter={false}
              loop
            >
              {/* Search Input */}
              <div className="flex items-center gap-3 px-4 border-b border-[var(--border-subtle)]">
                <Search className="w-5 h-5 text-[var(--text-muted)]" />
                <Command.Input
                  ref={inputRef}
                  value={search}
                  onValueChange={setSearch}
                  placeholder="Search signals, pages, or type a command..."
                  className={cn(
                    'flex-1 h-14 bg-transparent',
                    'text-[var(--text-primary)] placeholder-[var(--text-muted)]',
                    'outline-none border-none',
                    'text-base font-body'
                  )}
                />
                {search && (
                  <button
                    onClick={() => setSearch('')}
                    className="p-1 rounded hover:bg-[var(--bg-tertiary)]"
                  >
                    <X className="w-4 h-4 text-[var(--text-muted)]" />
                  </button>
                )}
                <kbd className="hidden sm:flex px-2 py-1 text-xs text-[var(--text-muted)] bg-[var(--bg-tertiary)] rounded border border-[var(--border-subtle)]">
                  ESC
                </kbd>
              </div>

              {/* Search Syntax Help */}
              {search.includes(':') && (
                <div className="px-4 py-2 bg-[var(--accent-cyan)]/5 border-b border-[var(--accent-cyan)]/20">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--accent-cyan)]">
                    <Shield className="w-3 h-3" />
                    <span>Search syntax:</span>
                    <code className="px-1.5 py-0.5 bg-[var(--accent-cyan)]/10 rounded font-mono">
                      status:active
                    </code>
                    <code className="px-1.5 py-0.5 bg-[var(--accent-cyan)]/10 rounded font-mono">
                      confidence:&gt;0.7
                    </code>
                    <code className="px-1.5 py-0.5 bg-[var(--accent-cyan)]/10 rounded font-mono">
                      category:GEOPOLITICAL
                    </code>
                    <code className="px-1.5 py-0.5 bg-[var(--accent-cyan)]/10 rounded font-mono">
                      severity:CRITICAL
                    </code>
                  </div>
                </div>
              )}

              {/* Results */}
              <Command.List className="max-h-[400px] overflow-y-auto overflow-x-hidden p-2">
                <Command.Empty className="py-12 text-center text-[var(--text-muted)]">
                  <Search className="w-8 h-8 mx-auto mb-3 opacity-50" />
                  <p>No results found for "{search}"</p>
                  <p className="text-xs mt-1">Try a different search term</p>
                </Command.Empty>

                {commandGroups.map((group) => (
                  <Command.Group key={group.heading} className="mb-3 last:mb-0">
                    <div className="px-2 py-1.5 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider font-mono">
                      {group.heading}
                    </div>

                    {group.items.map((item) => (
                      <Command.Item
                        key={item.id}
                        value={item.id}
                        onSelect={item.onSelect}
                        className={cn(
                          'flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer',
                          'text-[var(--text-secondary)] transition-colors',
                          'aria-selected:bg-[var(--accent-cyan)]/10 aria-selected:text-[var(--text-primary)]',
                          'hover:bg-[var(--bg-tertiary)]'
                        )}
                      >
                        {/* Icon */}
                        <span className="flex-shrink-0 text-[var(--text-muted)]">{item.icon}</span>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium truncate">{item.label}</span>
                            {item.type === 'signal' && (
                              <>
                                <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)] rounded">
                                  SIGNAL
                                </span>
                                {item.confidence !== undefined && (
                                  <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[var(--bg-tertiary)] text-[var(--text-muted)] rounded">
                                    {(item.confidence * 100).toFixed(0)}%
                                  </span>
                                )}
                              </>
                            )}
                          </div>
                          {item.description && (
                            <div className="text-sm text-[var(--text-muted)] truncate">
                              {item.description}
                            </div>
                          )}
                        </div>

                        {/* Shortcut */}
                        {item.shortcut && (
                          <kbd className="hidden sm:flex flex-shrink-0 px-1.5 py-0.5 text-[10px] text-[var(--text-muted)] bg-[var(--bg-tertiary)] rounded border border-[var(--border-subtle)] font-mono">
                            {item.shortcut}
                          </kbd>
                        )}

                        <ArrowRight className="flex-shrink-0 w-4 h-4 text-[var(--text-muted)] opacity-0 group-aria-selected:opacity-100" />
                      </Command.Item>
                    ))}
                  </Command.Group>
                ))}
              </Command.List>

              {/* Footer */}
              <div className="flex items-center justify-between px-4 py-2 border-t border-[var(--border-subtle)] text-xs text-[var(--text-muted)]">
                <div className="hidden sm:flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 bg-[var(--bg-tertiary)] rounded">↑↓</kbd> Navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 bg-[var(--bg-tertiary)] rounded">↵</kbd> Select
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 bg-[var(--bg-tertiary)] rounded">esc</kbd> Close
                  </span>
                </div>
                <span className="text-[var(--accent-cyan)] font-mono">OMEN Command Palette</span>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ============================================================================
// EXPORT HELPERS
// ============================================================================

function exportSignalsCSV(signals: Array<{ signal_id: string; title: string; probability: number; confidence_score: number; status: string; category: string }>) {
  if (!signals.length) {
    console.warn('No signals to export');
    return;
  }

  const headers = ['signal_id', 'title', 'probability', 'confidence_score', 'status', 'category'];
  const csvContent = [
    headers.join(','),
    ...signals.map((s) =>
      [
        s.signal_id,
        `"${s.title.replace(/"/g, '""')}"`,
        s.probability,
        s.confidence_score,
        s.status,
        s.category,
      ].join(',')
    ),
  ].join('\n');

  downloadFile(csvContent, 'omen-signals.csv', 'text/csv');
}

function exportSignalsJSON(signals: unknown[]) {
  if (!signals.length) {
    console.warn('No signals to export');
    return;
  }

  const jsonContent = JSON.stringify(signals, null, 2);
  downloadFile(jsonContent, 'omen-signals.json', 'application/json');
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ============================================================================
// EXPORTS
// ============================================================================

export default CommandPalette;
