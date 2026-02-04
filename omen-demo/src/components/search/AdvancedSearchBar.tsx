/**
 * AdvancedSearchBar - Enterprise search with syntax highlighting and suggestions
 * 
 * Features:
 * - Syntax highlighting for filters
 * - Auto-suggestions with keyboard navigation
 * - Filter pills for active filters
 * - Search history
 * - Clear and reset actions
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  X,
  Filter,
  Clock,
  ChevronRight,
  Sparkles,
  Tag,
  Hash,
  AlertCircle,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import {
  parseSearchQuery,
  getSearchSuggestions,
  SEARCHABLE_FIELDS,
  type ParsedQuery,
  type SearchSuggestion,
  type SearchFilter,
} from '../../lib/search-parser';

// ============================================================================
// TYPES
// ============================================================================

export interface AdvancedSearchBarProps {
  /** Current search value */
  value?: string;
  /** Callback when search changes */
  onChange?: (value: string, parsed: ParsedQuery) => void;
  /** Callback when search is submitted */
  onSubmit?: (value: string, parsed: ParsedQuery) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Show suggestions dropdown */
  showSuggestions?: boolean;
  /** Show active filter pills */
  showFilterPills?: boolean;
  /** Additional class names */
  className?: string;
  /** Auto-focus on mount */
  autoFocus?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

// ============================================================================
// STORAGE
// ============================================================================

const HISTORY_KEY = 'omen-search-history';
const MAX_HISTORY = 10;

function loadSearchHistory(): string[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveSearchHistory(history: string[]): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
  } catch {
    // Ignore
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

export function AdvancedSearchBar({
  value: controlledValue,
  onChange,
  onSubmit,
  placeholder = 'Search signals... (try status:ACTIVE or confidence:>0.7)',
  showSuggestions = true,
  showFilterPills = true,
  className,
  autoFocus = false,
  size = 'md',
}: AdvancedSearchBarProps) {
  // State
  const [internalValue, setInternalValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [history, setHistory] = useState<string[]>([]);

  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Controlled vs uncontrolled value
  const value = controlledValue !== undefined ? controlledValue : internalValue;
  const setValue = (newValue: string) => {
    if (controlledValue === undefined) {
      setInternalValue(newValue);
    }
    const parsed = parseSearchQuery(newValue);
    onChange?.(newValue, parsed);
  };

  // Parse current query
  const parsedQuery = useMemo(() => parseSearchQuery(value), [value]);

  // Get suggestions
  const suggestions = useMemo(() => {
    if (!showSuggestions || !isFocused) return [];
    
    const baseSuggestions = getSearchSuggestions(value);
    
    // Add history suggestions if no value
    if (!value && history.length > 0) {
      const historySuggestions: SearchSuggestion[] = history.slice(0, 3).map((h) => ({
        type: 'example',
        label: h,
        value: h,
        description: 'Recent search',
      }));
      return [...historySuggestions, ...baseSuggestions];
    }
    
    return baseSuggestions;
  }, [value, isFocused, showSuggestions, history]);

  // Load history on mount
  useEffect(() => {
    setHistory(loadSearchHistory());
  }, []);

  // Handle input change
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
    setSelectedIndex(-1);
  };

  // Handle submit
  const handleSubmit = useCallback(() => {
    if (!value.trim()) return;
    
    // Save to history
    const newHistory = [value, ...history.filter((h) => h !== value)].slice(0, MAX_HISTORY);
    setHistory(newHistory);
    saveSearchHistory(newHistory);
    
    onSubmit?.(value, parsedQuery);
    setIsFocused(false);
    inputRef.current?.blur();
  }, [value, history, parsedQuery, onSubmit]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, suggestions.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          setValue(suggestions[selectedIndex].value + ' ');
          setSelectedIndex(-1);
        } else {
          handleSubmit();
        }
        break;
      case 'Escape':
        setIsFocused(false);
        inputRef.current?.blur();
        break;
      case 'Tab':
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          e.preventDefault();
          setValue(suggestions[selectedIndex].value + ' ');
          setSelectedIndex(-1);
        }
        break;
    }
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: SearchSuggestion) => {
    setValue(suggestion.value + ' ');
    inputRef.current?.focus();
    setSelectedIndex(-1);
  };

  // Remove a filter pill
  const removeFilter = (filter: SearchFilter) => {
    const newValue = value.replace(filter.raw, '').replace(/\s+/g, ' ').trim();
    setValue(newValue);
  };

  // Clear all
  const clearAll = () => {
    setValue('');
    inputRef.current?.focus();
  };

  // Size config
  const sizeConfig = {
    sm: { input: 'h-9 text-sm', icon: 'w-4 h-4', pill: 'text-xs px-2 py-0.5' },
    md: { input: 'h-11 text-base', icon: 'w-5 h-5', pill: 'text-xs px-2.5 py-1' },
    lg: { input: 'h-14 text-lg', icon: 'w-6 h-6', pill: 'text-sm px-3 py-1.5' },
  };

  const config = sizeConfig[size];

  return (
    <div className={cn('relative', className)}>
      {/* Main Input */}
      <div
        className={cn(
          'relative flex items-center gap-2 rounded-xl border transition-all',
          'bg-[var(--bg-secondary)] border-[var(--border-subtle)]',
          isFocused && 'border-[var(--accent-cyan)] ring-2 ring-[var(--accent-cyan)]/20',
          config.input
        )}
      >
        {/* Search Icon */}
        <Search className={cn('ml-4 text-[var(--text-muted)]', config.icon)} />

        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className={cn(
            'flex-1 bg-transparent outline-none',
            'text-[var(--text-primary)] placeholder-[var(--text-muted)]',
            'font-body'
          )}
        />

        {/* Clear Button */}
        {value && (
          <button
            onClick={clearAll}
            className="p-1.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)] mr-2"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={!value.trim()}
          className={cn(
            'mr-2 px-3 py-1.5 rounded-lg font-medium text-sm transition-all',
            value.trim()
              ? 'bg-[var(--accent-cyan)] text-black hover:bg-[var(--accent-cyan)]/90'
              : 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] cursor-not-allowed'
          )}
        >
          Search
        </button>
      </div>

      {/* Filter Pills */}
      {showFilterPills && parsedQuery.filters.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap gap-2 mt-2"
        >
          {parsedQuery.filters.map((filter, idx) => (
            <FilterPill key={idx} filter={filter} onRemove={() => removeFilter(filter)} size={config.pill} />
          ))}
          {parsedQuery.freeText && (
            <span className={cn('rounded-full bg-[var(--bg-tertiary)] text-[var(--text-secondary)]', config.pill)}>
              "{parsedQuery.freeText}"
            </span>
          )}
        </motion.div>
      )}

      {/* Suggestions Dropdown */}
      <AnimatePresence>
        {isFocused && suggestions.length > 0 && (
          <motion.div
            ref={suggestionsRef}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className={cn(
              'absolute top-full left-0 right-0 mt-2 z-50',
              'bg-[var(--bg-secondary)] border border-[var(--border-subtle)]',
              'rounded-xl shadow-2xl shadow-black/20 overflow-hidden'
            )}
          >
            {/* Header */}
            <div className="px-3 py-2 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)]/50">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                <Sparkles className="w-3 h-3" />
                <span>Suggestions</span>
                <span className="text-[var(--text-muted)]/50">— Use ↑↓ to navigate, Tab to complete</span>
              </div>
            </div>

            {/* Suggestions List */}
            <div className="max-h-64 overflow-y-auto">
              {suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                    idx === selectedIndex
                      ? 'bg-[var(--accent-cyan)]/10 text-[var(--text-primary)]'
                      : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
                  )}
                >
                  {/* Icon */}
                  <span className="text-[var(--text-muted)]">
                    {suggestion.type === 'field' && <Tag className="w-4 h-4" />}
                    {suggestion.type === 'operator' && <Hash className="w-4 h-4" />}
                    {suggestion.type === 'value' && <Filter className="w-4 h-4" />}
                    {suggestion.type === 'example' && <Clock className="w-4 h-4" />}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm">{suggestion.label}</div>
                    {suggestion.description && (
                      <div className="text-xs text-[var(--text-muted)] truncate">
                        {suggestion.description}
                      </div>
                    )}
                  </div>

                  <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                </button>
              ))}
            </div>

            {/* Footer */}
            <div className="px-3 py-2 border-t border-[var(--border-subtle)] bg-[var(--bg-tertiary)]/50">
              <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)]">
                <span>
                  Examples: <code className="px-1 bg-[var(--bg-primary)] rounded">status:ACTIVE</code>
                  {' '}<code className="px-1 bg-[var(--bg-primary)] rounded">confidence:&gt;0.7</code>
                </span>
                <span>Press Enter to search</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// FILTER PILL COMPONENT
