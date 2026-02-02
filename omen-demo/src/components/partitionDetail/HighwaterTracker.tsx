import { Badge } from '../ui/Badge';
import type { HighwaterData } from '../../data/partitionDetailMock';

export interface HighwaterTrackerProps {
  highwater: HighwaterData;
  className?: string;
}

/**
 * Zone 3: Highwater Tracker (collapsed by default).
 */
export function HighwaterTracker({ highwater, className = '' }: HighwaterTrackerProps) {
  const { lastSeen, current, status } = highwater;
  const increased = status === 'increased';

  return (
    <div className={className}>
      <dl className="space-y-2 font-mono text-sm">
        <div>
          <dt className="text-[var(--text-muted)]">Last seen highwater</dt>
          <dd className="text-[var(--text-primary)]">{lastSeen}</dd>
        </div>
        <div>
          <dt className="text-[var(--text-muted)]">Current highwater</dt>
          <dd className="text-[var(--text-primary)]">{current}</dd>
        </div>
        <div>
          <dt className="text-[var(--text-muted)]">Status</dt>
          <dd className="text-[var(--text-secondary)]">
            {increased
              ? 'Highwater increased → re-reconcile suggested'
              : 'No change — reconcile not needed'}
          </dd>
        </div>
      </dl>
      {increased && (
        <div className="mt-3">
          <Badge variant="PARTIAL">Highwater increased → re-reconcile suggested</Badge>
        </div>
      )}
    </div>
  );
}
