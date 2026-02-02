/**
 * ProgressBar - Neural Command Center progress indicator
 * Features: Animated fill, glow effects, gradient variants, dynamic colors
 */
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface ProgressBarProps {
  /** Current value */
  value: number;
  /** Maximum value (default 100) */
  max?: number;
  /** Optional label (e.g. "Validation Rate") */
  label?: string;
  /** Color variant */
  variant?: 'default' | 'cyan' | 'amber' | 'success' | 'warning' | 'error' | 'gradient' | 'dynamic';
  /** Size */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** Show percentage value */
  showValue?: boolean;
  /** Show glow effect */
  glow?: boolean;
  /** Animation enabled */
  animated?: boolean;
  className?: string;
}

const variantStyles: Record<string, { fill: string; glow: string }> = {
  default: { fill: 'bg-accent-cyan', glow: 'shadow-[0_0_10px_rgba(0,240,255,0.5)]' },
  cyan: { fill: 'bg-accent-cyan', glow: 'shadow-[0_0_10px_rgba(0,240,255,0.5)]' },
  amber: { fill: 'bg-accent-amber', glow: 'shadow-[0_0_10px_rgba(255,170,0,0.5)]' },
  success: { fill: 'bg-status-success', glow: 'shadow-[0_0_10px_rgba(0,255,136,0.5)]' },
  warning: { fill: 'bg-status-warning', glow: 'shadow-[0_0_10px_rgba(255,170,0,0.5)]' },
  error: { fill: 'bg-status-error', glow: 'shadow-[0_0_10px_rgba(255,51,102,0.5)]' },
  gradient: { fill: 'bg-gradient-to-r from-accent-cyan to-accent-amber', glow: 'shadow-[0_0_10px_rgba(0,240,255,0.3)]' },
};

const sizeClasses = {
  xs: 'h-1',
  sm: 'h-1.5',
  md: 'h-2',
  lg: 'h-3',
};

function getDynamicColor(pct: number): { fill: string; glow: string } {
  if (pct >= 75) return variantStyles.success;
  if (pct >= 50) return variantStyles.cyan;
  if (pct >= 25) return variantStyles.warning;
  return variantStyles.error;
}

export function ProgressBar({
  value,
  max = 100,
  label,
  variant = 'default',
  size = 'md',
  showValue = false,
  glow = false,
  animated = true,
  className,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const styles = variant === 'dynamic' ? getDynamicColor(pct) : variantStyles[variant];

  return (
    <div className={cn('w-full', className)}>
      {(label != null || showValue) && (
        <div className="mb-1.5 flex justify-between text-xs font-mono">
          {label != null && <span className="text-text-secondary">{label}</span>}
          {showValue && <span className="text-text-muted">{Math.round(pct)}%</span>}
        </div>
      )}
      <div 
        className={cn(
          'overflow-hidden rounded-full bg-bg-tertiary',
          sizeClasses[size]
        )}
      >
        <motion.div
          className={cn(
            'h-full rounded-full',
            styles.fill,
            glow && styles.glow
          )}
          initial={animated ? { width: 0 } : { width: `${pct}%` }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

// Segmented progress bar (for pipeline stages)
export function SegmentedProgressBar({
  segments,
  className,
}: {
  segments: Array<{ value: number; color: 'cyan' | 'amber' | 'success' | 'warning' | 'error'; label?: string }>;
  className?: string;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);

  const colorMap = {
    cyan: 'bg-accent-cyan',
    amber: 'bg-accent-amber',
    success: 'bg-status-success',
    warning: 'bg-status-warning',
    error: 'bg-status-error',
  };

  return (
    <div className={cn('w-full', className)}>
      <div className="flex h-2 rounded-full overflow-hidden bg-bg-tertiary gap-0.5">
        {segments.map((segment, index) => {
          const width = total > 0 ? (segment.value / total) * 100 : 0;
          return (
            <motion.div
              key={index}
              className={cn('h-full first:rounded-l-full last:rounded-r-full', colorMap[segment.color])}
              initial={{ width: 0 }}
              animate={{ width: `${width}%` }}
              transition={{ duration: 0.8, delay: index * 0.1, ease: 'easeOut' }}
            />
          );
        })}
      </div>
      {segments.some(s => s.label) && (
        <div className="flex justify-between mt-1.5 text-xs">
          {segments.map((segment, index) => (
            <div key={index} className="flex items-center gap-1">
              <span className={cn('w-2 h-2 rounded-full', colorMap[segment.color])} />
              <span className="text-text-muted">{segment.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
