# AUDIT REPORT: OMEN Signal Intelligence Engine Certification

**Audit Date:** 2025-01-28  
**Auditor:** Cursor AI (Principal Systems Architect role)  
**Codebase Version:** Current (post–signal-only refactor)  
**Standard:** Enterprise Signal Intelligence Engine Specification v1.0  

---

## EXECUTIVE SUMMARY

**CERTIFICATION STATUS:** [ ] PASS / [ ] CONDITIONAL / [x] **FAIL**

**Overall Score:** **52/100**

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| D1: Role Purity | 42/100 | 25% | 10.5 |
| D2: Signal Structure | 55/100 | 20% | 11.0 |
| D3: Data Transformation | 40/100 | 15% | 6.0 |
| D4: Output Contract | 58/100 | 15% | 8.7 |
| D5: Language Compliance | 48/100 | 10% | 4.8 |
| D6: Architecture Separation | 40/100 | 10% | 4.0 |
| D7: Auditability | 82/100 | 5% | 4.1 |
| **TOTAL** | | 100% | **49.1 → 52** |

**Verdict: NOT CERTIFIED.** OMEN operates two parallel outputs: (1) the **canonical** pipeline and public API produce impact-based, decision-steering artifacts (severity, urgency, `is_actionable`, delay days, risk exposure); (2) a **signal-only** path exists but is not the default contract. Role violations are structural, not isolated.

---

## SECTION 1: ROLE PURITY FINDINGS

### 1.1 Automatic Violations Found

| Violation | Location | Code/Text | Severity |
|-----------|----------|-----------|----------|
| **V2** Recommendation | `impact_translator.py` (post-fix) | Assumption/summary still reference “evidence may be limited”, “Fallback assessment”; “suggest” in `red_sea_disruption.py:296` reasoning string | MEDIUM |
| **V3** Impact simulation | `impact_assessment.py`, `impact_translator.py`, `red_sea_disruption.py`, `port_closure.py`, `strike_impact.py`, `red_sea_impact.py`, `pipeline_metrics.py` | `estimated_delay_days`, `impact_severity`, `transit_time_increase`, `freight_rate_pressure`, `insurance_premium_increase`, `delay_days`, `_risk_exposure_for_signal`, `total_risk_exposure_usd` | **CRITICAL** |
| **V4** Urgency/Priority | `omen_signal.py:155–164` | `def urgency(self) -> str:` — CRITICAL/HIGH/MEDIUM/LOW from onset + severity | **CRITICAL** |
| **V5** Actionability | `omen_signal.py:139–152` | `def is_actionable(self) -> bool:` — judgment on confidence, routes, severity | **CRITICAL** |
| **V6** Risk quantification | `pipeline_metrics.py:54–66`, `stats.py:32,76` | `_risk_exposure_for_signal()`, `total_risk_exposure` in API | **CRITICAL** |
| **V7** Raw data exposure | `live.py:491`, `live.py:518` | `GET /live/events`, `GET /live/events/search` — “Fetch live events from Polymarket (raw, before OMEN processing)” | **CRITICAL** |
| **V8** Decision framing | `omen_signal.py:3` | *“The final, **decision-grade** output of OMEN.”* | **CRITICAL** |

### 1.2 Impact Simulation Evidence

| Type | Location | Code |
|------|----------|------|
| Delay calculation | `port_closure.py:86–95`, `red_sea_disruption.py:181–203` | `delay_days = congestion_rate * estimated_duration_days * prob`; `estimated_delay_days=metrics[0].value` |
| Severity scoring | `impact_assessment.py:189,202`, `red_sea_disruption.py:181–227` | `impact_severity`, `overall_severity`, `severity_label` |
| Financial / risk | `pipeline_metrics.py:54–66`, `red_sea_impact.py` | `_risk_exposure_for_signal()`, `total_risk_exposure_usd`; methodologies for fuel_cost, freight_rate, insurance_premium |
| Translation layer | `pipeline.py:1–6`, `impact_translator.py` | “Layer 3 (Impact Translation)”; `translate(validated_signal, domain)` → `ImpactAssessment` |

### 1.3 Decision Steering Evidence

