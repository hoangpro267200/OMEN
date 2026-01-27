# ADR-004: Validation Rule Design

## Status

Accepted.

## Context

Layer 2 (Validation) must filter and classify raw events consistently. We need:

1. A uniform contract for all validation rules
2. Explainability: each pass/fail must be justified
3. Composable rules (liquidity, geography, semantic, anomaly)
4. Stable order and behavior for reproducibility

## Decision

### Rule contract

Every validation rule implements the domain `Rule` protocol:

- **Input:** `RawSignalEvent` (and optionally `ProcessingContext` for timestamps)
- **Output:** `ValidationResult` with `rule_name`, `rule_version`, `status`, `score`, `reason`
- **Side effect:** None. Rules are pure functions of their inputs.

### Default rule order

`SignalValidator.create_default()` applies rules in this order:

1. **Liquidity** — fast, cheap; filters low-liquidity noise first
2. **Anomaly** — detects manipulation before heavier semantic work
3. **Semantic** — keyword/category relevance
4. **Geographic** — location vs. chokepoints

Order is fixed so that earlier rules reduce load on later ones and so replay is deterministic.

### Explanation

Each rule produces an `ExplanationStep` with:

- `step_id`, `rule_name`, `rule_version`
- `reasoning`, `confidence_contribution`
- `processing_time` (from context)
- `input_summary`, `output_summary` (structured for audit)

Steps are assembled into an `ExplanationChain` on the `ValidatedSignal`. The same pattern is used in translation rules for impact assessments.

### Failure handling

- **`fail_on_rule_error`:** If `True`, the first rule exception fails the event. If `False`, the error is recorded as `REJECTED_RULE_ERROR` and validation continues.
- Rejected events still produce a `ValidationOutcome` with `passed=False`, `rejection_reason`, and `results` (all rule results). The pipeline does not raise; it returns a result with `validation_failures` for inspection and optional DLQ.

## Consequences

### Positive

- All validation is explicit and auditable.
- New rules plug in by implementing the same contract.
- Order and configuration are clear and testable.

### Negative

- Rule order is part of the contract; changing it can change semantics and historical replay.
- Every rule must produce an explanation step, which adds some boilerplate.

## Notes

Validation rules live under `domain/rules/validation/`. Translation rules under `domain/rules/translation/` use a similar explainable pattern but different input/output types.
