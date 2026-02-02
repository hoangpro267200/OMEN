/**
 * MetricCard - Neural Command Center KPI display card
 * Features: CountUp animation, trend indicators, glow effects
 */
import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '../../lib/utils';
import { GlassCard } from './GlassCard';

export interface MetricCardProps {
  title: string;
  value: number;
  previousValue?: number;
  unit?: string;
  format?: 'number' | 'percent' | 'currency' | 'decimal';
  decimals?: number;
  icon?: React.ReactNode;
  color?: 'cyan' | 'amber' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
  delay?: number;
  className?: string;
  sparkline?: number[];
}

// Simple CountUp hook
function useCountUp(end: number, duration: number = 1500, delay: number = 0) {
  const [count, setCount] = useState(0);
  const countRef = useRef(0);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    const startValue = countRef.current;
    const startDelay = delay * 1000;

    const timer = setTimeout(() => {
      const animate = (timestamp: number) => {
        if (!startTimeRef.current) startTimeRef.current = timestamp;
        const progress = Math.min((timestamp - startTimeRef.current) / duration, 1);
        
        // Ease out cubic
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = startValue + (end - startValue) * easeOut;
        
        setCount(current);
        countRef.current = current;

        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          setCount(end);
          countRef.current = end;
        }
      };

      startTimeRef.current = null;
      requestAnimationFrame(animate);
    }, startDelay);

    return () => clearTimeout(timer);
  }, [end, duration, delay]);

  return count;
}

export function MetricCard({
  title,
  value,
  previousValue,
  unit,
  format = 'number',
  decimals,
  icon,
  color = 'cyan',
  size = 'md',
  delay = 0,
  className,
  sparkline,
}: MetricCardProps) {
  const animatedValue = useCountUp(value, 1500, delay);

  // Calculate trend
  const trend = previousValue !== undefined
    ? value > previousValue ? 'up'
    : value < previousValue ? 'down'
    : 'stable'
    : undefined;

  const trendPercent = previousValue && previousValue !== 0
    ? ((value - previousValue) / previousValue * 100).toFixed(1)
    : null;

  const colorClasses = {
    cyan: 'text-accent-cyan',
    amber: 'text-accent-amber',
    success: 'text-status-success',
    warning: 'text-status-warning',
    error: 'text-status-error',
  };

  const sizeConfig = {
    sm: { padding: 'p-3', valueSize: 'text-2xl', iconSize: 'w-4 h-4' },
    md: { padding: 'p-4', valueSize: 'text-3xl', iconSize: 'w-5 h-5' },
    lg: { padding: 'p-6', valueSize: 'text-4xl', iconSize: 'w-6 h-6' },
  };

  const { padding, valueSize, iconSize } = sizeConfig[size];

  // Format value display
  const formatValue = (val: number) => {
    const dec = decimals ?? (format === 'decimal' ? 2 : format === 'percent' ? 1 : 0);
    const formatted = val.toFixed(dec);
    
    switch (format) {
      case 'percent':
        return `${formatted}%`;
      case 'currency':
        return `$${Number(formatted).toLocaleString()}`;
      case 'decimal':
        return formatted;
      default:
        return Number(val.toFixed(0)).toLocaleString();
    }
  };

  return (
    <GlassCard className={cn(padding, className)} delay={delay}>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <span className="data-label">{title}</span>
        {icon && (
          <span className={cn(iconSize, 'opacity-60', colorClasses[color])}>
            {icon}
          </span>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end gap-2">
        <motion.span
          className={cn(
            'number-display font-bold leading-none',
            valueSize,
            colorClasses[color]
          )}
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: delay + 0.2, duration: 0.3, type: 'spring' }}
        >
          {formatValue(animatedValue)}
        </motion.span>
        {unit && (
          <span className="text-text-muted text-sm mb-1 font-mono">{unit}</span>
        )}
      </div>

      {/* Trend indicator */}
      {trend && (
        <motion.div
          className={cn(
            'flex items-center gap-1 mt-2 text-sm font-mono',
            trend === 'up' && 'text-status-success',
            trend === 'down' && 'text-status-error',
            trend === 'stable' && 'text-text-muted'
          )}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: delay + 0.4 }}
        >
          {trend === 'up' && <TrendingUp className="w-4 h-4" />}
          {trend === 'down' && <TrendingDown className="w-4 h-4" />}
          {trend === 'stable' && <Minus className="w-4 h-4" />}
          <span>{trend === 'stable' ? '0%' : `${trend === 'up' ? '+' : ''}${trendPercent}%`}</span>
        </motion.div>
      )}

      {/* Sparkline (mini chart) */}
      {sparkline && sparkline.length > 0 && (
        <div className="mt-3 h-8">
          <MiniSparkline data={sparkline} color={color} />
        </div>
      )}
    </GlassCard>
  );
}

// Mini sparkline chart
function MiniSparkline({ 
  data, 
  color 
}: { 
  data: number[]; 
  color: string 
}) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = 100 - ((val - min) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  const colorMap: Record<string, string> = {
    cyan: '#00f0ff',
    amber: '#ffaa00',
    success: '#00ff88',
    warning: '#ffaa00',
    error: '#ff3366',
  };

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
      <polyline
        points={points}
        fill="none"
        stroke={colorMap[color] || colorMap.cyan}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

// Compact metric display for tight spaces
export function MetricValue({
  label,
  value,
  format = 'number',
  color = 'cyan',
  className,
}: {
  label: string;
  value: number;
  format?: 'number' | 'percent' | 'decimal';
  color?: 'cyan' | 'amber' | 'success' | 'warning';
  className?: string;
}) {
  const colorClasses = {
    cyan: 'text-accent-cyan',
    amber: 'text-accent-amber',
    success: 'text-status-success',
    warning: 'text-status-warning',
  };

  const formatValue = (val: number) => {
    switch (format) {
      case 'percent':
        return `${val.toFixed(1)}%`;
      case 'decimal':
        return val.toFixed(2);
      default:
        return val.toLocaleString();
    }
  };

  return (
    <div className={cn('text-center', className)}>
      <p className={cn('text-2xl font-display font-bold', colorClasses[color])}>
        {formatValue(value)}
      </p>
      <p className="text-xs text-text-muted mt-0.5">{label}</p>
    </div>
  );
}
