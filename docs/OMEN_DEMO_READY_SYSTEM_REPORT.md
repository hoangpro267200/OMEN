# OMEN — DEMO-READY SYSTEM REPORT (FOR UI + PRESENTATION)

**Role:** Principal Product Engineer + Demo Narrator + Systems Architect  
**Scope:** Dual-Path system parts 1–6 (SignalEvent, Ledger Writer/Reader, Hot Path Emitter, RiskCast Ingest + SignalStore, Reconcile + ReconcileStateStore)  
**Output:** Presentation-grade report for competition UI design.

---

## 1) Executive Demo Story (2–3 minutes script)

1. **Intro (15s)**  
   “OMEN is a two-path intelligence pipeline: a **hot path** for real-time delivery and a **cold path** (ledger) for audit and replay. Every signal is written to the ledger first; only then do we push to RiskCast. If the hot path fails, nothing is lost—reconcile replays from the ledger.”

2. **Ingest (30s)**  
   “Raw events enter OMEN; we validate and emit a **SignalEvent**. The emitter writes the event to the ledger with a framed record—length, CRC, payload—then fsyncs. After that succeeds, we POST to RiskCast. You’ll see one 200 and repeated 409s for duplicates: RiskCast dedupes by `signal_id` and returns the original `ack_id`.”

3. **Ledger (30s)**  
   “The ledger is partition-per-day by `emitted_at`, with optional `-late` for out-of-order arrivals. Segments roll at 10MB or 10k records. On seal we write `_manifest.json` with highwater. The reader truncates any partial trailing frame after a crash—no corrupted records.”

4. **Reconcile (30s)**  
   “Reconcile runs on **sealed** main partitions only; late partitions can be reconciled even if open. We compare ledger signal IDs to RiskCast’s processed set, replay missing via the same ingest API with `X-Replay-Source: reconcile`. State is stored so we only re-reconcile when highwater increases.”

5. **Close (15s)**  
   “So: ledger-first, crash-safe framing, dedupe at ingest, and reconcile for completeness. That’s the story we’re proving on stage.”

---

## 2) System Diagram (Textual)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OMEN DUAL-PATH PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

  Raw Events
       │
       ▼
┌──────────────┐     SignalEvent      ┌──────────────────────────────────────┐
│ OMEN Pipeline │ ──────────────────► │ LedgerWriter (WAL framing)            │
│ (validate +   │  1) write(event)    │   • Partition by emitted_at (YYYY-MM-DD)
│  emit)        │  2) fsync            │   • Frame: [4B len][4B crc][payload]   │
└──────────────┘  3) then hot path    │   • _CURRENT, _manifest.json, _SEALED  │
       │                               └──────────────────┬───────────────────┘
       │                                                  │
       │  (only after ledger success)                     │ ledger (cold path)
       ▼                                                  ▼
┌──────────────────────────────────────┐         ┌─────────────────────────┐
│ SignalEmitter                         │         │ LedgerReader             │
│   _push_to_riskcast(event)            │         │   read_partition()       │
│   POST /api/v1/signals/ingest         │         │   get_partition_highwater│
└──────────────────┬───────────────────┘         │   (truncate partial tail)│
                    │                              └────────────┬────────────┘
                    │ hot path                                  │
                    ▼                                           │
