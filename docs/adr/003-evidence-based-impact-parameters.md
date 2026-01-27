# ADR-003: Evidence-Based Impact Parameters

## Status

Accepted.

## Context

Impact translation rules (e.g. “Red Sea disruption → +10 days transit”) rely on numeric constants. Those constants must be:

1. Based on evidence where possible
2. Documented with sources and dates
3. Updatable without changing rule logic
4. Auditable for compliance and reviews

## Decision

All impact parameters are defined in `domain/rules/translation/logistics/parameters.py` using a structured record:

```python
@dataclass(frozen=True)
class EvidenceRecord:
    value: float
    unit: str
    source: str
    source_date: date
    notes: str | None = None
```

Example:

```python
RED_SEA_PARAMS: dict[str, EvidenceRecord] = {
    "reroute_transit_increase_days": EvidenceRecord(
        value=10,
        unit="days",
        source="Drewry Maritime Research Q1 2024",
        source_date=date(2024, 2, 1),
        notes="Average for container vessels. Range: 7-14 days."
    ),
    ...
}
```

Rules (e.g. `RedSeaDisruptionRule`) call `get_param(RED_SEA_PARAMS, "reroute_transit_increase_days")` to obtain the value and a citation string.

### Review cadence

Parameters should be reviewed at least quarterly against new market and research data. `source_date` supports “staleness” checks and audit reports.

## Consequences

### Positive

- Assumptions are explicit and traceable.
- Sources and dates are visible in code and docs.
- Changing a number does not require editing rule logic.
- Easier to justify and audit outputs.

### Negative

- Ongoing maintenance to keep sources current.
- Need to track when sources expire or are superseded.
- Real-world events may move faster than quarterly reviews.

## Notes

Evidence and citations are also summarized in `docs/evidence/` where useful for non-developers.
