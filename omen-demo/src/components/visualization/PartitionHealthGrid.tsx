/**
 * Partition Health Grid
 *
 * Color-coded partition status at a glance.
 */

import { motion } from 'framer-motion'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import type { Partition } from '../../lib/api/contracts'
import { cn } from '../../lib/utils'

interface PartitionHealthGridProps {
  partitions: Partition[]
  onSelect?: (partition: Partition) => void
}

function getPartitionColor(partition: Partition): string {
  if (partition.type === 'LATE') {
    return 'bg-[var(--status-late)]/80'
  }
  if (partition.status === 'OPEN') {
    return 'bg-[var(--status-open)]/80'
  }
  const reconcileStatus = partition.reconcile_state?.status
  const missing = partition.reconcile_state?.missing_count ?? 0
  if (reconcileStatus === 'COMPLETED' && missing === 0) {
    return 'bg-[var(--status-completed)]/80'
  }
  if (reconcileStatus === 'PARTIAL' || missing > 0) {
    return 'bg-[var(--accent-amber)]/80'
  }
  if (reconcileStatus === 'FAILED') {
    return 'bg-[var(--status-failed)]/80'
  }
  return 'bg-[var(--status-sealed)]/80'
}

function getPartitionTooltip(partition: Partition): string {
  const lines = [
    partition.partition_date,
    `Type: ${partition.type}`,
    `Status: ${partition.status}`,
    `Records: ${partition.total_records}`,
  ]
  if (partition.reconcile_state) {
    lines.push(`Reconcile: ${partition.reconcile_state.status}`)
    lines.push(`Missing: ${partition.reconcile_state.missing_count}`)
  }
  return lines.join('\n')
}

export function PartitionHealthGrid({ partitions, onSelect }: PartitionHealthGridProps) {
  const reduced = useReducedMotion()

  return (
    <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-7 gap-2">
      {partitions.map((partition, index) => (
        <motion.div
          key={partition.partition_date}
          initial={reduced ? false : { opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: reduced ? 0 : index * 0.02 }}
          onClick={() => onSelect?.(partition)}
          className={cn(
            'aspect-square rounded-[var(--radius-button)] cursor-pointer',
            'flex flex-col items-center justify-center',
            'transition-all hover:scale-105 border border-white/10',
            getPartitionColor(partition)
          )}
          title={getPartitionTooltip(partition)}
        >
          <span className="text-[10px] font-mono text-white/80">
            {partition.partition_date.slice(5)}
          </span>
          <span className="text-xs font-bold text-white">
            {partition.total_records}
          </span>
        </motion.div>
      ))}
    </div>
  )
}