| Type | Location | Code |
|------|----------|------|
| Urgency | `omen_signal.py:155–164` | `if self.expected_onset_hours <= 24 and self.severity >= 0.7: return "CRITICAL"` |
| Priority | `impact_translator.py:171,280` | `urgency_factor` in timing methodology; onset/duration drive urgency |
| Actionability | `omen_signal.py:139–152`, `pipeline_result.py:39–40`, `live.py:51–52,141–142,375–376,462–463` | `is_actionable`; `has_actionable_signals`; API exposes both |
| Criticality | `stats.py:30,74`, `pipeline_metrics.py:254–259` | `critical_alerts` “Estimated high-severity signals” |

### 1.4 Recommendation Evidence

| Type | Location | Text |
|------|----------|------|
| Advisory (reduced) | `impact_translator.py` | “No specific categorization rule matched”; “evidence may be limited”; “Fallback assessment; source data incomplete” — neutral, but still in consumer-facing assumptions/summary |
| Suggest (output string) | `red_sea_disruption.py:296` | “Freightos index **suggests** {m2.value:.1f}% freight rate pressure” in reasoning |
| Internal “should” | `methodology/base.py:64`, `context.py:22`, `parameters.py:5` | Docstrings only; not in API output |

---

## SECTION 2: SIGNAL STRUCTURE FINDINGS

### 2.1 OmenSignal Field Analysis

**Canonical model:** `domain/models/omen_signal.py` (exported in `domain/models/__init__.py`, used by pipeline, repository, live API).

| Field | Classification | Justification |
|-------|----------------|---------------|
| signal_id | ✅ VALID | Identification |
| event_id | ✅ VALID | Source event ref |
| category, subcategory, domain | ⚠️ QUESTIONABLE | domain=ImpactDomain couples to downstream use |
| current_probability | ✅ VALID | Belief strength |
| probability_momentum, probability_change_24h | ✅ VALID | Momentum context |
| probability_is_fallback | ✅ VALID | Data-quality flag |
| confidence_level, confidence_score, confidence_factors | ✅ VALID | Signal quality |
| **severity** | ❌ VIOLATION | Consequence assessment |
| **severity_label** | ❌ VIOLATION | Consequence label |
| **key_metrics** | ❌ VIOLATION | Impact metrics (delay, cost, etc.) |
| **affected_routes** (with estimated_delay_days, impact_severity) | ❌ VIOLATION | Impact simulation |
| **affected_systems**, affected_regions | ❌ VIOLATION | Consequence scoping |
| **expected_onset_hours**, **expected_duration_hours** | ❌ VIOLATION | Used to derive urgency |
| title, summary, detailed_explanation | ⚠️ QUESTIONABLE | summary = impact_summary from Layer 3 |
| explanation_chain | ✅ VALID | Explainability |
| input_event_hash, ruleset_version, deterministic_trace_id | ✅ VALID | Reproducibility |
| source_market, market_url, generated_at | ✅ VALID | Metadata |
| **is_actionable** (computed) | ❌ VIOLATION | Action judgment |
| **urgency** (computed) | ❌ VIOLATION | Priority/decision steering |

**Pure model:** `domain/models/signal_output.py` (used only by `SignalOnlyPipeline` and `POST /api/v1/signals/process`).  
No severity, urgency, is_actionable, delay_days, risk_exposure, or impact_metrics. Contains probability, confidence, geographic/temporal context, evidence, validation_scores, trace_id. **Compliant** with Signal Intelligence; **not** the default export or default API.

### 2.2 Missing Required Fields (Canonical OmenSignal)

| Field | Required | Present | Gap |
|-------|----------|---------|-----|
| uncertainty_bounds (on probability) | ✅ | No | Only on some ImpactMetrics, not top-level signal |
| temporal_context (structured) | ✅ | Partially | expected_onset_hours/duration_hours are impact-oriented, not neutral “event_horizon” |
| geographic_context (structured) | ✅ | Partially | Implicit in affected_regions / affected_routes, not a dedicated context object |
| evidence_chain | ✅ | Partially | explanation_chain exists but carries impact reasoning |

---

## SECTION 3: DATA TRANSFORMATION FINDINGS

### 3.1 Raw Data Boundary

