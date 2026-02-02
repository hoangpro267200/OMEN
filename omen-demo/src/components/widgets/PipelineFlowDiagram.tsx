import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Inbox, CheckCircle2, Zap, RefreshCw, Target, X } from 'lucide-react';
import { cn } from '../../lib/utils';

/**
 * Animated dual-path pipeline: Event → Ledger → Hot Path / Reconcile.
 * "Ledger first. Hot path second. Nothing lost."
 */
export function PipelineFlowDiagram({ className = '' }: { className?: string }) {
  const [phase, setPhase] = useState<'idle' | 'flow' | 'split' | 'hot' | 'reconcile'>('idle');
  const [showFail, setShowFail] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('flow'), 400);
    const t2 = setTimeout(() => setPhase('split'), 1600);
    const t3 = setTimeout(() => setPhase('hot'), 2400);
    const t4 = setTimeout(() => setShowFail(true), 3200);
    const t5 = setTimeout(() => setPhase('reconcile'), 3800);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      clearTimeout(t5);
    };
  }, []);

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'relative rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6 md:p-8 overflow-hidden',
        className
      )}
    >
      <h2 className="mb-6 text-center font-mono text-sm font-medium uppercase tracking-wider text-[var(--text-muted)]">
        OMEN Dual-Path Pipeline
      </h2>

      <div className="flex flex-wrap items-center justify-center gap-3 md:gap-6">
        {/* Event */}
        <Node
          label="Event"
          active={phase !== 'idle'}
          icon={<Inbox className="h-5 w-5" strokeWidth={2} />}
        />

        <Arrow active={phase !== 'idle'} />

        {/* Ledger ✓ */}
        <Node
          label="Ledger ✓"
          active={phase !== 'idle'}
          icon={<CheckCircle2 className="h-5 w-5 text-[var(--accent-green)]" strokeWidth={2} />}
          highlight
        />

        <Arrow active={phase !== 'idle'} />

        {/* Split: Hot Path → RiskCast + Reconcile */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-2 md:gap-4">
            <Node
              label="Hot Path"
              active={phase === 'hot' || phase === 'split'}
              status={showFail ? 'fail' : 'ok'}
              icon={<Zap className="h-5 w-5" strokeWidth={2} />}
            />
            <Arrow active={phase === 'hot' || phase === 'split'} />
            <Node
              label="RiskCast"
              active={phase === 'hot' || phase === 'split'}
              icon={<Target className="h-5 w-5" strokeWidth={2} />}
            />
          </div>
          <div className="text-xs text-[var(--text-muted)]">(if missing)</div>
          <div className="flex items-center gap-2">
            <Node
              label="Reconcile"
              active={phase === 'reconcile'}
              icon={<RefreshCw className="h-5 w-5" strokeWidth={2} />}
            />
          </div>
        </div>
      </div>

      <p className="mt-6 text-center font-mono text-sm text-[var(--text-secondary)]">
        Ledger first. Hot path second. Nothing lost.
      </p>

      {/* Animated packet dot (optional: move along path) */}
      <PacketIndicator phase={phase} showFail={showFail} />
    </motion.section>
  );
}

function Node({
  label,
  active,
  icon,
  status,
  highlight,
}: {
  label: string;
  active: boolean;
  icon?: ReactNode;
  status?: 'ok' | 'fail';
  highlight?: boolean;
}) {
  return (
    <motion.div
      animate={{
        opacity: active ? 1 : 0.6,
        borderColor: highlight && active
          ? 'var(--accent-green)'
          : status === 'fail'
            ? 'var(--accent-red)'
            : active
              ? 'var(--border-active)'
              : 'var(--border-subtle)',
        boxShadow: active && !status
          ? (highlight ? '0 0 0 2px var(--accent-green)' : '0 0 0 1px var(--accent-blue)')
          : status === 'fail'
            ? '0 0 0 2px var(--accent-red)'
            : 'none',
      }}
      transition={{ duration: 0.2 }}
      className={cn(
        'flex flex-col items-center gap-2 rounded-[var(--radius-card)] border px-4 py-3 font-mono text-sm',
        'min-w-[4.5rem] shadow-[0_2px_8px_rgba(0,0,0,0.15)]',
        highlight && active && 'bg-[var(--accent-green)]/10',
        status === 'fail' && 'border-[var(--accent-red)] bg-[var(--accent-red)]/10'
      )}
    >
      {icon && (
        <span className={cn(
          'flex h-10 w-10 items-center justify-center rounded-[var(--radius-button)]',
          highlight && active && 'text-[var(--accent-green)]',
          status === 'fail' && 'text-[var(--accent-red)]'
        )}>
          {icon}
        </span>
      )}
      <span className={cn(
        'text-xs font-medium tracking-wide',
        status === 'fail' && 'text-[var(--accent-red)]'
      )}>
        {label}
      </span>
      {status === 'fail' && <X className="h-4 w-4 text-[var(--accent-red)]" />}
    </motion.div>
  );
}

function Arrow({ active }: { active: boolean }) {
  return (
    <motion.div
      initial={{ scaleX: 0 }}
      animate={{ scaleX: active ? 1 : 0 }}
      transition={{ duration: 0.25 }}
      className="h-0.5 w-4 origin-left bg-[var(--accent-blue)] md:w-6"
    />
  );
}

function PacketIndicator({ phase, showFail }: { phase: string; showFail: boolean }) {
  const visible = phase !== 'idle';
  const x = phase === 'flow' ? 20 : phase === 'split' ? 40 : phase === 'hot' ? 60 : phase === 'reconcile' ? 50 : 10;
  return (
    <motion.div
      className="pointer-events-none absolute inset-0 flex items-center"
      initial={false}
      animate={{ opacity: visible ? 1 : 0 }}
    >
      <motion.div
        className="absolute h-2 w-2 rounded-full bg-[var(--accent-blue)] shadow-[0_0_8px_var(--accent-blue)]"
        style={{ top: '50%', marginTop: -4 }}
        animate={{ left: `${x}%` }}
        transition={{ duration: 0.6, ease: 'easeInOut' }}
      />
      {showFail && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute text-[var(--accent-red)]"
          style={{ left: '58%', top: '50%', marginTop: -10 }}
        >
          <X className="h-5 w-5" />
        </motion.div>
      )}
    </motion.div>
  );
}
