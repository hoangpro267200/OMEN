# OMEN — Signal Intelligence Engine Role Audit

**Audit date:** 2025-01-28  
**Standard:** OMEN must be a **Signal Intelligence Engine** — not a raw data lake, not a decision-making system.  
**Scope:** `src/omen/` (domain, application, api, adapters) — current codebase.

---

## A. VERDICT

**Choice:** [x] **OMEN is incorrectly acting as a decision engine** (in part) **and exposes raw data**

Strictly applied:

- OMEN **does** emit structured, probabilistic signals with confidence and traceability.
- OMEN **also** (1) exposes raw/pre-processed event data via API, (2) embeds recommendation language in outputs, (3) uses “decision-grade” framing and “actionable”/“urgency” semantics, and (4) implements **impact simulation** (consequence translation: delay days, severity per route, etc.), which goes beyond “predictive-grade signal” and into “simulated downstream impact.”

So it is **not** a pure Signal Intelligence Engine by the given definition. It is **part engine, part impact simulator, with decision-facing wording and raw data exposure**.

---

## B. EVIDENCE

### 1. Raw data exposure

| Location | Evidence |
|----------|----------|
| `src/omen/api/routes/live.py:491–513` | `GET /live/events` returns `list[LiveEventResponse]` — docstring: *"Fetch live events from Polymarket (raw, before OMEN processing)."* Response fields: `event_id`, `title`, `probability`, `liquidity_usd`, `volume_usd`, `keywords`, `source_url`, `observed_at`. This is **raw/normalized market data**, not the signal layer. |
| `src/omen/api/routes/live.py:518–536` | `GET /live/events/search` returns ad-hoc dicts with `event_id`, `title`, `probability`, `liquidity_usd`, `keywords` — again **pre–signal** data. |

Raw data **does** exist as a separate layer (RawSignalEvent → ValidatedSignal → ImpactAssessment → OmenSignal), but the **API exposes that pre-signal layer** via `/live/events` and `/live/events/search`. So “raw data” is not only internal; it is a first-class, public surface.

### 2. Signal intelligence (probability, confidence, time, uncertainty)

| Requirement | Implemented | Code reference |
|-------------|-------------|-----------------|
| **Probability** | **Pass-through** | `OmenSignal.from_impact_assessment` sets `current_probability=original.probability` (`src/omen/domain/models/omen_signal.py:228`). OMEN does not compute a new probability; it carries market odds forward. |
| **Confidence** | **Computed** | Same file: `confidence_score` from `confidence_factors` (signal_strength, liquidity_score, validation_score); `ConfidenceLevel.from_score(confidence_score)`. |
| **Time horizon** | **Set in translation** | `expected_onset_hours`, `expected_duration_hours` from `ImpactAssessment` (`src/omen/domain/models/omen_signal.py:246–247`), filled by `ImpactTranslator` and methodology (e.g. `TIMING_METHODOLOGY`, fallback onset/duration in `impact_translator.py`). |
| **Uncertainty** | **Present on metrics** | `ImpactMetric.uncertainty: UncertaintyBounds | None` (`src/omen/domain/models/impact_assessment.py:56–59`). Rules (e.g. Red Sea, port closure) set bounds. Not consistently on every metric. |

So: confidence and time horizon are OMEN-derived; probability is market-derived; uncertainty exists but is partial.

### 3. Role violations

