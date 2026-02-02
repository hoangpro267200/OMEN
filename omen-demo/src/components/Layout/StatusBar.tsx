/**
 * StatusBar - Neural Command Center bottom status bar
 * Features: Data source health indicators, system metrics, version info
 */
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import { StatusIndicator, type StatusType } from '../ui/StatusIndicator';

interface DataSourceStatus {
  name: string;
  status: StatusType;
}

const DATA_SOURCES: DataSourceStatus[] = [
  { name: 'Polymarket', status: 'healthy' },
  { name: 'AIS', status: 'healthy' },
  { name: 'Commodity', status: 'healthy' },
  { name: 'Weather', status: 'warning' },
  { name: 'News', status: 'healthy' },
  { name: 'Stock', status: 'healthy' },
  { name: 'Freight', status: 'mock' },
];

export interface StatusBarProps {
  ledgerCount?: number;
  hotPathStatus?: 'ok' | 'degraded' | 'error';
  version?: string;
  className?: string;
}

export function StatusBar({
  ledgerCount = 2847,
  hotPathStatus = 'ok',
  version = '1.0.0',
  className,
}: StatusBarProps) {
  return (
    <motion.footer
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.3 }}
      className={cn(
        'fixed bottom-0 left-0 right-0 z-30 h-8 flex items-center justify-between px-4',
        'bg-bg-secondary/95 backdrop-blur-sm border-t border-border-subtle',
        'text-xs font-mono',
        className
      )}
    >
      {/* Left: Data source status indicators */}
      <div className="flex items-center gap-4 overflow-x-auto overflow-thin-scroll">
        {DATA_SOURCES.map(({ name, status }) => (
          <div key={name} className="flex items-center gap-1.5 shrink-0">
            <StatusIndicator status={status} size="xs" pulse={status === 'healthy'} />
            <span className="text-text-muted">{name}</span>
          </div>
        ))}
      </div>

      {/* Right: System info */}
      <div className="flex items-center gap-4 shrink-0 ml-4">
        {/* Ledger count */}
        <div className="flex items-center gap-1.5">
          <span className="text-text-muted">Ledger:</span>
          <span className="text-status-success tabular-nums">{ledgerCount.toLocaleString()}</span>
        </div>

        {/* Hot Path status */}
        <div className="flex items-center gap-1.5">
          <span className="text-text-muted">Hot Path:</span>
          <span className={cn(
            hotPathStatus === 'ok' && 'text-status-success',
            hotPathStatus === 'degraded' && 'text-status-warning',
            hotPathStatus === 'error' && 'text-status-error'
          )}>
            {hotPathStatus === 'ok' ? 'OK' : hotPathStatus === 'degraded' ? 'DEGRADED' : 'ERROR'}
          </span>
        </div>

        {/* Version */}
        <span className="text-text-muted">v{version}</span>
      </div>
    </motion.footer>
  );
}
