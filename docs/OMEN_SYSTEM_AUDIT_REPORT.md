# OMEN System Comprehensive Audit Report

**Date:** January 2025  
**Auditor:** Principal Systems Architect (internal)  
**Scope:** Full codebase discovery, architecture analysis, benchmark evaluation, RiskCast readiness

---

## SECTION 1: SYSTEM IDENTITY

**What is OMEN?**  
OMEN is a 4-layer signal intelligence pipeline that ingests raw prediction-market events, validates them, translates probabilities into domain-specific impact assessments, and emits structured **OmenSignal** artifacts for downstream consumption.

**Core purpose and positioning**  
Convert "belief" (market probabilities) into "consequence" (quantified logistics/impact metrics) with explicit explainability, reproducibility, and auditability. It is designed as the intelligence engine that can power risk and supply-chain systems.

**Relationship with downstream systems (RiskCast)**  
OMEN produces **OmenSignal** as the contract. RiskCast (or any consumer) would ingest these via REST, webhook, or message queue. The audit evaluates output-contract compliance and integration readiness in Phase 7.

---

## SECTION 2: ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL WORLD                                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  INPUTS (Port: SignalSource)              OUTPUTS (Port: OutputPublisher)               │
│  • Polymarket (adapter stub)               • ConsolePublisher                           │
│  • StubSignalSource (testing)              • WebhookPublisher                           │
│  • fetch_events() / fetch_events_async()   • KafkaPublisher (stub)                      │
│                                            • publish(signal) -> bool                    │
│  PERSISTENCE (Port: SignalRepository)                                                   │
│  • InMemorySignalRepository               • save(), find_by_id(), find_by_hash(),      │
│                                            find_by_event_id(), find_recent()            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: RawSignalEvent (normalized market event)                                    │
│  event_id, title, description, probability, movement, keywords, market, observed_at   │
│  input_event_hash = hash(event_id, title, probability, volume, source)                │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: SignalValidator → ValidatedSignal                                           │
│  Rules: LiquidityValidationRule only (others orphaned / incompatible)                 │
│  Output: event_id, original_event, category, affected_chokepoints, validation_results,│
│          explanation (ExplanationChain), ruleset_version                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: ImpactTranslator → ImpactAssessment                                         │
│  Rules: RedSeaDisruptionRule (Protocol-compliant); PortClosure/StrikeImpact use       │
│         old contract (ImpactCategory, ImpactSeverity, tuple return) → BROKEN          │
│  Output: metrics, affected_routes, affected_systems, severity, explanation_chain      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: OmenSignal.from_impact_assessment()                                         │
│  Final artifact: signal_id, confidence_level, severity, key_metrics,                  │
│  explanation_chain, input_event_hash, deterministic_trace_id                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  OmenPipeline.process_single(event) → PipelineResult                                  │
│  Idempotency: find_by_hash(input_event_hash); save(signal); publish(signal)           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 3: COMPONENT INVENTORY

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| **Domain models** |
| RawSignalEvent, MarketMetadata | domain/models/raw_signal.py | Layer 1 normalized event | ✅ Current |
| ValidatedSignal, ValidationResult | domain/models/validated_signal.py | Layer 2 output | ✅ Current |
| ImpactAssessment, ImpactMetric, AffectedRoute, AffectedSystem | domain/models/impact_assessment.py | Layer 3 output | ✅ Current |
| OmenSignal | domain/models/omen_signal.py | Layer 4 contract | ✅ Current |
| ExplanationChain, ExplanationStep | domain/models/explanation.py | Audit trail | ✅ Current (no StepType) |
| Common (ConfidenceLevel, SignalCategory, ImpactDomain, ValidationStatus, GeoLocation, ProbabilityMovement) | domain/models/common.py | Shared types | ✅ Current (no GeographicRegion, SignalSource, SignalType, ImpactCategory, ImpactSeverity) |
| **Validation rules** |
| LiquidityValidationRule | domain/rules/validation/liquidity_rule.py | Liquidity check | ✅ Works with Rule[RawSignalEvent, ValidationResult] |
| GeographicRelevanceRule | domain/rules/validation/geographic_relevance_rule.py | Geo relevance | ❌ Uses GeographicRegion, ValidationRule, signal.content, StepType — **broken** |
| SemanticRelevanceRule | domain/rules/validation/semantic_relevance_rule.py | Keyword relevance | ❌ Uses ValidationRule, signal.content, StepType — **broken** |
| AnomalyDetectionRule | domain/rules/validation/anomaly_detection_rule.py | Quality check | ❌ Uses ValidationRule, signal.content, signal.metadata, StepType — **broken** |
| **Translation rules** |
| RedSeaDisruptionRule | domain/rules/translation/logistics/red_sea_disruption.py | Red Sea → logistics impact | ✅ Protocol-compliant, TranslationResult |
| PortClosureRule | domain/rules/translation/logistics/port_closure.py | Port closure → impact | ❌ Uses ImpactCategory, ImpactSeverity, signal.content, tuple return — **broken** |
| StrikeImpactRule | domain/rules/translation/logistics/strike_impact.py | Strike → impact | ❌ Same old contract — **broken** |
| **Services** |
| SignalValidator | domain/services/signal_validator.py | Layer 2 orchestration | ✅ Uses Rule, ValidationResult, new models |
| ImpactTranslator | domain/services/impact_translator.py | Layer 3 orchestration | ✅ Uses ImpactTranslationRule, TranslationResult |
| ConfidenceCalculator | domain/services/confidence_calculator.py | Confidence scoring | ❌ References OMENSignal, assessment.confidence, impact_categories, geographic_regions, source — **broken**, unused in pipeline |
| **Application** |
| OmenPipeline | application/pipeline.py | 4-layer orchestration | ✅ process_single, process_batch, idempotency |
| PipelineConfig, PipelineResult, PipelineStats | application/dto/pipeline_result.py | Result DTOs | ✅ |
| SignalSource, SignalRepository, OutputPublisher | application/ports/ | Hexagonal ports | ✅ |
| **Adapters** |
| StubSignalSource | adapters/inbound/stub_source.py | Test events | ✅ New RawSignalEvent shape |
| PolymarketClient, PolymarketMapper, schemas | adapters/inbound/polymarket/ | Polymarket ingest | ⚠️ Mapper uses SignalSource, SignalType (removed from common) — **broken** |
| InMemorySignalRepository | adapters/persistence/in_memory_repository.py | In-memory store | ✅ find_by_hash, save, find_recent |
| ConsolePublisher | adapters/outbound/console_publisher.py | Stdout | ✅ publish(signal)->bool |
| WebhookPublisher | adapters/outbound/webhook_publisher.py | HTTP webhook | ❌ OMENSignal casing, settings.webhook_url missing from OmenConfig, async-only vs port |
| KafkaPublisher | adapters/outbound/kafka_publisher.py | Kafka stub | ❌ OMENSignal, NotImplementedError |
| **API** |
| main, health, signals, dependencies | api/ | FastAPI | ❌ signals use OMENSignal, list_omen_signals/get_omen_signal (not on port); repository is sync but routes await it |
| **Scripts** |
| run_pipeline.py | scripts/ | CLI runner | ❌ Imports Pipeline, LiquidityRule, fetch_signals, process(), old rule names and contract |
| seed_test_data.py | scripts/ | Seed data | ❌ Uses GeographicRegion, ImpactCategory, ImpactSeverity, OMENSignal(id, source, content…), old explanation — **broken** |
| **Tests** |
| conftest, test_models, test_validation_rules, test_translation_rules, test_pipeline, test_full_pipeline | tests/ | Pytest | ❌ Old model names (SignalSource, SignalType, RawSignalEvent id/raw_content), old ValidationRule/LiquidityRule, Pipeline/process — **tests do not run** |