| Type | Location | Evidence |
|------|----------|----------|
| **“Decision-grade” framing** | `src/omen/domain/models/omen_signal.py:3` | Docstring: *"The final, **decision-grade** output of OMEN."* This frames the output as suitable for decisions, which blurs the line between “signal” and “decision support.” |
| **Recommendation language** | `src/omen/domain/services/impact_translator.py:257` | Reasoning string: *"Manual review **recommended**."* |
| | `src/omen/domain/services/impact_translator.py:286` | Summary: *"No specific model applied; **review recommended**."* |
| | `src/omen/domain/services/impact_translator.py:305` | Assumption: *"**Manual review recommended for operational decisions.**"* |
| **Actionability / urgency** | `src/omen/domain/models/omen_signal.py:139–149` | `is_actionable`: *"A signal is actionable if it has: HIGH or MEDIUM confidence, at least one affected route or system, non-negligible severity."* This is an explicit **judgment** about whether the signal is fit for action. |
| | `src/omen/domain/models/omen_signal.py:153–164` | `urgency`: CRITICAL / HIGH / MEDIUM / LOW from onset + severity. Encodes **priority**, i.e. “how urgently to treat this,” which is decision-steering. |
| **Impact simulation** | `src/omen/domain/models/impact_assessment.py:3` | Docstring: *"**Translates belief into consequence.**"* Layer 3 is described as producing consequences, not only beliefs. |
| | `src/omen/domain/models/impact_assessment.py:189–191` | `AffectedRoute` has `impact_severity`, `estimated_delay_days` — **consequence metrics**. |
| | `src/omen/domain/rules/translation/logistics/red_sea_disruption.py:181–227` | Rule writes `estimated_delay_days`, `impact_severity` per route from evidence-based parameters. That is **simulating downstream impact** (delay, severity), not only reporting probability/confidence. |
| | `src/omen/domain/rules/translation/logistics/port_closure.py:86–95` | Computes `delay_days`, uncertainty bounds — again **impact simulation**. |

So: there is explicit “recommendation” text, “decision-grade” and “actionable”/“urgency” semantics, and a full layer that “translates belief into consequence” with delay and severity. That exceeds “predictive-grade signal” and enters “simulated impact and decision-facing cues.”

### 4. Output contract and consumability

| Criterion | Status | Detail |
|----------|--------|--------|
| **Typed output object** | Yes | `OmenSignal` (`src/omen/domain/models/omen_signal.py`) is a single Pydantic model. API exposes `FullProcessedSignalResponse` built from it (`live.py:383–449`). |
| **Consumable without OMEN internals** | Partly | Downstream can use the JSON shape of `FullProcessedSignalResponse` / `OmenSignal` without touching pipeline code. Contract is not a separate, versioned schema doc; it’s the current response model. |
| **Deterministic and auditable** | Yes | `input_event_hash`, `ruleset_version`, `deterministic_trace_id`, `explanation_chain` support reproducibility and audit. |

### 5. Separation of concerns

| Question | Answer | Justification |
|----------|--------|----------------|
| Could RiskCast replace OMEN with another signal engine? | **Partly** | RiskCast would need to consume the same **contract** (or a subset). Today that contract is implicit (OmenSignal / FullProcessedSignalResponse). If RiskCast is bound to fields like `affected_routes[].delay_days`, `is_actionable`, `urgency`, it is bound to OMEN’s **impact and decision-facing semantics**, not only to “probability + confidence + uncertainty.” A different engine that *only* produced probability/confidence/uncertainty would not match that contract. |
| Could OMEN feed multiple downstream systems without change? | **Yes, if they accept current contract** | POST /live/process returns one shape. Any consumer that accepts `FullProcessedSignalResponse` (or the same JSON) can use it. No change in OMEN needed. But that contract already encodes impact and actionability. |

---

## C. GAP ANALYSIS

Mismatches between **intended role (Signal Intelligence Engine)** and **current implementation**:

1. **Raw data as a first-class API product**  
   - Intended: intelligence layer only; raw data internal or out of scope.  
   - Actual: `GET /live/events` and `GET /live/events/search` expose pre-signal event data. Raw (or lightly normalized) data is a **direct API offering**, not clearly separated as “internal/debug only.”

2. **Impact simulation in the core output**  
   - Intended: “DOES NOT simulate downstream impact”; output = predictive-grade signal (probability, confidence, time, uncertainty).  
   - Actual: Layer 3 “translates belief into consequence”; outputs include `estimated_delay_days`, `impact_severity` per route, and metrics (e.g. transit time, fuel, freight) that describe **consequences**, not only beliefs. That is **simulated impact**.

3. **Recommendation and “what should be done”**  
   - Intended: no recommendations, no “what should be done.”  
   - Actual: “Manual review recommended” and “Manual review recommended for operational decisions” appear in reasoning and assumptions (`impact_translator.py`). That is **operational advice**.

4. **Decision-facing framing and semantics**  
   - Intended: output suitable for downstream systems, but OMEN does not make decisions.  
   - Actual: docstring calls output “decision-grade”; model exposes `is_actionable` and `urgency`, which guide “whether/what to act on” and “how urgently.” That **blurs the line** between signal and decision.