┌──────────────────────────────────────┐                       │
│ RiskCast                             │                       │
│   Ingest API → SignalStore (SQLite)  │◄──────────────────────┘
│   • signal_id PRIMARY KEY            │     ReconcileJob: ledger vs processed
│   • 200 + ack_id / 409 + original     │     → replay missing via ingest
│     ack_id on duplicate               │
└──────────────────┬───────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│ ReconcileStateStore                   │
│   needs_reconcile(partition, highwater)│
│   save_state(partition, ...)          │
└──────────────────────────────────────┘
```

**Flow summary:** OMEN → Ledger (first) → Webhook to RiskCast → Reconcile reads Ledger + SignalStore, replays missing via same ingest.

---

## 3) Data Model Cheatsheet

| Entity | Purpose | Key fields |
|--------|---------|------------|
| **SignalEvent** | Canonical envelope for dual-path delivery | `signal_id`, `observed_at`, `emitted_at`, `ledger_written_at`, `ledger_partition`, `ledger_sequence`, `signal` (OmenSignal), `input_event_hash`, `deterministic_trace_id` |
| **WAL Record Frame** | One on-disk record in a segment | **Header:** 4B payload length (big-endian), 4B CRC32 (big-endian). **Body:** UTF-8 JSON of SignalEvent (exclude_none). |
| **Partition** | Logical day bucket for ledger | Key = `YYYY-MM-DD` or `YYYY-MM-DD-late`. Dir contains `signals-001.wal`, … , `_CURRENT`, `_manifest.json`, `_SEALED`. |
| **Segment** | Single WAL file in a partition | `signals-NNN.wal`. Rollover at 10MB or 10k records; sealed segment chmod 0o444. |
| **Manifest** | Snapshot at partition seal | `partition_date`, `sealed_at`, `total_records`, `highwater_sequence`, `manifest_revision`, `segments[]`, `is_late_partition`. |
| **ReconcileState** | Last reconcile result per partition | `partition_date`, `last_reconcile_at`, `ledger_highwater`, `manifest_revision`, `ledger_record_count`, `processed_count`, `missing_count`, `status` (COMPLETED/PARTIAL/FAILED). |
| **ProcessedSignal** | One row in RiskCast SignalStore | `signal_id`, `trace_id`, `ack_id`, `processed_at`, `emitted_at`, `partition_date`, `source` (hot_path | reconcile), `signal_data` (JSON). |

---

## 4) Semantics (Watermark + Time + Ordering)

### Timestamps

| Field | Meaning | Set by | Used for |
|-------|---------|--------|----------|
| **observed_at** | When source data was observed | Pipeline (from source) | Provenance only; not partitioning. |
| **emitted_at** | When OMEN emitted this signal | Pipeline at emit time (`datetime.now(timezone.utc)`) | **Partitioning:** partition = `emitted_at.date().isoformat()`. |
| **ledger_written_at** | When written to ledger | LedgerWriter in `with_ledger_metadata()` | Audit trail; set after append. |

### Ordering and out-of-order

- **Ordering:** Ledger append order within a segment is the write order. `ledger_sequence` is partition-wide monotonic: `(segment_ordinal << 32) | record_index`.
- **Out-of-order:** If a signal arrives after its partition is sealed (e.g. main partition `2026-01-28` already sealed), writer routes it to **late partition** `2026-01-28-late`. No overwrite of main partition.

### Watermark and partition completeness

- **Watermark:** For a partition, the **highwater** is the number of records (or at seal, the value in `_manifest.json`: `highwater_sequence` = total_records at seal). Open partition: reader sums valid records in all segments → highwater = that count.
- **How RiskCast knows “complete vs open”:**
  - **Sealed:** Partition dir has `_SEALED` and `_manifest.json`. Reconcile is allowed for main partitions only when sealed; late partitions can be reconciled even if not sealed (within grace window).
  - **Open:** No `_SEALED`; writer may still be appending. Reconcile job skips main partition with reason `main_partition_not_sealed`.
- **Late arrivals:** New records in a sealed main partition are not allowed (writer sends to `-late`). Late partition highwater can increase; `needs_reconcile` returns true when `current_highwater > state.ledger_highwater` (reason `highwater_increased_...`), triggering re-reconcile.

### Vocabulary

- **OPEN:** Partition not sealed; writes may still occur.
- **SEALED:** Partition has `_SEALED`; no more writes to main partition (late partition can still receive).
- **LATE:** Partition name ends with `-late`; holds out-of-order arrivals for that date.
- **RECONCILED:** Last reconcile status COMPLETED; state saved.
- **PARTIAL:** Reconcile ran but some replays failed or batch cap hit.
- **FAILED:** Reconcile error (e.g. ledger read failure).

---

## 5) Reliability Proof Pack (What to Show on Stage)

| Proof | What to show | What it proves | Data/metric |
|-------|----------------|-----------------|-------------|
| **Crash-tail** | Unit test or log: write 3 records, truncate segment after 2 full frames; reader returns 2 events, logs “Partial payload… truncating”, yields no 3rd. | Partial trailing write is detected; reader truncates; no corrupted record returned. | `test_ledger_crash_tail_returns_n_minus_1_valid_records`; reader warning + count. |
| **Dedupe** | Ingest: 1 POST → 200 + `ack_id`; N concurrent POSTs same body → all 409 with same `ack_id`. DB has 1 row. | RiskCast dedupes by `signal_id`; 409 returns original ack_id; safe under concurrency. | 1×200, N×409; `processed_signals` count = 1. |
| **Reconcile** | Before: ledger has 10 signal_ids, RiskCast has 8. Run reconcile. After: RiskCast has 10; reconcile result `missing_count=2`, `replayed_count=2`. | Missing signals (e.g. hot path loss) are replayed from ledger via ingest; state updated. | ReconcileResult; `processed_signals` count before/after. |
| **Ledger-first** | Emitter code path: `ledger.write(event)` then `_push_to_riskcast(event)`; on LedgerWriteError return FAILED and do not push. Test: mock ledger to raise → no HTTP POST. | No hot path push unless ledger write succeeded. | `test_ledger_first_invariant_hot_path_fails`; emit flow in code. |
| **Metadata durability** | Test: `_atomic_write_text` call order = write temp → flush → fsync(temp) → replace → fsync(parent dir). | _CURRENT and _manifest survive crash (temp + rename + dir fsync). | `test_atomic_write_text_fsync_order`. |

---

## 6) Demo Dataset (UI Seed Data)

### 10 demo SignalEvents (JSON)

Assume `OmenSignal` nested under `signal` with required fields; timestamps ISO UTC.

**1. Normal (in-order)**  
```json
{
  "schema_version": "1.0.0",
  "signal_id": "OMEN-DEMO001ABCD",
  "deterministic_trace_id": "a1b2c3d4e5f6g7h8",
  "input_event_hash": "sha256:abc123",
  "source_event_id": "evt-001",
  "ruleset_version": "1.0.0",
  "observed_at": "2026-01-28T10:00:00+00:00",
  "emitted_at": "2026-01-28T10:00:05+00:00",
  "ledger_written_at": "2026-01-28T10:00:05+00:00",
  "ledger_partition": "2026-01-28",
  "ledger_sequence": 1,
  "signal": {
    "signal_id": "OMEN-DEMO001ABCD",
    "source_event_id": "evt-001",
    "title": "Red Sea transit disruption",
    "probability": 0.72,
    "confidence_score": 0.85,
    "confidence_level": "HIGH",
    "category": "GEOPOLITICAL",
    "trace_id": "a1b2c3d4e5f6g7h8",
    "ruleset_version": "1.0.0",
    "generated_at": "2026-01-28T10:00:05+00:00"
  }
}
```

**2. Duplicate (same signal_id as 1)**  
Same as above, `signal_id`: `OMEN-DEMO001ABCD` — use for 409 demo.

**3. Second distinct signal**  
```json
{
  "schema_version": "1.0.0",
  "signal_id": "OMEN-DEMO002WXYZ",
  "deterministic_trace_id": "b2c3d4e5f6g7h8i9",
  "input_event_hash": "sha256:def456",
  "source_event_id": "evt-002",
  "ruleset_version": "1.0.0",
  "observed_at": "2026-01-28T11:00:00+00:00",
  "emitted_at": "2026-01-28T11:00:02+00:00",
  "ledger_partition": "2026-01-28",
  "ledger_sequence": 2,
  "signal": {
    "signal_id": "OMEN-DEMO002WXYZ",
    "source_event_id": "evt-002",
    "title": "Suez canal delay probability",
    "probability": 0.55,
    "confidence_score": 0.7,
    "confidence_level": "MEDIUM",
    "category": "INFRASTRUCTURE",
    "trace_id": "b2c3d4e5f6g7h8i9",
    "ruleset_version": "1.0.0",
    "generated_at": "2026-01-28T11:00:02+00:00"
  }
}
```

**4–7.** Same pattern for `OMEN-DEMO003` … `OMEN-DEMO007` (vary title/category/observed_at/emitted_at on 2026-01-28).

**8. Out-of-order arrival (emitted next day, observed previous day)**  
```json
{
  "schema_version": "1.0.0",
  "signal_id": "OMEN-DEMO008LATE",
  "deterministic_trace_id": "c3d4e5f6g7h8i9j0",
  "input_event_hash": "sha256:late001",
  "source_event_id": "evt-008",
  "ruleset_version": "1.0.0",
  "observed_at": "2026-01-27T23:50:00+00:00",
  "emitted_at": "2026-01-29T02:00:00+00:00",
  "ledger_partition": "2026-01-28-late",
  "ledger_sequence": 1,
  "signal": {
    "signal_id": "OMEN-DEMO008LATE",
    "source_event_id": "evt-008",
    "title": "Late report: port closure",
    "probability": 0.6,
    "confidence_score": 0.65,
    "confidence_level": "MEDIUM",
    "category": "GEOPOLITICAL",
    "trace_id": "c3d4e5f6g7h8i9j0",
    "ruleset_version": "1.0.0",
    "generated_at": "2026-01-29T02:00:00+00:00"
  }
}
```

**9. Duplicate of 3**  
Same `signal_id` as event 3: `OMEN-DEMO002WXYZ` (for 409 demo).

**10. Tenth distinct**  
`OMEN-DEMO010TENTH`, any category/title, partition `2026-01-28`.

---

### Sample WAL hex/layout (one record)

- **Frame:** `[4B length][4B crc32][N bytes JSON]`, big-endian.
- Example: payload length 500, CRC32 0x1a2b3c4d.  
  **Hex (header only):** `00 00 01 f4 1a 2b 3c 4d` (then 500 bytes UTF-8 JSON).
- **Layout:**
  - Bytes 0–3: payload length (e.g. `0x000001f4` = 500).
  - Bytes 4–7: CRC32 of payload.
  - Bytes 8–507: SignalEvent JSON (exclude_none).

---

### Sample reconcile run output

**Before (missing replay):**  
- Ledger partition `2026-01-28`: 10 signal_ids.  
- RiskCast `processed_signals` for `2026-01-28`: 8 (missing e.g. `OMEN-DEMO005`, `OMEN-DEMO009`).

**Reconcile run (one partition):**  
```text
Reconciling partition: 2026-01-28
Ledger has 10 signals for 2026-01-28
Processed 8 signals for 2026-01-28
Found 2 missing signals for 2026-01-28
✓ 2026-01-28: replayed 2 signals
```

**After:**  
- ReconcileResult: `status=COMPLETED`, `ledger_count=10`, `processed_count=10`, `missing_count=2`, `replayed_count=2`, `replayed_ids=["OMEN-DEMO005","OMEN-DEMO009"]`.  
- RiskCast now has 10 rows for partition `2026-01-28`.

---

### Sample duplicate ingest scenario (1×200 + N×409)

- **Action:** 1 POST with SignalEvent `OMEN-DEMO001ABCD` → **200** `{"ack_id": "riskcast-ack-abc123"}`.  
  Then 5 concurrent POSTs same body (same `signal_id`).  
- **Result:** All 5 return **409** `{"ack_id": "riskcast-ack-abc123", "duplicate": true}`.  
- **DB:** 1 row in `processed_signals` with that `signal_id`.

---

### Fake manifest JSON (one sealed partition)

```json
{
  "schema_version": "1.0.0",
  "partition_date": "2026-01-28",
  "sealed_at": "2026-01-29T04:00:00+00:00",
  "total_records": 10,
  "highwater_sequence": 10,
  "manifest_revision": 1,
  "is_late_partition": false,
  "segments": [
    {
      "file": "signals-001.wal",
      "record_count": 10,
      "size_bytes": 8192,
      "checksum": "crc32:deadbeef"
    }
  ]
}
```

---

### Fake reconcile_state row (that partition)

| partition_date | last_reconcile_at        | ledger_highwater | manifest_revision | ledger_record_count | processed_count | missing_count | status    |
|----------------|--------------------------|-----------------|-------------------|---------------------|-----------------|---------------|-----------|
| 2026-01-28     | 2026-01-29T05:00:00+00:00 | 10              | 1                 | 10                  | 8               | 2             | COMPLETED |

(After reconcile run that replayed 2, processed_count would become 10, missing_count 0.)

---

### Fake processed_signals snapshot (missing 2 for reconcile demo)

Partition `2026-01-28`; 8 rows (omit `OMEN-DEMO005`, `OMEN-DEMO009`):

| signal_id           | ack_id             | partition_date | source   |
|---------------------|--------------------|----------------|----------|
| OMEN-DEMO001ABCD    | riskcast-ack-1     | 2026-01-28     | hot_path |
| OMEN-DEMO002WXYZ    | riskcast-ack-2     | 2026-01-28     | hot_path |
| OMEN-DEMO003...     | riskcast-ack-3     | 2026-01-28     | hot_path |
| OMEN-DEMO004...     | riskcast-ack-4     | 2026-01-28     | hot_path |
| OMEN-DEMO006...     | riskcast-ack-6     | 2026-01-28     | hot_path |
| OMEN-DEMO007...     | riskcast-ack-7     | 2026-01-28     | hot_path |
| OMEN-DEMO008LATE    | riskcast-ack-8     | 2026-01-28     | hot_path |
| OMEN-DEMO010TENTH   | riskcast-ack-10    | 2026-01-28     | hot_path |

(No OMEN-DEMO005, OMEN-DEMO009 — reconcile will replay these two.)

---

## 7) UI Requirements (Presentation-First)

### Top-level navigation (5–8 screens)

| # | Screen | Purpose | Key components | Primary KPIs (max 5) | Interactions | Failure/edge states |
|---|--------|---------|-----------------|----------------------|--------------|----------------------|
| 1 | **Dashboard** | High-level health and throughput | Partition status cards, last reconcile summary, ingest rate | Partitions sealed/open, last reconcile time, signals today, ingest 200/409 counts | Filter by date range; drill to partition | Loading skeleton; empty “No partitions”; error banner |
| 2 | **Partitions** | List and status of ledger partitions | Table: partition_date, is_sealed, is_late, total_records, highwater | Partitions count, sealed vs open, late count | Sort by date; filter sealed/open/late; open partition detail | Empty; partial (some sealed some not) |
| 3 | **Partition detail** | Single partition: ledger vs RiskCast | Ledger segment list, manifest summary, processed count, missing list, reconcile state | total_records, processed_count, missing_count, status | Run reconcile; view history | OPEN (reconcile disabled); PARTIAL/FAILED status |
| 4 | **Signals** | Browse/search emitted signals | Table or cards: signal_id, emitted_at, category, title, partition | Signals count, by category breakdown | Filter by partition/date/category; drill to signal | Empty; loading |
| 5 | **Reconcile** | Trigger and results | Run button (all or per partition), results table: partition, status, missing, replayed | Reconcile runs count, replayed total, failed count | Run; filter by partition/date | FAILED/PARTIAL; no sealed partitions |
| 6 | **Ingest / API** | Demo ingest and dedupe | “Send 1” / “Send N duplicates” buttons, response log (200/409), ack_id display | 200 count, 409 count, last ack_id | Send single; send N duplicates; copy ack_id | 400 invalid body; 5xx server error |
| 7 | **Ledger proof** | Crash-tail / framing demo | Segment hex or record list, “Truncate & read” demo, record count before/after | Records read, truncation warning shown | Select segment; run truncate+read | File not found; empty segment |
| 8 | **Settings / Copy** | Stage labels and microcopy | Nav labels, hero headline, status vocabulary (reference) | — | — | — |

### Data per component (field-level)

- **Partition card/row:** `partition_date`, `is_sealed`, `is_late`, `total_records`, `highwater_sequence`, `segments[]` (count or names).
- **Reconcile state line:** `partition_date`, `last_reconcile_at`, `ledger_highwater`, `processed_count`, `missing_count`, `status`, `replayed_count`.
- **Signal row:** `signal_id`, `emitted_at`, `observed_at`, `ledger_partition`, `ledger_sequence`, `signal.category`, `signal.title`, `signal.probability`, `signal.confidence_level`.
- **Ingest response:** `status_code`, `ack_id`, `duplicate` (if 409).

### States to support

- **Loading:** Spinner or skeleton for tables/cards.
- **Empty:** “No partitions” / “No signals” with short explanation.
- **Error:** Banner + message; retry where applicable.
- **Partial:** Some partitions sealed, some open; show both.
- **Sealed:** Partition has _SEALED; show “Sealed” badge; reconcile allowed (main).
- **Open:** No _SEALED; “Open” badge; reconcile skipped for main.
- **Late:** Partition name `*-late`; “Late” badge.

---

## 8) Copywriting (Stage Text)

### Nav labels (short)

- Dashboard  
- Partitions  
- Partition detail  
- Signals  
- Reconcile  
- Ingest demo  
- Ledger proof  
- Copy ref  

### Hero headline

**“OMEN: Two-path signal intelligence — ledger first, then live.”**

### Microcopy (6–10)

- “Ledger written before hot path; reconcile recovers any loss.”  
- “Duplicate ingest returns 409 with original ack_id.”  
- “Partition sealed: no more writes; safe to reconcile.”  
- “Late partition: out-of-order arrivals for this date.”  
- “Reconcile replays missing signals from ledger to RiskCast.”  
- “Partial frame at end of segment truncated; no corrupt record.”  
- “Highwater increased → re-reconcile to catch late arrivals.”  
- “Main partition: reconcile only when sealed.”  
- “1×200, N×409: one accepted, rest deduped.”  
- “Crash-tail: reader returns only complete frames.”  

### Status vocabulary

- **SEALED** — Partition closed for writes; has _SEALED and _manifest.json.  
- **OPEN** — Partition still writable.  
- **LATE** — Partition name ends with `-late`; holds late arrivals.  
- **RECONCILED** — Last reconcile status COMPLETED.  
- **PARTIAL** — Reconcile ran but some replays failed or capped.  
- **FAILED** — Reconcile error.  

---

## 9) What Not To Build (Anti-Requirements)

- **No impact/decision UI in OMEN demo** — OMEN emits signals only; no impact assessment or recommendation screens.  
- **No auth/permissions** — Demo uses fixed API key; no login or role-based UI.  
- **No historical trend charts** — No time-series charts or long-range analytics; keep to “today” or last N days.  
- **No raw ledger file edit** — No UI to edit WAL or manifest on disk; read-only for proof.  
- **No pipeline config UI** — No changing ruleset, partition grace, or segment size in demo.  
- **No multi-tenant or org switcher** — Single tenant, single ledger/RiskCast instance.  
- **No alerting/notifications** — No emails or webhooks for reconcile failure; show status on screen only.  
- **No replay of individual signal from UI** — Replay is via reconcile job; no “replay this one” button (optional for later).  
- **No schema evolution UI** — Fixed SignalEvent 1.0.0 for demo.  

---

*End of report.*