---

## SECTION 4: DATA MODEL ANALYSIS

**Pydantic models (current domain):**

| Model | Key fields | Notes |
|-------|------------|--------|
| RawSignalEvent | event_id, title, description, probability, movement, keywords, market (MarketMetadata), observed_at, **input_event_hash** (computed) | Hash omits description, movement, keywords, observed_at → **not fully deterministic** for “same event” |
| MarketMetadata | source, market_id, total_volume_usd, current_liquidity_usd, ... | Frozen |
| ValidatedSignal | event_id, original_event, category, affected_chokepoints, validation_results, explanation, ruleset_version, **deterministic_trace_id** (computed) | Frozen |
| ValidationResult | rule_name, rule_version, status, score, reason | Frozen |
| ImpactAssessment | event_id, source_signal, domain, metrics, affected_routes, affected_systems, overall_severity, explanation_steps, explanation_chain, impact_summary, assumptions | Frozen |
| ImpactMetric, AffectedRoute, AffectedSystem | name/value/unit, route_id/route_name/…, system_id/… | Frozen |
| OmenSignal | signal_id, event_id, category, domain, confidence_level, severity, key_metrics, explanation_chain, input_event_hash, ruleset_version, deterministic_trace_id, **is_actionable**, **urgency** | Frozen; _source_assessment in model (excluded from API) |
| ExplanationStep | step_id, rule_name, rule_version, input_summary, output_summary, reasoning, confidence_contribution, **timestamp** (default now) | **timestamp = now → non-deterministic** |
| ExplanationChain | trace_id, steps, total_steps, started_at, completed_at | started_at/completed_at set to now in use → **non-deterministic** |

