/**
 * Category Distribution Donut Chart
 *
 * Shows breakdown of signals by category.
 */

import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useReducedMotion } from '../../hooks/useReducedMotion'

export interface CategoryData {
  category: string
  count: number
  color: string
}

const CATEGORY_COLORS: Record<string, string> = {
  GEOPOLITICAL: '#ef4444',
  INFRASTRUCTURE: '#3b82f6',
  OPERATIONAL: '#6b7280',
  FINANCIAL: '#22c55e',
  CLIMATE: '#14b8a6',
  COMPLIANCE: '#a855f7',
  NETWORK: '#f97316',
}

interface CategoryDistributionProps {
  data: CategoryData[]
  size?: number
}

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  const radians = ((angle - 90) * Math.PI) / 180
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  }
}

function describeArc(
  cx: number,
  cy: number,
  outerRadius: number,
  innerRadius: number,
  startAngle: number,
  endAngle: number
): string {
  const start = polarToCartesian(cx, cy, outerRadius, endAngle)
  const end = polarToCartesian(cx, cy, outerRadius, startAngle)
  const innerStart = polarToCartesian(cx, cy, innerRadius, endAngle)
  const innerEnd = polarToCartesian(cx, cy, innerRadius, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1
  return [
    'M', start.x, start.y,
    'A', outerRadius, outerRadius, 0, largeArcFlag, 0, end.x, end.y,
    'L', innerEnd.x, innerEnd.y,
    'A', innerRadius, innerRadius, 0, largeArcFlag, 1, innerStart.x, innerStart.y,
    'Z',
  ].join(' ')
}

export function CategoryDistribution({ data, size = 180 }: CategoryDistributionProps) {
  const reduced = useReducedMotion()
  const total = data.reduce((sum, d) => sum + d.count, 0)

  const segments = useMemo(() => {
    let currentAngle = 0
    return data.map((d) => {
      const percentage = total > 0 ? d.count / total : 0
      const angle = percentage * 360
      const startAngle = currentAngle
      currentAngle += angle
      return {
        ...d,
        percentage,
        startAngle,
        endAngle: currentAngle,
        color: CATEGORY_COLORS[d.category] ?? '#6b7280',
      }
    })
  }, [data, total])

  const center = size / 2
  const radius = size / 2 - 10
  const innerRadius = radius * 0.6

  return (
    <div className="flex flex-col sm:flex-row items-center gap-6">
      <svg width={size} height={size} className="shrink-0" aria-hidden>
        <g>
          {segments.map((segment, index) => (
            <motion.g
              key={segment.category}
              initial={reduced ? false : { opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: reduced ? 0 : index * 0.1 }}
            >
              <path
                d={describeArc(
                  center,
                  center,
                  radius,
                  innerRadius,
                  segment.startAngle,
                  segment.endAngle
                )}
                fill={segment.color}
                className="cursor-pointer hover:opacity-80 transition-opacity"
              />
            </motion.g>
          ))}
        </g>
        <text
          x={center}
          y={center - 8}
          textAnchor="middle"
          className="text-2xl font-bold"
          fill="var(--text-primary)"
        >
          {total}
        </text>
        <text
          x={center}
          y={center + 12}
          textAnchor="middle"
          className="text-xs"
          fill="var(--text-secondary)"
        >
          signals
        </text>
      </svg>

      <div className="flex flex-col gap-1 min-w-0">
        {segments.map((segment) => (
          <div key={segment.category} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm shrink-0"
              style={{ backgroundColor: segment.color }}
            />
            <span className="text-xs text-[var(--text-secondary)] truncate">
              {segment.category}
            </span>
            <span className="text-xs font-mono text-[var(--text-muted)] shrink-0">
              {segment.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
