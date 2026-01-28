# OMEN SYSTEM AUDIT REPORT — ENTERPRISE DATA INTEGRITY

**Audit Date:** 2025-01-28  
**Auditor:** AI Systems Auditor (Senior Systems Auditor / Principal Data Engineer)  
**System Version:** Current main branch  
**Scope:** Full stack (Backend `src/omen/`, Frontend `omen-demo/src/`, Integration)

---

## EXECUTIVE SUMMARY

**Overall Grade:** C (62/100)  
**Production Readiness:** NOT READY  
**Data Integrity Score:** 58/100  
**UI Quality Score:** 52/100  
**Architecture Score:** 72/100  

### Critical Findings

1. **Fabricated or unsourced data is injected in the live API response layer**  
   The `/live/process` response is enriched with synthetic `probability_history`, synthetic confidence breakdowns, unsourced metric projections, and a `delay_days = severity * 10` formula. These are presented to the UI as if they were pipeline outputs and are not traceable to Polymarket or to cited methodology.

2. **Stats and activity endpoints return hardcoded or demo data**  
   System stats (`/stats`) use hardcoded values (e.g. `avg_confidence=0.78`, `total_risk_exposure=2_500_000`, `system_latency_ms=12`, `polymarket_events_per_min=847`). The pipeline never calls `record_processing()`, so counts stay at zero while other fields are fabricated. The activity feed is pre‑populated with demo messages and is never written by the live pipeline.

3. **Real-time price streaming cannot work in production**  
   `PriceStreamer` maps updates by `signal_id → token_id`, but `register_signal(signal_id, token_id, ...)` is never called. The UI subscribes with OMEN signal IDs; the streamer has an empty mapping, so no Polymarket token is ever subscribed and no real-time updates reach the UI.

### Recommendations

1. **Remove all synthesis in live response building**  
   In `api/routes/live.py`:  
   - Do not fabricate `probability_history`; return only what the pipeline stores or leave empty and let the UI show “No history”.  
   - Do not build confidence breakdown from `hash(signal_id)`; use actual validation/translation outputs or omit.  
   - Do not add `_metric_projection(...)`; drop projection or compute it from a documented, sourced methodology.  
   - Replace `delay_days = severity * 10` with values from the impact assessment (e.g. `estimated_delay_days`).

2. **Wire pipeline outcomes into stats and activity**  
   Call `record_processing()` (or equivalent) from the pipeline on each processed batch, and use real metrics for avg_confidence, risk_exposure, and latency. Populate the activity feed via `log_activity()` from the pipeline so the UI shows real processing events.

3. **Fix or honestly label real-time**  
   Either register `(signal_id, token_id)` when building signals (using condition tokens from Polymarket) and document the flow, or remove/disable the “LIVE” real-time claim and document that updates are poll-based only.

---

## DETAILED FINDINGS

### 1. DATA INTEGRITY

#### 1.1 Data Sources

| Data Point | Source | Verified | Issues |
|------------|--------|----------|--------|
| Probability | Polymarket Gamma (outcomePrices / market fields) via mapper | ✅ | Mapper fallback to 0.5 when missing; no use of CLOB for live price in main flow |
| Liquidity | Gamma API `liquidityNum` / `liquidity` in mapper | ✅ | Clear path from API to RawSignalEvent.market.current_liquidity_usd |
| Volume | Gamma API `volumeNum` / `volume` in mapper | ✅ | Same as above |
| Transit impact | `parameters.RED_SEA_PARAMS` + `red_sea_disruption.translate()` | ✅ | Sourced (Drewry, etc.); formula `transit_days * prob` with 7–14 day uncertainty |
| Fuel impact | Same params + rule | ✅ | Lloyd's List cited in parameters |
| Freight impact | Same params + rule | ✅ | Freightos cited |
| Insurance impact | Same params + rule | ✅ | Lloyd's of London cited |
| Route coordinates | `live.py` `_LOCATIONS` / `_CHOKEPOINTS` | ⚠️ | Hardcoded but plausible lat/lng; no DB or external source |
| Chokepoint list | Same | ⚠️ | Hardcoded; risk_level not from external source |
| Confidence score | Validation rule scores → `OmenSignal.from_impact_assessment` | ✅ | Mean of signal_strength, liquidity_score, validation_score |
| Probability history (API) | **Synthetic** in `_signal_to_full_response` | ❌ | `prob_history = [round(prob * (0.92 + 0.08*i/24), 4) for i in range(24)]` — fabricated |
| Confidence breakdown (API) | **Synthetic** in `_confidence_breakdown()` | ❌ | Derived from `hash(signal_id)`; not from validation/translation |
| Metric projection (API) | **Synthetic** in `_metric_projection()` | ❌ | `current_value * (1 - exp(-d/2))` — no cited methodology |
| Delay days (route) | **Arbitrary** in `_route_coords()` | ❌ | `delay_days = severity * 10` — not from assessment |