**Data transformation chain:**

1. **RawSignalEvent** → `input_event_hash` from (event_id, title, probability, total_volume_usd, source). **Gap:** description, movement, keywords, observed_at not in hash.
2. **ValidatedSignal** → `deterministic_trace_id` from (input_event_hash, ruleset_version, "validated"). **Good.**
3. **ImpactAssessment** → `deterministic_trace_id` from (source_signal.deterministic_trace_id, ruleset_version, domain, "impact"). **Good.**
4. **OmenSignal** → `deterministic_trace_id` from (input_event_hash, ruleset_version, domain, "omen_signal"). **Good.**

**Schema gaps/inconsistencies:**

- **Two parallel schemas:** New (event_id, title, probability, market, …) vs old (id, source, signal_type, raw_content, metadata). Tests, scripts, and several rules still assume the old schema; they fail to import or run.
- **ExplanationStep.timestamp** and **ExplanationChain.started_at / completed_at** use `datetime.utcnow()` → reproducibility at “same output” level is compromised if these are stored or compared.
- **input_event_hash** does not include all input fields; replay from “same logical event” with different description/movement/keywords can change downstream output while hash stays same, or vice versa if hash included more later.

---

## SECTION 5: RULE ENGINE ANALYSIS

**Validation rules inventory**

| Rule | Interface | Input | Output | Status |
|------|-----------|--------|--------|--------|
| LiquidityValidationRule | Rule[RawSignalEvent, ValidationResult] | RawSignalEvent | ValidationResult (PASSED / REJECTED_LOW_LIQUIDITY) | ✅ In use |
| GeographicRelevanceRule | Old ValidationRule | RawSignalEvent (expects .content) | (bool, float, List[ExplanationStep]) | ❌ Wrong model; uses GeographicRegion, StepType |
| SemanticRelevanceRule | Old ValidationRule | RawSignalEvent (expects .content) | (bool, float, List[ExplanationStep]) | ❌ Same |
| AnomalyDetectionRule | Old ValidationRule | RawSignalEvent (expects .content, .metadata) | (bool, float, List[ExplanationStep]) | ❌ Same |

Only **LiquidityValidationRule** is wired; the rest are incompatible with current domain and are not registered in the validation __init__ used by the pipeline.

**Translation rules inventory**

| Rule | Protocol / base | Input | Output | Status |
|------|------------------|--------|--------|--------|
| RedSeaDisruptionRule | BaseTranslationRule, ImpactTranslationRule | ValidatedSignal | TranslationResult | ✅ Used by ImpactTranslator |
| PortClosureRule | Old ImpactTranslationRule | ValidatedSignal (.content, .id, .source, …) | (ImpactAssessment \| None, List[ExplanationStep]) | ❌ Old Assessment shape; ImpactCategory, ImpactSeverity, StepType |
| StrikeImpactRule | Same | Same | Same | ❌ Same |

**Rule extensibility**

- **Validation:** New rules must implement `Rule[RawSignalEvent, ValidationResult]` with `apply` and `explain`. Adding a new validator is clear; migrating Geographic/Semantic/Anomaly to this contract is needed.
- **Translation:** Protocol `ImpactTranslationRule` plus `BaseTranslationRule` is clear. New domains (e.g. energy) can add new modules and register rules without touching core. **Gap:** PortClosure and StrikeImpact are still on the old translation contract and must be refactored to return `TranslationResult` and use current models.

---

## PHASE 3: EVALUATION AGAINST GOLD STANDARDS

### BENCHMARK 1: DATA INTEGRITY & REPRODUCIBILITY

**Checklist:**

