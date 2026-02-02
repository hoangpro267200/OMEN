/**
 * Gauge - Neural Command Center circular progress/gauge
 * Features: Animated SVG arc, glow effect, center content
 */
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface GaugeProps {
  /** Value (0-1 for probability, 0-100 for percentage) */
  value: number;
  /** Maximum value */
  max?: number;
  /** Size in pixels */
  size?: number;
  /** Stroke width */
  strokeWidth?: number;
  /** Color variant */
  variant?: 'cyan' | 'amber' | 'dynamic' | 'gradient';
  /** Show value in center */
  showValue?: boolean;
  /** Value format */
  format?: 'percent' | 'decimal' | 'number';
  /** Label below value */
  label?: string;
  /** Animation delay */
  delay?: number;
  className?: string;
}

function getColor(value: number, max: number): string {
  const pct = (value / max) * 100;
  if (pct >= 70) return '#ff3366'; // High risk - red
  if (pct >= 40) return '#ffaa00'; // Medium - amber
  return '#00ff88'; // Low - green
}

export function Gauge({
  value,
  max = 100,
  size = 120,
  strokeWidth = 8,
  variant = 'cyan',
  showValue = true,
  format = 'percent',
  label,
  delay = 0,
  className,
}: GaugeProps) {
  const [animatedValue, setAnimatedValue] = useState(0);

  const percentage = (value / max) * 100;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedValue / 100) * circumference;

  // Animate value on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedValue(percentage);
    }, delay * 1000 + 100);
    return () => clearTimeout(timer);
  }, [percentage, delay]);

  // Get stroke color
  const strokeColor = variant === 'dynamic' 
    ? getColor(value, max)
    : variant === 'amber' 
      ? '#ffaa00'
      : '#00f0ff';

  // Format value display
  const displayValue = () => {
    switch (format) {
      case 'percent':
        return `${percentage.toFixed(1)}%`;
      case 'decimal':
        return value.toFixed(2);
      default:
        return Math.round(value).toString();
    }
  };

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      {/* Background glow */}
      <div
        className="absolute inset-0 rounded-full opacity-20 blur-xl"
        style={{ background: strokeColor }}
      />

      {/* SVG Gauge */}
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={strokeWidth}
        />

        {/* Gradient definition for gradient variant */}
        {variant === 'gradient' && (
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00f0ff" />
              <stop offset="100%" stopColor="#ffaa00" />
            </linearGradient>
          </defs>
        )}

        {/* Animated progress arc */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={variant === 'gradient' ? 'url(#gaugeGradient)' : strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.5, ease: 'easeOut', delay }}
          style={{
            filter: `drop-shadow(0 0 10px ${strokeColor})`,
          }}
        />
      </svg>

      {/* Center content */}
      {showValue && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="font-display font-bold leading-none"
            style={{ 
              color: strokeColor,
              fontSize: size * 0.22,
            }}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: delay + 0.5, duration: 0.3 }}
          >
            {displayValue()}
          </motion.span>
          {label && (
            <span 
              className="text-text-muted mt-1 uppercase tracking-wider"
              style={{ fontSize: size * 0.08 }}
            >
              {label}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// Mini gauge for inline use
export function MiniGauge({
  value,
  max = 100,
  size = 32,
  color = 'cyan',
  className,
}: {
  value: number;
  max?: number;
  size?: number;
  color?: 'cyan' | 'amber' | 'success' | 'warning' | 'error';
  className?: string;
}) {
  const percentage = (value / max) * 100;
  const radius = (size - 4) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const colorMap: Record<string, string> = {
    cyan: '#00f0ff',
    amber: '#ffaa00',
    success: '#00ff88',
    warning: '#ffaa00',
    error: '#ff3366',
  };

  return (
    <svg width={size} height={size} className={cn('transform -rotate-90', className)}>
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="rgba(255,255,255,0.1)"
        strokeWidth={3}
      />
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={colorMap[color]}
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset }}
        transition={{ duration: 1, ease: 'easeOut' }}
      />
    </svg>
  );
}

// Confidence gauge with multiple segments
export function ConfidenceGauge({
  confidence,
  size = 140,
  className,
}: {
  confidence: number; // 0-1
  size?: number;
  className?: string;
}) {
  const level = confidence >= 0.7 ? 'HIGH' : confidence >= 0.4 ? 'MEDIUM' : 'LOW';
  const color = confidence >= 0.7 ? '#00ff88' : confidence >= 0.4 ? '#ffaa00' : '#ff3366';

  return (
    <div className={cn('flex flex-col items-center', className)}>
      <Gauge
        value={confidence}
        max={1}
        size={size}
        strokeWidth={10}
        variant="dynamic"
        format="decimal"
        showValue={true}
      />
      <div className="mt-2 flex items-center gap-2">
        <span
          className="px-2 py-0.5 rounded text-xs font-mono font-bold"
          style={{ 
            backgroundColor: `${color}20`,
            color: color,
            border: `1px solid ${color}40`
          }}
        >
          {level}
        </span>
      </div>
    </div>
  );
}
