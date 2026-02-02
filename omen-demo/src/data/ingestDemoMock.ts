/**
 * Ingest Demo — mock payload options and simulate idempotent ingest API.
 * First POST → 200 + ack_id; duplicates → 409 + same ack_id.
 */

export interface IngestPayloadOption {
  id: string;
  label: string;
  /** JSON payload to POST (signal envelope or minimal shape) */
  payloadJson: string;
}

/** Simulated API response */
export interface IngestResponse {
  status: 200 | 409 | 400 | 500;
  ack_id?: string | null;
  error?: string;
}

/** One row in the request log */
export interface RequestLogEntry {
  time: string;
  status: 200 | 409;
  signal_id: string;
  ack_id: string;
  duplicate: boolean;
}

/** One row in the database snapshot (processed_signals) */
export interface DatabaseSnapshotRow {
  signal_id: string;
  ack_id: string;
  partition: string;
  source: string;
  at: string;
}

/** In-memory: which signal_ids have already been accepted (for mock) */
const accepted = new Map<string, string>(); // signal_id -> ack_id

function ackIdFor(signalId: string): string {
  const base = signalId.replace(/[^A-Za-z0-9]/g, '').toLowerCase();
  return `riskcast-ack-${base.slice(0, 12)}`;
}

/**
 * Simulates POST /ingest: first request → 200 + ack_id; duplicates → 409 + same ack_id.
 */
export async function mockIngest(payload: { signal_id: string }): Promise<IngestResponse> {
  await new Promise((r) => setTimeout(r, 200 + Math.random() * 150));
  const signalId = payload.signal_id;
  if (!signalId) {
    return { status: 400, error: 'Missing signal_id' };
  }
  const existingAck = accepted.get(signalId);
  if (existingAck) {
    return { status: 409, ack_id: existingAck };
  }
  const ackId = ackIdFor(signalId);
  accepted.set(signalId, ackId);
  return { status: 200, ack_id: ackId };
}

/** Clear accepted state (for "Clear" button). */
export function clearIngestState(): void {
  accepted.clear();
}

/** Get current accepted ack_id for a signal_id (for database snapshot). */
export function getAcceptedAckId(signalId: string): string | null {
  return accepted.get(signalId) ?? null;
}

/** Whether this signal_id has been accepted at least once. */
export function hasAccepted(signalId: string): boolean {
  return accepted.has(signalId);
}

/** Payload dropdown options: Red Sea, Suez, Late arrival, Custom */
export const ingestPayloadOptions: IngestPayloadOption[] = [
  {
    id: 'OMEN-DEMO001ABCD',
    label: 'OMEN-DEMO001ABCD (Red Sea)',
    payloadJson: JSON.stringify(
      {
        signal_id: 'OMEN-DEMO001ABCD',
        title: 'Red Sea transit disruption',
        category: 'GEOPOLITICAL',
        probability: 0.72,
        confidence_score: 0.85,
        confidence_level: 'HIGH',
        generated_at: '2026-01-28T10:00:05Z',
      },
      null,
      2
    ),
  },
  {
    id: 'OMEN-DEMO002WXYZ',
    label: 'OMEN-DEMO002WXYZ (Suez)',
    payloadJson: JSON.stringify(
      {
        signal_id: 'OMEN-DEMO002WXYZ',
        title: 'Suez canal delay projected',
        category: 'INFRASTRUCTURE',
        probability: 0.55,
        confidence_score: 0.6,
        confidence_level: 'MEDIUM',
        generated_at: '2026-01-28T11:00:02Z',
      },
      null,
      2
    ),
  },
  {
    id: 'OMEN-DEMO008LATE',
    label: 'OMEN-DEMO008LATE (Late arrival)',
    payloadJson: JSON.stringify(
      {
        signal_id: 'OMEN-DEMO008LATE',
        title: 'Late report: port congestion',
        category: 'GEOPOLITICAL',
        probability: 0.6,
        confidence_score: 0.55,
        confidence_level: 'MEDIUM',
        generated_at: '2026-01-29T02:00:00Z',
      },
      null,
      2
    ),
  },
];

/** Build database snapshot row for a signal_id (1 row after first accept). */
export function getDatabaseSnapshotRow(signalId: string): DatabaseSnapshotRow | null {
  const ackId = getAcceptedAckId(signalId);
  if (!ackId) return null;
  const partition = new Date().toISOString().slice(0, 10);
  const at = new Date().toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  });
  return {
    signal_id: signalId,
    ack_id: ackId,
    partition,
    source: 'hot_path',
    at,
  };
}
