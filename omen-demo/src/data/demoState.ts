/**
 * In-memory mutable state for mock client.
 * Used only by mockClient; screens must not import this file.
 *
 * - processed_ids: signal_ids that RiskCast has "processed" (starts as 8 of 10 for 2026-01-28)
 * - ingest_accepted: signal_id -> ack_id for idempotent ingest (first 200, dup 409 same ack_id)
 */

const STORAGE_KEY_PROCESSED = 'omen.demo.processed_ids';
const STORAGE_KEY_INGEST = 'omen.demo.ingest_accepted';

/** Initial processed signal IDs for partition 2026-01-28 (8 of 10; missing OMEN-DEMO005, OMEN-DEMO009). */
const INITIAL_PROCESSED_2026_01_28 = [
  'OMEN-DEMO001',
  'OMEN-DEMO002',
  'OMEN-DEMO003',
  'OMEN-DEMO004',
  'OMEN-DEMO006',
  'OMEN-DEMO007',
  'OMEN-DEMO008',
  'OMEN-DEMO010',
];

let processedIds: Set<string> = new Set(INITIAL_PROCESSED_2026_01_28);
const ingestAccepted: Map<string, string> = new Map();

function loadFromStorage(): void {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_PROCESSED);
    if (raw) {
      const arr = JSON.parse(raw) as string[];
      processedIds = new Set(arr);
    }
  } catch {
    processedIds = new Set(INITIAL_PROCESSED_2026_01_28);
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY_INGEST);
    if (raw) {
      const obj = JSON.parse(raw) as Record<string, string>;
      ingestAccepted.clear();
      Object.entries(obj).forEach(([k, v]) => ingestAccepted.set(k, v));
    }
  } catch {
    ingestAccepted.clear();
  }
}

function saveProcessed(): void {
  try {
    localStorage.setItem(STORAGE_KEY_PROCESSED, JSON.stringify([...processedIds]));
  } catch {
    // ignore
  }
}

function saveIngest(): void {
  try {
    const obj = Object.fromEntries(ingestAccepted);
    localStorage.setItem(STORAGE_KEY_INGEST, JSON.stringify(obj));
  } catch {
    // ignore
  }
}

export function getProcessedIds(): Set<string> {
  return processedIds;
}

export function getProcessedIdsList(): string[] {
  return [...processedIds];
}

export function addProcessedIds(ids: string[]): void {
  ids.forEach((id) => processedIds.add(id));
  saveProcessed();
}

export function getIngestAckId(signalId: string): string | null {
  return ingestAccepted.get(signalId) ?? null;
}

export function setIngestAccepted(signalId: string, ackId: string): void {
  ingestAccepted.set(signalId, ackId);
  saveIngest();
}

export function hasIngestAccepted(signalId: string): boolean {
  return ingestAccepted.has(signalId);
}

/** Deterministic ack_id: riskcast-ack-${signal_id.slice(-4).toLowerCase()} */
export function deterministicAckId(signalId: string): string {
  const suffix = signalId.slice(-4).toLowerCase();
  return `riskcast-ack-${suffix}`;
}

/** Reset processed and ingest state to initial. */
export function resetDemoState(): void {
  processedIds = new Set(INITIAL_PROCESSED_2026_01_28);
  ingestAccepted.clear();
  saveProcessed();
  saveIngest();
}

// Load persisted state on module load (optional; for dev refresh persistence)
if (typeof window !== 'undefined') {
  loadFromStorage();
}
