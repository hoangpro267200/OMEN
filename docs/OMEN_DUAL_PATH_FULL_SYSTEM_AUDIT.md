# OMEN DUAL-PATH — FULL SYSTEM AUDIT (6 PARTS)

**Role:** Principal Engineer + Systems Architect — hardline design+implementation audit.  
**Scope:** Parts 1–6 (SignalEvent schema, Ledger Writer/Reader, Emitter, SignalStore, Reconcile).  
**Date:** Audit run after mandatory tests added (crash-tail, concurrent ingest dedupe).

---

## (A) System Map

| Part | Key files | Key entrypoints |
|------|-----------|-----------------|
| **1 — SignalEvent schema** | `src/omen/domain/models/signal_event.py` | `SignalEvent`, `LedgerRecord`, `SCHEMA_VERSION`, `generate_input_event_hash` |
| **2 — Ledger Writer** | `src/omen/infrastructure/ledger/writer.py` | `LedgerWriter.write()`, `_append_framed_record`, `_set_current_segment`, `seal_partition`, `get_partitions_to_seal` |
| **3 — Ledger Reader** | `src/omen/infrastructure/ledger/reader.py` | `LedgerReader.read_partition`, `_read_segment`, `get_partition_highwater`, `query_by_time_range`, `query_by_trace_ids`, `query_by_category` |
| **4 — Hot Path Emitter** | `src/omen/infrastructure/emitter/signal_emitter.py` | `SignalEmitter.emit()`, `_push_to_riskcast`, `BackpressureController` |
| **5 — RiskCast SignalStore** | `src/riskcast/infrastructure/signal_store.py` | `SignalStore.store()`, `get_by_signal_id`, `list_processed_ids`; **Ingest API:** `src/riskcast/api/routes/ingest.py` (added in audit) |
| **6 — Reconcile** | `src/riskcast/infrastructure/reconcile_state.py`, `src/riskcast/jobs/reconcile_job.py`, `src/riskcast/api/routes/reconcile.py` | `ReconcileStateStore.needs_reconcile`, `ReconcileJob.reconcile_partition`, `run_reconcile_job`, `POST/GET /reconcile/*` |

**Dependency flow:**  
OMEN pipeline → SignalEvent → LedgerWriter (ledger-first) → SignalEmitter.emit() → RiskCast ingest URL.  
Reconcile: LedgerReader + ReconcileStateStore + SignalStore → ReconcileJob → replay missing via ingest URL.

---

## (B) Invariant Checklist

| Invariant | Result | Code location |
|-----------|--------|----------------|
| **Ledger-first: every signal durably written to ledger BEFORE hot-path push** | **PASS** | `signal_emitter.py`: `emit()` does `event = self.ledger.write(event)` then `_push_to_riskcast(event)`; on ledger exception returns `EmitStatus.FAILED` and does not push. |
| **Effective exactly-once: RiskCast dedupe by signal_id; duplicates safe under concurrency** | **PASS** | `signal_store.py`: `signal_id TEXT PRIMARY KEY`; `ingest.py`: INSERT then catch `IntegrityError` → 409 with original ack_id. Concurrent test: 20 requests → 1×200, 19×409, 1 row in DB. |
| **No lost signals: hot-path loss recoverable via reconcile** | **PASS** | All emitted signals written to ledger first; reconcile reads ledger, compares to SignalStore, replays missing. |
| **No stateful business logic in OMEN emitter beyond delivery** | **PASS** | Emitter only: build event, ledger.write, HTTP POST; no business rules. |
| **Append crash-safe: partial writes detectable, trailing partial handled** | **PASS** | Writer: frame = [4B length][4B crc][payload], `os.fsync` after write. Reader: partial header/payload → break, no corrupted record yielded. `test_ledger_crash_tail_returns_n_minus_1_valid_records` added. |
| **Atomic metadata: _CURRENT and manifest durable (temp + rename + fsync dir)** | **PARTIAL** | Writer: `_set_current_segment` and manifest use `temp.write_text` then `os.replace`; **no fsync of temp or parent dir** before replace. So metadata may not be durable after power loss. |
| **Immutability: ledger append-only; sealed segments immutable** | **PASS** | Writer only appends; rollover seals with chmod 0o444 (best-effort on Windows). |
| **ledger_sequence monotonic within logical partition across segments** | **FAIL** | Writer: `sequence = _increment_record_count(segment_file)` is **per-segment**; after rollover new segment gets 1,2,3… again. Manifest `highwater_sequence` is partition-wide at seal only. |
| **Highwater semantics explicit; late arrivals handled** | **PASS** | Reader: `get_partition_highwater` from manifest or scan; late partition = `{date}-late`; reconcile uses `needs_reconcile(partition_date, current_highwater, current_revision)`. |
| **Main partitions: reconcile NOT run unless SEALED** | **PASS** | `reconcile_job.py`: `if not is_late and not info.is_sealed: return ReconcileResult(..., reason="main_partition_not_sealed")`. |
| **Late partitions: re-reconcile when highwater changes** | **PASS** | `needs_reconcile` returns True when `current_highwater > state.ledger_highwater` or `current_revision > state.manifest_revision`; reason contains `highwater_increased` / `manifest_revision_increased`. |
| **Reconcile state persisted** | **PASS** | `ReconcileStateStore` uses aiosqlite; `reconcile_state` + `reconcile_history` tables. |
| **Reconcile detects impossible state: processed not in ledger** | **PASS** | `extra_ids = list(processed_ids - ledger_ids)`; logged as CRITICAL. |
| **Ingest concurrency-safe; IntegrityError → 409 with original ack_id** | **PASS** | Ingest route: INSERT; on `IntegrityError`, `get_by_signal_id` and return 409 with `rec.ack_id`. SignalStore: PRAGMA busy_timeout for concurrent writers. |
| **Persist-before-ack: RiskCast persist before 200** | **PASS** | Ingest: `await store.store(...)` then `return JSONResponse(..., status_code=200)`. |
| **Async correctness: no sync sqlite in async path** | **PASS** | SignalStore and ReconcileStateStore use aiosqlite throughout. |
| **Timezone-aware UTC end-to-end** | **PARTIAL** | `signal_event.py`: `emitted_at=datetime.utcnow()` (naive). Emitter/ingest use `datetime.now(timezone.utc)` where added. |
| **emitted_at for partitioning; observed_at for provenance** | **PASS** | Writer uses `event.emitted_at.date().isoformat()` for partition; observed_at stored in event only. |
| **signal_id deterministic and stable** | **PASS** | OmenSignal builds signal_id from trace; trace from `_generate_deterministic_trace_id(event_id, input_event_hash, ruleset_version)`. |