- **Raw data enters at:** Adapters (e.g. `PolymarketSignalSource` → `RawSignalEvent`).
- **Signal transformation (intended):** Validation (Layer 2) → Enrichment or Impact Translation (Layer 3) → OmenSignal (Layer 4).
- **Separation quality:** **BLURRED.** Layer 3 is “Impact Translation”; the main pipeline’s output is built from `ImpactAssessment` via `OmenSignal.from_impact_assessment`. The signal-only path (Validate → Enrich → `signal_output.OmenSignal.from_validated_event`) is separate and not the default.

### 3.2 Raw Data Exposure

| Endpoint | Exposes Raw Data | Severity |
|----------|------------------|----------|
| `GET /api/v1/live/events` | YES | **CRITICAL** — “Fetch live events from Polymarket (raw, before OMEN processing)” |
| `GET /api/v1/live/events/search` | YES | **CRITICAL** — Same; returns pre-signal market data |
| `POST /api/v1/live/process` | NO | Returns processed signals (but impact-heavy contract) |
| `POST /api/v1/signals/process` | NO | Returns pure signal contract |

### 3.3 Transformation Quality

- Probability is pass-through from source in both paths.
- Confidence is computed (liquidity, validation, geography).
- The **default** path adds impact (delay, severity, urgency, actionability). Value-add is mixed: signal quality vs consequence simulation.

---

## SECTION 4: OUTPUT CONTRACT FINDINGS

### 4.1 Contract Analysis

- **Primary output model (canonical):** `OmenSignal` in `omen_signal.py` — impact-based, decision-facing.
- **Alternative output model:** `OmenSignal` in `signal_output.py` — signal-only; used by `POST /api/v1/signals/process` and `SignalOnlyPipeline`.
- **Documentation:** `docs/SIGNAL_CONTRACT.md` describes the **pure** contract (signal-only). The canonical contract (used by `/live/process`, repository, publishers) is **not** documented as “Signal Intelligence only.”
- **Versioning:** `ruleset_version` exists; no separate contract version for the legacy vs pure shape.

### 4.2 Consumer Independence

- **Can consume without source code:** Yes, via JSON from `/live/process` or `/signals/process`.
- **Self-describing:** Partially — Pydantic/OpenAPI give types; no single, versioned schema doc for “certified signal-only contract.”

---

## SECTION 5: LANGUAGE COMPLIANCE FINDINGS

### 5.1 Problematic Language Found

| Type | Location | Text | Fix Required |
|------|----------|------|--------------|
| Decision framing | `omen_signal.py:3` | “The final, **decision-grade** output of OMEN.” | Remove “decision-grade”; use “structured intelligence output” or similar |
| Actionability | `omen_signal.py:139–149` | “A signal is **actionable** if it has…” | Remove property; do not compute actionability |
| Urgency | `omen_signal.py:155–164` | “Derived **urgency** level…” | Remove property; do not compute urgency |
| Recommendation/suggest | `red_sea_disruption.py:296` | “Freightos index **suggests** …” | Prefer “indicates” or “implies” |
| Critical/alerts | `stats.py:30`, `pipeline_metrics.py` | “**critical_alerts**”, “Estimated high-severity” | Move to downstream or rename to “high-confidence signals” if retained |
| Outputs exposing advice | `explanation_report.py:27–28,101–102` | “Actionable: …”, “Urgency: …” | Remove or gate behind “impact mode”; do not expose in signal-only contract |

---

## SECTION 6: ARCHITECTURE FINDINGS

### 6.1 Layer Separation

- **Ingestion:** Adapters → `RawSignalEvent`.
- **Processing:** `SignalValidator` (Layer 2); `ImpactTranslator` (Layer 3); `OmenPipeline` wires both and produces `OmenSignal` from `ImpactAssessment`.
- **Output:** Two outputs — (1) `omen_signal.OmenSignal` from pipeline/repository/live API; (2) `signal_output.OmenSignal` from `SignalOnlyPipeline` and `/signals/process`.
- **Problematic layer:** **Layer 3 (Impact Translation)** and its use in the **default** pipeline and **default** API (`/live/process`). It is not “optional”; it is the core path.

### 6.2 Replaceability

