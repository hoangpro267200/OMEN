interface EmptyStateProps {
  message: string;
  onLoadDemo?: () => void;
}

export function EmptyState({ message, onLoadDemo }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-center px-6">
      <div
        className="w-20 h-20 rounded-full bg-[var(--bg-elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-6"
        aria-hidden
      >
        <svg
          className="w-10 h-10 text-[var(--text-tertiary)]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z"
          />
        </svg>
      </div>
      <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">
        Không có tín hiệu
      </h2>
      <p className="text-[var(--text-secondary)] max-w-md mb-6">{message}</p>
      {onLoadDemo && (
        <button
          type="button"
          onClick={onLoadDemo}
          className="px-4 py-2 bg-[var(--bg-elevated)] border border-[var(--border-default)] rounded-lg hover:bg-[var(--bg-hover)] transition-colors text-[var(--text-primary)]"
        >
          Xem dữ liệu demo
        </button>
      )}
    </div>
  );
}
