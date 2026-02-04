# OMEN API Reference

**Version:** 1.0  
**Base URL:** `http://localhost:8000` (development) | `https://api.omen.io` (production)  
**Authentication:** API Key via `X-API-Key` header

---

## Table of Contents

1. [Authentication](#authentication)
2. [Signals API](#signals-api)
3. [Live Mode API](#live-mode-api)
4. [Health API](#health-api)
5. [WebSocket API](#websocket-api)
6. [Error Handling](#error-handling)

---

## Authentication

All API endpoints require authentication via API key.

### Headers

```http
X-API-Key: your-api-key-here
```

### Development Mode

In development (`OMEN_ENV=development`), authentication is bypassed with a warning log. **Never use in production.**

### Rate Limiting

| Plan | Requests/Minute | Burst |
|------|-----------------|-------|
| Free | 60 | 10 |
| Standard | 300 | 50 |
| Enterprise | Unlimited | Unlimited |

---

## Signals API

### List Signals

Retrieve paginated list of signals with optional filters.

```http
GET /api/v1/signals/
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max results (1-500) |
| `offset` | int | 0 | Pagination offset |
| `category` | string | - | Filter by category |
| `source` | string | - | Filter by data source |
| `min_confidence` | float | - | Minimum confidence (0.0-1.0) |
| `max_confidence` | float | - | Maximum confidence (0.0-1.0) |

**Response:**

```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "data_mode": "demo",
  "signals": [
    {
      "id": "OMEN-DEMO001ABCD",
      "title": "Wheat futures surge on drought concerns",
      "category": "commodity",
      "confidence": 0.85,
      "impact": "high",
      "source": {
        "name": "commodity_prices",
        "type": "REAL",
        "provider": "alphavantage"
      },
      "created_at": "2026-02-03T04:00:00Z",
      "expires_at": "2026-02-04T04:00:00Z"
    }
  ]
}
```

### Get Signal by ID

```http
GET /api/v1/signals/{signal_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `signal_id` | string | Signal ID (format: `OMEN-DEMO###XXXX` or `OMEN-LIVE###XXXX`) |

**Response:** Single signal object (same structure as list item)

### Create Signal (Admin)

```http
POST /api/v1/signals/
```

**Request Body:**

```json
{
  "title": "New trading signal",
  "category": "stock",
  "confidence": 0.75,
  "impact": "medium",
  "description": "Detailed signal description...",
  "metadata": {
    "ticker": "AAPL",
    "price_target": 185.00
  }
}
```

---

## Live Mode API

### Get Live Mode Status

Check current data source status and LIVE mode availability.

```http
GET /api/v1/live-mode/status
```

**Response:**

```json
{
  "live_allowed": false,
  "current_mode": "demo",
  "summary": {
    "total_sources": 7,
    "real_count": 5,
    "mock_count": 2,
    "disabled_count": 0
  },
  "sources": {
    "polymarket": {
      "type": "REAL",
      "provider": "gamma_api",
      "status": "healthy"
    },
    "ais": {
      "type": "MOCK",
      "reason": "Using mock data (OMEN_AIS_PROVIDER=mock)"
    }
  },
  "blockers": [
    "ais: Using mock data (OMEN_AIS_PROVIDER=mock)",
    "freight: No real freight provider implemented yet"
  ]
}
```

### Get Production Readiness

Comprehensive production readiness assessment.

```http
GET /api/v1/live-mode/production-readiness
```

**Response:**

```json
{
  "readiness_level": "PARTIAL",
  "data_integrity_score": 71.4,
  "requirements": {
    "authentication": {
      "status": "PASS",
      "details": "API key authentication configured"
    },
    "data_sources": {
      "status": "PARTIAL",
      "real_sources": 5,
      "mock_sources": 2,
      "required_real": 7
    },
    "security": {
      "status": "PASS",
      "features": ["rate_limiting", "audit_logging", "input_validation"]
    }
  },
  "blockers": [
    "AIS provider requires MarineTraffic API key",
    "Freight provider not implemented"
  ],
  "recommendations": [
    "Configure OMEN_AIS_API_KEY for real maritime data",
    "Implement freight data integration"
  ]
}
```

---

## Health API

### Basic Health Check

```http
GET /health/
```

**Response:**

```json
{
  "status": "healthy",
  "service": "omen",
  "active_requests": 3,
  "timestamp": "2026-02-03T04:00:00Z"
}
```

### Readiness Check (Kubernetes)

```http
GET /health/ready
```

Returns `200 OK` when ready, `503 Service Unavailable` during shutdown.

### Liveness Check (Kubernetes)

```http
GET /health/live
```

Always returns `200 OK` if the service is running.

### Authentication Health

```http
GET /health/auth
```

**Response:**

```json
{
  "status": "healthy",
  "environment": "development",
  "api_keys_configured": 1,
  "rate_limiting_enabled": true,
  "audit_logging_enabled": true,
  "production_issues": []
}
```

### Circuit Breakers Status

```http
GET /health/circuit-breakers
```

**Response:**

```json
{
  "timestamp": "2026-02-03T04:00:00Z",
  "summary": {
    "total": 5,
    "closed": 5,
    "open": 0,
    "half_open": 0,
    "healthy": true
  },
  "breakers": {
    "polymarket": {
      "state": "closed",
      "failure_count": 0,
      "total_calls": 150,
      "last_success": "2026-02-03T03:59:55Z"
    }
  }
}
```

### Reset Circuit Breaker

```http
POST /health/circuit-breakers/{name}/reset
```

### Comprehensive System Health

```http
GET /health/system
```

**Response:**

```json
{
  "timestamp": "2026-02-03T04:00:00Z",
  "status": "healthy",
  "components": {
    "requests": {
      "active": 3,
      "shutting_down": false
    },
    "auth": {
      "status": "healthy",
      "api_keys_configured": 1
    },
    "circuit_breakers": {
      "total": 5,
      "open": 0
    },
    "data_sources": {
      "status": "healthy",
      "healthy_count": 7,
      "unhealthy_count": 0
    }
  }
}
```

### Data Source Health

```http
GET /health/sources
```

Check all data source health status.

```http
GET /health/sources/{source_name}
```

Check specific source health.

---

## WebSocket API

### Connect

```
ws://localhost:8000/ws/signals?token={api_key}
```

### Message Types

**Subscribe to signals:**

```json
{
  "type": "subscribe",
  "channels": ["signals", "alerts"]
}
```

**Incoming signal:**

```json
{
  "type": "signal",
  "data": {
    "id": "OMEN-LIVE001ABCD",
    "title": "Breaking: Major market movement",
    "confidence": 0.92,
    "timestamp": "2026-02-03T04:00:00Z"
  }
}
```

**Heartbeat (every 30s):**

```json
{
  "type": "ping"
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "details": {
    "field": "Additional context"
  },
  "trace_id": "abc123def456"
}
```

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Request completed |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server error |
| 503 | Service Unavailable | Shutting down or overloaded |

### Common Error Codes

| Code | Description |
|------|-------------|
| `invalid_api_key` | API key is missing or invalid |
| `rate_limit_exceeded` | Too many requests |
| `invalid_input` | Request validation failed |
| `resource_not_found` | Requested resource doesn't exist |
| `circuit_open` | Service circuit breaker is open |
| `source_unavailable` | Data source is unreachable |

---

## Metrics Endpoint

Prometheus-compatible metrics:

```http
GET /metrics
```

Returns metrics in Prometheus text format including:
- `omen_signals_emitted_total`
- `omen_http_request_duration_seconds`
- `omen_data_source_status`
- `omen_auth_requests_total`
- `omen_circuit_breaker_state`

---

## SDKs & Examples

### Python

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

headers = {"X-API-Key": API_KEY}

# Get signals
response = requests.get(
    f"{BASE_URL}/api/v1/signals/",
    headers=headers,
    params={"limit": 10, "category": "stock"}
)
signals = response.json()
```

### JavaScript/TypeScript

```typescript
const API_KEY = 'your-api-key';
const BASE_URL = 'http://localhost:8000';

async function getSignals() {
  const response = await fetch(`${BASE_URL}/api/v1/signals/?limit=10`, {
    headers: {
      'X-API-Key': API_KEY,
    },
  });
  return response.json();
}
```

### cURL

```bash
# Get signals
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/?limit=10"

# Check health
curl "http://localhost:8000/health/system"
```

---

## Rate Limiting Headers

All responses include rate limiting information:

```http
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 295
X-RateLimit-Reset: 1706932800
```

---

## Changelog

### v1.0 (2026-02-03)
- Initial API release
- Signals CRUD endpoints
- Live mode status API
- Comprehensive health checks
- WebSocket support
- Prometheus metrics
