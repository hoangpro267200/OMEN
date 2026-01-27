# Changelog

All notable changes to OMEN are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

## [Unreleased]

### Added

- Async pipeline (`AsyncOmenPipeline`) for high-throughput processing with backpressure.
- Async signal repository port and in-memory implementation.
- Performance monitoring (`PipelineMetrics`, `LatencyStats`, `ThroughputStats`) in `infrastructure/monitoring/`.
- Performance benchmarks in `tests/benchmarks/` (sync/async latency, throughput, backpressure, memory).
- Comprehensive README with quick start, architecture overview, and project structure.
- Architecture Decision Records (ADRs) for deterministic processing, hexagonal architecture, evidence-based parameters, validation rule design, and security.
- Onboarding guide and API documentation outline.
- CONTRIBUTING.md and CHANGELOG.md.

### Changed

- None yet.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Polymarket mapper updated to use current `RawSignalEvent` and `MarketMetadata` schema (removes broken imports of non-existent types).

## [0.1.0] — Initial release

- 4-layer pipeline: RawSignalEvent → ValidatedSignal → ImpactAssessment → OmenSignal.
- Validation rules: liquidity, anomaly, semantic, geographic.
- Translation rules: Red Sea disruption, port closure, strike impact.
- Stub and Polymarket (stub) signal sources.
- In-memory repository and console/webhook publishers.
- FastAPI API with health and signals endpoints.
- Security: API key auth, rate limiting, CORS, input validation, redaction, audit logging.
- Deterministic processing and replay via `ProcessingContext` and `input_event_hash`.

[Unreleased]: https://github.com/your-org/omen/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/omen/releases/tag/v0.1.0
