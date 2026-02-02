/**
 * AnimatedPipeline - Neural Command Center signal processing pipeline visualization
 * Features: Animated particles flowing through stages, real-time counters, rejection bin
 */
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../lib/utils';

interface PipelineStage {
  id: string;
  name: string;
  icon: string;
  eventsPerHour: number;
  passRate: number;
}

const STAGES: PipelineStage[] = [
  { id: 'ingest', name: 'INGEST', icon: '📥', eventsPerHour: 1250, passRate: 100 },
  { id: 'validate', name: 'VALIDATE', icon: '✓', eventsPerHour: 520, passRate: 41.6 },
  { id: 'enrich', name: 'ENRICH', icon: '🔬', eventsPerHour: 480, passRate: 92.3 },
  { id: 'classify', name: 'CLASSIFY', icon: '🏷️', eventsPerHour: 480, passRate: 100 },
  { id: 'emit', name: 'EMIT', icon: '📡', eventsPerHour: 47, passRate: 9.8 },
];

interface Particle {
  id: number;
  status: 'flowing' | 'rejected' | 'success';
  progress: number; // 0-100 representing position through pipeline
}

export interface AnimatedPipelineProps {
  onSelectSignal?: (id: string) => void;
  className?: string;
}

export function AnimatedPipeline({ onSelectSignal: _onSelectSignal, className }: AnimatedPipelineProps) {
  const [particles, setParticles] = useState<Particle[]>([]);
  const [nextId, setNextId] = useState(0);

  // Generate new particles
  const spawnParticle = useCallback(() => {
    setNextId((prev) => prev + 1);
    setParticles((prev) => [
      ...prev.slice(-15), // Keep last 15 particles max
      { id: nextId, status: 'flowing', progress: 0 },
    ]);
  }, [nextId]);

  // Spawn particles periodically
  useEffect(() => {
    const interval = setInterval(spawnParticle, 800);
    return () => clearInterval(interval);
  }, [spawnParticle]);

  // Animate particles
  useEffect(() => {
    const interval = setInterval(() => {
      setParticles((prev) =>
        prev
          .map((p) => {
            if (p.status !== 'flowing') return p;

            // Rejection chance at validation stage (around 20-25 progress)
            if (p.progress >= 18 && p.progress < 25 && Math.random() < 0.08) {
              return { ...p, status: 'rejected' as const };
            }

            // Move forward
            const newProgress = p.progress + 4;
            if (newProgress >= 100) {
              return { ...p, progress: 100, status: 'success' as const };
            }
            return { ...p, progress: newProgress };
          })
          .filter((p) => {
            // Remove completed particles after a delay
            if (p.status === 'success' && p.progress >= 100) return Math.random() > 0.3;
            if (p.status === 'rejected') return Math.random() > 0.1;
            return true;
          })
      );
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={cn('relative', className)}>
      {/* Pipeline Stages */}
      <div className="flex items-center justify-between px-4 py-8">
        {STAGES.map((stage, index) => (
          <div key={stage.id} className="flex flex-col items-center relative">
            {/* Connector line */}
            {index < STAGES.length - 1 && (
              <div
                className="absolute top-1/2 left-full w-full h-0.5 -translate-y-1/2"
                style={{
                  background:
                    'linear-gradient(90deg, rgba(0,240,255,0.3) 0%, rgba(0,240,255,0.1) 100%)',
                  width: 'calc(100% - 60px)',
                  marginLeft: '30px',
                }}
              >
                {/* Animated dash */}
                <motion.div
                  className="h-full w-8 bg-accent-cyan/50"
                  animate={{ x: ['0%', '1000%'] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                />
              </div>
            )}

            {/* Stage Box */}
            <motion.div
              className={cn(
                'relative w-20 h-20 rounded-xl border-2 flex flex-col items-center justify-center',
                'bg-bg-tertiary/50 backdrop-blur transition-all duration-300 z-10',
                index === STAGES.length - 1
                  ? 'border-status-success shadow-glow-success'
                  : 'border-accent-cyan/30 hover:border-accent-cyan hover:shadow-glow-cyan'
              )}
              whileHover={{ scale: 1.05 }}
            >
              <span className="text-xl mb-0.5">{stage.icon}</span>
              <span className="text-xs font-heading text-text-primary">{stage.name}</span>
              <span className="text-xs text-accent-cyan font-mono">{stage.eventsPerHour}/hr</span>
            </motion.div>

            {/* Pass Rate */}
            <div className="mt-2 text-center">
              <span
                className={cn(
                  'text-xs font-mono',
                  stage.passRate >= 90
                    ? 'text-status-success'
                    : stage.passRate >= 50
                    ? 'text-status-warning'
                    : 'text-status-error'
                )}
              >
                {stage.passRate}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Particles Layer */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <AnimatePresence>
          {particles.map((particle) => {
            const xPercent = 5 + particle.progress * 0.9; // 5% to 95% of width

            return (
              <motion.div
                key={particle.id}
                className={cn(
                  'absolute w-3 h-3 rounded-full',
                  particle.status === 'flowing' && 'bg-accent-cyan shadow-glow-cyan',
                  particle.status === 'rejected' && 'bg-status-error shadow-glow-error',
                  particle.status === 'success' && 'bg-status-success shadow-glow-success'
                )}
                style={{
                  top: '50%',
                  left: `${xPercent}%`,
                }}
                initial={{ scale: 0, opacity: 0 }}
                animate={{
                  scale: 1,
                  opacity: particle.status === 'rejected' ? 0 : 1,
                  y: particle.status === 'rejected' ? 80 : 0,
                }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              />
            );
          })}
        </AnimatePresence>
      </div>

      {/* Rejection Bin */}
      <motion.div
        className="absolute bottom-2 left-1/3 w-28 h-10 rounded-lg border border-status-error/30 bg-status-error/10 flex items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <span className="text-xs text-status-error font-mono">REJECTED: 730/hr</span>
      </motion.div>
    </div>
  );
}