- [ ] Every output traceable to exact input → **Partial:** event_id and input_event_hash exist; hash excludes description, movement, keywords, observed_at.
- [x] Deterministic: identical input → identical output → **Partial:** Logic is deterministic, but ExplanationStep.timestamp and ExplanationChain started_at/completed_at use `datetime.utcnow()`; if they are part of “output,” replay differs by timestamps.
- [x] Hash-based deduplication → **Yes:** find_by_hash(input_event_hash) in pipeline and repository.
- [x] Version-locked rule execution → **Yes:** ruleset_version in config and passed through.
- [x] Audit trail for every transformation → **Yes:** ExplanationChain and explanation_steps.

**Findings:**

- `input_event_hash` does **not** cover all input fields (description, movement, keywords, observed_at, etc.). Two events that differ only in those can share a hash, or the opposite if hashing is later extended.
- `deterministic_trace_id` is deterministic **given** the same inputs to the hash (input_event_hash, ruleset_version, domain, etc.). Trace ID design is sound.
- Replay from “historical data” is possible only if the stored payload is the same as what was hashed; right now that’s a subset of fields.
- **Non-determinism:** Default `timestamp` in ExplanationStep and `started_at`/`completed_at` in ExplanationChain.

**Score: 6 / 10**  
**Gaps:** Hash input completeness; optional normalization of timestamps in explanations for true replay-equivalence.

---

### BENCHMARK 2: EXPLAINABILITY & AUDITABILITY

**Checklist:**

- [x] Every decision has machine-readable explanation → **Yes:** ExplanationStep list and ExplanationChain.
- [x] No black-box transformations → **Yes:** Rules and steps are explicit.
- [x] Assumptions explicitly documented → **Yes:** RedSeaDisruptionRule (and spec) list assumptions; ImpactAssessment.assumptions.
- [x] Full reasoning chain preserved → **Yes:** explanation_chain and explanation_steps.
- [ ] External auditor can verify any output → **Partial:** Structure supports it; real verification would need stable schema docs and a “reproduce from this event” path.

**Findings:**

- ExplanationChain is populated for the path that uses LiquidityValidationRule + RedSeaDisruptionRule. Orphaned rules (geographic, semantic, anomaly, port_closure, strike_impact) currently do not feed into the live pipeline, so their reasoning is not in the chain.
- Red Sea rule assumptions are explicit and documented.
- **Magic numbers:** Red Sea uses 0.8, 0.75, 0.6 for metric confidence and 1.2 for severity scaling; they are in code but not in a central “rule parameters” or config layer. Minor.

**Score: 8 / 10**  
**Gaps:** Bring orphaned rules into the pipeline with the new contract; consider explicit “rule parameter” docs or config.

---

### BENCHMARK 3: SIGNAL QUALITY & NOISE REJECTION

**Checklist:**

- [x] Clear acceptance/rejection criteria → **Yes:** LiquidityValidationRule (configurable threshold); ValidationStatus.
- [ ] Multi-layer validation → **Partial:** Only liquidity is active; geographic/semantic/anomaly are broken/unused.
- [ ] Manipulation detection → **Partial:** ValidationStatus.REJECTED_MANIPULATION_SUSPECTED exists; no dedicated logic beyond “rule error.”
- [ ] Confidence calibration → **Partial:** ConfidenceLevel.from_score bands (0.4, 0.7); no backtesting or calibration data.
- [ ] False positive rate tracking → **No:** No metrics or tracking.

**Findings:**

- Liquidity threshold (e.g. $1000) is configurable via rule constructor but not clearly justified in docs.
- Geographic/semantic/anomaly are not in the active path → effectively single-layer (liquidity only).
- No cross-market or cross-event consistency checks.

**Score: 4 / 10**  
**Gaps:** Activate and align additional validation rules; add confidence calibration and FPR/quality metrics.

---

### BENCHMARK 4: IMPACT TRANSLATION ACCURACY

**Checklist:**

- [x] Domain-specific impact models → **Yes:** Red Sea logistics (transit, fuel, freight) and explicit assumptions.
- [x] Quantified metrics with units → **Yes:** ImpactMetric (name, value, unit, baseline, confidence).
- [ ] Uncertainty bounds on estimates → **Partial:** Metric-level confidence only; no intervals or bounds.
- [ ] Historical validation of predictions → **No:** No backtesting or accuracy tracking.
- [ ] Cascading impact modeling → **No:** Only direct impacts.

**Findings:**

- Red Sea constants (10 days, 30% fuel, 15% freight) are documented as assumptions; no citation or sensitivity analysis.
- No confidence intervals or min/max ranges.
- No feedback or model-performance loop.

**Score: 5 / 10**  
**Gaps:** Uncertainty bounds; historical validation; optional cascading impacts and sensitivity parameters.

