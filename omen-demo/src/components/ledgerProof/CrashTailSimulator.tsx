import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../ui/Button';
import { ProofResult } from './ProofResult';
import { cn } from '../../lib/utils';
import {
  crashSimulatorFrameSizes,
  crashSimulatorPartialBytes,
  crashSimulatorTruncateOffset,
  crashSimulatorValidRecordsAfterRead,
} from '../../data/ledgerProofMock';

type SimStep = 'idle' | 'crashed' | 'read';

export interface CrashTailSimulatorProps {
  className?: string;
}

/**
 * Crash-tail simulator: 3 complete frames → simulate crash (Frame 3 partial) → Run Read Demo → proof result.
 */
export function CrashTailSimulator({ className = '' }: CrashTailSimulatorProps) {
  const [step, setStep] = useState<SimStep>('idle');
  const [readLog, setReadLog] = useState<string[]>([]);
  const [readComplete, setReadComplete] = useState(false);

  const onSimulateCrash = () => {
    setStep('crashed');
    setReadLog([]);
    setReadComplete(false);
  };

  const onRunReadDemo = () => {
    setStep('read');
    setReadLog([
      'Reading segment...',
      '✓ Frame 1: valid (500 bytes, CRC OK)',
      '✓ Frame 2: valid (480 bytes, CRC OK)',
      '⚠ Frame 3: partial payload (200 of 520 bytes) — TRUNCATING',
      '',
      `Result: ${crashSimulatorValidRecordsAfterRead} valid records returned`,
      `Warning logged: "Partial payload at offset ${crashSimulatorTruncateOffset}, truncating"`,
    ]);
    setReadComplete(true);
  };

  const onReset = () => {
    setStep('idle');
    setReadLog([]);
    setReadComplete(false);
  };

  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden', className)}>
      <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-3">
        <h3 className="font-mono text-sm font-medium text-[var(--text-primary)]">
          Crash-Tail Simulator
        </h3>
        <p className="mt-1 text-xs text-[var(--text-muted)]">
          Simulates a crash mid-write. See how the reader handles partial frames.
        </p>
      </div>
      <div className="p-4 space-y-6">
        {/* Step 1: 3 complete frames */}
        <div>
          <h4 className="mb-2 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
            Step 1: Start with 3 complete records
          </h4>
          <div className="flex flex-wrap gap-2">
            {crashSimulatorFrameSizes.map((size, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={cn(
                  'rounded-[var(--radius-button)] border px-4 py-2 font-mono text-sm',
                  i < 2 || step === 'idle'
                    ? 'border-[var(--accent-green)]/50 bg-[var(--accent-green)]/10 text-[var(--accent-green)]'
                    : step === 'crashed' || step === 'read'
                      ? 'border-[var(--accent-amber)]/50 bg-[var(--accent-amber)]/10 text-[var(--accent-amber)]'
                      : 'border-[var(--border-subtle)] bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
                )}
              >
                {i < 2 ? (
                  <>Frame {i + 1} ✓ — {size} bytes</>
                ) : step === 'idle' ? (
                  <>Frame 3 ✓ — {size} bytes</>
                ) : (
                  <>
                    Frame 3 ██░░░░ — {crashSimulatorPartialBytes}/{size} bytes
                    <span className="ml-1 text-[var(--text-muted)]">← Partial (crash here)</span>
                  </>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Step 2: Simulate crash */}
        <div>
          <h4 className="mb-2 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
            Step 2: Simulate crash (truncate after Frame 2)
          </h4>
          <p className="mb-3 text-xs text-[var(--text-secondary)]">
            {step === 'idle'
              ? 'Click below to simulate a crash mid-write of Frame 3.'
              : 'Crash simulated. Frame 3 is partial. Run the reader to see truncation.'}
          </p>
          {step === 'idle' && (
            <Button variant="primary" onClick={onSimulateCrash} data-demo-target="simulate-crash-button">
              Simulate Crash
            </Button>
          )}
          {(step === 'crashed' || step === 'read') && (
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={onRunReadDemo} disabled={step === 'read' && readComplete} data-demo-target="run-read-button">
                Run Read Demo
              </Button>
              <Button variant="ghost" onClick={onReset}>
                Reset
              </Button>
            </div>
          )}
        </div>

        {/* Step 3: Read with LedgerReader */}
        <AnimatePresence>
          {(step === 'read' && readLog.length > 0) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <h4 className="mb-2 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                Step 3: Read with LedgerReader
              </h4>
              <div className="rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-4 font-mono text-xs text-[var(--text-secondary)] whitespace-pre-wrap">
                {readLog.map((line, i) => (
                  <div
                    key={i}
                    className={cn(
                      line.startsWith('✓') && 'text-[var(--accent-green)]',
                      line.startsWith('⚠') && 'text-[var(--accent-amber)]',
                      line.startsWith('Result') && 'font-medium text-[var(--text-primary)]',
                      line.startsWith('Warning') && 'text-[var(--accent-amber)]'
                    )}
                  >
                    {line}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Proof result */}
        <AnimatePresence>
          {readComplete && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <ProofResult
                success
                title="PROOF: Partial frame detected and truncated."
                lines={[
                  'No corrupted records returned to application.',
                  'Data integrity maintained despite crash.',
                ]}
              />
              {/* Optional: Corrupted vs Valid side-by-side */}
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="rounded-[var(--radius-card)] border border-[var(--accent-red)]/40 bg-[var(--accent-red)]/5 p-3">
                  <div className="font-mono text-xs font-medium uppercase text-[var(--accent-red)]">
                    Corrupted (would be)
                  </div>
                  <div className="mt-2 font-mono text-xs text-[var(--text-secondary)]">
                    Frame 3: [len: 520][crc: 0x1a2b3c4d]
                    <br />
                    [payload: 200 bytes...] ← Missing 320 bytes
                    <br />
                    Status: ✗ INCOMPLETE
                  </div>
                </div>
                <div className="rounded-[var(--radius-card)] border border-[var(--accent-amber)]/40 bg-[var(--accent-amber)]/5 p-3">
                  <div className="font-mono text-xs font-medium uppercase text-[var(--accent-amber)]">
                    Valid (what reader returns)
                  </div>
                  <div className="mt-2 font-mono text-xs text-[var(--text-secondary)]">
                    Frame 3: NOT RETURNED
                    <br />
                    &quot;Truncated at offset {crashSimulatorTruncateOffset}&quot;
                    <br />
                    Status: ⚠ SKIPPED (safe)
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
