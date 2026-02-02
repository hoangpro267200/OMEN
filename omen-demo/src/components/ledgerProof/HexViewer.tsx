import { Table, TableHeader, TableBody, TableHead } from '../ui/Table';
import { cn } from '../../lib/utils';
import type { FrameHeaderRow } from '../../data/ledgerProofMock';

export interface HexViewerProps {
  rows: FrameHeaderRow[];
  className?: string;
}

/**
 * Table of offset, hex bytes, and decoded meaning (for frame header).
 */
export function HexViewer({ rows, className = '' }: HexViewerProps) {
  return (
    <div className={cn('overflow-hidden rounded-[var(--radius-card)] border border-[var(--border-subtle)]', className)}>
      <Table>
        <TableHeader>
          <TableHead>Offset</TableHead>
          <TableHead>Hex</TableHead>
          <TableHead>Decoded</TableHead>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <tr key={r.offset} className="border-b border-[var(--border-subtle)] last:border-0">
              <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)]">
                0x{r.offset.toString(16).padStart(4, '0')}
              </td>
              <td className="px-4 py-2 font-mono text-xs tracking-wider text-[var(--text-primary)]">
                {r.hex}
              </td>
              <td className="px-4 py-2 text-xs text-[var(--text-primary)]">{r.decoded}</td>
            </tr>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