---

### BENCHMARK 5: ARCHITECTURE & EXTENSIBILITY

**Checklist:**

- [x] Domain logic isolated from infrastructure → **Yes:** Domain has no I/O or framework imports.
- [x] Ports & adapters pattern → **Yes:** SignalSource, SignalRepository, OutputPublisher; adapters implement them.
- [x] New data sources pluggable → **Yes:** Implement SignalSource and normalize to RawSignalEvent.
- [x] New domains (energy, insurance) pluggable → **Yes:** New translation rules and ImpactDomain; energy __init__ is placeholder.
- [x] No circular dependencies → **Yes:** Dependency flow is inbound (adapters → app → domain).
- [x] Single Responsibility → **Yes:** Rules, services, and layers are focused.

**Findings:**

- Adding a Kalshi adapter only requires a new SignalSource implementation and RawSignalEvent mapping; no domain change.
- Adding an EnergyImpactRule only requires a new translation module and registration; no change to logistics or core.
- ConfidenceCalculator and some adapters still reference old types (OMENSignal, old Assessment fields); they are either broken or unused but do not contradict the intended boundaries.

**Score: 8 / 10**  
**Gaps:** Remove or fix dead code (e.g. ConfidenceCalculator, old rule files) so the tree compiles and runs cleanly.

---

### BENCHMARK 6: ERROR HANDLING & RESILIENCE

**Checklist:**

- [ ] Graceful degradation → **Partial:** ValidationFailure returns a result with validation_failures; pipeline continues to next event in batch. No “degraded mode” for missing services.
- [ ] No silent failures → **Partial:** Validation and translation failures are logged and returned; repository/publisher are optional. Missing repository → no idempotency; missing publisher → no upstream delivery, but no explicit error to caller.
- [ ] Comprehensive error types → **Partial:** ValidationFailure exists; no domain-specific errors for “source unavailable,” “translation not applicable,” etc.
- [ ] Retry logic with backoff → **No:** None in pipeline or adapters.
- [ ] Circuit breaker → **No:** None.
- [ ] Dead letter queue for failed signals → **No:** Failures only in PipelineResult.error / validation_failures.

**Findings:**

- Polymarket (and any real source) have no retry or circuit breaker; a failing API would surface as raised exceptions.
- If a translation rule raises, ImpactTranslator has no try/except; the exception propagates and process_single fails.
- Repository/publisher failures during save/publish would bubble up; no DLQ or partial-success handling.

**Score: 3 / 10**  
**Gaps:** Retry/backoff for external calls; circuit breaker for sources; explicit handling of “no assessment” and repository/publisher failures; optional DLQ.

---

### BENCHMARK 7: TESTING & QUALITY ASSURANCE

**Checklist:**

- [ ] >80% code coverage → **Unknown:** Tests do not run (import errors from old model names).
- [ ] Unit tests for all rules → **No:** Only LiquidityValidationRule is aligned; others are written for old contracts and fail at import.
- [ ] Integration tests for pipeline → **No:** test_full_pipeline imports old Pipeline, old source interface, old repository methods.
- [ ] Property-based testing → **No:** None.
- [ ] Determinism tests → **No:** None.
- [ ] Regression tests for known scenarios → **No:** No golden scenarios; tests are structurally broken.

**Findings:**

- conftest and tests use SignalSource, SignalType, RawSignalEvent(id, raw_content, metadata), LiquidityRule, Pipeline, process(), etc. These do not exist or differ in the current codebase → **test suite is effectively dead.**
- run_pipeline and integration tests expect `source.fetch_signals()` and `pipeline.process(signal)` (async, old pipeline), and `repository.list_omen_signals()`. Current pipeline is sync process_single; repository has find_recent, not list_omen_signals.

**Score: 1 / 10**  
**Gaps:** Align tests with current models and ports; add determinism and regression tests; measure coverage.

---

### BENCHMARK 8: PERFORMANCE & SCALABILITY

**Checklist:**

- [ ] Sub-second latency for single signal → **Not measured:** No benchmarks or SLAs.
- [ ] Horizontal scaling capability → **Partial:** Stateless pipeline and in-memory repository allow multiple workers; no shared store or partitioning specified.
- [ ] Backpressure handling → **No:** fetch_events is iterator; no explicit backpressure.
- [ ] Memory-efficient processing → **Partial:** Event-by-event processing; no streaming of large payloads.
- [ ] Batch processing support → **Yes:** process_batch(events) exists.

**Findings:**

