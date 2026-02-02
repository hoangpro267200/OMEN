# OMEN 5-Minute Demo Script — “Ledger-First, Nothing Lost”

**Goal:** Show that signals are written to the ledger first; if hot path (API/emit) fails, reconcile can replay from ledger so nothing is lost.

---

## Prerequisites

- Backend: `uvicorn omen.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend (optional): `cd omen-demo && npm run dev`
- Ledger dir writable (e.g. `.demo/ledger` or env `OMEN_LEDGER_BASE_PATH`)

---

## Scene 1 — Happy path (≈1 min)

1. **Health:** `GET /health/` → 200, `"status":"ok"`.
2. **Live stats:** `GET /api/v1/stats/live` (or equivalent) → polymarket_status, counts.
3. **Trigger pipeline** (stub or polymarket): run `python -m scripts.run_pipeline --source stub --limit 5`.
4. **Show ledger:** list partition dir (e.g. `.demo/ledger/YYYY-MM-DD/`) and confirm segment file(s) (e.g. `signals-001.wal` or similar).

**Talking point:** “Every signal is appended to the ledger first; then emitted. Ledger is the source of truth.”

---

## Scene 2 — Failure: hot path down (≈2 min)

1. **Stop or mock failure** of emit path (e.g. disconnect webhook, or use a failing publisher).
2. **Run pipeline again** (or send ingest): signals still **written to ledger** (ledger-first).
3. **Show:** Ledger partition has new writes; emit may fail (e.g. 503), but **data is in ledger**.
4. **Reconcile:** Trigger reconcile job (or endpoint) that reads from ledger and retries emit.
5. **Show:** After reconcile, downstream has events; ledger and downstream consistent.

**Talking point:** “When emit fails, we don’t lose data — it’s in the ledger. Reconcile replays and catches up.”

---

## Scene 3 — Proof UI (≈1 min)

1. Open Proof UI (or dashboard) that shows **ledger count** vs **processed/emitted count**.
2. After Scene 2, show **gap** (ledger &gt; processed) before reconcile.
3. Run reconcile; show counts **converge** (or “nothing lost” message).

**Talking point:** “One screen: ledger vs processed; one button: reconcile. Nothing lost.”

---

## Checklist (competition / ship)

- [ ] Health and (if present) /ready return 200 when up.
- [ ] Ledger dir exists and grows when pipeline runs.
- [ ] Kill or fail emit → ledger still grows; reconcile recovers.
- [ ] Proof UI (or equivalent) shows ledger vs processed and reconcile CTA.
- [ ] 5 min total; no data loss narrative clear.

---

## Runbook refs

- Runbooks: `docs/runbooks/README.md`
- Deployment: `docs/deployment.md`
- Ledger seal/partition: `docs/runbooks/partition-seal.md` (if present).
