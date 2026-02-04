/**
 * ExplainPopover - "Explain This" data point explanation popover
 * 
 * Provides comprehensive context for any data point:
 * - What: Semantic definition, unit, normal range
 * - Source: System, API endpoint, request ID
 * - Time: Event time, ingest time, compute time, display time
 * - Quality: Quality score, indicators, warnings
 * 
 * Features:
 * - Hover or click trigger
 * - Tabbed interface
 * - Copy to clipboard
 * - Links to documentation
 */

import React, { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  useFloating,
  offset,
  flip,
  shift,
  useHover,
  useClick,
  useDismiss,
  useInteractions,
  FloatingPortal,
  arrow,
  type Placement,
} from '@floating-ui/react';
import {
  HelpCircle,
  ExternalLink,
  Clock,
  Code,
  Database,
  AlertTriangle,
  CheckCircle,
  Info,
  Copy,
  X,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { getFieldDefinitionWithFallback, type FieldDefinition } from '../../lib/field-definitions';

// ============================================================================
// TYPES
// ============================================================================

export interface ExplainContext {
  /** When the underlying event occurred */
  eventTime?: string;
  /** When OMEN received/ingested the data */
  ingestTime?: string;
  /** When OMEN computed/processed the data */
  computeTime?: string;
  /** Rule version used for computation */
  ruleVersion?: string;
  /** Unique request/trace ID */
  requestId?: string;
  /** Quality score 0-1 */
  quality?: number;
  /** Additional quality flags */
  qualityFlags?: string[];
  /** Source-specific metadata */
  sourceMeta?: Record<string, unknown>;
}

export interface ExplainPopoverProps {
  /** Field identifier for definition lookup (e.g., 'signal.probability') */
  fieldId: string;
  /** Current value to display */
  value?: string | number | null;
  /** Override or extend the definition */
  definition?: Partial<FieldDefinition>;
  /** Runtime context (timestamps, versions, quality) */
  context?: ExplainContext;
  /** Popover placement */
  placement?: Placement;
  /** Trigger mode */
  trigger?: 'hover' | 'click' | 'both';
  /** Delay before showing (hover only) */
  hoverDelay?: number;
  /** Whether to show the help icon */
  showIcon?: boolean;
  /** Additional class for wrapper */
  className?: string;
  /** Children to wrap */
  children: React.ReactNode;
}

type TabId = 'what' | 'source' | 'time' | 'quality';

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'what', label: 'What', icon: <Info className="w-3 h-3" /> },
  { id: 'source', label: 'Source', icon: <Database className="w-3 h-3" /> },
  { id: 'time', label: 'Time', icon: <Clock className="w-3 h-3" /> },
  { id: 'quality', label: 'Quality', icon: <Sparkles className="w-3 h-3" /> },
];

// ============================================================================
// COMPONENT
// ============================================================================

