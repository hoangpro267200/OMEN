# ADR 001: Deterministic Processing and Data Lineage

## Status

Accepted.

## Context

OMEN must support full auditability, reproducibility, and replay from historical data. The initial design had several sources of non-determinism:

- **input_event_hash** omitted fields that define event identity (description, movement, keywords, observed_at), so different representations of the same logical event could hash differently or duplicates could be missed.
- **ExplanationStep** and **ExplanationChain** used `datetime.utcnow()` for timestamps, so the same input processed at different times produced different explanations and trace metadata.
- No single “processing time” was passed through the pipeline, so output timestamps could differ across layers and replay could not reproduce bit-identical output.

This made it impossible to guarantee: *identical input + same ruleset → bit-identical output*.

## Decision

### 1. Canonical input_event_hash

The `input_event_hash` on `RawSignalEvent` is the canonical fingerprint for event identity and deduplication. It includes **all** fields that define identity:

- `event_id`, `title`, `description` (or `""`)
- `probability` (fixed precision, e.g. `.10f`)
- `movement` (serialized as `current|previous|delta|window_hours` when present)
- `keywords` (sorted for determinism, joined)
- `market.source`, `market.market_id`, `market.total_volume_usd`, `market.current_liquidity_usd` (fixed precision)

Excluded by design: `observed_at` (observation time, not identity), `raw_payload` (debug), `inferred_locations` (derived).

### 2. ProcessingContext

A single **ProcessingContext** (frozen dataclass) carries:

- `processing_time: datetime` — the one timestamp used for all output timestamps in that run
- `ruleset_version: RulesetVersion`
- `trace_id: TraceId` — derived deterministically from `processing_time` and `ruleset_version`

- **`ProcessingContext.create(ruleset_version)`** — uses current UTC time; for normal runs.
- **`ProcessingContext.create_for_replay(processing_time, ruleset_version)`** — uses a given time; for replay and tests.

All timestamps in explanations, validated signals, impact assessments, and OMEN signals should be set from `context.processing_time`.

### 3. Explicit timestamps in explanations

- **ExplanationStep**: `timestamp` is required (no default). Use `ExplanationStep.create(..., processing_time=context.processing_time)` when building steps from a context.
- **ExplanationChain**: `started_at` is required. Use `ExplanationChain.create(context)` and `finalize(context)` so `started_at` and `completed_at` come from the context.

Rules that build explanation steps accept an optional `processing_time` (e.g. in `explain(..., processing_time=None)`) and pass it into steps so that validation and translation stay deterministic when a context is provided.

### 4. Pipeline and services

- **Pipeline**: `process_single(event, context=None)`. If `context` is `None`, the pipeline creates one via `ProcessingContext.create(config.ruleset_version)`. Callers can pass a context for replay.
- **Validator**: `validate(event, context: ProcessingContext)`. Builds the explanation chain with `ExplanationChain.create(context)` and uses `context.processing_time` for step timestamps and `validated_at`.
- **Translator**: `translate(signal, domain, context: ProcessingContext)`. Uses `context.processing_time` for step timestamps, chain start/complete, and `assessed_at`.
- **OmenSignal.from_impact_assessment(..., generated_at=None)**: When building the final signal, pass `generated_at=context.processing_time` for determinism.

### 5. Versioning and replay

- Same **RawSignalEvent** (by `input_event_hash`) + same **ProcessingContext** (same `processing_time` and `ruleset_version`) + same rule code → **bit-identical** output.
- Replay is done by calling `process_single(event, context=ProcessingContext.create_for_replay(processing_time, ruleset_version))` with the desired historical time and ruleset version.

## Consequences

- **Positive**
  - Full audit trail: every output timestamp ties back to a single processing time.
  - Reproducibility: replay with the same context yields identical JSON/output.
  - Clear data lineage: trace ids and hashes are deterministic and documentable.
  - Tests can use `ProcessingContext.create_for_replay(...)` for stable, deterministic assertions.

- **Negative**
  - Rules and services must accept and forward `processing_time` (or a context) where deterministic behavior is required.
  - Call sites that build `ExplanationStep` or `ExplanationChain` directly must supply timestamps or use the context-based factories.

- **Neutral**
  - `ProcessingContext` is immutable and easy to pass through layers. Default `context=None` in `process_single` keeps existing callers working while enabling replay when needed.