5. **Probability is pass-through, not engine output**  
   - Intended: “Predictive-grade signal” with probability.  
   - Actual: probability is **market pass-through** (`original.probability`). OMEN adds structure and confidence but does not produce a distinct **probability**; it passes through odds. Acceptable if “signal” is “structured view of market belief,” but the engine does not add a separate predictive probability.

---

## D. REQUIRED CHANGES (minimal, to realign with Signal Intelligence role)

Without expanding scope, the **minimum** changes to move back toward a strict Signal Intelligence Engine:

1. **Stop exposing raw data as a primary product**  
   - Option A: Remove `GET /live/events` and `GET /live/events/search`, or restrict them to an internal/debug-only path (e.g. behind a different router or capability).  
   - Option B: Clearly document that these endpoints are **not** part of the Signal Intelligence contract and are for “market discovery” or “debug” only, and do not guarantee compatibility.

2. **Remove recommendation language from outputs**  
   - In `src/omen/domain/services/impact_translator.py`, remove or reword:
     - “Manual review recommended” (e.g. → “No specific model applied; evidence limited.”).
     - “Manual review recommended for operational decisions” in assumptions (e.g. → “No rule matched; assessment is generic and evidence-limited.”).  
   - Do not add new “recommend,” “should,” or “advise” wording in reasoning, summary, or assumptions.

3. **Reframe “decision-grade” and constrain “actionable” / “urgency”**  
   - In `src/omen/domain/models/omen_signal.py`:
     - Change docstring from “decision-grade” to something like “downstream-ready” or “contract-grade” so it does not imply OMEN is producing decisions.  
   - Either:
     - Drop `is_actionable` and `urgency` from the **contract** (make them optional or UI-only), and document that “actionability” and “urgency” are **consumer responsibilities**, or  
     - Keep them but document explicitly that they are **descriptive labels** (e.g. “meets common thresholds for attention”) and **not** recommendations to act or prioritization advice.

4. **Clarify Layer 3 vs “no impact simulation”**  
   - The biggest architectural tension: today Layer 3 is **defined** as “belief → consequence.”  
   - To comply with “does not simulate downstream impact,” at least one of the following is needed:
     - **Option A (strict):** Redefine Layer 3 so it does **not** output delay days, impact severity, or other consequence metrics; restrict output to probability, confidence, time horizon, and perhaps **conditional** statements (“if event occurs, methodology X implies …”) without prescribing “estimated_delay_days” or “impact_severity” as point estimates. Impact modeling then becomes the responsibility of downstream systems (e.g. RiskCast).  
     - **Option B (compromise):** Keep current behavior but **relabel** it in docs and contracts as “**conditional impact estimates**” or “scenario-based impact indicators” — i.e. “if you assume these methodologies, these are the implied consequences,” not “OMEN’s forecast of impact.” Then treat `estimated_delay_days` / `impact_severity` as **methodology-dependent scenario outputs**, not “OMEN’s impact forecast.”  
   - Without one of these, OMEN continues to act as an impact simulator in the sense of the audit.

5. **Document the contract**  
   - Publish a short, versioned **Signal Intelligence contract** (e.g. which fields are stable, semantics of probability vs confidence, and that OMEN does not recommend or decide).  
   - Reference it from the API and from `OmenSignal` / `FullProcessedSignalResponse` so downstream systems can integrate against a fixed role.

---

## Summary

- **Verdict:** OMEN is **not** a strict Signal Intelligence Engine today: it exposes raw data, embeds recommendations, uses decision-facing language and semantics, and implements impact simulation (consequence translation).
- **Evidence:** Code references above for raw APIs, pass-through probability, recommendation text, `is_actionable`/`urgency`, and Layer 3 “belief → consequence” with delay/severity.
- **Gaps:** Raw data exposure; impact simulation; recommendation language; “decision-grade”/actionability/urgency framing; probability as pass-through.
- **Minimum changes:** (1) Demote or remove raw-data APIs from the intelligence contract, (2) remove “recommend” language, (3) reframe “decision-grade” and clarify or restrict actionable/urgency, (4) either remove consequence metrics from the contract or relabel them as conditional/methodology-dependent, (5) document the signal contract and OMEN’s non-decision role.