export function ExplainPopover({
  fieldId,
  value,
  definition: definitionOverride,
  context,
  placement = 'top',
  trigger = 'hover',
  hoverDelay = 300,
  showIcon = true,
  className,
  children,
}: ExplainPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('what');
  const [copied, setCopied] = useState(false);
  const arrowRef = useRef(null);

  // Get field definition
  const definition = getFieldDefinitionWithFallback(fieldId, definitionOverride);

  // Floating UI setup
  const { refs, floatingStyles, context: floatingContext } = useFloating({
    open: isOpen,
    onOpenChange: setIsOpen,
    placement,
    middleware: [
      offset(12),
      flip({ fallbackPlacements: ['bottom', 'left', 'right'] }),
      shift({ padding: 8 }),
      arrow({ element: arrowRef }),
    ],
  });

  // Interactions
  const hover = useHover(floatingContext, {
    enabled: trigger === 'hover' || trigger === 'both',
    delay: { open: hoverDelay, close: 100 },
  });
  const click = useClick(floatingContext, {
    enabled: trigger === 'click' || trigger === 'both',
  });
  const dismiss = useDismiss(floatingContext);

  const { getReferenceProps, getFloatingProps } = useInteractions([hover, click, dismiss]);

  // Copy to clipboard
  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  // Format value with unit
  const formattedValue = value !== null && value !== undefined
    ? `${value}${definition.unit ? ` ${definition.unit}` : ''}`
    : 'N/A';

  return (
    <>
      {/* Trigger */}
      <span
        ref={refs.setReference}
        {...getReferenceProps()}
        className={cn(
          'inline-flex items-center gap-1 cursor-help group',
          className
        )}
      >
        {children}
        {showIcon && (
          <HelpCircle
            className={cn(
              'w-3.5 h-3.5 transition-all duration-200',
              'text-[var(--text-muted)]',
              'group-hover:text-[var(--accent-cyan)] group-hover:scale-110',
              trigger === 'hover' ? 'opacity-0 group-hover:opacity-100' : 'opacity-40'
            )}
          />
        )}
      </span>

      {/* Popover */}
      <FloatingPortal>
        <AnimatePresence>
          {isOpen && (
            <motion.div
              ref={refs.setFloating}
              style={floatingStyles}
              {...getFloatingProps()}
              initial={{ opacity: 0, scale: 0.95, y: placement.includes('top') ? 8 : -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className={cn(
                'z-[100] w-80 rounded-xl overflow-hidden',
                'bg-[var(--bg-secondary)]/98 backdrop-blur-xl',
                'border border-[var(--border-subtle)]',
                'shadow-2xl shadow-black/40'
              )}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--accent-cyan)]/5">
                <div className="flex items-center gap-2 min-w-0">
                  <Info className="w-4 h-4 text-[var(--accent-cyan)] flex-shrink-0" />
                  <span className="text-sm font-medium text-[var(--text-primary)] truncate">
                    {definition.label}
                  </span>
                </div>
                {trigger === 'click' && (
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Tabs */}
              <div className="flex border-b border-[var(--border-subtle)]">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      'flex-1 flex items-center justify-center gap-1.5 px-2 py-2 text-xs font-medium transition-colors',
                      activeTab === tab.id
                        ? 'text-[var(--accent-cyan)] border-b-2 border-[var(--accent-cyan)] bg-[var(--accent-cyan)]/5'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                    )}
                  >
                    {tab.icon}
                    <span className="hidden sm:inline">{tab.label}</span>
                  </button>
                ))}
              </div>

              {/* Content */}
              <div className="p-4 max-h-64 overflow-y-auto overflow-thin-scroll">
                {/* What Tab */}
                {activeTab === 'what' && (
                  <div className="space-y-3">
                    {/* Description */}
                    <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                      {definition.description}
                    </p>

                    {/* Current Value */}
                    {value !== null && value !== undefined && (
                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
                        <span className="text-xs text-[var(--text-muted)]">Current Value</span>
                        <span className="text-sm font-mono text-[var(--accent-cyan)] font-medium">
                          {formattedValue}
                        </span>
                      </div>
                    )}

                    {/* Normal Range */}
                    {definition.normalRange && (
                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
                        <span className="text-xs text-[var(--text-muted)]">Normal Range</span>
                        <span className="text-sm font-mono text-[var(--text-secondary)]">
                          {definition.normalRange.min} – {definition.normalRange.max}
                          {definition.normalRange.unit ? ` ${definition.normalRange.unit}` : ''}
                        </span>
                      </div>
                    )}

                    {/* Formula */}
                    {definition.formula && (
                      <div className="p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
                        <div className="flex items-center gap-1 text-xs text-[var(--text-muted)] mb-1.5">
                          <Code className="w-3 h-3" />
                          <span>Formula</span>
                        </div>
                        <code className="text-xs font-mono text-[var(--accent-amber)] break-all">
                          {definition.formula}
                        </code>
                      </div>
                    )}

                    {/* Notes */}
                    {definition.notes && (
                      <div className="flex items-start gap-2 p-2.5 rounded-lg bg-[var(--accent-amber)]/5 border border-[var(--accent-amber)]/20">
                        <AlertTriangle className="w-3.5 h-3.5 text-[var(--accent-amber)] mt-0.5 flex-shrink-0" />
                        <p className="text-xs text-[var(--accent-amber)]">{definition.notes}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Source Tab */}
                {activeTab === 'source' && (
                  <div className="space-y-3">
                    {/* Source System */}
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
                      <span className="text-xs text-[var(--text-muted)]">System</span>
                      <span className="text-sm text-[var(--text-primary)]">
                        {definition.source.system}
                      </span>
                    </div>

                    {/* API Endpoint */}
                    {definition.source.endpoint && (
                      <div className="p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
                        <div className="flex items-center gap-1 text-xs text-[var(--text-muted)] mb-1.5">
                          <Database className="w-3 h-3" />
                          <span>API Endpoint</span>
                        </div>
                        <code className="text-xs font-mono text-[var(--status-success)]">
                          {definition.source.endpoint}
                        </code>
                      </div>
                    )}

                    {/* Request ID */}
                    {context?.requestId && (
                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
                        <span className="text-xs text-[var(--text-muted)]">Request ID</span>
                        <div className="flex items-center gap-2">
                          <code className="text-xs font-mono text-[var(--text-secondary)]">
                            {context.requestId.slice(0, 16)}...
                          </code>
                          <button
                            onClick={() => copyToClipboard(context.requestId!)}
                            className="p-1 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                            title="Copy to clipboard"
                          >
                            {copied ? (
                              <CheckCircle className="w-3 h-3 text-[var(--status-success)]" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Computed By */}
                    {definition.computedBy && (
                      <div className="p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
                        <div className="text-xs text-[var(--text-muted)] mb-1.5">Computed By</div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-[var(--text-primary)]">
                            {definition.computedBy.rule}
                          </span>
                          <span className="px-1.5 py-0.5 text-[10px] bg-[var(--bg-elevated)] text-[var(--text-muted)] rounded font-mono">
                            v{context?.ruleVersion || definition.computedBy.version}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Documentation Link */}
                    {definition.source.documentation && (
                      <a
                        href={definition.source.documentation}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-xs text-[var(--accent-cyan)] hover:underline"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View Documentation
                        <ChevronRight className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                )}

                {/* Time Tab */}
                {activeTab === 'time' && (
                  <div className="space-y-3">
                    {context?.eventTime && (
                      <TimeRow
                        label="Event Time"
                        sublabel="When the event occurred"
                        time={context.eventTime}
                        color="text-[var(--text-primary)]"
                      />
                    )}

                    {context?.ingestTime && (
                      <TimeRow
                        label="Ingest Time"
                        sublabel="When OMEN received data"
                        time={context.ingestTime}
                        color="text-[var(--accent-amber)]"
                      />
                    )}

                    {context?.computeTime && (
                      <TimeRow
                        label="Compute Time"
                        sublabel="When OMEN processed data"
                        time={context.computeTime}
                        color="text-[var(--status-success)]"
                      />
                    )}

                    <TimeRow
                      label="Display Time"
                      sublabel="Current time"
                      time={new Date().toISOString()}
                      color="text-[var(--text-muted)]"
                    />

                    {!context?.eventTime && !context?.ingestTime && !context?.computeTime && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--bg-tertiary)]/50 text-[var(--text-muted)]">
                        <Clock className="w-4 h-4" />
                        <span className="text-sm">No timestamp data available</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Quality Tab */}
                {activeTab === 'quality' && (
                  <div className="space-y-3">
                    {/* Quality Score */}
                    {context?.quality !== undefined && (
                      <div className="p-3 rounded-lg bg-[var(--bg-tertiary)]/50">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-[var(--text-muted)]">Quality Score</span>
                          <span
                            className={cn(
                              'text-sm font-mono font-bold',
                              context.quality >= 0.7
                                ? 'text-[var(--status-success)]'
                                : context.quality >= 0.4
                                ? 'text-[var(--accent-amber)]'
                                : 'text-[var(--status-error)]'
                            )}
                          >
                            {(context.quality * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
                          <div
                            className={cn(
                              'h-full rounded-full transition-all duration-500',
                              context.quality >= 0.7
                                ? 'bg-[var(--status-success)]'
                                : context.quality >= 0.4
                                ? 'bg-[var(--accent-amber)]'
                                : 'bg-[var(--status-error)]'
                            )}
                            style={{ width: `${context.quality * 100}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Quality Indicators */}
                    {definition.qualityIndicators?.map((indicator, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-3.5 h-3.5 text-[var(--status-success)]" />
                          <span className="text-xs text-[var(--text-secondary)]">
                            {indicator.metric}
                          </span>
                        </div>
                        <span className="text-xs text-[var(--text-muted)] font-mono">
                          ≥ {indicator.threshold}
                        </span>
                      </div>
                    ))}

                    {/* Quality Flags */}
                    {context?.qualityFlags && context.qualityFlags.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs text-[var(--text-muted)]">Quality Flags</div>
                        {context.qualityFlags.map((flag, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 p-2 rounded bg-[var(--accent-amber)]/10 text-[var(--accent-amber)]"
                          >
                            <AlertTriangle className="w-3 h-3" />
                            <span className="text-xs">{flag}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* No Quality Data */}
                    {context?.quality === undefined && !definition.qualityIndicators && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--bg-tertiary)]/50 text-[var(--text-muted)]">
                        <Sparkles className="w-4 h-4" />
                        <span className="text-sm">No quality metrics available</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="px-4 py-2 border-t border-[var(--border-subtle)] bg-[var(--bg-tertiary)]/30">
                <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)]">
                  <span className="font-mono">{fieldId}</span>
                  <span>Press ESC to close</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </FloatingPortal>
    </>
  );
}

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

function TimeRow({
  label,
  sublabel,
  time,
  color,
}: {
  label: string;
  sublabel: string;
  time: string;
  color: string;
}) {
  const date = new Date(time);
  const isValid = !isNaN(date.getTime());

  return (
    <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-tertiary)]/50">
      <div>
        <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <Clock className="w-3 h-3" />
          {label}
        </div>
        <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{sublabel}</div>
      </div>
      <span className={cn('text-xs font-mono', color)}>
        {isValid ? date.toLocaleString() : time}
      </span>
    </div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default ExplainPopover;
