# RiskCast Service

RiskCast is a **separate microservice** that runs alongside OMEN.

## Purpose

RiskCast is responsible for:
- Signal ingestion from OMEN
- Signal reconciliation and replay
- Impact assessment (downstream consumer responsibility)

## Deployment

RiskCast runs as a separate container. See `docker-compose.yml`:

```yaml
riskcast:
  build:
    context: .
    dockerfile: Dockerfile.riskcast
  ports:
    - "8001:8001"
```

## Integration with OMEN

OMEN communicates with RiskCast via:
- **Signal Emitter**: Pushes signals to `/api/v1/signals/ingest`
- **Health Check**: Monitors RiskCast at `/health`

## Configuration

Environment variables:
- `RISKCAST_URL`: URL to RiskCast service (default: `http://localhost:8001`)
- `RISKCAST_DB_PATH`: SQLite database path for signal storage

## API Endpoints

- `POST /api/v1/signals/ingest` - Ingest signals from OMEN
- `GET /api/v1/reconcile` - Reconcile and replay signals
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Note

This package is NOT dead code - it's an active microservice.
Do not delete without updating docker-compose.yml and OMEN's signal emitter.
