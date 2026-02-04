/**
 * Advanced Search Parser - Parse and execute structured search queries
 * 
 * Supported syntax:
 * - field:value (exact match)
 * - field:>number (greater than)
 * - field:<number (less than)
 * - field:>=number (greater than or equal)
 * - field:<=number (less than or equal)
 * - field:"exact phrase" (exact phrase match)
 * - field:*partial* (contains)
 * - Multiple conditions with AND (implicit)
 * - Free text search across all fields
 */

// ============================================================================
// TYPES
// ============================================================================

export type FilterOperator = '=' | '>' | '<' | '>=' | '<=' | 'contains' | 'startsWith' | 'endsWith';

export interface SearchFilter {
  field: string;
  operator: FilterOperator;
  value: string | number;
  raw: string;
}

export interface ParsedQuery {
  filters: SearchFilter[];
  freeText: string;
  raw: string;
}

export interface SearchSuggestion {
  type: 'field' | 'operator' | 'value' | 'example';
  label: string;
  value: string;
  description?: string;
}

// ============================================================================
// FIELD CONFIGURATION
// ============================================================================

export interface FieldConfig {
  name: string;
  type: 'string' | 'number' | 'date' | 'enum';
  label: string;
  description?: string;
  enumValues?: string[];
  aliases?: string[];
}

export const SEARCHABLE_FIELDS: Record<string, FieldConfig> = {
  status: {
    name: 'status',
    type: 'enum',
    label: 'Status',
    description: 'Signal status',
    enumValues: ['ACTIVE', 'MONITORING', 'CANDIDATE', 'ARCHIVED', 'DEGRADED'],
    aliases: ['state', 's'],
  },
  confidence: {
    name: 'confidence_score',
    type: 'number',
    label: 'Confidence',
    description: 'Confidence score (0-1)',
    aliases: ['conf', 'c', 'score'],
  },
  probability: {
    name: 'probability',
    type: 'number',
    label: 'Probability',
    description: 'Event probability (0-1)',
    aliases: ['prob', 'p'],
  },
  category: {
    name: 'category',
    type: 'enum',
    label: 'Category',
    description: 'Signal category',
    enumValues: ['GEOPOLITICAL', 'CLIMATE', 'INFRASTRUCTURE', 'ECONOMIC', 'SUPPLY_CHAIN'],
    aliases: ['cat', 'type'],
  },
  severity: {
    name: 'severity_label',
    type: 'enum',
    label: 'Severity',
    description: 'Severity level',
    enumValues: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
    aliases: ['sev', 'level'],
  },
  source: {
    name: 'probability_source',
    type: 'string',
    label: 'Source',
    description: 'Data source',
    aliases: ['src'],
  },
  region: {
    name: 'geographic.regions',
    type: 'string',
    label: 'Region',
    description: 'Geographic region',
    aliases: ['geo', 'location'],
  },
  id: {
    name: 'signal_id',
    type: 'string',
    label: 'Signal ID',
    description: 'Unique signal identifier',
    aliases: ['signal', 'sid'],
  },
  title: {
    name: 'title',
    type: 'string',
    label: 'Title',
    description: 'Signal title',
    aliases: ['name'],
  },
};

// ============================================================================
// PARSER
// ============================================================================

/**
 * Parse a search query string into structured filters
 */
export function parseSearchQuery(query: string): ParsedQuery {
  const filters: SearchFilter[] = [];
  let freeText = query;

  // Pattern for field:value, field:>value, field:"value", etc.
  const filterPattern = /(\w+):(>=?|<=?|!=|=)?("([^"]+)"|(\S+))/g;
  
  let match;
  while ((match = filterPattern.exec(query)) !== null) {
    const [fullMatch, rawField, operator = '=', , quotedValue, unquotedValue] = match;
    const value = quotedValue || unquotedValue;
    
    // Resolve field alias
    const field = resolveFieldName(rawField.toLowerCase());
    if (!field) continue;

    // Parse operator and value
    const parsedFilter = parseFilterValue(field, operator, value);
    if (parsedFilter) {
      filters.push({ ...parsedFilter, raw: fullMatch });
      freeText = freeText.replace(fullMatch, '').trim();
    }
  }

  return {
    filters,
    freeText: freeText.trim(),
    raw: query,
  };
}

/**
 * Resolve field alias to actual field name
 */
function resolveFieldName(input: string): string | null {
  // Direct match
  if (SEARCHABLE_FIELDS[input]) {
    return SEARCHABLE_FIELDS[input].name;
  }

  // Check aliases
  for (const [, config] of Object.entries(SEARCHABLE_FIELDS)) {
    if (config.aliases?.includes(input)) {
      return config.name;
    }
  }

  return null;
}

/**
 * Parse filter value based on operator
 */
function parseFilterValue(
  field: string,
  operator: string,
  value: string
): Omit<SearchFilter, 'raw'> | null {
  // Determine actual operator
  let op: FilterOperator = '=';
  let val: string | number = value;

  if (operator === '>') op = '>';
  else if (operator === '<') op = '<';
  else if (operator === '>=') op = '>=';
  else if (operator === '<=') op = '<=';
  else if (value.startsWith('*') && value.endsWith('*')) {
    op = 'contains';
    val = value.slice(1, -1);
  } else if (value.startsWith('*')) {
    op = 'endsWith';
    val = value.slice(1);
  } else if (value.endsWith('*')) {
    op = 'startsWith';
    val = value.slice(0, -1);
  }

  // Parse numeric values
  const numVal = parseFloat(val as string);
  if (!isNaN(numVal) && ['>', '<', '>=', '<='].includes(op)) {
    val = numVal;
  }

  return { field, operator: op, value: val };
}