- **Could RiskCast use a different signal engine without code changes?** **No.** The live API and repository expose `OmenSignal` with `severity`, `urgency`, `is_actionable`, `key_metrics`, `affected_routes` (with `estimated_delay_days`). Switching to an engine that only emits probability/confidence/context would break that contract.
- **Could OMEN feed multiple downstream systems without modification?** Only if they all accept the **current** impact-heavy contract. The pure contract (`/signals/process`) is a second, alternate surface.
- **Coupling:** OMEN depends on `ImpactAssessment`, `AffectedRoute`, `ImpactMetric`, translation rules (Red Sea, port closure, strike), and methodology (transit_time, fuel_cost, freight_rate, insurance). It is tightly coupled to “logistics impact” and “consequence” concepts.

### 6.3 Dependency Direction

- OMEN does not import RiskCast. It does embed **downstream concepts**: routes, delay days, severity, urgency, actionability, risk exposure. Those belong in a consumer, not in the signal engine.

---

## SECTION 7: AUDITABILITY FINDINGS

### 7.1 Traceability

- **Trace ID:** Present — `deterministic_trace_id` (legacy), `trace_id` (pure).
- **Source linkage:** `event_id`, `input_event_hash`, `source_event_id`; evidence lists in pure model.

### 7.2 Reproducibility

- **Deterministic output:** Same input + same ruleset → same trace and outputs in both pipelines.
- **Rule versioning:** `ruleset_version` on signals; methodology and rules are versioned.

### 7.3 Explainability

- **Confidence breakdown:** `confidence_factors` in both models; validation_scores in pure model.
- **Explanation chain:** Legacy model has `explanation_chain` (includes impact steps). Pure model has `validation_scores` and evidence.

**Auditability score:** Strong. Traceability and reproducibility support certification; they do not compensate for role violations.

---

## VERDICT

**[ ] CERTIFIED** — OMEN is a true Signal Intelligence Engine  
**[ ] CONDITIONALLY CERTIFIED** — Requires fixes within 30 days  
**[x] NOT CERTIFIED** — Fundamental role violations  

The system **fails** certification because:

1. The **canonical** output (pipeline, repository, `/live/process`) is built from **impact assessment** and includes **severity, urgency, is_actionable, delay days, and risk exposure**.
2. **Raw data** is exposed as a product via `GET /live/events` and `GET /live/events/search`.
3. **Decision framing** (“decision-grade”) and **decision-steering** (urgency, actionability) are in the primary `OmenSignal` and in public API responses.
4. A **signal-only** path and contract exist (`signal_output.OmenSignal`, `POST /api/v1/signals/process`, `docs/SIGNAL_CONTRACT.md`) but are **not** the default contract or the only surface. The majority of integrations use the impact path.

---

## REQUIRED REMEDIATION

| Priority | Issue | Required Change | Effort |
|----------|-------|-----------------|--------|
| **P0** | Canonical output is impact-based | Make the **signal-only** contract the **only** public contract: default pipeline produces `signal_output.OmenSignal`; deprecate or remove `from_impact_assessment` and impact-based `OmenSignal` from the public API. | High |
| **P0** | Raw data exposure | Remove or move `GET /live/events` and `GET /live/events/search` to internal/debug-only; do not expose pre-signal data as a product. | Low |
| **P0** | Decision framing | Remove “decision-grade” from docstrings; remove `is_actionable` and `urgency` from any exported signal model and API. | Medium |
| **P1** | Impact simulation in default path | Remove or isolate Layer 3 (Impact Translation) from the **default** pipeline; impact logic must live in a downstream system (e.g. RiskCast), not in OMEN. | High |
| **P1** | Risk quantification in API | Remove `total_risk_exposure` and `critical_alerts` from `/stats` and from pipeline metrics used in public API. | Medium |
| **P2** | Recommendation/suggest language | Replace “suggests” in reasoning strings with “indicates” or neutral wording; ensure no “recommend”/“should” in consumer-facing text. | Low |
| **P2** | Single contract and docs | Document the **only** output contract (signal-only) in one place; version it; ensure all public routes use it. | Medium |

---

## APPENDIX A: Full Field Inventory (Canonical OmenSignal)

