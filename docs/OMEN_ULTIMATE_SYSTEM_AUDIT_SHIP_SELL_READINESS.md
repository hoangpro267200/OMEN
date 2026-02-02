# OMEN — Ultimate System Audit + Ship/Sell Readiness Report (Hardline)

**Date:** 2026-01-29  
**Scope:** Entire OMEN system as in repository today.  
**Standards:** Correctness, reliability, security, operability, competition-grade.

---

## (0) Executive Narrative (90 seconds)

- **OMEN** turns market and logistics events into **structured probability signals** that downstream systems (e.g. RiskCast) use for impact and decisions. OMEN does not make impact or recommendations.
- **Dual-path architecture:** Every signal is written to a **ledger first**, then pushed to the hot path (RiskCast ingest). If the hot path fails, **reconcile** replays from the ledger so **no signal is ever lost**.
- **Ledger** is append-only, crash-safe (WAL framing, fsync, atomic metadata). Power loss yields either old state or complete new state—never a corrupted mixed state.
- **RiskCast ingest** accepts signals with **exactly-once semantics**: duplicate `signal_id` gets 409 with the **original ack_id**; concurrent requests are safe (1× 200, rest 409).
- **Determinism:** `signal_id` and `trace_id` are derived from input hash and ruleset; same input → same IDs for audits and idempotency.
- **Time** is UTC end-to-end; partitioning is by `emitted_at` date with explicit late-partition handling.
- **Security:** API key auth, rate limiting, payload validation, redaction; secrets from env, no secrets in logs.
- **Evidence:** 40+ hardline checks below with file/function/test references; critical items have proof tests.

**One-liner:** *OMEN = ledger-first + reconcile = nothing lost.*

---