- Single-event cost is rule application + hashing + model builds; should be well under a second for small batches.
- Throughput untested; 1000/min is plausible for in-memory and simple rules, but unverified.
- Ports define both sync and async (e.g. fetch_events, fetch_events_async; publish, publish_async); pipeline uses sync only. Async path exists for future scaling.

**Score: 5 / 10**  
**Gaps:** Latency/throughput benchmarks; backpressure and scaling design if needed.

---

### BENCHMARK 9: SECURITY & DATA PROTECTION

**Checklist:**

- [x] No secrets in code → **Yes:** .env.example documents vars; config loads from environment.
- [ ] Input validation on all external data → **Partial:** Pydantic validates RawSignalEvent; adapter-level validation (e.g. Polymarket response) is minimal.
- [ ] Rate limiting → **No:** None in API or source adapters.
- [ ] API authentication ready → **No:** No auth on FastAPI or webhook.
- [ ] Sensitive data handling → **Partial:** raw_payload excluded from serialization; no PII taxonomy.

**Findings:**

- API keys (e.g. POLYMARKET_API_KEY) are env-based; .env in .gitignore is assumed.
- WebhookPublisher posts full signal; no redaction of internal fields (e.g. _source_assessment if ever serialized).
- No injection surface in domain logic; API uses path/query params and repository lookup.

**Score: 5 / 10**  
**Gaps:** Rate limiting; auth for API/webhook; document sensitive fields and redaction for external push.

---

### BENCHMARK 10: DOCUMENTATION & MAINTAINABILITY

**Checklist:**

- [x] Docstrings on public functions → **Mostly:** Models and main services are documented; some helpers light.
- [ ] Architecture decision records → **No:** None found.
- [ ] API documentation → **Partial:** FastAPI gives OpenAPI for mounted routes; signals routes are misaligned with repository port.
- [x] Onboarding guide → **Partial:** README has structure, setup, run; no “day one” narrative or design overview.
- [x] Code is self-documenting → **Mostly:** Naming and layers are clear; dead/old code causes confusion.

**Findings:**

- A new engineer would see two “worlds” (new domain vs old scripts/tests) and import errors; one-day understanding is blocked by broken tests and scripts.
- Design choices (hash inputs, rule set, why only liquidity) are not captured in ADRs.

**Score: 5 / 10**  
**Gaps:** ADRs; align README and API with current design; fix or remove obsolete entrypoints and tests.

---

## PHASE 4: CRITICAL FINDINGS

### CRITICAL (must fix before production)

1. **Tests and scripts do not run**  
   conftest/tests/scripts import SignalSource, SignalType, GeographicRegion, ImpactCategory, ImpactSeverity, LiquidityRule, Pipeline, fetch_signals, process, list_omen_signals, get_omen_signal, save_omen_signal, OMENSignal(id, source, content…). These types or signatures no longer exist or differ. **Impact:** No automated regression, no working CLI or seed data.

2. **Partial determinism**  
   ExplanationStep and ExplanationChain use `default_factory=datetime.utcnow` for timestamp/started_at/completed_at. For bit-identical replay, these must either be set from a single “processing time” or omitted from deterministic comparison.

3. **input_event_hash is incomplete**  
   Hash uses (event_id, title, probability, total_volume_usd, source). description, movement, keywords, observed_at (and optionally market_id, liquidity) are omitted. **Impact:** Deduplication and replay can be wrong when those fields differ.

4. **API and repository contract mismatch**  
   signals routes call `repository.list_omen_signals(limit, offset)` and `repository.get_omen_signal(signal_id)` and use `OMENSignal`. The port and InMemorySignalRepository define find_recent(limit, since), find_by_id(signal_id), and use OmenSignal. **Impact:** API cannot run against current repository without code changes or an adapter.

5. **Webhook/Kafka and config**  
   WebhookPublisher uses `settings.webhook_url`; OmenConfig has no webhook_url (and uses OMEN_ prefix). KafkaPublisher and signals routes use `OMENSignal` (wrong casing). **Impact:** Runtime errors or wrong type when those paths are used.

### HIGH PRIORITY (fix within ~2 weeks)

6. **Only one validation rule and one translation rule are active**  
   Geographic, semantic, and anomaly validation plus port_closure and strike_impact translation are incompatible with current domain and are unused. Either migrate them to the new Rule/TranslationResult and models, or remove them and document that only liquidity + Red Sea are in use.

