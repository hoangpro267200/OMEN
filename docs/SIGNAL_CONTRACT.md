# OMEN Signal Contract v2.0

## Purpose

This document defines the ONLY public output contract of the OMEN Signal
Intelligence Engine.

## Design Philosophy

### What OMEN Is

OMEN is a **Signal Intelligence Engine**. It transforms unstructured market
events into structured probability signals with confidence bounds.

### What OMEN Is NOT

OMEN is **not** a decision system. It does not:

- Assess impact or severity
- Determine urgency or priority
- Make recommendations
- Quantify risk exposure
- Steer decisions

### Responsibility Boundary

```
┌─────────────────────────────────────────┐
│ OMEN Responsibility                     │
│                                         │
│ - Probability estimation                │
│ - Confidence measurement                │
│ - Context extraction                    │
│ - Evidence linking                      │
│ - Traceability                          │
└─────────────────────────────────────────┘
                    │
                    ▼ Pure Signal
┌─────────────────────────────────────────┐
│ Consumer Responsibility (e.g. RiskCast) │
│                                         │
│ - Impact assessment                     │
│ - Severity calculation                  │
│ - Urgency determination                 │
│ - Actionability judgment                │
│ - Risk quantification                   │
│ - Decision support                      │
└─────────────────────────────────────────┘
```

## Signal Schema

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| signal_id | string | Unique identifier |
| probability | float | Event likelihood [0,1] |
| confidence_score | float | Signal quality [0,1] |
| confidence_level | enum | HIGH, MEDIUM, LOW |
| confidence_factors | object | Breakdown of confidence |
| temporal_context | object | Time horizon information |
| geographic_context | object | Location relevance |
| evidence | array | Supporting evidence |
| trace_id | string | Deterministic trace |

### Forbidden Fields

The following fields MUST NOT appear in OMEN signal output:

- severity, severity_label
- urgency, priority
- is_actionable, actionable
- delay_days, estimated_delay
- risk_exposure, cost_impact
- recommendation, advice

## Parameter Registry

OMEN's rule parameter registry (`src/omen/domain/rules/registry.py`) contains only parameters used for **signal validation** (e.g. liquidity thresholds). Impact-assessment parameters (freight, transit, fuel, severity, etc.) are **not** registered in OMEN; downstream consumers (e.g. RiskCast) define their own impact parameters.

## Versioning

- Contract version: 2.0.0
- Breaking changes require major version bump
- All responses include `X-OMEN-Contract-Version` header
