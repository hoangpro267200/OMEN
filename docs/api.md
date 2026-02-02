# OMEN API Documentation

## Base URL

- **Production:** `https://omen.example.com`
- **Staging:** `https://omen-staging.example.com`
- **Local:** `http://localhost:8000`

Protected routes are under `/api/v1/` and require an API key.

## Authentication

All protected API requests require the **X-API-Key** header:

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://omen.example.com/api/v1/signals/
```

Missing or invalid key returns **401 Unauthorized**.

## Endpoints

### Health & Readiness

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health/` | No | Health check. Returns 503 during shutdown. |
| GET | `/health/live` | No | Liveness (always 200 when process is up). |
| GET | `/health/ready` | No | Readiness (ledger, RiskCast checks; 503 if not ready). |

**Example:**

```bash
curl http://localhost:8000/health/
# {"status":"healthy","service":"omen","active_requests":0,"timestamp":"..."}
```

### Signals (Protected)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/signals/` | List recent signals (paginated). Query: `limit`, `offset`, `since`. |
| GET | `/api/v1/signals/stats` | Pipeline processing statistics (pass rate, rejections, latency). |
| POST | `/api/v1/signals/process` | Fetch events (e.g. Polymarket), run pipeline, return signals. Query: `limit`, `min_liquidity`, `min_confidence`. |
| GET | `/api/v1/signals/{signal_id}` | Get one signal by ID. Query: `detail_level` (minimal, standard, full). |

**List signals response (200):**

```json
{
  "signals": [...],
  "total": 1250,
  "limit": 100,
  "offset": 0
}
```

**Process response (200):**

```json
{
  "signals": [...],
  "total": 10,
  "processed": 12,
  "passed": 10,
  "rejected": 2,
  "pass_rate": 0.833
}
```

**Error responses:**

- **401:** Missing or invalid API key.
- **404:** Signal not found (`GET /api/v1/signals/{id}`).
- **503:** Source unavailable (e.g. Polymarket) when calling `POST /process`.

### Explanations (Protected)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/signals/{signal_id}/explanation` | Get explanation chain for a signal. |
| GET | `/api/v1/parameters` | List all parameters (methodology, validation). |

### Live / Demo (Optional Auth)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/process` | Process events (Polymarket); may require API key depending on config. |
| POST | `/api/v1/process-single` | Process a single raw event. |

### Activity & Stats

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/activity` | Activity feed. |
| GET | `/api/v1/stats` | System stats. |

### UI API (Demo Backend)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ui/overview` | Overview stats for demo UI. |
| GET | `/api/ui/partitions` | Partitions list. |
| GET | `/api/ui/partitions/{partition_date}` | Partition detail. |
| POST | `/api/ui/partitions/{partition_date}/reconcile` | Trigger reconcile (demo). |
| GET | `/api/ui/signals` | Signals list for demo. |
| GET | `/api/ui/ledger/{partition_date}/segments` | Ledger segments. |

### Metrics & Circuit Breakers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/metrics` | Prometheus metrics. |
| GET | `/api/v1/metrics/circuit-breakers` | Circuit breaker status. |
| POST | `/api/v1/metrics/circuit-breakers/{name}/reset` | Reset a circuit breaker. |

### Storage & Debug

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/storage/stats` | Storage statistics. |
| POST | `/api/v1/storage/lifecycle/run` | Trigger lifecycle (e.g. seal, archive). |
| GET | `/api/v1/rejections` | Debug: rejection tracker. |
| GET | `/api/v1/passed` | Debug: passed events. |
| GET | `/api/v1/statistics` | Debug: pipeline statistics. |

### WebSocket

| Path | Description |
|------|-------------|
| WS | `/ws` | WebSocket endpoint (e.g. for real-time updates). |

## Rate Limits

- Configurable via `OMEN_SECURITY_RATE_LIMIT_*` (e.g. 300 req/min, burst 50).
- 429 when exceeded.

## OpenAPI / Swagger

When the API is running, interactive docs are available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

See also: [SIGNAL_CONTRACT.md](SIGNAL_CONTRACT.md), [OMEN_API_EXAMPLES.md](OMEN_API_EXAMPLES.md).