7. **ConfidenceCalculator is broken and unused**  
   It references OMENSignal and Assessment attributes that do not exist. Pipeline confidence comes from OmenSignal.from_impact_assessment. Either delete ConfidenceCalculator or refactor it to the current models and plug it in where needed.

8. **No retries or resilience for external calls**  
   Source fetches and webhook publish have no retries, backoff, or circuit breaker. Any transient failure fails the run or the event.

9. **Polymarket mapper imports removed types**  
   polymarket/mapper uses SignalSource and SignalType from common; those enums were removed. Mapper will fail on import until it uses the new schema (e.g. RawSignalEvent + category inference only, or a new minimal taxonomy).

10. **Repository sync vs API async**  
    SignalRepository methods are synchronous; signals routes use await repository.list_omen_signals() and get_omen_signal(). That suggests either the port should be async or the routes should call sync methods without await. Fix contract and implementation together.

### IMPROVEMENTS (nice to have)

11. **Uncertainty and calibration**  
    Add ranges or intervals to impact metrics; document or implement confidence calibration and quality metrics.

12. **Property-based and determinism tests**  
    Use Hypothesis (or similar) for model and rule properties; add tests that “same input → same output” for pipeline and hashes.

13. **ADRs and runbook**  
    Document “why input_event_hash includes X,” “why only liquidity (for now),” and “how to add a new source/domain”; add a short runbook for deploy and operations.

14. **Backpressure and throughput**  
    If high throughput is required, define batching, backpressure, and async consumption on top of the current ports.

---

## PHASE 5: RECOMMENDATIONS

### Immediate (this week)

1. **Restore a single, runnable path**  
   - Fix run_pipeline to use OmenPipeline, StubSignalSource.fetch_events(), process_single(), and repository.find_recent() (or add a thin list method to the port and repo).  
   - Use only LiquidityValidationRule and RedSeaDisruptionRule and the current models.  
   - Verify end-to-end: stub events → pipeline → ConsolePublisher and repository.

2. **Align API with repository port**  
   - Expose find_recent(limit= limit, since= None) as the “list” semantic, or add list(limit, offset) to the port and implement it in InMemorySignalRepository.  
   - Use find_by_id for get by signal_id.  
   - Use OmenSignal everywhere and fix Webhook/Kafka/Config (webhook_url, OmenSignal casing, publish signature) so that at least one publish path runs.

3. **Fix or remove broken imports**  
   - Either add back compat aliases (e.g. GeographicRegion, SignalSource, SignalType, ImpactCategory, ImpactSeverity, StepType) or remove/rewrite every file that imports them so the tree loads and tests can be updated incrementally.

### Short-term (this month)

4. **Migrate tests to current domain**  
   - conftest: Build RawSignalEvent(event_id, title, probability, market=MarketMetadata(...)), ValidationResult, etc.  
   - test_validation_rules: Use LiquidityValidationRule and Rule/apply/explain; remove or skip tests that depend on old rules until they are migrated.  
   - test_translation_rules: Use ValidatedSignal(original_event=…, category=…, affected_chokepoints=…, …) and RedSeaDisruptionRule.translate → TranslationResult.  
   - test_pipeline: Use OmenPipeline, process_single, PipelineResult.signals, repository.find_recent().  
   - Add one determinism test: same RawSignalEvent (with fixed observed_at or normalized time) → same OmenSignal.deterministic_trace_id and same key fields.

5. **Complete input_event_hash and explanation timestamps**  
   - Either extend input_event_hash to all fields that define “same event” (and document them), or document that hash is “logical id” and that full replay requires storing raw input.  
   - For explanations, pass an explicit “processed_at” into the pipeline and use it in ExplanationStep/Chain so that replay uses that time instead of utcnow().

6. **Error handling and resilience**  
   - Wrap source fetch and webhook publish in retry with backoff (e.g. tenacity).  
   - In ImpactTranslator, catch rule exceptions and return None or a structured “translation failed” instead of raising.  
   - Define explicit behaviors when repository or publisher is missing (e.g. “always require repository if idempotency is required”).

### Long-term (architecture evolution)

7. **Activate multi-layer validation**  
   - Implement GeographicRelevanceRule, SemanticRelevanceRule, AnomalyDetectionRule (or equivalents) on Rule[RawSignalEvent, ValidationResult] and current RawSignalEvent (title, description, keywords, inferred_locations).  
   - Register them in the validator and document order and failure semantics.

