/**
 * Animated Pipeline Flow Diagram
 *
 * Dual-path architecture with animated data packets.
 * Premium icons: Event (inbox), Ledger (verified), Hot Path (fast), RiskCast (target).
 */

import type { ReactNode } from 'react'
import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Inbox, CheckCircle2, Zap, Target } from 'lucide-react'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import { cn } from '../../lib/utils'

interface DataPacket {
  id: string
  stage: 'event' | 'ledger' | 'hotpath' | 'reconcile' | 'riskcast'
  status: 'moving' | 'success' | 'failed'
}

export function AnimatedPipelineFlow() {
  const [packets, setPackets] = useState<DataPacket[]>([])
  const [showReconcile, setShowReconcile] = useState(false)
  const reduced = useReducedMotion()
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (reduced) return
    intervalRef.current = setInterval(() => {
      const id = Math.random().toString(36).slice(2, 8)
      const willFail = Math.random() < 0.1
      setPackets((prev) => [...prev, { id, stage: 'event', status: 'moving' }])
      setTimeout(() => {
        setPackets((prev) =>
          prev.map((p) => (p.id === id ? { ...p, stage: 'ledger', status: 'success' } : p))
        )
      }, 500)
      setTimeout(() => {
        if (willFail) {
          setPackets((prev) =>
            prev.map((p) => (p.id === id ? { ...p, stage: 'hotpath', status: 'failed' } : p))
          )
          setShowReconcile(true)
          setTimeout(() => {
            setPackets((prev) =>
              prev.map((p) => (p.id === id ? { ...p, stage: 'reconcile', status: 'moving' } : p))
            )
          }, 300)
          setTimeout(() => {
            setPackets((prev) =>
              prev.map((p) => (p.id === id ? { ...p, stage: 'riskcast', status: 'success' } : p))
            )
            setTimeout(() => setShowReconcile(false), 1000)
          }, 800)
        } else {
          setPackets((prev) =>
            prev.map((p) => (p.id === id ? { ...p, stage: 'hotpath', status: 'moving' } : p))
          )
          setTimeout(() => {
            setPackets((prev) =>
              prev.map((p) => (p.id === id ? { ...p, stage: 'riskcast', status: 'success' } : p))
            )
          }, 500)
        }
      }, 1000)
      setTimeout(() => setPackets((prev) => prev.filter((p) => p.id !== id)), 3000)
    }, 2000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [reduced])

  return (
    <div className="relative w-full min-h-[12rem] rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6 overflow-hidden">
      <div className="flex items-center justify-between h-full gap-2 md:gap-4">
        <PipelineNode label="Event" icon={<Inbox className="h-5 w-5" strokeWidth={2} />} />
        <PipelineArrow />
        <PipelineNode label="Ledger" icon={<CheckCircle2 className="h-5 w-5" strokeWidth={2} />} highlight />
        <div className="flex flex-col items-center gap-2">
          <PipelineArrow label="hot path" />
          <AnimatePresence>
            {showReconcile && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-1"
              >
                <PipelineArrow label="reconcile" dashed />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <PipelineNode label="Hot Path" icon={<Zap className="h-5 w-5" strokeWidth={2} />} />
        <PipelineArrow />
        <PipelineNode label="RiskCast" icon={<Target className="h-5 w-5" strokeWidth={2} />} />
      </div>
      {!reduced && (
        <AnimatePresence>
          {packets.map((packet) => (
            <DataPacketDot key={packet.id} packet={packet} />
          ))}
        </AnimatePresence>
      )}
      <div className="absolute bottom-4 left-0 right-0 text-center">
        <span className="text-sm text-[var(--text-secondary)]">
          Ledger first. Hot path second.{' '}
          <span className="text-[var(--accent-green)]">Nothing lost.</span>
        </span>
      </div>
    </div>
  )
}

function PipelineNode({
  label,
  icon,
  highlight = false,
}: {
  label: string
  icon: ReactNode
  highlight?: boolean
}) {
  return (
    <div className={cn('flex flex-col items-center gap-2.5 z-10', highlight && 'scale-105')}>
      <div
        className={cn(
          'w-14 h-14 rounded-[var(--radius-card)] flex items-center justify-center border transition-colors',
          'shadow-[0_2px_8px_rgba(0,0,0,0.2)]',
          highlight
            ? 'bg-[var(--accent-green)]/15 border-2 border-[var(--accent-green)] text-[var(--accent-green)]'
            : 'bg-[var(--bg-tertiary)] border-[var(--border-subtle)] text-[var(--text-secondary)]'
        )}
      >
        {icon}
      </div>
      <span
        className={cn(
          'text-xs font-medium font-mono tracking-wide',
          highlight ? 'text-[var(--accent-green)]' : 'text-[var(--text-secondary)]'
        )}
      >
        {label}
      </span>
    </div>
  )
}

function PipelineArrow({ label, dashed }: { label?: string; dashed?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={cn(
          'w-8 h-0.5 md:w-16',
          dashed
            ? 'border-t border-dashed border-[var(--accent-amber)]'
            : 'bg-[var(--border-subtle)]'
        )}
      />
      {label && (
        <span
          className={cn(
            'text-[10px]',
            dashed ? 'text-[var(--accent-amber)]' : 'text-[var(--text-muted)]'
          )}
        >
          {label}
        </span>
      )}
    </div>
  )
}

function DataPacketDot({ packet }: { packet: DataPacket }) {
  const positions: Record<DataPacket['stage'], { left: string; top: string }> = {
    event: { left: '5%', top: '50%' },
    ledger: { left: '25%', top: '50%' },
    hotpath: { left: '55%', top: '40%' },
    reconcile: { left: '55%', top: '60%' },
    riskcast: { left: '90%', top: '50%' },
  }
  const colors = {
    moving: 'bg-[var(--accent-blue)]',
    success: 'bg-[var(--accent-green)]',
    failed: 'bg-[var(--accent-red)]',
  }
  const pos = positions[packet.stage]
  return (
    <motion.div
      className={cn('absolute w-3 h-3 rounded-full z-20 shadow-lg', colors[packet.status])}
      initial={{ opacity: 0, scale: 0 }}
      animate={{ opacity: 1, scale: 1, left: pos.left, top: pos.top }}
      exit={{ opacity: 0, scale: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      style={{ transform: 'translate(-50%, -50%)' }}
    />
  )
}
