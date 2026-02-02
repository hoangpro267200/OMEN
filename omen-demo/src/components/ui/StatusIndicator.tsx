/**
 * StatusIndicator - Neural Command Center status indicator
 * Features: Pulsing animation, glow effect, multiple sizes, status colors
 */
import { cn } from '../../lib/utils';

export type StatusType = 'healthy' | 'warning' | 'error' | 'inactive' | 'mock' | 'live' | 'success';

export interface StatusIndicatorProps {
  status: StatusType;
  pulse?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  label?: string;
  showLabel?: boolean;
  className?: string;
}

const statusColors: Record<StatusType, { bg: string; glow: string }> = {
  healthy: { 
    bg: 'bg-status-success', 
    glow: 'shadow-[0_0_8px_rgba(0,255,136,0.6)]' 
  },
  success: { 
    bg: 'bg-status-success', 
    glow: 'shadow-[0_0_8px_rgba(0,255,136,0.6)]' 
  },
  live: { 
    bg: 'bg-status-success', 
    glow: 'shadow-[0_0_8px_rgba(0,255,136,0.6)]' 
  },
  warning: { 
    bg: 'bg-status-warning', 
    glow: 'shadow-[0_0_8px_rgba(255,170,0,0.6)]' 
  },
  error: { 
    bg: 'bg-status-error', 
    glow: 'shadow-[0_0_8px_rgba(255,51,102,0.6)]' 
  },
  inactive: { 
    bg: 'bg-text-muted', 
    glow: '' 
  },
  mock: { 
    bg: 'bg-text-secondary', 
    glow: '' 
  },
};

const statusLabels: Record<StatusType, string> = {
  healthy: 'Healthy',
  success: 'Success',
  live: 'Live',
  warning: 'Warning',
  error: 'Error',
  inactive: 'Inactive',
  mock: 'Mock',
};

const sizeClasses = {
  xs: 'w-1.5 h-1.5',
  sm: 'w-2 h-2',
  md: 'w-2.5 h-2.5',
  lg: 'w-3 h-3',
};

export function StatusIndicator({
  status,
  pulse = true,
  size = 'md',
  label,
  showLabel = false,
  className,
}: StatusIndicatorProps) {
  const { bg, glow } = statusColors[status];
  const shouldPulse = pulse && status !== 'inactive' && status !== 'mock';

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="relative inline-flex">
        {/* Pulse ring */}
        {shouldPulse && (
          <span
            className={cn(
              'absolute inset-0 rounded-full animate-ping',
              bg,
              'opacity-40'
            )}
          />
        )}
        {/* Main dot */}
        <span
          className={cn(
            'relative rounded-full',
            sizeClasses[size],
            bg,
            shouldPulse && glow
          )}
        />
      </span>
      {showLabel && (
        <span className="text-sm text-text-secondary font-mono">
          {label || statusLabels[status]}
        </span>
      )}
    </div>
  );
}

// Compact version for table cells
export function StatusBadge({
  status,
  className,
}: {
  status: StatusType;
  className?: string;
}) {
  const statusConfig: Record<StatusType, { label: string; className: string }> = {
    healthy: { label: 'OK', className: 'bg-status-success/20 text-status-success border-status-success/30' },
    success: { label: 'OK', className: 'bg-status-success/20 text-status-success border-status-success/30' },
    live: { label: 'LIVE', className: 'bg-status-success/20 text-status-success border-status-success/30' },
    warning: { label: 'WARN', className: 'bg-status-warning/20 text-status-warning border-status-warning/30' },
    error: { label: 'ERR', className: 'bg-status-error/20 text-status-error border-status-error/30' },
    inactive: { label: 'OFF', className: 'bg-text-muted/20 text-text-muted border-text-muted/30' },
    mock: { label: 'MOCK', className: 'bg-text-secondary/20 text-text-secondary border-text-secondary/30' },
  };

  const config = statusConfig[status];

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-mono border',
        config.className,
        className
      )}
    >
      <StatusIndicator status={status} size="xs" pulse={false} className="mr-1.5" />
      {config.label}
    </span>
  );
}