8. **Migrate PortClosure and StrikeImpact**  
   - Refactor to BaseTranslationRule/TranslationResult, build ImpactAssessment inside ImpactTranslator from TranslationResult, and use current ValidatedSignal (original_event.title, .description, .keywords, affected_chokepoints).

9. **Observability and product readiness**  
   - Add a small metrics layer (counts: received, validated, translated, published; latencies).  
   - Optional: DLQ or “failed_events” store for signals that fail validation or translation.  
   - Document and, if needed, implement auth and rate limiting for API and webhook.

---

## PHASE 6: FINAL SCORECARD

| Benchmark | Score | Grade |
|-----------|-------|--------|
| Data Integrity & Reproducibility | 6/10 | C |
| Explainability & Auditability | 8/10 | B |
| Signal Quality & Noise Rejection | 4/10 | D |
| Impact Translation Accuracy | 5/10 | D+ |
| Architecture & Extensibility | 8/10 | B |
| Error Handling & Resilience | 3/10 | F |
| Testing & Quality Assurance | 1/10 | F |
| Performance & Scalability | 5/10 | D+ |
| Security & Data Protection | 5/10 | D+ |
| Documentation & Maintainability | 5/10 | D+ |
| **OVERALL** | **50/100** | **D+** |

**Grade scale:** 90–100 production-ready / 80–89 production with gaps / 70–79 beta / 60–69 alpha / &lt;60 prototype.

**Verdict:** OMEN is a **prototype** with a strong architectural spine (hexagonal, clear layers, one validation and one translation rule aligned to the new contract). Production readiness is blocked by broken tests and scripts, incomplete determinism and hashing, only one active validation rule, and missing resilience and test coverage. The design is suitable to evolve into a robust intelligence engine once the critical and high-priority items are addressed.

---

## PHASE 7: RISKCAST INTEGRATION READINESS

### Output contract compliance

- **OmenSignal** contains: signal_id, event_id, category, domain, current_probability, probability_momentum, probability_change_24h, confidence_level, confidence_score, confidence_factors, severity, severity_label, key_metrics, affected_routes, affected_systems, affected_regions, expected_onset_hours, expected_duration_hours, title, summary, detailed_explanation, explanation_chain, input_event_hash, ruleset_version, deterministic_trace_id, source_market, market_url, generated_at, is_actionable, urgency.
- **Open point:** Confirm with RiskCast that these fields and types (and any enums) match their consumer contract. confidence_level (LOW/MEDIUM/HIGH) and is_actionable/urgency are designed to be actionable.
- **Impact metrics:** ImpactMetric has name, value, unit, baseline, confidence. Units in Red Sea rule are “days” and “percent.” Confirm unit and semantics (e.g. “percent” of what) with RiskCast.

### Integration options

- **REST API:** Current FastAPI exposes health and signals. Once routes use the real repository port (find_recent, find_by_id) and OmenSignal, RiskCast can poll GET /api/v1/signals and GET /api/v1/signals/{id}. **Gap:** Pagination is via limit/offset today; repository uses find_recent(limit, since). Align and document.
- **Message queue (Kafka):** KafkaPublisher is a stub (NotImplementedError). For push, implement Kafka publish and (if needed) schema registry. Port already has publish(signal); async can call the same logic.
- **Webhook:** WebhookPublisher exists but needs correct config (webhook_url), sync/async alignment), and OmenSignal casing fixed. RiskCast would register a URL and receive HTTP POST with the signal payload.
- **Direct call:** RiskCast could import OmenPipeline and call process_single(event) or process_batch(events), then read from a shared repository. Requires shipping OMEN as a library and agreeing on event sourcing.

### Data freshness

- **Latency:** From “market event observed” to OmenSignal is one sync run of validation + translation + output build; no explicit polling or scheduling. For a pull-based source, freshness is “when the last fetch ran.” Sub-second per event is realistic for in-memory and current rules; not measured.
- **Acceptability:** Depends on RiskCast use case (e.g. real-time dashboards vs daily reports). Document “event time” (observed_at) vs “processing time” (generated_at) so RiskCast can judge staleness.

### Reliability and SLA

- **SLA:** Not defined. To offer one, add retries, circuit breakers, and clear failure semantics; then define “availability” and “latency” targets.
- **When OMEN is unavailable:** RiskCast must either cache last-known signals, rely on another feed, or treat “no data” as a defined state. OMEN does not currently provide a “last successful run” or heartbeat API; health only confirms process liveness.

---

*End of report. For questions or clarification, refer to the component inventory and the file paths listed in Section 3.*