## (1) System Map

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                      OMEN (FastAPI)                      │
                    │  main.py → create_app()                                 │
                    │  Routes: /health, /api/v1/signals, /api/v1/live/*,     │
                    │          /api/v1/stats, /api/v1/activity, /api/ui       │
                    └───────────────────────────┬─────────────────────────────┘
                                                │
    ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
    │                                           │                                               │
    ▼                                           ▼                                               ▼
┌───────────────┐                    ┌─────────────────────┐                    ┌─────────────────────┐
│ Pipeline      │                    │ Ledger (Writer)      │                    │ Emitter              │
│ application/  │ ── OmenSignal ──►  │ infrastructure/      │ ── SignalEvent ──►  │ infrastructure/      │
│ pipeline.py   │                    │ ledger/writer.py     │                    │ emitter/             │
│ async_*.py    │                    │ WAL framing, fsync   │                    │ signal_emitter.py    │
└───────────────┘                    └──────────┬──────────┘                    └──────────┬──────────┘
                                                │                                           │
                                                │ base_path                                 │ POST ingest
                                                ▼                                           ▼
                                    ┌─────────────────────┐                    ┌─────────────────────┐
                                    │ Ledger Reader       │                    │ RiskCast (separate) │
                                    │ ledger/reader.py    │◄── reconcile job   │ riskcast/api/       │
                                    │ Crash-tail, CRC    │                    │ routes/ingest.py     │
                                    └────────────────────┘                    └──────────┬──────────┘
                                                                                         │
                                                                                         ▼
                                                                             ┌─────────────────────┐
                                                                             │ SignalStore          │
                                                                             │ signal_store.py     │
                                                                             │ aiosqlite, WAL       │
                                                                             └─────────────────────┘
                                                                                         │
                                    ┌─────────────────────┐                             │
                                    │ ReconcileStateStore  │◄───────────────────────────┘
                                    │ reconcile_state.py  │   (reconcile job writes state)
                                    └─────────────────────┘
```

**Entrypoints**

| Entrypoint | File | Purpose |
|------------|------|---------|
| OMEN API | `src/omen/main.py` | `uvicorn omen.main:app --reload` |
| RiskCast API | `src/riskcast/api/app.py` | Ingest + reconcile routes |
| Reconcile job | `src/riskcast/jobs/reconcile_job.py` | `python -m riskcast.jobs.reconcile_job` |
| Pipeline CLI | `pyproject.toml` scripts | `omen-pipeline` (if configured) |

**Key dependencies (pyproject.toml):** fastapi, uvicorn, pydantic, pydantic-settings, httpx, tenacity, pyjwt, filelock, aiosqlite; dev: pytest, pytest-asyncio, pytest-cov, hypothesis, black, ruff, mypy.

---

## (2) Formal Invariants & Guarantees

**Guaranteed**

1. **Ledger-first:** Signal is written to ledger before any hot-path push. Code: `SignalEmitter.emit()` writes via `self.ledger.write(event)` then `_push_to_riskcast()`. Test: `test_ledger_first_invariant_hot_path_fails`, `test_ledger_write_failure_returns_failed`.
2. **Crash consistency (ledger):** Atomic metadata via temp write + fsync(file) + rename + fsync(dir). Partial WAL frame is truncated by reader; no half-record returned. Tests: `test_atomic_write_text_fsync_order`, `test_partial_frame_truncation`, `test_ledger_crash_tail_returns_n_minus_1_valid_records`.
3. **Monotonic ledger_sequence:** Within a partition, across segments and restarts. Formula: `(segment_ordinal << 32) | record_index`. Test: `test_ledger_sequence_monotonic_across_rollover`.
4. **Exactly-once at ingest:** Dedupe by `signal_id` (PK); 409 returns original `ack_id`. Concurrent: 1× 200, rest 409. Test: `test_concurrent_ingest_dedupe`.
5. **Deterministic IDs:** `trace_id` = SHA256(event_id\|input_hash\|ruleset)[:16]; `signal_id` = "OMEN-" + trace_id[:12].upper(). Tests: `test_generate_deterministic_trace_id_*`, `test_signal_id_derived_from_trace_id`.
6. **UTC timestamps:** SignalEvent validators require timezone-aware; naive datetime rejected. Tests: `test_signal_event_naive_datetime_raises`, `test_signal_event_json_z_suffix_timezone_aware`.
7. **Partitioning:** By `emitted_at.date()`; late arrivals go to `{date}-late`. Writer: `_is_sealed()` + late partition dir; Reader: `read_partition(include_late=True)`.
8. **Reconcile only when allowed:** Main partition only if sealed; late partition allowed; `needs_reconcile` by highwater/status. Tests: `test_needs_reconcile_*`.

**Not guaranteed**

- **Exactly-once delivery to RiskCast:** At-least-once; duplicates handled by 409.
- **Ordering across partitions:** Order is per-partition; cross-partition order not defined.
- **Safe shutdown:** No explicit flush-on-SIGTERM in emitter/ledger (see Go/No-Go).
- **Circuit breaker on emitter:** Emitter has retry + backpressure but no circuit breaker in hot path (retry.py CircuitBreaker exists for sources).
- **Persistent DLQ:** Dead letter is in-memory; process restart loses DLQ entries.

---

## (3) Hardline PASS/FAIL Matrix (≥40 checks)

| # | Category | Check | Severity | Status | Evidence | Fix recommendation |
|---|----------|-------|----------|--------|----------|--------------------|
| 1 | Durability | File durability: temp write + fsync(file) + rename + fsync(dir) | CRITICAL | PASS | `writer.py` `_atomic_write_text()` L56–79; `test_atomic_write_text_fsync_order` | None |
| 2 | Durability | fsync on segment append | CRITICAL | PASS | `writer.py` `_append_framed_record()` L181–183 `f.flush(); os.fsync(f.fileno())` | None |
| 3 | Ledger | Partial header at tail truncated, no crash | CRITICAL | PASS | `reader.py` L161–166; `test_partial_frame_truncation` | None |
| 4 | Ledger | Partial payload at tail truncated | CRITICAL | PASS | `reader.py` L172–178; `test_ledger_crash_tail_returns_n_minus_1_valid_records` | None |
| 5 | Ledger | CRC mismatch: log and skip record | HIGH | PASS | `reader.py` L183–192 `continue`; no test that asserts skip count | Add test: corrupt one record CRC, assert N-1 returned |
| 6 | Ledger | Manifest highwater_sequence / total_records | HIGH | PASS | `writer.py` `_create_manifest()` L352–376; reader uses it in `_get_partition_info` | None |
| 7 | Ledger | manifest_revision policy | MEDIUM | PARTIAL | Writer always writes `manifest_revision: 1`; `needs_reconcile()` ignores revision (comment L216). Stored in state. | Document: "revision not used for needs_reconcile; highwater only" or remove from manifest |
| 8 | Ledger | ledger_sequence monotonic across rollover/restart | CRITICAL | PASS | `writer.py` L139–141; `test_ledger_sequence_monotonic_across_rollover` | None |
| 9 | Ledger | Partition seal: _SEALED + chmod 444 segments | HIGH | PASS | `writer.py` `_seal_partition_impl()` L326–347; `get_partitions_to_seal()` L381–419 | None |
| 10 | Ledger | Late partition routing (emitted after seal) | HIGH | PASS | `writer.py` L121–126 `_is_sealed` → `{date}-late` | None |
| 11 | Ledger | Reader query by time range (emitted_at) | HIGH | PASS | `reader.py` `query_by_time_range()` L265–285; `test_query_by_time_range` | None |
| 12 | Ledger | Reader query by trace_ids | MEDIUM | PASS | `reader.py` `query_by_trace_ids()` L287–304; `test_query_by_trace_ids` | None |
| 13 | Ledger | Reader query by category | MEDIUM | PASS | `reader.py` `query_by_category()` L306–322; `test_query_by_category` | None |
| 14 | Emitter | Ledger-first: write before hot path | CRITICAL | PASS | `signal_emitter.py` L161–166 then L184–211; `test_ledger_first_invariant_hot_path_fails` | None |
| 15 | Emitter | Ledger write failure → FAILED, no hot path | CRITICAL | PASS | `test_ledger_write_failure_returns_failed` | None |
| 16 | Emitter | Retry/backoff on hot path | HIGH | PASS | `RetryConfig`, `_push_to_riskcast()` loop, `_wait_before_retry()`; `test_retry_config_used` | None |
| 17 | Emitter | 409 → DUPLICATE, ledger already written | HIGH | PASS | `signal_emitter.py` L247–252; `test_duplicate_when_riskcast_returns_409` | None |
| 18 | Emitter | HTTP client timeout | HIGH | PASS | `signal_emitter.py` L125 `httpx.AsyncClient(timeout=30.0)` | None |
| 19 | Emitter | Idempotency key (X-Idempotency-Key = signal_id) | HIGH | PASS | `signal_emitter.py` L276; RiskCast ingest uses signal_id for dedupe | None |
| 20 | Emitter | Backpressure after consecutive failures | MEDIUM | PASS | `BackpressureController`, `record_failure`/`wait_if_needed`; `test_backpressure_record_success_resets_failures` | None |
| 21 | Emitter | Circuit breaker on hot path | MEDIUM | PASS | `resilience/circuit_breaker.py`; emitter wraps hot path with CircuitBreaker; LEDGER_ONLY when open; `test_ledger_only_when_circuit_open` | None |
| 22 | RiskCast | Ingest: persist then 200; duplicate → 409 + original ack_id | CRITICAL | PASS | `ingest.py` store then return; IntegrityError → get_by_signal_id, 409 with ack_id; `test_concurrent_ingest_dedupe` | None |
| 23 | RiskCast | SignalStore busy_timeout | HIGH | PASS | `signal_store.py` L53 `PRAGMA busy_timeout=10000`; L139 in store() | None |
| 24 | RiskCast | Concurrent dedupe: 1× 200, rest 409, same ack_id | CRITICAL | PASS | `test_concurrent_ingest_dedupe` (20 concurrent, 19× 409, DB 1 row) | None |
| 25 | Reconcile | needs_reconcile: never / highwater increased / status != COMPLETED | HIGH | PASS | `reconcile_state.py` L202–218; tests `test_needs_reconcile_*` | None |
| 26 | Reconcile | Reconcile only sealed main partitions; late allowed | HIGH | PASS | `reconcile_job.py` L199–208 (main not sealed → SKIPPED) | None |
| 27 | Reconcile | Partial failure: save state, report failed_ids | HIGH | PASS | `reconcile_job.py` L286–296, save_state with status PARTIAL | None |
| 28 | Reconcile | Replay uses X-Idempotency-Key and X-Replay-Source | MEDIUM | PASS | `reconcile_job.py` L337–345 | None |
| 29 | Schema | SignalEvent schema_version 1.0.0 | MEDIUM | PASS | `signal_event.py` SCHEMA_VERSION, LedgerRecord.create/verify | None |
| 30 | Schema | Schema evolution (SCHEMA_VERSION) | LOW | PARTIAL | Constant present; no versioned read path or migration doc | Add doc: forward-compat strategy (ignore unknown fields) and test |
| 31 | Migration | SQLite table creation IF NOT EXISTS | MEDIUM | PASS | `signal_store.py` L55–84; `reconcile_state.py` L59–93 | Add migration story for new columns if needed |
| 32 | API | Input validation / error codes | HIGH | PASS | Ingest: `SignalEvent.model_validate` → 400 on error; auth → 401; rate limit → 429 | None |
| 33 | API | Payload validation (Pydantic) | HIGH | PASS | Ingest uses `SignalEvent.model_validate(await request.json())` | None |
| 34 | Logging | No PII in logs (no API key/body dump) | HIGH | PASS | Auth uses compare_digest; logs use signal_id/partition, not body | Add explicit redaction test for logs |
| 35 | Logging | Trace correlation (trace_id in context) | MEDIUM | PARTIAL | trace_id in model; no middleware that injects trace_id into log context | Add request-scoped trace_id to logging |
| 36 | Perf | Segment rollover thresholds (10MB, 10k records) | LOW | PASS | `writer.py` MAX_SEGMENT_SIZE_BYTES, MAX_SEGMENT_RECORDS; `test_rollover_creates_new_segment` | None |
| 37 | Cost | Ledger growth (append-only, partition per day) | LOW | PARTIAL | No retention/compaction; seal prevents new writes | Document retention policy and add seal job |
| 38 | Ops | How to run: uvicorn, reconcile job | MEDIUM | PASS | README/main.py; reconcile_job `if __name__ == "__main__"` | Add one-line runbook to README |
| 39 | Ops | Deploy: Docker / env | MEDIUM | PARTIAL | docker-compose exists but only commented postgres/kafka | Add Dockerfile for OMEN + RiskCast and env matrix |
| 40 | Safe shutdown | Flush on SIGTERM | HIGH | PASS | Lifespan shutdown: drain requests, flush writers, close emitters; /health and /ready return 503 when shutting down. `main.py` lifespan, `test_graceful_shutdown.py` | None |
| 41 | Security | API key auth on protected routes | HIGH | PASS | `main.py` Depends(verify_api_key) on signals/explanations; `test_auth` (unit) | None |
| 42 | Security | Rate limiting | MEDIUM | PASS | `rate_limit_middleware`, TokenBucketRateLimiter; `test_rate_limit` | None |
| 43 | Security | Secrets from env, not in logs | HIGH | PASS | SecurityConfig api_keys from env; auth does not log key | None |

---

## (4) Failure Modes & Blast Radius

| Failure | Blast radius | Detection | Recovery |
|---------|--------------|-----------|----------|
| Ledger disk full | New writes fail (LedgerWriteError); hot path not attempted | Emitter returns FAILED; logs | Free space; retry emit (idempotent if re-run same signal) |
| Ledger power loss mid-append | Last frame may be partial | Next read: partial header/payload → truncate | Reader returns only complete records; reconcile replays from ledger |
| RiskCast ingest down | Emitter returns LEDGER_ONLY | Logs "Hot path failed (will reconcile)" | Reconcile job replays missing signals from ledger |
| RiskCast DB locked | Ingest 500 or timeout; PRAGMA busy_timeout=10s | Client retries (emitter) or 409 on duplicate | Retry; concurrent dedupe keeps 1 row |
| Duplicate signal_id (concurrent) | None | 409 with original ack_id | Idempotent; clients can treat 409 as success |
| OMEN API key missing/invalid | 401 on /api/v1/signals | Client error | Set OMEN_SECURITY_API_KEYS |
| Reconcile job crash mid-partition | State may be PARTIAL/FAILED | needs_reconcile true for status != COMPLETED | Re-run job; replay idempotent (409) |
| Process kill (no graceful shutdown) | In-flight emit: ledger may have written, hot path not | Reconcile finds missing and replays | Reconcile recovers |
| Segment rollover chmod failure (e.g. Windows) | Logged, segment still writable | Logger; possible double-write to same segment if limits exceeded | Prefer Linux for production or document Windows behavior |

---

## (5) Proof Pack (tests, commands, simulations)

**Run all tests**
```bash
cd /path/to/OMEN
pip install -e ".[dev]"
pytest tests/ -v --tb=short
```

**Run critical subset (ledger + emitter + ingest + reconcile state)**
```bash
pytest tests/unit/infrastructure/test_ledger.py tests/unit/infrastructure/test_emitter.py tests/unit/test_signal_store.py tests/unit/test_reconcile_state.py tests/integration/test_riskcast_concurrent_ingest.py -v --tb=short
```

**Key test ↔ guarantee**

| Test (file) | Guarantee |
|-------------|-----------|
| `test_ledger_first_invariant_hot_path_fails` | Ledger-first: hot path fail → LEDGER_ONLY |
| `test_ledger_crash_tail_returns_n_minus_1_valid_records` | Crash-tail: N writes, truncate → N-1 valid |
| `test_ledger_sequence_monotonic_across_rollover` | Monotonic ledger_sequence across rollover and restart |
| `test_atomic_write_text_fsync_order` | fsync before replace, then fsync dir |
| `test_concurrent_ingest_dedupe` | 20 concurrent same signal_id → 1× 200, 19× 409, 1 row in DB |
| `test_needs_reconcile_highwater_increased` | Highwater increase triggers re-reconcile |
| `test_needs_reconcile_manifest_revision_ignored` | manifest_revision not used for needs_reconcile |
| `test_signal_event_naive_datetime_raises` | UTC required on SignalEvent |
| `test_generate_deterministic_trace_id_same_input_same_output` | Deterministic trace_id |
| `test_signal_id_derived_from_trace_id` | signal_id = OMEN- + trace_id[:12].upper() |

**Simulation: crash-tail**
1. Write 3 events to ledger.
2. Truncate segment after 2 full frames (binary).
3. Read partition with validate=True.
4. Expected: 2 events, both valid; third omitted.  
Test already: `test_ledger_crash_tail_returns_n_minus_1_valid_records`.

**Simulation: concurrent dedupe**
1. Start RiskCast app with temp DB.
2. Fire 20 concurrent POST /api/v1/signals/ingest with same body.
3. Expected: 1× 200 with ack_id A, 19× 409 with ack_id A; DB has exactly 1 row for that signal_id.  
Test: `test_concurrent_ingest_dedupe`.

---

## (6) Production Readiness Checklist — Go/No-Go

**Verdict: GO** (with gating items below that must be fixed before ship)

**Gating items (must fix before ship)**

1. **Safe shutdown:** ~~Implement flush-on-SIGTERM or lifespan shutdown~~ **DONE (B1).** Lifespan shutdown: drain in-flight requests (30s timeout), flush registered ledger writers, close registered emitters. Signal handlers (Unix) set shutdown event so /health and /ready return 503. Evidence: `src/omen/main.py` lifespan + `graceful_shutdown`, `tests/unit/test_graceful_shutdown.py`.
2. **Circuit breaker or doc:** ~~Either add circuit breaker~~ **DONE (B2).** Circuit breaker on emitter hot path: opens after 5 consecutive failures (or 50% failure rate in 60s window), 30s timeout, HALF_OPEN probe; LEDGER_ONLY when open. Evidence: `src/omen/infrastructure/resilience/circuit_breaker.py`, `signal_emitter.py` integration, `tests/unit/infrastructure/resilience/test_circuit_breaker.py`, `test_ledger_only_when_circuit_open`.

**Strongly recommended**

3. Document manifest_revision: "highwater only for needs_reconcile; revision stored for audit."
4. Add one-page runbook: how to run OMEN + RiskCast, run reconcile job, check seal, check highwater.
5. Add retention policy for ledger (e.g. seal job schedule, delete partitions older than X days if desired).

**Acceptable risks (documented)**

- At-least-once delivery to RiskCast (409 dedupe is acceptable).
- In-memory DLQ (restart loses entries); acceptable for v1 if pipeline failures are rare and logged.
- Windows: fsync(dir) may warn; chmod 444 may no-op; acceptable for dev only.
- Reconcile job not wired in CI; run manually or via cron.

---

## (7) Security & Compliance Review

**Threat model (concise)**

| Threat | Mitigation | Gap |
|--------|------------|-----|
| Unauthorized API access | API key (X-API-Key), verify_api_key | Key rotation not automated |
| Injection (XSS, etc.) | Pydantic validation; sanitize_string / DANGEROUS_PATTERNS in validation.py | Ingest body is JSON→SignalEvent; no raw HTML in contract |
| SSRF | Outbound HTTP to configured RiskCast URL only | Document: do not put user-controlled URL in config |
| Replay of ingest request | Idempotency by signal_id; 409 returns same ack_id | Replay within idempotency window is safe by design |
| Tampering (ledger) | CRC per frame; reader validates | No HMAC on file; acceptable for append-only local storage |
| Secrets in logs | No API key or body in logs; SecretStr for JWT | Add test that log output does not contain api_keys |
| Rate limiting | Token bucket per client (API key or IP) | Per-key limits documented in config |

**Secrets:** From env (OMEN_SECURITY_API_KEYS, etc.); pydantic-settings; no secrets in code or logs.

**Data protection:** Ledger and RiskCast DB are local; no encryption at rest in code (rely on FS/volume). Least privilege: DB files should be restricted to app user.

**Supply chain:** Dependencies in pyproject.toml with version ranges; no lock file in repo. Recommendation: pin versions or use pip-tools/poetry lock; add CVE scan in CI (e.g. pip-audit or Dependabot).

---

## (8) Observability & Operability

**Logging:** Python logging; debug/info/warning/error. No structured JSON logger by default; no request-scoped trace_id in log context (partial).

**Metrics:** Pipeline metrics in `infrastructure/metrics/pipeline_metrics.py`; not wired to Prometheus/OpenTelemetry in main app. Stats endpoint `/api/v1/stats` returns events_processed etc.

**Traces:** trace_id and signal_id in model; no distributed tracing (e.g. OpenTelemetry) in code.

**SLOs (proposed):**  
- Ledger write success rate ≥ 99.9% (excluding disk full).  
- Ingest 409/200 idempotent behavior 100%.  
- Reconcile completion for sealed partitions within 1 run; partial allowed with alert.

**Runbooks (short):**

- **Ledger full:** Free space; retry; if same signal re-emitted, idempotent at ingest.
- **RiskCast 5xx:** Emitter returns LEDGER_ONLY; run reconcile job after recovery.
- **Reconcile PARTIAL:** Check failed_ids; fix ingest (e.g. schema); re-run job.
- **Seal partitions:** Call `LedgerWriter.get_partitions_to_seal()` and `seal_partition()` (e.g. cron); or add seal job.

---

## (9) Scalability & Performance

**Limits (today):**

- Ledger: single writer per partition (FileLock); segment 10MB / 10k records; rollover creates new segment.
- Ingest: SQLite with WAL; busy_timeout 10s; one DB file.
- Emitter: single-threaded async; one HTTP client; backpressure after 5 consecutive failures.
- Reconcile: sequential per partition; max_replay_batch 100 per partition.

**Bottlenecks:** Disk I/O (fsync every append); SQLite write contention under high concurrency; reconcile scans full partition.

**Load test plan (proposed):**

1. Ledger: 10k writes, measure throughput and rollover; then reader full scan.
2. Ingest: 100 concurrent distinct signal_ids, then 50 concurrent same signal_id (expect 1× 200, 49× 409).
3. Reconcile: partition with 1k ledger signals, 100 already processed; measure time and replay count.

---

## (10) Data Integrity & Exactly-once Semantics (end-to-end)

- **Producer (OMEN pipeline → Emitter):** Each signal emitted once per pipeline run; duplicate run can produce same signal_id (deterministic) and re-emit → ingest sees duplicate → 409.
- **Ledger:** Append-only; no update/delete; crash-tail truncation preserves only complete records.
- **Consumer (RiskCast ingest):** One row per signal_id (PK); first insert wins, rest get IntegrityError → 409 with original ack_id. So at consumer boundary: **exactly-once semantics** (1 row per logical signal).
- **Reconcile:** Replay is idempotent (same signal_id → 409); no double-apply.

End-to-end: **at-least-once** from OMEN to RiskCast; **exactly-once** in RiskCast store.

---

## (11) Cost Model (compute, storage, network) + Tuning

**Compute:** One process per OMEN API; one per RiskCast API; one reconcile job (cron or worker). CPU bound by pipeline and JSON; I/O by fsync.

**Storage:** Ledger: ~1–10 KB per event (JSON); 10MB per segment; retention = all partitions unless policy. RiskCast SQLite: row per signal + signal_data JSON. Tuning: MAX_SEGMENT_SIZE_BYTES, MAX_SEGMENT_RECORDS; retention/archive for old partitions.

**Network:** Emitter → RiskCast POST per signal; reconcile replays over HTTP. Tuning: batch replay (current batch size max_replay_batch), or keep single-event POST for simplicity.

**Knobs:** SEAL_GRACE_PERIOD_HOURS, LATE_SEAL_GRACE_DAYS, retry_config (max_attempts, base_delay_ms, max_delay_ms), rate_limit_requests_per_minute, busy_timeout.

---

## (12) Roadmap

**Sellable v1 in 7 days**

1. **Safe shutdown (gating):** Lifespan or signal handler: flush ledger, wait in-flight emit (e.g. 10s), then exit.
2. **Runbook:** One-page: start OMEN, start RiskCast, run reconcile, verify with one partition.
3. **Manifest revision:** Document "highwater only" or remove revision from needs_reconcile logic.
4. **Seal job:** Script or cron that calls get_partitions_to_seal + seal_partition.
5. **Env matrix:** Document OMEN_*, RiskCast, and reconcile env vars for dev/stage/prod.
6. **Pin deps:** Lock file or pinned versions; add pip-audit or similar in CI.

**Competition God Mode in 48 hours**

1. **Hero moment:** One screen: "Ledger count" vs "RiskCast processed" for today’s partition; button "Run Reconcile" → show "Replayed N" or "Up to date." Proves no signal lost.
2. **Proof-first UI:** Links from UI to test names or log snippets (e.g. "Concurrent dedupe: test_concurrent_ingest_dedupe").
3. **Deterministic demo:** Seed or fixed data path so same run shows same signal_ids and counts; no live Polymarket required for demo.
4. **Timeboxed runbook:** 5-min script: start both APIs, emit 5 signals, kill RiskCast, emit 2 more, run reconcile, show 7 in RiskCast.
5. **Fallback:** If network fails, show "Ledger-only" counts and "Reconcile will recover" message; optional offline ledger browser (read-only).

---

## (13) Appendix: Code References & Diffs Needed

**File paths and main functions**

| Component | File | Key functions |
|-----------|------|----------------|
| SignalEvent | `src/omen/domain/models/signal_event.py` | SignalEvent, LedgerRecord.create/verify, generate_input_event_hash, SCHEMA_VERSION |
| Ledger writer | `src/omen/infrastructure/ledger/writer.py` | LedgerWriter.write, _append_framed_record, _atomic_write_text, _create_manifest, seal_partition |
| Ledger reader | `src/omen/infrastructure/ledger/reader.py` | LedgerReader.read_partition, _read_segment, get_partition_highwater, query_by_* |
| Emitter | `src/omen/infrastructure/emitter/signal_emitter.py` | SignalEmitter.emit, _push_to_riskcast, BackpressureController |
| SignalStore | `src/riskcast/infrastructure/signal_store.py` | store, get_by_signal_id, list_processed_ids |
| ReconcileStateStore | `src/riskcast/infrastructure/reconcile_state.py` | needs_reconcile, get_state, save_state |
| Ingest | `src/riskcast/api/routes/ingest.py` | ingest_signal (POST /signals/ingest) |
| Reconcile job | `src/riskcast/jobs/reconcile_job.py` | ReconcileJob.reconcile_partition, run, _replay_signal |
| OmenSignal IDs | `src/omen/domain/models/omen_signal.py` | _generate_deterministic_trace_id, from_validated_event (signal_id/trace_id) |
| Config | `src/omen/config.py`, `src/omen/infrastructure/security/config.py` | OmenConfig, SecurityConfig |
| Auth / rate limit | `src/omen/infrastructure/security/auth.py`, `rate_limit.py` | verify_api_key, rate_limit_middleware |

**Diffs / changes suggested**

1. **Safe shutdown:** In `main.py` lifespan or new shutdown handler: get ledger reference if any (e.g. from app state), call flush or wait; same for emitter in-flight. If emitter is created per-request, document "in-flight requests may get connection closed."
2. **Circuit breaker (optional):** In `signal_emitter.py`, wrap `_push_to_riskcast` with a CircuitBreaker from retry.py; open after N failures; half-open probe. Or add comment: "Backpressure only; circuit breaker not used."
3. **ReconcileStateStore.needs_reconcile:** Comment or code: "manifest_revision is not used; highwater and status only."
4. **Logging:** Add middleware or context that sets trace_id (from request header or first signal in request) for the request scope so logs can be correlated.

---

*End of report. Evidence and code references are from repository state as of 2026-01-29.*