// ============================================================================
// FILTER EXECUTION
// ============================================================================

/**
 * Apply parsed filters to a data array
 */
export function applyFilters<T extends Record<string, unknown>>(
  data: T[],
  query: ParsedQuery
): T[] {
  return data.filter((item) => {
    // Check all filters
    for (const filter of query.filters) {
      if (!matchesFilter(item, filter)) {
        return false;
      }
    }

    // Check free text (search across title, description, id)
    if (query.freeText) {
      const searchText = query.freeText.toLowerCase();
      const searchableText = [
        getNestedValue(item, 'title'),
        getNestedValue(item, 'description'),
        getNestedValue(item, 'signal_id'),
        getNestedValue(item, 'category'),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      if (!searchableText.includes(searchText)) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Check if an item matches a filter
 */
function matchesFilter<T extends Record<string, unknown>>(
  item: T,
  filter: SearchFilter
): boolean {
  const value = getNestedValue(item, filter.field);
  if (value === undefined || value === null) return false;

  const itemValue = typeof value === 'string' ? value.toLowerCase() : value;
  const filterValue =
    typeof filter.value === 'string' ? filter.value.toLowerCase() : filter.value;

  switch (filter.operator) {
    case '=':
      return String(itemValue) === String(filterValue);
    case '>':
      return Number(itemValue) > Number(filterValue);
    case '<':
      return Number(itemValue) < Number(filterValue);
    case '>=':
      return Number(itemValue) >= Number(filterValue);
    case '<=':
      return Number(itemValue) <= Number(filterValue);
    case 'contains':
      return String(itemValue).includes(String(filterValue));
    case 'startsWith':
      return String(itemValue).startsWith(String(filterValue));
    case 'endsWith':
      return String(itemValue).endsWith(String(filterValue));
    default:
      return false;
  }
}

/**
 * Get nested value from object using dot notation
 */
function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce((current: unknown, key) => {
    if (current && typeof current === 'object') {
      return (current as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

// ============================================================================
// SUGGESTIONS
// ============================================================================

/**
 * Generate search suggestions based on current input
 */
export function getSearchSuggestions(input: string): SearchSuggestion[] {
  const suggestions: SearchSuggestion[] = [];
  const lowerInput = input.toLowerCase();

  // If input is empty, show field suggestions
  if (!input) {
    return Object.entries(SEARCHABLE_FIELDS).map(([key, config]) => ({
      type: 'field',
      label: `${key}:`,
      value: `${key}:`,
      description: config.description,
    }));
  }

  // If input ends with ':', show value suggestions for that field
  const colonMatch = input.match(/^(\w+):$/);
  if (colonMatch) {
    const field = colonMatch[1].toLowerCase();
    const config = SEARCHABLE_FIELDS[field];
    
    if (config?.enumValues) {
      return config.enumValues.map((val) => ({
        type: 'value',
        label: `${field}:${val}`,
        value: `${field}:${val}`,
        description: `Filter by ${config.label} = ${val}`,
      }));
    }
    
    if (config?.type === 'number') {
      return [
        { type: 'operator', label: `${field}:>`, value: `${field}:>`, description: 'Greater than' },
        { type: 'operator', label: `${field}:<`, value: `${field}:<`, description: 'Less than' },
        { type: 'operator', label: `${field}:>=`, value: `${field}:>=`, description: 'Greater or equal' },
        { type: 'operator', label: `${field}:<=`, value: `${field}:<=`, description: 'Less or equal' },
      ];
    }
  }

  // Match partial field names
  const partialMatch = input.match(/^(\w*)$/);
  if (partialMatch) {
    const partial = partialMatch[1].toLowerCase();
    Object.entries(SEARCHABLE_FIELDS).forEach(([key, config]) => {
      if (key.startsWith(partial) || config.aliases?.some((a) => a.startsWith(partial))) {
        suggestions.push({
          type: 'field',
          label: `${key}:`,
          value: `${key}:`,
          description: config.description,
        });
      }
    });
  }

  // Add example queries if no specific suggestions
  if (suggestions.length === 0) {
    suggestions.push(
      { type: 'example', label: 'status:ACTIVE', value: 'status:ACTIVE', description: 'Active signals' },
      { type: 'example', label: 'confidence:>0.7', value: 'confidence:>0.7', description: 'High confidence' },
      { type: 'example', label: 'category:GEOPOLITICAL', value: 'category:GEOPOLITICAL', description: 'Geopolitical events' },
      { type: 'example', label: 'severity:CRITICAL', value: 'severity:CRITICAL', description: 'Critical severity' }
    );
  }

  return suggestions.slice(0, 8);
}

// ============================================================================
// QUERY BUILDER
// ============================================================================

/**
 * Build a query string from filters
 */
export function buildQueryString(filters: SearchFilter[], freeText?: string): string {
  const parts: string[] = [];

  for (const filter of filters) {
    let op = '';
    if (filter.operator === '>') op = '>';
    else if (filter.operator === '<') op = '<';
    else if (filter.operator === '>=') op = '>=';
    else if (filter.operator === '<=') op = '<=';

    const value = typeof filter.value === 'string' && filter.value.includes(' ')
      ? `"${filter.value}"`
      : filter.value;

    // Get short field name
    const shortField = Object.entries(SEARCHABLE_FIELDS).find(
      ([, config]) => config.name === filter.field
    )?.[0] || filter.field;

    parts.push(`${shortField}:${op}${value}`);
  }

  if (freeText) {
    parts.push(freeText);
  }

  return parts.join(' ');
}

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  parseSearchQuery,
  applyFilters,
  getSearchSuggestions,
  buildQueryString,
  SEARCHABLE_FIELDS,
};
