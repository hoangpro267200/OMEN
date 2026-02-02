import { useState } from 'react';
import { Table, TableHeader, TableBody, TableHead } from '../ui/Table';
import { PartitionRow } from './PartitionRow';
import { PartitionContextPanel } from './PartitionContextPanel';
import type { LedgerPartition } from '../../data/partitionsMock';

export interface PartitionsTableProps {
  partitions: LedgerPartition[];
  showContextPanel?: boolean;
  className?: string;
}

/**
 * Partitions table with header row; hover on row shows context panel to the right.
 */
export function PartitionsTable({
  partitions,
  showContextPanel = true,
  className = '',
}: PartitionsTableProps) {
  const [hoveredPartition, setHoveredPartition] = useState<LedgerPartition | null>(null);

  return (
    <div className={`relative ${className}`}>
      <Table>
        <TableHeader>
          <TableHead>Partition</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Records</TableHead>
          <TableHead>Highwater</TableHead>
          <TableHead>Segments</TableHead>
          <TableHead>Reconcile</TableHead>
          <TableHead className="w-24">{''}</TableHead>
        </TableHeader>
        <TableBody>
          {partitions.map((p) => (
            <PartitionRow
              key={p.partitionDate}
              partition={p}
              onHover={setHoveredPartition}
              isHovered={hoveredPartition?.partitionDate === p.partitionDate}
            />
          ))}
        </TableBody>
      </Table>

      {showContextPanel && hoveredPartition && (
        <div className="absolute right-0 top-0 z-10 translate-x-full pl-4">
          <PartitionContextPanel partition={hoveredPartition} />
        </div>
      )}
    </div>
  );
}
