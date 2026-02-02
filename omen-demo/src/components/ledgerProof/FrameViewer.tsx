import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '../ui/Button';
import { CodeBlock } from '../ui/CodeBlock';
import { HexViewer } from './HexViewer';
import { getFrameHeaderRows } from '../../data/ledgerProofMock';
import type { WalFrameRecord } from '../../data/ledgerProofMock';
import { cn } from '../../lib/utils';

export interface FrameViewerProps {
  records: WalFrameRecord[];
  className?: string;
}

/**
 * Interactive frame viewer: Prev/Next, Record #N of M, Header (HexViewer), Payload preview, View Full JSON.
 */
export function FrameViewer({ records, className = '' }: FrameViewerProps) {
  const [index, setIndex] = useState(0);
  const [showFullJson, setShowFullJson] = useState(false);

  useEffect(() => setShowFullJson(false), [index]);

  if (records.length === 0) {
    return (
      <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6', className)}>
        <p className="font-mono text-sm text-[var(--text-muted)]">No records in this segment.</p>
      </div>
    );
  }

  const record = records[index];
  const headerRows = getFrameHeaderRows(record.offset, record.length, record.crc32Hex);

  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden', className)}>
      <div className="flex items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-4 py-3">
        <h3 className="font-mono text-sm font-medium text-[var(--text-primary)]">Frame Viewer</h3>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={() => setIndex((i) => Math.max(0, i - 1))}
            disabled={index === 0}
            className="h-8 px-2"
          >
            <ChevronLeft className="h-4 w-4" />
            Prev
          </Button>
          <Button
            variant="ghost"
            onClick={() => setIndex((i) => Math.min(records.length - 1, i + 1))}
            disabled={index === records.length - 1}
            className="h-8 px-2"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="p-4">
        <p className="mb-4 font-mono text-sm text-[var(--text-secondary)]">
          Record #{record.recordIndex} of {records.length}
        </p>

        <div className="mb-4">
          <h4 className="mb-2 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
            Header
          </h4>
          <HexViewer rows={headerRows} />
        </div>

        <div>
          <h4 className="mb-2 font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
            Payload (first 200 chars)
          </h4>
          {showFullJson ? (
            <div>
              <CodeBlock raw={record.payloadFull} language="json" className="max-h-[400px] overflow-y-auto">
                {' '}
              </CodeBlock>
              <Button variant="ghost" onClick={() => setShowFullJson(false)} className="mt-2 text-xs">
                Show preview
              </Button>
            </div>
          ) : (
            <div>
              <CodeBlock raw={record.payloadPreview} language="json" className="max-h-[120px] overflow-y-auto">
                {' '}
              </CodeBlock>
              <Button variant="ghost" onClick={() => setShowFullJson(true)} className="mt-2 text-xs">
                View Full JSON
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