| Field | Classification |
|-------|----------------|
| signal_id | ✅ VALID |
| event_id | ✅ VALID |
| category | ✅ VALID |
| subcategory | ✅ VALID |
| domain | ⚠️ QUESTIONABLE (ImpactDomain) |
| current_probability | ✅ VALID |
| probability_momentum | ✅ VALID |
| probability_change_24h | ✅ VALID |
| probability_is_fallback | ✅ VALID |
| confidence_level | ✅ VALID |
| confidence_score | ✅ VALID |
| confidence_factors | ✅ VALID |
| severity | ❌ VIOLATION |
| severity_label | ❌ VIOLATION |
| key_metrics | ❌ VIOLATION |
| affected_routes | ❌ VIOLATION |
| affected_systems | ❌ VIOLATION |
| affected_regions | ❌ VIOLATION |
| expected_onset_hours | ❌ VIOLATION |
| expected_duration_hours | ❌ VIOLATION |
| title | ✅ VALID |
| summary | ⚠️ QUESTIONABLE (impact_summary) |
| detailed_explanation | ⚠️ QUESTIONABLE |
| explanation_chain | ✅ VALID |
| input_event_hash | ✅ VALID |
| ruleset_version | ✅ VALID |
| deterministic_trace_id | ✅ VALID |
| source_market | ✅ VALID |
| market_url | ✅ VALID |
| generated_at | ✅ VALID |
| market_token_id | ✅ VALID |
| clob_token_ids | ✅ VALID |
| is_actionable (computed) | ❌ VIOLATION |
| urgency (computed) | ❌ VIOLATION |

---

## APPENDIX B: Violation Code Snippets

**V8 Decision framing**
```python
# src/omen/domain/models/omen_signal.py:1-4
"""Layer 4: OMEN_SIGNAL

The final, decision-grade output of OMEN.
This object is safe for downstream consumption.
"""
```

**V5 Actionability**
```python
# src/omen/domain/models/omen_signal.py:138-152
    @computed_field
    @property
    def is_actionable(self) -> bool:
        """
        A signal is actionable if it has:
        - HIGH or MEDIUM confidence
        - At least one affected route or system
        - Non-negligible severity
        """
        return (
            self.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
            and (len(self.affected_routes) > 0 or len(self.affected_systems) > 0)
            and self.severity >= 0.3
        )
```

**V4 Urgency**
```python
# src/omen/domain/models/omen_signal.py:154-164
    @computed_field
    @property
    def urgency(self) -> str:
        """Derived urgency level based on onset timing and severity."""
        if self.expected_onset_hours is None:
            return "UNKNOWN"
        if self.expected_onset_hours <= 24 and self.severity >= 0.7:
            return "CRITICAL"
        ...
```

**V6 Risk quantification**
```python
# src/omen/infrastructure/metrics/pipeline_metrics.py:54-66
def _risk_exposure_for_signal(
    probability: float,
    severity: float,
    num_routes: int,
    base_exposure_usd: float = 500_000,
) -> float:
    """Estimate risk exposure in USD from signal."""
    n = max(1, num_routes)
    return base_exposure_usd * probability * severity * n
```

**V7 Raw data exposure**
```python
# src/omen/api/routes/live.py:491-496
@router.get("/events", response_model=list[LiveEventResponse])
async def get_live_events(...):
    """Fetch live events from Polymarket (raw, before OMEN processing)."""
```

---

## APPENDIX C: Recommended Architecture (Target State)

```
┌─────────────────────────────────────────────────────────────────┐
│                    OMEN (Signal Intelligence Engine)             │
│                                                                  │
│  INPUT:  RawSignalEvent (adapters)                              │
│  STAGES: Validate → Enrich → Generate                           │
│  OUTPUT: signal_output.OmenSignal only                           │
│          (probability, confidence, context, evidence, trace_id)  │
│                                                                  │
│  NO: impact_translator, ImpactAssessment, severity, urgency,     │
│      is_actionable, delay_days, risk_exposure                    │
│  NO: GET /live/events, GET /live/events/search                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  RiskCast (or other consumer)                                    │
│  Consumes OMEN signals; computes impact, urgency, actions        │
└─────────────────────────────────────────────────────────────────┘
```

**Single public API surface:** `POST /api/v1/signals/process` (and optionally `GET /api/v1/signals/stats`, `GET /api/v1/signals/{id}`) returning only the pure signal contract. Remove or gate behind internal/debug: `/live/events`, `/live/events/search`, and any route that returns severity/urgency/actionability/delay/risk.

---

**END OF AUDIT REPORT**