// ============================================================================

interface FilterPillProps {
  filter: SearchFilter;
  onRemove: () => void;
  size?: string;
}

function FilterPill({ filter, onRemove, size }: FilterPillProps) {
  // Get field config
  const fieldConfig = Object.entries(SEARCHABLE_FIELDS).find(
    ([, config]) => config.name === filter.field
  )?.[1];

  // Determine color based on field type
  const getColor = () => {
    if (!fieldConfig) return 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]';
    
    switch (fieldConfig.type) {
      case 'enum':
        return 'bg-[var(--accent-cyan)]/20 text-[var(--accent-cyan)] border-[var(--accent-cyan)]/30';
      case 'number':
        return 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border-[var(--accent-amber)]/30';
      default:
        return 'bg-[var(--text-muted)]/20 text-[var(--text-secondary)] border-[var(--text-muted)]/30';
    }
  };

  // Format operator
  const formatOperator = () => {
    switch (filter.operator) {
      case '>': return '>';
      case '<': return '<';
      case '>=': return '≥';
      case '<=': return '≤';
      case 'contains': return '~';
      default: return '=';
    }
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border font-mono',
        getColor(),
        size
      )}
    >
      <span className="opacity-70">{fieldConfig?.label || filter.field}</span>
      <span className="opacity-50">{formatOperator()}</span>
      <span>{filter.value}</span>
      <button
        onClick={onRemove}
        className="ml-1 p-0.5 rounded-full hover:bg-black/10"
      >
        <X className="w-3 h-3" />
      </button>
    </span>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default AdvancedSearchBar;
