/**
 * ActivityFeed - Neural Command Center live activity feed
 * Features: Auto-scrolling, type icons, animated entries
 */
import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, Activity, RefreshCw, AlertTriangle, Radio } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { ActivityFeedItem } from '../../types/omen';

type ActivityType = 'signal' | 'validation' | 'rejection' | 'reconcile' | 'alert' | 'source' | 'translation';

interface ActivityConfig {
  icon: React.ReactNode;
  color: string;
  label: string;
}

const TYPE_CONFIG: Record<ActivityType, ActivityConfig> = {
  signal: {
    icon: <CheckCircle className="w-4 h-4" />,
    color: 'text-status-success',
    label: 'Signal',
  },
  validation: {
    icon: <Activity className="w-4 h-4" />,
    color: 'text-accent-cyan',
    label: 'Validation',
  },
  rejection: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'text-status-error',
    label: 'Rejection',
  },
  reconcile: {
    icon: <RefreshCw className="w-4 h-4" />,
    color: 'text-accent-amber',
    label: 'Reconcile',
  },
  alert: {
    icon: <AlertTriangle className="w-4 h-4" />,
    color: 'text-status-warning',
    label: 'Alert',
  },
  source: {
    icon: <Radio className="w-4 h-4" />,
    color: 'text-text-muted',
    label: 'Source',
  },
  translation: {
    icon: <Activity className="w-4 h-4" />,
    color: 'text-accent-cyan',
    label: 'Translation',
  },
};

// Extended activity item with more fields
export interface LiveActivityItem extends Omit<ActivityFeedItem, 'type'> {
  type: ActivityType;
  id?: string;
}

interface ActivityFeedProps {
  items?: LiveActivityItem[];
  maxItems?: number;
  autoScroll?: boolean;
  className?: string;
}

// Sample data for demo mode
const SAMPLE_ACTIVITIES: LiveActivityItem[] = [
  { id: '1', type: 'signal', message: 'Signal OMEN-9C4860 generated', time: '14:32:45' },
  { id: '2', type: 'validation', message: 'Event polymarket-677404 validated', time: '14:32:44' },
  { id: '3', type: 'rejection', message: 'Event filtered: low liquidity', time: '14:32:42' },
  { id: '4', type: 'reconcile', message: 'Ledger reconciled: 0 missing', time: '14:30:00' },
  { id: '5', type: 'signal', message: 'Signal OMEN-ABC123 generated', time: '14:28:15' },
  { id: '6', type: 'rejection', message: 'Event filtered: irrelevant', time: '14:28:10' },
  { id: '7', type: 'validation', message: 'Event ais-update-45 validated', time: '14:27:30' },
  { id: '8', type: 'source', message: 'Weather API connected', time: '14:25:00' },
];

export function ActivityFeed({
  items = SAMPLE_ACTIVITIES,
  maxItems = 20,
  autoScroll = true,
  className,
}: ActivityFeedProps) {
  const list = items.slice(0, maxItems);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest on new items
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [list.length, autoScroll]);

  return (
    <div
      ref={containerRef}
      className={cn(
        'h-full overflow-y-auto overflow-thin-scroll space-y-1 pr-2',
        className
      )}
    >
      <AnimatePresence mode="popLayout">
        {list.map((item, index) => {
          const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.source;
          return (
            <motion.div
              key={item.id || index}
              initial={{ opacity: 0, x: -20, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              exit={{ opacity: 0, x: 20, height: 0 }}
              transition={{ duration: 0.2, delay: index * 0.02 }}
              className="flex items-start gap-2 p-2 rounded-lg hover:bg-bg-tertiary/50 transition-colors"
            >
              <span className={cn('mt-0.5 shrink-0', config.color)}>
                {config.icon}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary truncate">{item.message}</p>
                <p className="text-xs text-text-muted font-mono">{item.time}</p>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

// Compact version for dashboard
export function CompactActivityFeed({
  items = SAMPLE_ACTIVITIES,
  maxItems = 6,
  className,
}: ActivityFeedProps) {
  const list = items.slice(0, maxItems);

  return (
    <div className={cn('space-y-1', className)}>
      {list.map((item, index) => {
        const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.source;
        return (
          <div
            key={item.id || index}
            className="flex items-center gap-2 px-2 py-1.5 text-xs rounded hover:bg-bg-tertiary/30 transition-colors"
          >
            <span className={cn('shrink-0', config.color)}>{config.icon}</span>
            <span className="flex-1 truncate text-text-secondary">{item.message}</span>
            <span className="shrink-0 text-text-muted font-mono">{item.time}</span>
          </div>
        );
      })}
    </div>
  );
}
