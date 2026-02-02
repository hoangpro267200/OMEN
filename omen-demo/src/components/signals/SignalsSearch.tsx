import { useState, useEffect, useCallback } from 'react';
import { Search } from 'lucide-react';
import { cn } from '../../lib/utils';

const DEBOUNCE_MS = 300;

export interface SignalsSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

/**
 * Debounced search input (300ms). For signal_id, trace_id, source_event_id.
 */
export function SignalsSearch({
  value,
  onChange,
  placeholder = 'Search by signal_id, trace_id, source_event_id...',
  className = '',
}: SignalsSearchProps) {
  const [local, setLocal] = useState(value);

  useEffect(() => {
    setLocal(value);
  }, [value]);

  useEffect(() => {
    const t = setTimeout(() => {
      if (local !== value) onChange(local);
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [local]); // eslint-disable-line react-hooks/exhaustive-deps -- only debounce on local change

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => setLocal(e.target.value),
    []
  );

  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 focus-within:border-[var(--border-active)]',
        className
      )}
    >
      <Search className="h-4 w-4 shrink-0 text-[var(--text-muted)]" />
      <input
        id="search-input"
        data-demo-target="search-input"
        type="text"
        value={local}
        onChange={handleChange}
        placeholder={placeholder}
        className="min-w-0 flex-1 border-0 bg-transparent font-mono text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
        aria-label="Search signals"
      />
    </div>
  );
}
