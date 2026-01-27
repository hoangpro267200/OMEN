# OMEN API Documentation

## OpenAPI (Swagger)

When the OMEN API server is running:

```bash
uvicorn omen.main:app --reload
```

- **Interactive docs (Swagger UI):** http://localhost:8000/docs  
- **ReDoc:** http://localhost:8000/redoc  
- **OpenAPI JSON:** http://localhost:8000/openapi.json  

## Main endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe |
| GET | `/api/v1/signals` | List signals (requires `X-API-Key`) |
| GET | `/api/v1/signals/{signal_id}` | Get one signal (requires `X-API-Key`) |

## Authentication

Send a valid API key in the header:

```
X-API-Key: your-api-key
```

Keys are configured via `OMEN_SECURITY_API_KEYS` (comma-separated). Invalid or missing key returns `401 Unauthorized`.

## Usage examples

```bash
# List recent signals
curl -H "X-API-Key: dev-key-1" "http://localhost:8000/api/v1/signals?limit=10"

# Get a specific signal
curl -H "X-API-Key: dev-key-1" "http://localhost:8000/api/v1/signals/OMEN-ABC123"
```

## Rate limiting

Responses include headers such as `X-RateLimit-Remaining` and `Retry-After` (when limited). Configure limits via `OMEN_SECURITY_RATE_LIMIT_*` (see `.env.example`).
