# ADR-002: Hexagonal Architecture

## Status

Accepted.

## Context

OMEN must support multiple data sources (Polymarket, Kalshi, stub), multiple output targets (API, webhooks, Kafka, console), multiple domains (logistics, energy, insurance), and keep business logic testable without real I/O.

## Decision

We adopt Hexagonal (Ports and Adapters) architecture.

```
                    +------------------+
                    |     DOMAIN       |
                    |  (pure logic)    |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
        +-----v-----+  +-----v-----+  +-----v-----+
        |   PORTS   |  |   PORTS   |  |   PORTS   |
        | (inbound) |  | (outbound)|  |(persistence)|
        +-----+-----+  +-----+-----+  +-----+-----+
              |              |              |
        +-----v-----+  +-----v-----+  +-----v-----+
        | ADAPTERS  |  | ADAPTERS  |  | ADAPTERS  |
        | Polymarket|  | Webhook   |  | In-Memory |
        | Stub      |  | Kafka     |  | Async     |
        +-----------+  +-----------+  +-----------+
```

### Layers

1. **Domain** (`src/omen/domain/`) — Pure Python, no I/O. Models, rules, services. Zero external dependencies.
2. **Application** (`src/omen/application/`) — Use cases (sync and async pipeline), ports (abstract interfaces), orchestration only.
3. **Adapters** (`src/omen/adapters/`) — Concrete implementations of ports. All I/O lives here. Inbound: signal sources; outbound: publishers; persistence: repositories.

### Rules

1. Domain depends on nothing outside `src/omen/domain/`.
2. Application depends only on domain and declares ports (interfaces).
3. Adapters depend on application ports, not the reverse.
4. Dependency injection at composition root (e.g. main, scripts).

## Consequences

**Positive:** Domain is testable without mocks; new sources/targets are new adapters; clear separation. **Negative:** More files and indirection; team must respect boundaries.

## Notes

Ports live in `application/ports/`. Adapters under `adapters/inbound/`, `adapters/outbound/`, `adapters/persistence/`.
