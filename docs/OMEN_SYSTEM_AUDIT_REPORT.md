# OMEN SYSTEM AUDIT REPORT

**Audit Date:** 2025-01-28  
**Auditor:** AI Systems Auditor (Senior Systems Auditor / Principal Data Engineer)  
**System Version:** Current codebase (post–integrity-audit fixes)  
**Scope:** Full stack (Backend `src/omen/`, Frontend `omen-demo/src/`, Integration)

---

## EXECUTIVE SUMMARY

**Overall Grade:** B- (78/100)  
**Production Readiness:** CONDITIONAL  
**Data Integrity Score:** 80/100  
**UI Quality Score:** 72/100  
**Architecture Score:** 82/100  

### Critical Findings

1. **Probability fallbacks can surface as “real” data**  
   When Polymarket omits `outcomePrices` / price fields, the mapper returns `0.5`; CLOB `get_midpoint` returns `0.5` on exception. Both are displayed without marking the value as missing or fallback. No circuit breaker or “NO DATA” when the source is degraded.

2. **Stats and activity use mock fallback in the UI**  
   When `/stats` or `/activity` fail or return empty, the frontend falls back to `systemStats` and `activityFeed` from `mockSignals.ts`. Those numbers (e.g. `events_processed: 12_847`, `events_per_second: 847`) are fabricated and can be shown while the header still suggests live data if signals came from the API.

3. **$1000 liquidity threshold is uncited**  
   Liquidity rule and `/live/process` use `min_liquidity=1000` with no referenced industry standard or internal policy. Acceptable for internal use; not acceptable for sellable “gold-standard” intelligence without documentation.

4. **Confidence components use hardcoded defaults**  
   `source_reliability_score` defaults to `0.85` in `OmenSignal.from_impact_assessment` and in `_confidence_breakdown_from_factors` when missing. Displayed as part of confidence breakdown without marking as default.

### Recommendations

1. **Eliminate silent probability fallbacks**  
   When mapper or CLOB cannot resolve price, either fail the event (no probability) or pass a structured “missing”/“fallback” flag so the UI can show “Probability unavailable” or “Data incomplete” instead of 50%.

2. **Never show mock stats/activity as live**  
   If `liveStats` or `liveActivity` is unavailable, show “Stats unavailable” / “Activity unavailable” and zeros or empty state. Do not substitute `systemStats` or `activityFeed` from `mockSignals.ts` when the user is in live mode.

3. **Document liquidity threshold**  
   Add a short rationale or reference (e.g. “Internal policy v1.0” or “Below typical noise floor for prediction markets”) and consider making it configurable per environment.

4. **Mark default confidence components**  
   When `source_reliability_score` or other factors are defaulted, expose a flag (e.g. `is_default`) or omit those components in the UI so the breakdown is not presented as fully observed.

---

## DETAILED FINDINGS

### 1. DATA INTEGRITY

#### 1.1 Data Sources

| Data Point | Source | Verified | Issues |
|------------|--------|----------|--------|
| Probability | Polymarket Gamma `outcomePrices` / `bestAsk` / `price` via mapper | ✅ | Mapper fallback `0.5` when all missing (`mapper.py:123`); no “missing” marker |
| Liquidity | Gamma API `liquidityNum` / `liquidity` in mapper | ✅ | Clear path to `RawSignalEvent.market.current_liquidity_usd` |
| Volume | Gamma API `volumeNum` / `volume` in mapper | ✅ | Same as above |
| Transit impact | `parameters.RED_SEA_PARAMS` + `red_sea_disruption.translate()` | ✅ | Sourced (Drewry 2024); formula `transit_days * prob`; uncertainty 7–14 from methodology |
| Fuel impact | Same params + rule | ✅ | Lloyd's List cited in parameters |
| Freight impact | Same params + rule | ✅ | Freightos cited; base/crisis by probability |
| Insurance impact | Same params + rule | ✅ | Lloyd's of London cited |
| Route coordinates | `live.py` `_LOCATIONS` / `_CHOKEPOINTS` | ⚠️ | Plausible lat/lng; static table, no external DB |
| Chokepoint list | Same | ⚠️ | risk_level from static table |
| Confidence score | Validation rule scores → `OmenSignal.from_impact_assessment` | ✅ | Mean of signal_strength, liquidity_score, validation_score |
| Probability history (API) | `get_signal_history_store().get_probability_series()` | ✅ | Real stored history; empty when none |
| Confidence breakdown (API) | `_confidence_breakdown_from_factors(score, s.confidence_factors)` | ✅ | From pipeline when present; `source_reliability` defaults to 0.85 |
| Metric projection (API) | Omitted | ✅ | `projection=[]` in `_enhance_metric` — no unsourced projection |
| Delay days (route) | `r.estimated_delay_days` from AffectedRoute | ✅ | From impact assessment |

