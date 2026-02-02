/**
 * SystemStatus - Neural Command Center system health display
 * Features: Pipeline status, data source count, hot path status, ledger sync
 */
import { motion } from 'framer-motion';
import { GitBranch, Database, Zap, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';
import { StatusIndicator, type StatusType } from '../ui/StatusIndicator';

interface StatusItemProps {
  icon: React.ReactNode;
  label: string;
  detail: string;
  status: StatusType;
  index: number;
}

function StatusItem({ icon, label, detail, status, index }: StatusItemProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary/50 border border-border-subtle hover:border-border-active transition-colors"
    >
      <div className="flex items-center gap-3">
        <span className="text-text-muted">{icon}</span>
        <div>
          <p className="text-sm font-medium text-text-primary">{label}</p>
          <p className="text-xs text-text-muted">{detail}</p>
        </div>
      </div>
      <StatusIndicator status={status} size="md" />
    </motion.div>
  );
}

export interface SystemStatusProps {
  pipelineStatus?: StatusType;
  pipelineDetail?: string;
  sourcesActive?: number;
  sourcesTotal?: number;
  hotPathStatus?: StatusType;
  hotPathDetail?: string;
  ledgerStatus?: StatusType;
  lastReconcile?: string;
  className?: string;
}

export function SystemStatus({
  pipelineStatus = 'healthy',
  pipelineDetail = 'Processing 2.1 events/sec',
  sourcesActive = 7,
  sourcesTotal = 8,
  hotPathStatus = 'healthy',
  hotPathDetail = 'Circuit closed',
  ledgerStatus = 'healthy',
  lastReconcile = '2m ago',
  className,
}: SystemStatusProps) {
  const items = [
    {
      icon: <GitBranch className="w-4 h-4" />,
      label: 'Pipeline',
      detail: pipelineDetail,
      status: pipelineStatus,
    },
    {
      icon: <Database className="w-4 h-4" />,
      label: 'Data Sources',
      detail: `${sourcesActive}/${sourcesTotal} connected`,
      status: sourcesActive === sourcesTotal ? 'healthy' : sourcesActive > 0 ? 'warning' : 'error',
    },
    {
      icon: <Zap className="w-4 h-4" />,
      label: 'Hot Path',
      detail: hotPathDetail,
      status: hotPathStatus,
    },
    {
      icon: <RefreshCw className="w-4 h-4" />,
      label: 'Ledger Sync',
      detail: `Last reconcile: ${lastReconcile}`,
      status: ledgerStatus,
    },
  ];

  return (
    <div className={cn('space-y-2', className)}>
      {items.map((item, index) => (
        <StatusItem
          key={item.label}
          icon={item.icon}
          label={item.label}
          detail={item.detail}
          status={item.status as StatusType}
          index={index}
        />
      ))}
    </div>
  );
}
