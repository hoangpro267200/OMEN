/**
 * Ledger Proof — WAL framing and crash-tail safety. Mock data for Frame Viewer and Crash Simulator.
 */

export interface WalSegment {
  partition: string;
  segmentId: string;
  filename: string;
  status: 'SEALED' | 'OPEN';
  recordCount: number;
  sizeBytes: number;
}

export interface WalFrameRecord {
  /** 1-based index in segment */
  recordIndex: number;
  /** Byte offset in segment file */
  offset: number;
  /** Payload length (bytes) */
  length: number;
  /** CRC32 of payload (hex) */
  crc32Hex: string;
  /** First N chars of payload JSON */
  payloadPreview: string;
  /** Full payload JSON (for View Full JSON) */
  payloadFull: string;
}

/** Header row for hex viewer: offset, hex bytes, decoded meaning */
export interface FrameHeaderRow {
  offset: number;
  hex: string;
  decoded: string;
}

export const ledgerProofPartitions = ['2026-01-27', '2026-01-28', '2026-01-29'];

export const ledgerProofSegments: WalSegment[] = [
  { partition: '2026-01-28', segmentId: '001', filename: 'signals-001.wal', status: 'SEALED', recordCount: 10, sizeBytes: 8192 },
  { partition: '2026-01-28', segmentId: '002', filename: 'signals-002.wal', status: 'SEALED', recordCount: 8, sizeBytes: 6144 },
  { partition: '2026-01-29', segmentId: '001', filename: 'signals-001.wal', status: 'SEALED', recordCount: 5, sizeBytes: 4096 },
];

function makePayload(signalId: string, traceId: string): string {
  return JSON.stringify({
    schema_version: '1.0.0',
    signal_id: signalId,
    deterministic_trace_id: traceId,
    input_event_hash: 'sha256:abc123',
    source_event_id: 'evt-001',
    ruleset_version: '1.0.0',
    observed_at: '2026-01-28T10:00:00Z',
    emitted_at: '2026-01-28T10:00:05Z',
    signal: { signal_id: signalId, title: 'Red Sea transit disruption', category: 'GEOPOLITICAL', probability: 0.72 },
  });
}

/** Build mock frame records for segment (e.g. signals-001.wal for 2026-01-28). */
export function getFrameRecordsForSegment(_partition: string, _filename: string): WalFrameRecord[] {
  const records: WalFrameRecord[] = [];
  let offset = 0;
  const signals = [
    { id: 'OMEN-DEMO001ABCD', trace: 'a1b2c3d4e5f6g7h8' },
    { id: 'OMEN-DEMO002WXYZ', trace: 'b2c3d4e5f6g7h8i9' },
    { id: 'OMEN-DEMO003DEF', trace: 'c3d4e5f6g7h8i9j0' },
    { id: 'OMEN-DEMO004GHI', trace: 'd4e5f6g7h8i9j0k1' },
    { id: 'OMEN-DEMO005JKL', trace: 'e5f6g7h8i9j0k1l2' },
    { id: 'OMEN-DEMO006MNO', trace: 'f6g7h8i9j0k1l2m3' },
    { id: 'OMEN-DEMO007PQR', trace: 'g7h8i9j0k1l2m3n4' },
    { id: 'OMEN-DEMO008LATE', trace: 'h8i9j0k1l2m3n4o5' },
    { id: 'OMEN-DEMO009STU', trace: 'i9j0k1l2m3n4o5p6' },
    { id: 'OMEN-DEMO010VWX', trace: 'j0k1l2m3n4o5p6q7' },
  ];
  for (let i = 0; i < Math.min(10, signals.length); i++) {
    const s = signals[i];
    const payloadFull = makePayload(s.id, s.trace);
    const length = new TextEncoder().encode(payloadFull).length;
    const crc32Hex = '1a2b3c4d'; // mock
    const payloadPreview = payloadFull.length > 200 ? payloadFull.slice(0, 200) + '...' : payloadFull;
    records.push({
      recordIndex: i + 1,
      offset,
      length,
      crc32Hex,
      payloadPreview,
      payloadFull,
    });
    offset += 4 + 4 + length;
  }
  return records;
}

/** Format length as 4-byte big-endian hex (e.g. 500 -> 0x000001f4). */
export function lengthToHex(length: number): string {
  const hex = length.toString(16).padStart(8, '0');
  return hex.match(/.{2}/g)!.join(' ');
}

/** Get header rows for a frame (offset 0: length, offset 4: crc). */
export function getFrameHeaderRows(offset: number, length: number, crc32Hex: string): FrameHeaderRow[] {
  const crcBytes = crc32Hex.padStart(8, '0').match(/.{2}/g)!.join(' ');
  return [
    { offset, hex: lengthToHex(length), decoded: `Length: ${length} bytes` },
    { offset: offset + 4, hex: crcBytes, decoded: `CRC32: 0x${crc32Hex} ✓ Valid` },
  ];
}

/** Crash simulator: 3 frames, then "truncate" so frame 3 is partial. */
export const crashSimulatorFrameSizes = [500, 480, 520];
export const crashSimulatorPartialBytes = 200; // Frame 3 has 200 of 520 bytes when crashed
export const crashSimulatorTruncateOffset = 988; // offset where reader truncates (after frame 2)
export const crashSimulatorValidRecordsAfterRead = 2;
