/**
 * Circular Completeness Gauge
 *
 * Shows ledger vs processed as a circular progress indicator.
 * Animates smoothly when values change.
 */

import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useReducedMotion } from '../../hooks/useReducedMotion'

interface CompletenessGaugeProps {
  ledgerCount: number
  processedCount: number
  missingCount: number
  size?: number
  strokeWidth?: number
}

export function CompletenessGauge({
  ledgerCount,
  processedCount,
  missingCount,
  size = 200,
  strokeWidth = 20,
}: CompletenessGaugeProps) {
  const reduced = useReducedMotion()
  const percentage =
    ledgerCount > 0 ? Math.round((processedCount / ledgerCount) * 100) : 100

  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (percentage / 100) * circumference
  const center = size / 2

  const statusColor = useMemo(() => {
    if (percentage === 100) return 'var(--accent-green)'
    if (percentage >= 80) return 'var(--accent-amber)'
    return 'var(--accent-red)'
  }, [percentage])

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="var(--bg-tertiary)"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={statusColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: reduced ? 0 : 1, ease: 'easeOut' }}
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-4xl font-bold font-mono"
          style={{ color: statusColor }}
          key={percentage}
          initial={reduced ? false : { scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
        >
          {percentage}%
        </motion.span>
        <span className="text-sm text-[var(--text-secondary)]">Complete</span>
      </div>

      <div className="absolute -bottom-8 left-0 right-0 flex justify-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-[var(--accent-green)]" />
          <span className="text-[var(--text-muted)]">Processed: {processedCount}</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-[var(--accent-red)]" />
          <span className="text-[var(--text-muted)]">Missing: {missingCount}</span>
        </div>
      </div>
    </div>
  )
}