**Score:** 80/100  
**Grade:** B  

#### 1.2 Processing Pipeline

| Stage | Documented | Sourced | Issues |
|-------|------------|---------|--------|
| Ingestion | ✅ | N/A | PolymarketLiveClient calls Gamma `/events`; circuit breaker, timeouts, rate-limit handling |
| Validation | ⚠️ | ⚠️ | Liquidity rule $1000 min uncited; geo/semantic/anomaly rules present |
| Translation | ✅ | ✅ | Red Sea rule uses `parameters.py` EvidenceRecords; methodology in `red_sea_impact.py`; onset/duration from TIMING_METHODOLOGY |
| Generation | ✅ | ✅ | OmenSignal.from_impact_assessment uses validation scores and assessment; confidence from factors |

**Score:** 82/100  
**Grade:** B  

#### 1.3 Evidence Quality

| Metric | Source Tier | Date | Uncertainty | Issues |
|--------|-------------|------|-------------|--------|
| Transit time | 1 (Drewry) | 2024-02 | ✅ Bounds in rule (7–14 days) | Implemented and cited |
| Fuel cost | 1 (Lloyd's List) | 2024-01 | ✅ In rule | EvidenceRecord in parameters |
| Freight rate | 2 (Freightos) | 2024-01 | ✅ In rule | Base/crisis by probability |
| Insurance | 1 (Lloyd's) | 2024-01 | ✅ In rule | EvidenceRecord in parameters |
| Onset/duration | Internal + historical | 2024-01 | ✅ TIMING_METHODOLOGY | Documented in red_sea_impact.py |

**Score:** 85/100  
**Grade:** B  

---

### 2. UI INTEGRITY

#### 2.1 Data Display

| Component | Live Data | Mock Fallback | Honest Display | Issues |
|-----------|-----------|---------------|----------------|--------|
| Signals | ✅ when API returns data | `mockSignals` only when `source.type === 'demo'` (error or no data yet) | ✅ | Demo vs live clearly separated in useDataSource |
| ProbabilityGauge | From selected signal | From mock when demo | ✅ | Value from signal |
| ConfidenceRadar | From API | From mock when demo | ⚠️ | When from API, `source_reliability` may be default 0.85 |
| Impact metrics | From API | From mock when demo | ✅ | No invented uncertainty; projection empty when unsourced |
| Stats (KPI row) | From `/stats` when `liveStats` present | **Fabricated** `systemStats` when `liveStats` null | ❌ | Mock stats shown in live mode if stats API fails or not yet loaded |
| Activity | From `/activity` when `liveActivity` present | **Fabricated** `activityFeed` when null/empty | ❌ | Mock activity in live mode when activity empty |
| Error state | N/A | N/A | ✅ | DataSourceBanner “Đang hiển thị dữ liệu demo” on API error |
| Empty state | ✅ | N/A | ✅ | “Không có tín hiệu…” when API returns []; no mock substitution for signals |

**Data flow (one signal):**  
Polymarket Gamma → LiveClient.fetch_events / get_logistics_events → Mapper.map_event → RawSignalEvent (probability from outcomePrices or 0.5 fallback) → Pipeline validates → ImpactTranslator (Red Sea rule + RED_SEA_PARAMS) → OmenSignal.from_impact_assessment → live._signal_to_full_response (history from store, breakdown from confidence_factors, routes from assessment, projection=[]) → mapApiSignalToUi → UI.

**Score:** 72/100  
**Grade:** C+  

#### 2.2 Real-Time

| Feature | Implemented | Working | Issues |
|---------|-------------|---------|--------|
| SSE connection | ✅ `/realtime/prices` | ✅ | Frontend opens SSE and POSTs `/realtime/subscribe` with signal IDs |
| Price updates | PriceStreamer + Polymarket WS | ✅ When tokens registered | Pipeline calls `register_signal(signal_id, token_id, …)` when generating signals; token_id from condition_token_id or clob_token_ids[0]. If Gamma omits these, real-time stays inactive for those signals |
| Live indicator | Header `isLive={dataSource.type === 'live'}` | ✅ | Tied to useDataSource; “TRỰC TIẾP” only when type is live |

**Score:** 75/100  
**Grade:** C+  

#### 2.3 Visual Quality

| Aspect | Meets Standard | Issues |
|--------|----------------|--------|
| Color consistency | ✅ | CSS variables, severity colors |
| Typography | ✅ | Clear hierarchy |
| Spacing / layout | ✅ | Grid and cards |
| Loading | ✅ | Spinner when loading and no signals |
| Error visibility | ✅ | Banner on backend failure; DataSourceBanner for demo |
| Empty vs mock | ✅ | Empty responses do not substitute mock signals; demo is explicit |

**Score:** 78/100  
**Grade:** C+  

---

### 3. ARCHITECTURE

#### 3.1 Data Flow

```
Polymarket Gamma API
    ↓
PolymarketLiveClient.fetch_events() / get_logistics_events()
    ↓
PolymarketMapper.map_event() → RawSignalEvent
    ↓
Pipeline: SignalValidator.validate() → ValidatedSignal
    ↓
Pipeline: ImpactTranslator.translate() → ImpactAssessment (RED_SEA_PARAMS, methodologies)
    ↓
Pipeline: OmenSignal.from_impact_assessment() → OmenSignal
    ↓  (pipeline also: history_store.record(), price_streamer.register_signal(), metrics.record_from_pipeline_result(), activity_logger calls)
    ↓
live._signal_to_full_response() — prob_history from store, confidence from factors, routes from assessment, projection=[]
    ↓
API Response → mapApiSignalToUi() → UI
```

**Issues:**

1. **Stats/activity fallback in UI**  
   When `liveStats` or `liveActivity` is null/empty, App uses `systemStats` and `activityFeed` from mockSignals. In live mode this presents fabricated numbers without a clear “Stats unavailable” or “Activity unavailable” state.

2. **Probability fallback semantics**  
   Mapper and CLOB use 0.5 when price is missing. Downstream and UI treat it as a normal value. No “missing” or “degraded source” indicator.

**Score:** 82/100  
**Grade:** B  

#### 3.2 Code Quality

| Aspect | Status | Issues |
|--------|--------|--------|
| Hardcoded “real” data in API | ✅ Largely resolved | Default 0.85 for source_reliability in confidence breakdown |
| Error handling | ✅ | Circuit breakers, DLQ, 503 on source failure |
| Documentation | ⚠️ | Red Sea rule and parameters documented; $1000 liquidity and 0.85 default not |
| Traceability | ✅ | explanation_chain, trace_id, ruleset_version, evidence_source on metrics |

**Score:** 80/100  
**Grade:** B  

---

## SPECIFIC ISSUES

### CRITICAL (Must fix before production)

1. **ISSUE-001: Stats/activity mock fallback in live mode**  
   - **Location:** `omen-demo/src/App.tsx` lines 77–85  
   - **Code:** `const stats = liveStats ? liveStats : systemStats`; `const activity = liveActivity?.length ? liveActivity : activityFeed`  
   - **Impact:** When stats or activity API fails or returns empty, UI shows fabricated numbers (e.g. 12_847 events, 847/s) while user may believe they are in live mode.  
   - **Fix:** When in live mode, if `liveStats` is null or request failed, show “Stats unavailable” and zeros or a dedicated empty state; do not use `systemStats`. Same for activity: use empty list and “Activity unavailable” instead of `activityFeed`.

2. **ISSUE-002: Probability 0.5 used as real value when source missing**  
   - **Location:** `src/omen/adapters/inbound/polymarket/mapper.py:123`; `src/omen/adapters/inbound/polymarket/clob_client.py:191,193`  
   - **Code:** `return 0.5` when outcomePrices/probability/bestAsk/price absent; CLOB returns 0.5 on midpoint exception  
   - **Impact:** 50% is displayed as if it were from the market. No way for UI or downstream to know the value is a fallback.  
   - **Fix:** Either omit probability and fail validation for “no price”, or add a flag (e.g. `probability_missing: bool`) and have API/UI show “Probability unavailable” or “Data incomplete” when set.

### HIGH (Should fix soon)

1. **ISSUE-003: Liquidity threshold $1000 uncited**  
   - **Location:** `src/omen/domain/rules/validation/liquidity_rule.py` default 1000; `api/routes/live.py` min_liquidity=1000  
   - **Impact:** Threshold has no referenced basis; weak for “sellable” or regulated use.  
   - **Fix:** Add a short rationale or reference (e.g. internal policy doc or benchmark) and consider env-driven config.

2. **ISSUE-004: source_reliability_score default 0.85**  
   - **Location:** `src/omen/domain/models/omen_signal.py:194`; `src/omen/api/routes/live.py:312`  
   - **Code:** `confidence_factors.setdefault("source_reliability_score", 0.85)`; `_f("source_reliability_score", 0.85)`  
   - **Impact:** Confidence breakdown shows 0.85 as if it were observed.  
   - **Fix:** When using default, either omit from breakdown in API/UI or add an `is_default` (or similar) so the UI can label or hide it.

3. **ISSUE-005: CLOB get_midpoint returns 0.5 on any exception**  
   - **Location:** `src/omen/adapters/inbound/polymarket/clob_client.py:179–193`  
   - **Impact:** Any CLOB error (timeout, 5xx, parse error) yields 0.5 with no logging or differentiation.  
   - **Fix:** Prefer raising or returning a dedicated “unavailable” result; do not return 0.5 as a silent fallback.

### MEDIUM (Should fix eventually)

1. **ISSUE-006: Transit uncertainty bounds hardcoded in rule**  
   - **Location:** `src/omen/domain/rules/translation/logistics/red_sea_disruption.py:107–110`  
   - **Code:** `UncertaintyBounds(lower=round(7*prob,1), upper=round(14*prob,1))`  
   - **Impact:** 7/14 align with methodology but are literals in the rule, not parameters.  
   - **Fix:** Source from TRANSIT_TIME_METHODOLOGY or RED_SEA_PARAMS so one place drives both value and bounds.

2. **ISSUE-007: BottomPanel “/phút” vs events_per_second**  
   - **Location:** `omen-demo/src/components/Layout/BottomPanel.tsx`; `omen-demo/src/lib/mapApiToUi.ts`  
   - **Impact:** Backend sends events_per_minute; frontend maps to events_per_second and label says “/phút” — confusing.  
   - **Fix:** Use one unit and label consistently (e.g. “sự kiện/phút” and pass through events_per_minute).

### LOW (Nice to have)

1. **ISSUE-008: Location/chokepoint tables static**  
   - **Location:** `src/omen/api/routes/live.py` `_LOCATIONS`, `_CHOKEPOINTS`  
   - **Impact:** Coordinates and risk levels are hardcoded; fine for demos, not a single source of truth for production geography.  
   - **Fix:** Consider loading from config or a geo service and versioning.

---

## FAKE DATA INVENTORY

| Location | Type | Value / Behavior | Should Be |
|----------|------|------------------|-----------|
| `App.tsx:77–80` | Mock fallback | `stats = liveStats ?? systemStats` | When live: show “unavailable” + zeros or empty state |
| `App.tsx:83–85` | Mock fallback | `activity = liveActivity?.length ? liveActivity : activityFeed` | When live: [] and “Activity unavailable” |
| `mockSignals.ts` (systemStats, activityFeed) | Mock | Static numbers and messages | Used only when source.type === 'demo' and never as “live” |
| `mapper.py:123` | Fallback | `return 0.5` when no price | Fail or tag as missing |
| `clob_client.py:191,193` | Fallback | `return 0.5` on error/missing | Raise or return “unavailable” |
| `omen_signal.py:194` | Default | `source_reliability_score=0.85` | Document or omit when defaulted |
| `live.py:312` | Default | `source_reliability=_f(..., 0.85)` | Same as above |

---

## CERTIFICATION

- [ ] **CERTIFIED FOR PRODUCTION** — System meets enterprise standards  
- [x] **CONDITIONALLY CERTIFIED** — Fix critical issues first  
- [ ] **NOT CERTIFIED** — Major rework required  
- [ ] **REJECTED** — Fundamental integrity issues  

**Auditor Notes:**

The **pipeline** is in strong shape: Polymarket Gamma → mapper → validation → Red Sea translation (EvidenceRecords + methodology) → OmenSignal. Probability, liquidity, and volume are from the API; impact metrics use cited parameters; confidence comes from validation; onset/duration use TIMING_METHODOLOGY. Probability history and confidence breakdown in the API are driven by stored history and pipeline confidence_factors. Route delay_days come from the impact assessment; metric projections are not fabricated.

**Remaining blockers for full “sellable” trust:**  
(1) **No mock stats/activity in live mode** — when stats or activity are unavailable, the UI must not show `systemStats` or `activityFeed`.  
(2) **Probability fallbacks** — 0.5 when price is missing or CLOB fails must not be shown as real data; either fail or mark clearly as “unavailable”.  
(3) **Document or parameterize** the $1000 liquidity threshold and the 0.85 source_reliability default so they are auditable.

**Real-time:** Pipeline registers `(signal_id, token_id)` when producing signals; token comes from condition_token_id or clob_token_ids. Real-time works when Gamma supplies those IDs. If it does not, the streamer simply has no mapping for that signal — no fake data.

**Recommended path:**  
Address ISSUE-001 and ISSUE-002, then document or adjust ISSUE-003 and ISSUE-004. After that, the system is in a position to be used for high-stakes logistics intelligence with clear, traceable data and honest presentation of defaults and fallbacks.