**Score:** 58/100  
**Grade:** D  

#### 1.2 Processing Pipeline

| Stage | Documented | Sourced | Issues |
|-------|------------|---------|--------|
| Ingestion | ✅ | N/A | PolymarketLiveClient calls Gamma `/events`; circuit breaker and timeouts in place |
| Validation | ⚠️ | ⚠️ | Liquidity rule uses $1000 min; no cited benchmark. Other rules (geo, semantic, anomaly) exist but see prior audit for compatibility |
| Translation | ✅ | ✅ | Red Sea rule uses `parameters.py` EvidenceRecords and get_param(); assumptions listed |
| Generation | ✅ | ✅ | OmenSignal.from_impact_assessment uses validation scores and assessment fields |

**Translation details:**  
- Red Sea: transit 7–14 days (params), fuel/insurance/freight from RED_SEA_PARAMS, probability-scaled.  
- impact_translator hardcodes `expected_onset_hours=24`, `expected_duration_hours=720` with no source.

**Score:** 70/100  
**Grade:** C  

#### 1.3 Evidence Quality

| Metric | Source Tier | Date | Uncertainty | Issues |
|--------|-------------|------|-------------|--------|
| Transit time | 1 (Drewry) | 2024-02 | ✅ Bounds in rule | Implemented in rule and params |
| Fuel cost | 1 (Lloyd's List) | 2024-01 | ✅ In rule | EvidenceRecord in parameters |
| Freight rate | 2 (Freightos) | 2024-01 | ✅ In rule | Base/crisis split by probability |
| Insurance | 1 (Lloyd's) | 2024-01 | ✅ In rule | EvidenceRecord in parameters |

Impact metrics produced by the **pipeline** (Red Sea rule and parameters) are Tier 1/2 and cite sources.  
The **live API** then overwrites or adds unsourced constructs (projections, synthetic history, synthetic confidence breakdown, severity-based delay_days).

**Score:** 72/100 (pipeline only); degraded by API-layer fabrication.  
**Grade:** C  

---

### 2. UI INTEGRITY

#### 2.1 Data Display

| Component | Live Data | Mock Fallback | Honest Display | Issues |
|-----------|-----------|---------------|----------------|--------|
| SignalFeed / Main | ✅ when API returns signals | Uses `mockSignals` when `liveSignals` empty | ⚠️ | If API returns 200 with `[]`, UI shows mock data but `isLive` can remain true (no error) — user may see “LIVE” with demo data |
| ProbabilityGauge | From API | From mock | ✅ | Value comes from selected signal |
| ConfidenceRadar | From API | From mock | ⚠️ | When from API, breakdown is the synthetic one from `_confidence_breakdown` |
| Impact metrics | From API | From mock | ⚠️ | Projections are unsourced when from API |
| Error state | N/A | N/A | ✅ | Banner “Đang hiển thị dữ liệu demo” when backend fails |

**Data flow:**  
- Probability: API → mapApiSignalToUi → ProcessedSignal.probability ✅  
- Transit/etc.: API metrics (which include fabricated projection and possibly fabricated uncertainty in enhancement) → UI ✅ display, ❌ provenance  
- Confidence breakdown: API (synthetic) → UI ✅ display, ❌ provenance  

**Score:** 52/100  
**Grade:** D  

#### 2.2 Real-Time

| Feature | Implemented | Working | Issues |
|---------|-------------|---------|--------|
| SSE connection | ✅ `/realtime/prices` | N/A | Frontend opens SSE and POSTs to `/realtime/subscribe` with signal IDs |
| Price updates | Backend uses PriceStreamer + Polymarket WS | ❌ | `register_signal(signal_id, token_id, ...)` is never called; `_signal_token_map` always empty; subscribe yields no token_ids → no Polymarket subscription |
| Live indicator | Header `isLive={!signalsError}` | ⚠️ | “LIVE” hidden on API error; when API returns empty, mock is shown and “LIVE” can still show |

**Score:** 30/100  
**Grade:** F  

#### 2.3 Visual Quality

| Aspect | Meets Standard | Issues |
|--------|----------------|--------|
| Color consistency | ✅ | CSS variables, severity colors |
| Typography | ✅ | Clear hierarchy |
| Spacing / layout | ✅ | Grid and cards |
| Loading | ✅ | Spinner when no signals and loading |
| Error visibility | ✅ | Red banner on backend failure |
| Empty vs mock | ⚠️ | Empty and “using demo” are not clearly distinguished when API returns [] |

**Score:** 72/100  
**Grade:** C  

---

### 3. ARCHITECTURE

#### 3.1 Data Flow

```
Polymarket Gamma API
    ↓
PolymarketLiveClient.fetch_events() / get_logistics_events()
    ↓
PolymarketMapper.map_event() → RawSignalEvent (probability, liquidity, volume from API)
    ↓
Pipeline: SignalValidator.validate() → ValidatedSignal
    ↓
Pipeline: ImpactTranslator.translate() → ImpactAssessment (metrics, routes, evidence from parameters)
    ↓
Pipeline: OmenSignal.from_impact_assessment() → OmenSignal (confidence from validation)
    ↓
live._signal_to_full_response()  ← INJECTS: prob_history, conf_breakdown, projection, delay_days=severity*10
    ↓
API Response → mapApiSignalToUi() → UI
```

**Issues:**

1. **Live response layer adds unsourced data**  
   `_signal_to_full_response` and helpers build probability_history, confidence_breakdown, metric projections, and route delay_days without pipeline or cited methodology.

2. **Stats/activity disconnected**  
   `record_processing()` and `log_activity()` are never invoked by the pipeline; stats and activity are static or demo.

3. **Real-time gap**  
   No registration of (signal_id, token_id) anywhere, so the streamer cannot map Polymarket tokens to OMEN signals.

**Score:** 72/100  
**Grade:** C  

#### 3.2 Code Quality

| Aspect | Status | Issues |
|--------|--------|--------|
| Hardcoded “real” data in API” | ❌ | prob_history, confidence_breakdown, projection, delay_days in live.py |
| Error handling | ✅ | Circuit breakers, DLQ, HTTP 503 on source failure |
| Documentation | ⚠️ | Red Sea rule and parameters documented; $1000 liquidity and many API formulas undocumented |
| Traceability | ✅ | explanation_chain, trace_id, ruleset_version in pipeline output |

**Score:** 68/100  
**Grade:** C  

---

## SPECIFIC ISSUES

### CRITICAL (Must fix before production)

1. **ISSUE-001: Synthetic probability_history in live API**  
   - **Location:** `src/omen/api/routes/live.py` lines 339–340  
   - **Code:** `prob_history = [round(prob * (0.92 + 0.08 * i / 24), 4) for i in range(24)]`  
   - **Impact:** UI shows a 24-point “history” that is fabricated. Not traceable to any feed.  
   - **Fix:** Return only stored history from the pipeline, or return `[]` and treat “no history” explicitly in the UI.

2. **ISSUE-002: Synthetic confidence_breakdown in live API**  
   - **Location:** `src/omen/api/routes/live.py` lines 272–284  
   - **Code:** `_confidence_breakdown(score, signal_id)` uses `hash(signal_id)` to derive per-component values.  
   - **Impact:** Radar and breakdown look like real validation outputs but are deterministic synthetic.  
   - **Fix:** Use `confidence_factors` from OmenSignal when present; otherwise omit breakdown or document as “approximate” and do not show as rule output.

3. **ISSUE-003: Unsourced metric projection in live API**  
   - **Location:** `src/omen/api/routes/live.py` lines 254–256, 265  
   - **Code:** `_metric_projection(current_value, 7)` → `current_value * (1 - exp(-d/2))`.  
   - **Impact:** 7-day “projection” has no methodology or source.  
   - **Fix:** Remove projection from the response, or implement and document a sourced methodology (e.g. referenced study or internal doc version).

4. **ISSUE-004: Arbitrary delay_days in route enrichment**  
   - **Location:** `src/omen/api/routes/live.py` line 244  
   - **Code:** `delay_days=severity * 10`  
   - **Impact:** Route cards show delay numbers that are not from impact assessment.  
   - **Fix:** Use `estimated_delay_days` (and optional uncertainty) from AffectedRoute when building EnhancedRoute; do not use `severity * 10`.

5. **ISSUE-005: Stats endpoint returns fabricated and static values**  
   - **Location:** `src/omen/api/routes/stats.py`  
   - **Impact:** `avg_confidence=0.78`, `total_risk_exposure=2_500_000`, `system_latency_ms=12`, `polymarket_events_per_min=847` are hardcoded. Pipeline never calls `record_processing()`, so counts stay at 0.  
   - **Fix:** Call `record_processing()` (or equivalent) from the pipeline; compute or pull avg_confidence, risk_exposure, latency, and Polymarket rate from real metrics or remove/hide them until implemented.

6. **ISSUE-006: Activity feed is demo-only**  
   - **Location:** `src/omen/api/routes/activity.py`  
   - **Impact:** `_init_demo_activity()` fills the feed; pipeline never calls `log_activity()`.  
   - **Fix:** Call `log_activity()` from the pipeline (and related services) for real signal/validation/rule events, or stop exposing activity as “live” and label as “Sample” or “Demo”.

7. **ISSUE-007: Real-time subscription cannot work**  
   - **Location:** `src/omen/infrastructure/realtime/price_streamer.py`; no caller of `register_signal()`  
   - **Impact:** UI subscribes with OMEN signal IDs; streamer has no token mapping, so no Polymarket subscription and no live price updates.  
   - **Fix:** When building OmenSignal or when persisting, register (signal_id, condition_token_id, initial_price) from Polymarket market/condition data, and pass token IDs through to the streamer; or remove/disable real-time and document polling-only.

### HIGH (Should fix soon)

1. **ISSUE-008: Mock data shown with “LIVE” when API returns empty**  
   - **Location:** `omen-demo/src/App.tsx` (e.g. `signals = liveSignals?.length ? liveSignals : mockSignals`; `isLive={!signalsError}`).  
   - **Impact:** Empty success response leads to mock data + possible “LIVE” and “ĐÃ KẾT NỐI”.  
   - **Fix:** Treat “empty and not loading” as a distinct state; show “No signals” or “Demo data” and set connection/live state to reflect that no live data is being shown.

2. **ISSUE-009: mapApiToUi invents uncertainty when missing**  
   - **Location:** `omen-demo/src/lib/mapApiToUi.ts` line 158  
   - **Code:** `uncertainty: m.uncertainty ?? { lower: m.value * 0.8, upper: m.value * 1.2 }`  
   - **Impact:** Missing API uncertainty is shown as ±20% with no basis.  
   - **Fix:** Omit uncertainty when API does not provide it, or show “Uncertainty not available” and do not display fake bounds.

3. **ISSUE-010: Impact translator hardcodes onset/duration**  
   - **Location:** `src/omen/domain/services/impact_translator.py` lines 134–135  
   - **Code:** `expected_onset_hours=24`, `expected_duration_hours=720`  
   - **Impact:** All assessments get the same timing; not scenario- or source-based.  
   - **Fix:** Make onset/duration rule- or parameter-driven and document source, or mark as placeholder until methodology exists.

### MEDIUM (Should fix eventually)

1. **ISSUE-011: Liquidity threshold $1000 unsourced**  
   - **Location:** `src/omen/domain/rules/validation/liquidity_rule.py`  
   - **Impact:** Threshold is arbitrary for “sellable” use.  
   - **Fix:** Add a short rationale or reference (e.g. internal policy or external benchmark) and consider making it configurable.

2. **ISSUE-012: Urgency/onset in OmenSignal**  
   - **Location:** `src/omen/domain/models/omen_signal.py` urgency logic and use of `expected_onset_hours`.  
   - **Impact:** Uses the same hardcoded 24h from the translator.  
   - **Fix:** Align with ISSUE-010 so urgency is driven by sourced or documented inputs.

### LOW (Nice to have)

1. **ISSUE-013: mapApiStatsToUi events_per_second**  
   - **Location:** `omen-demo/src/lib/mapApiToUi.ts`  
   - **Impact:** `events_per_second: Math.round((api.events_per_minute ?? 0) / 60)` — unit semantics (per second from per minute) are correct but label “/phút” in BottomPanel is confusing.  
   - **Fix:** Use a consistent unit and label (e.g. “event/min” or “sự kiện/phút”).

---

## FAKE DATA INVENTORY

| Location | Type | Value / Behavior | Should Be |
|----------|------|------------------|-----------|
| `live.py:339–340` | Synthetic | `prob_history = [round(prob*(0.92+0.08*i/24),4) for i in range(24)]` | Stored history or [] |
| `live.py:272–284` | Synthetic | `_confidence_breakdown(score, signal_id)` from hash | Real confidence_factors or omitted |
| `live.py:254–256` | Unsourced formula | `_metric_projection(v) = v*(1-exp(-d/2))` | Sourced methodology or none |
| `live.py:244` | Magic number | `delay_days=severity*10` | assessment.affected_routes[].estimated_delay_days |
| `stats.py:65–77` | Hardcoded | `avg_confidence=0.78`, `total_risk_exposure=2_500_000`, `system_latency_ms=12`, `polymarket_events_per_min=847` | From pipeline/metrics or removed |
| `activity.py:50–74` | Demo | Pre-filled Vietnamese activity messages | Real log_activity() from pipeline |
| `mapApiToUi.ts:158` | Invented default | `uncertainty ?? { lower: value*0.8, upper: value*1.2 }` | Omit or “N/A” |
| `mockSignals.ts` (whole file) | Mock | Static ProcessedSignal[] with fake evidence_source strings | Used only when explicitly in “demo” mode and clearly labeled |

---

## CERTIFICATION

- [ ] **CERTIFIED FOR PRODUCTION** — System meets enterprise standards  
- [ ] **CONDITIONALLY CERTIFIED** — Fix critical issues first  
- [x] **NOT CERTIFIED** — Major rework required  
- [ ] **REJECTED** — Fundamental integrity issues  

**Auditor Notes:**

The pipeline’s **core path** (Gamma → mapper → validation → Red Sea translation with EvidenceRecords → OmenSignal) is traceable and uses cited parameters for impact metrics. Probability, liquidity, and volume are from the Polymarket API. Confidence is derived from validation scores. That is sufficient to build a sellable, auditable product **if** the API and UI do not add or display unsourced numbers.

The **live API response layer** and **dashboard data sources** currently introduce or expose synthetic and hardcoded data (probability history, confidence breakdown, projections, route delay_days, stats, activity). Until these are removed or replaced with traceable, sourced values, the system cannot be presented as production-grade “intelligence” for high-stakes decisions.

Real-time price streaming is designed to use Polymarket’s WebSocket but is effectively dead code until signal_id → token_id registration is implemented and wired to the pipeline.

**Recommended path to conditional certification:**  
(1) Remove or clearly separate all synthetic enrichment in `live.py`; (2) connect stats and activity to pipeline events; (3) either implement token registration for real-time or disable/hide the live stream and document polling; (4) ensure the UI never shows “LIVE” when displaying mock or empty data. Re-audit after these changes.