---

## (C) Findings

### CRITICAL

**C1. LedgerWriter never raises LedgerWriteError** — **FIX APPLIED**

- **Symptom:** Emitter catches `LedgerWriteError` and `Exception`. Writer only raised `ValueError` in `seal_partition`; OSError (e.g. disk full) propagated as generic Exception.
- **Root cause:** `writer.write()` did not wrap write/fsync failures in `LedgerWriteError`.
- **Fix applied:** `write()` now delegates to `_write_impl()` and wraps OSError in `LedgerWriteError`; callers get a typed exception on I/O failure.

---

### HIGH

**H1. _CURRENT and manifest updates not durable (no fsync before/after rename)** — **FIX APPLIED**

- **Symptom:** After crash, _CURRENT or _manifest.json could point to wrong segment or stale manifest if temp file was not flushed.
- **Root cause:** `_set_current_segment` and manifest write used `temp.write_text(...)` then `os.replace` with no fsync.
- **Fix applied:** Both paths now open temp file, write, `flush()`, `os.fsync(f.fileno())`, then `os.replace`.

**H2. ledger_sequence not partition-wide monotonic**

- **Symptom:** Per-event `ledger_sequence` resets to 1,2,3… in each new segment; ordering across segments within a partition is not reflected in sequence numbers.
- **Root cause:** `_increment_record_count(segment_file)` is per-segment; manifest `highwater_sequence` is partition-wide only at seal.
- **Reproduction:** Write until rollover; second segment events have ledger_sequence 1, 2, … again.
- **Fix (minimal):** Either (1) document that ledger_sequence is per-segment and highwater is the partition-wide source of truth, or (2) maintain a partition-wide counter (e.g. in a small state file or _CURRENT sidecar) and assign that to each event. Option (1) is minimal; option (2) satisfies strict “monotonic within partition” requirement.

---

### MEDIUM

**M1. Naive datetime in SignalEvent**

- **Symptom:** `from_omen_signal` and `with_ledger_metadata` use `datetime.utcnow()` (naive); invariant requires timezone-aware UTC.
- **Root cause:** Legacy use of utcnow in domain model.
- **Fix:** Use `datetime.now(timezone.utc)` and ensure emitted_at/ledger_written_at are timezone-aware in schema and API.

**M2. RiskCast ingest API was missing**

- **Status:** Addressed during audit. Added `src/riskcast/api/routes/ingest.py` (POST /api/v1/signals/ingest), persist-before-ack, 409 on duplicate with original ack_id, and `riskcast.api.app` including ingest router. Concurrent dedupe test added and passing.

---

### LOW

**L1.** Document highwater semantics (partition-wide at seal vs per-segment ledger_sequence) in ledger README or ADR.  
**L2.** Consider adding LedgerWriteError in writer docstring and type hints so all callers know to catch it.

---

## (D) Tests Run / Added

| Test | Location | Result |
|------|----------|--------|
| **Ledger crash-tail** | `tests/unit/infrastructure/test_ledger.py::test_ledger_crash_tail_returns_n_minus_1_valid_records` | **PASS** — Write 3 records, truncate segment after 2 frames; reader returns 2 valid records, no corrupted record. |
| **RiskCast concurrent ingest dedupe** | `tests/integration/test_riskcast_concurrent_ingest.py::test_concurrent_ingest_dedupe` | **PASS** — 20 concurrent POSTs same signal_id → 1×200, 19×409, original ack_id in 409; DB has exactly 1 row. |

**Commands:**

```bash
pytest tests/unit/infrastructure/test_ledger.py::test_ledger_crash_tail_returns_n_minus_1_valid_records -v --no-cov
pytest tests/integration/test_riskcast_concurrent_ingest.py -v --no-cov
```

**Other tests run:** Existing ledger, emitter, signal_store, reconcile_state unit tests (run as part of full suite).

---

## (E) Final Verdict

- **Safe to demo?** **Yes.** Ledger-first holds, reader handles crash-tail safely, RiskCast ingest dedupes under concurrency; mandatory tests pass.
- **Safe for production MVP?** **Conditional.** Before production MVP:
  1. **DONE:** C1 (LedgerWriteError from writer on OSError) and H1 (fsync for _CURRENT and manifest) — applied in this audit.
  2. **MUST fix or explicitly accept:** H2 — either implement partition-wide monotonic ledger_sequence or document that sequence is per-segment and highwater is the authority.
  3. **SHOULD fix:** M1 (timezone-aware UTC in SignalEvent).
- **Remaining patch list (priority):**
  1. H2 — Document or implement partition-wide ledger_sequence.
  2. M1 — Use `datetime.now(timezone.utc)` in SignalEvent factories.
