import { cn } from '../../lib/utils';
import type { PartitionManifest, PartitionSegment } from '../../data/partitionDetailMock';

export interface ManifestPanelProps {
  manifest: PartitionManifest;
  segments: PartitionSegment[];
  className?: string;
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toISOString();
  } catch {
    return iso;
  }
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} bytes`;
  return `${(n / 1024).toFixed(1)} KB`;
}

/**
 * Zone 1: Manifest & Segments (collapsed by default).
 */
export function ManifestPanel({ manifest, segments, className = '' }: ManifestPanelProps) {
  return (
    <div className={cn('grid grid-cols-1 gap-6 md:grid-cols-2', className)}>
      <div>
        <h3 className="mb-3 font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Manifest
        </h3>
        <dl className="space-y-2 font-mono text-sm">
          <div>
            <dt className="text-[var(--text-muted)]">Sealed at</dt>
            <dd className="text-[var(--text-secondary)]">{formatDateTime(manifest.sealedAt)}</dd>
          </div>
          <div>
            <dt className="text-[var(--text-muted)]">Total records</dt>
            <dd className="text-[var(--text-secondary)]">{manifest.totalRecords}</dd>
          </div>
          <div>
            <dt className="text-[var(--text-muted)]">Highwater</dt>
            <dd className="text-[var(--text-secondary)]">{manifest.highwater}</dd>
          </div>
          <div>
            <dt className="text-[var(--text-muted)]">Revision</dt>
            <dd className="text-[var(--text-secondary)]">{manifest.revision}</dd>
          </div>
          <div>
            <dt className="text-[var(--text-muted)]">Checksum</dt>
            <dd className="break-all text-[var(--text-secondary)]">{manifest.checksum}</dd>
          </div>
        </dl>
      </div>
      <div>
        <h3 className="mb-3 font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Segments
        </h3>
        <ul className="space-y-3">
          {segments.map((seg) => (
            <li
              key={seg.name}
              className="rounded-[var(--radius-badge)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-3 font-mono text-sm"
            >
              <div className="font-medium text-[var(--text-primary)]">{seg.name}</div>
              <div className="mt-1 text-xs text-[var(--text-muted)]">
                Records: {seg.records} · Size: {formatBytes(seg.sizeBytes)}
              </div>
              <div className="mt-0.5 text-xs text-[var(--text-muted)]">
                Checksum: {seg.checksum}
              </div>
              <div className="mt-0.5 text-xs text-[var(--text-muted)]">
                Status: {seg.status}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
