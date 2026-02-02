import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ledgerProofPartitions,
  ledgerProofSegments,
  getFrameRecordsForSegment,
} from '../data/ledgerProofMock';
import { FrameDiagram } from '../components/ledgerProof/FrameDiagram';
import { SegmentSelector } from '../components/ledgerProof/SegmentSelector';
import { FrameViewer } from '../components/ledgerProof/FrameViewer';
import { CrashTailSimulator } from '../components/ledgerProof/CrashTailSimulator';

const pageVariants = {
  initial: { opacity: 0, x: 8 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -8 },
};
const pageTransition = { duration: 0.15, ease: 'easeOut' as const };

/**
 * Ledger Proof screen: WAL framing and crash-tail safety. Visual frame diagram, segment selector,
 * frame viewer, crash-tail simulator.
 */
export function LedgerProofScreen() {
  const [selectedPartition, setSelectedPartition] = useState(ledgerProofPartitions[0]);
  const [selectedSegment, setSelectedSegment] = useState(ledgerProofSegments[0].filename);

  const filteredSegments = useMemo(
    () => ledgerProofSegments.filter((s) => s.partition === selectedPartition),
    [selectedPartition]
  );

  useEffect(() => {
    const inList = filteredSegments.some((s) => s.filename === selectedSegment);
    if (!inList && filteredSegments[0]) setSelectedSegment(filteredSegments[0].filename);
  }, [selectedPartition, filteredSegments, selectedSegment]);

  const currentSegmentFilename =
    filteredSegments.some((s) => s.filename === selectedSegment)
      ? selectedSegment
      : (filteredSegments[0]?.filename ?? ledgerProofSegments[0].filename);

  const frameRecords = useMemo(
    () => getFrameRecordsForSegment(selectedPartition, currentSegmentFilename),
    [selectedPartition, currentSegmentFilename]
  );

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      className="min-h-full p-4 md:p-6"
    >
      {/* Hero */}
      <header className="mb-6 rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6">
        <h1 className="font-display text-xl font-medium text-[var(--text-primary)]">
          Ledger Proof: WAL Framing & Crash Safety
        </h1>
        <p className="mt-3 text-sm text-[var(--text-secondary)]">
          Every signal is written as a framed record: [length][crc][payload]. If a crash occurs
          mid-write, the reader truncates partial frames. No corrupted records ever surface.
        </p>
      </header>

      {/* Visual Frame Diagram */}
      <section className="mb-6">
        <FrameDiagram />
      </section>

      {/* Segment Selector */}
      <section className="mb-6">
        <SegmentSelector
          partitions={ledgerProofPartitions}
          segments={ledgerProofSegments}
          selectedPartition={selectedPartition}
          selectedSegment={currentSegmentFilename}
          onPartitionChange={setSelectedPartition}
          onSegmentChange={setSelectedSegment}
        />
      </section>

      {/* Frame Viewer */}
      <section className="mb-6">
        <FrameViewer records={frameRecords} />
      </section>

      {/* Crash-Tail Simulator */}
      <section>
        <CrashTailSimulator />
      </section>
    </motion.div>
  );
}
