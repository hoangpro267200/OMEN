# OMEN Architecture

## High-Level Architecture

OMEN is a **Signal Intelligence Engine**: it ingests raw events (e.g. from prediction markets), validates and enriches them, and emits structured **OmenSignal** artifacts for downstream systems (RiskCast, BI, webhooks). The core follows a **hexagonal / clean architecture** with domain, application, and adapters.

### Conceptual Data Flow (Dual-Write / Downstream)

```
┌─────────────────┐
│   Client API    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Signal Emitter │──────┐
│  (Dual Write)   │      │
└────────┬────────┘      │
         │               │
         ├───────────────┼─────────┐
         ▼               ▼         ▼
    ┌────────┐    ┌──────────┐  ┌──────────┐
    │ Ledger │    │ RiskCast │  │ Metrics  │
    │  (WAL) │    │   (API)  │  │ (Prom)   │
    └────────┘    └──────────┘  └──────────┘
         │               │
         └───────┬───────┘
                 ▼
         ┌──────────────┐
         │ Reconciler   │
         │ (Periodic)   │
         └──────────────┘
```

*Note: Ledger, RiskCast, and Reconciler are part of the broader OMEN ecosystem; the core `src/omen/` pipeline produces OmenSignal and can write to ledger/outbound publishers.*

### Components

#### 1. Signal Pipeline (Core)

**Responsibility:** Validate → Enrich → Emit OmenSignal  
**Technologies:** FastAPI, asyncio, Pydantic  
**Location:** `src/omen/application/pipeline.py`, `signal_pipeline.py`

**Flow:**

1. **Layer 1:** Inbound adapter (Polymarket, Stub) produces **RawSignalEvent**.
2. **Layer 2:** **SignalValidator** runs validation rules (liquidity, semantic, geographic, anomaly). Output: **ValidatedSignal** or reject.
3. **Layer 3:** **SignalEnricher** and **SignalClassifier** produce **OmenSignal** (probability, confidence, context, evidence, routing hints).
4. **Output:** OmenSignal is saved to **SignalRepository** and optionally published via **OutputPublisher** (console, webhook, Kafka).

**Idempotency:** Pipeline checks `repository.find_by_hash(event.input_event_hash)` before processing; duplicate events return cached result.

#### 2. Ledger (When Used)

**Responsibility:** Immutable event log (append-only WAL).  
**Technologies:** File-based WAL, partitioned by date.

**Structure (typical):**

```
ledger/
├── 2026-01-30/
│   ├── signals-000001.wal
│   ├── signals-000002.wal
│   └── _SEALED
├── 2026-01-30-late/
│   └── signals-000001.wal
└── 2026-01-31/
    └── signals-000001.wal
```

**Features:** Partitioning by date, late-arriving partitions, sealing, compression, archival. See `src/omen/infrastructure/ledger/` when integrated.

#### 3. RiskCast / Downstream

**Responsibility:** Primary consumer of OmenSignal (impact assessment, storage, dashboards).  
**Location:** Separate service; OMEN publishes signals via **OutputPublisher** (webhook, Kafka) or repository.

OMEN does **not** implement RiskCast; it produces the signal contract (**OmenSignal**) that downstream systems consume.

#### 4. Reconciler

**Responsibility:** Detect and repair data drift between Ledger and downstream (e.g. RiskCast).  
**Process:** Read Ledger partition → query downstream for same partition → compare IDs → replay missing signals.  
**Location:** `src/riskcast/` or separate job when ledger + RiskCast are in use.

#### 5. Observability

- **Logging:** Structured JSON with trace context (`src/omen/infrastructure/observability/logging.py`).
- **Metrics:** Prometheus (`GET /metrics`), pipeline stats, circuit breakers (`/api/v1/metrics/circuit-breakers`).
- **Tracing:** Request tracking middleware; OpenTelemetry can be added.

## Data Flow

### Happy Path

```
Client → API → Pipeline → [Repository + Publisher] → Success
```

### Source Unavailable (e.g. Polymarket)

```
POST /api/v1/signals/process → Pipeline → 503 SourceUnavailableError
```

### Reconciliation (When Ledger + Downstream Exist)

```
Scheduler → Reconciler → Read Ledger partition → Query downstream → Compare → Replay missing
```

## Design Decisions

### Why Hexagonal?

- **Domain** is independent of I/O and frameworks.
- **Ports** (interfaces) define contracts; **adapters** implement them.
- Easy to swap sources (Stub, Polymarket) and outputs (console, webhook, Kafka).

### Why File-Based Ledger (When Used)?

- Simplicity; no external DB for WAL.
- Natural partitioning by date; easy backup/archive.
- Alternative: Kafka or DB can be used via adapters.

### Why Reconciliation?

- Data drift is inevitable in distributed systems.
- Periodic comparison + replay keeps Ledger and downstream in sync.

## Scalability

- **Single instance:** Throughput limited by validation/enrichment and I/O.
- **Scaling:** Partition by signal source; vertical scaling; optional horizontal scaling with shared repository/queue.
- **Ledger:** Disk I/O bound; EFS/S3 for distributed storage in production.
- **Repository:** In-memory by default; PostgreSQL or other store via adapter for production.

## Security Architecture

### Authentication

- **API key** via `X-API-Key` for protected routes (`/api/v1/signals`, explanations, etc.).
- Keys validated in `src/omen/infrastructure/security/auth.py`; optional rotation in `key_rotation.py`.

### Data Protection

- HTTPS in production; security headers middleware.
- Secrets redaction in logs (`redaction.py`).
- Encryption at rest where configured (Secrets Manager, EFS).

### Network

- Private VPC in production (Terraform); security groups; no public DB access.

---

See also: [ADR-002 Hexagonal Architecture](adr/002-hexagonal-architecture.md), [ADR-005 Security Model](adr/005-security-model.md), [README Quick Start](../README.md).
