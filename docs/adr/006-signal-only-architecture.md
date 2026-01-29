# ADR 006: Signal-Only Architecture

## Status

Accepted

## Context

OMEN was originally designed with integrated impact translation. Audit
revealed this violates Signal Intelligence Engine principles:

- Role confusion (signal vs. impact)
- Decision steering (urgency, actionability)
- Tight coupling with downstream concepts

## Decision

OMEN will produce ONLY pure signals. Impact assessment is delegated to
downstream consumers.

## Consequences

### Positive

- Clear responsibility boundary
- Reusable across different impact models
- Auditable and certifiable
- Consumer independence

### Negative

- Breaking change for existing integrations
- Impact logic must be duplicated or imported by consumers
- Additional integration step for consumers

## Migration

1. Phase 1: Pure contract as default
2. Phase 2: API surface cleanup
3. Phase 3: Impact isolation
4. Phase 4: Language compliance
5. Phase 5: Consumer migration support
