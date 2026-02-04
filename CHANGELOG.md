# Changelog

All notable changes to OMEN are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

## [Unreleased]

### Added

- **Production Hardening** (v2.1.0 prep)
  - Event fingerprinting for cross-source correlation (`EventFingerprint`, `EventFingerprintCache`)
  - Production startup validation (`startup_checks.py`)
  - Enhanced health checks with Redis and database connectivity
  - Deployment verification script (`scripts/verify-deployment.sh`)
  - Complete production Docker Compose with PostgreSQL, Redis, Prometheus, Grafana
  - Production configuration templates (`.env.production.example`)
  - Deployment guide (`DEPLOYMENT.md`)

- Certification check script `scripts/certification_check.py` for Signal Intelligence Engine compliance (target 90+/100).
- Async pipeline (`AsyncOmenPipeline`) for high-throughput processing with backpressure.
- Async signal repository port and in-memory implementation.
- Performance monitoring (`PipelineMetrics`, `LatencyStats`, `ThroughputStats`) in `infrastructure/monitoring/`.
- Performance benchmarks in `tests/benchmarks/` (sync/async latency, throughput, backpressure, memory).
- Comprehensive README with quick start, architecture overview, and project structure.
- Architecture Decision Records (ADRs) for deterministic processing, hexagonal architecture, evidence-based parameters, validation rule design, and security.
- Onboarding guide and API documentation outline.
- CONTRIBUTING.md and CHANGELOG.md.

### Changed

- `CrossSourceValidationRule` now uses fingerprint-based matching (v2.0.0 of the rule)
  - Provides confidence boost up to +35% when multiple sources confirm
  - Uses global fingerprint cache for event matching

### Deprecated

- None.

### Removed

- `src/omen_impact/` package (15 files) - isolated for separate RiskCast service
- Impact assessment is now downstream consumer responsibility

### Fixed

- Polymarket mapper updated to use current `RawSignalEvent` and `MarketMetadata` schema (removes broken imports of non-existent types).

## [2.0.0] — Signal-only architecture (certified)

### Breaking changes

- **OmenSignal** no longer contains impact fields (severity, urgency, is_actionable, delay_days, risk_exposure, key_metrics). See `docs/SIGNAL_CONTRACT.md` v2.0.
- **Stats API** no longer exposes `critical_alerts` or `total_risk_exposure`; use `high_confidence_signals` and treat risk as consumer responsibility.
- **Activity and debug** use `confidence_level` / `confidence_label` instead of `severity` in event payloads and PassedRecord.
- **Pipeline metrics** no longer compute or store `total_risk_exposure_usd`; risk quantification is consumer responsibility. `complete_batch(..., total_risk_exposure_usd=...)` has been removed.
- **/live/events** and other raw-data-only endpoints are out of the certified public API surface; pure signal contract only.

### Migration guide (consumers, e.g. RiskCast)

1. **Impact and decisions** — Import and use the `omen_impact` package for impact assessment, severity, time-horizon, and actionability. OMEN core outputs only probability, confidence, and context.
2. **Response parsing** — Drop expectations for `severity`, `urgency`, `is_actionable`, `delay_days`, `risk_exposure` on signal or stats. Rely on `probability`, `confidence_score`, `confidence_level`, `temporal`, `geographic`, `evidence`, `trace_id`.
3. **Activity/debug** — If you depended on `details["severity"]` or PassedRecord `severity`, switch to `details["confidence_level"]` and PassedRecord `confidence_level`.
4. **Metrics** — If you called `complete_batch(total_risk_exposure_usd=...)` or read risk from stats, remove that; implement risk in your own layer.

### Added

- `scripts/certification_check.py`: validates D1–D7 dimensions (role purity, signal structure, API surface, language, architecture, auditability).
- `docs/SIGNAL_CONTRACT.md` v2.0 and `docs/adr/006-signal-only-architecture.md`.

### Removed

- Risk exposure computation from `PipelineMetricsCollector` and `ProcessingBatch`.
- Parameter `total_risk_exposure_usd` from `complete_batch()` and from `get_stats()` output.

## [0.1.0] — Initial release

- 4-layer pipeline: RawSignalEvent → ValidatedSignal → ImpactAssessment → OmenSignal.
- Validation rules: liquidity, anomaly, semantic, geographic.
- Translation rules: Red Sea disruption, port closure, strike impact.
- Stub and Polymarket (stub) signal sources.
- In-memory repository and console/webhook publishers.
- FastAPI API with health and signals endpoints.
- Security: API key auth, rate limiting, CORS, input validation, redaction, audit logging.
- Deterministic processing and replay via `ProcessingContext` and `input_event_hash`.

[Unreleased]: https://github.com/your-org/omen/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/your-org/omen/compare/v0.1.0...v2.0.0
[0.1.0]: https://github.com/your-org/omen/releases/tag/v0.1.0
