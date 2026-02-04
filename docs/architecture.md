# OMEN Architecture Documentation

**Version:** 1.0  
**Last Updated:** 2026-02-03

---

## Overview

OMEN (Opportunity & Market Event Navigator) is a **real-time signal intelligence platform** that aggregates data from multiple sources to generate actionable trading and business signals.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OMEN PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Polymarket  │    │    Stock     │    │    News      │               │
│  │   (REAL)     │    │   (REAL)     │    │   (REAL)     │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐               │
│  │  Commodity   │    │   Weather    │    │    AIS       │               │
│  │   (REAL)     │    │   (REAL)     │    │   (MOCK)     │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
│         └───────────────────┼───────────────────┘                        │
│                             ▼                                            │
│                   ┌─────────────────┐                                    │
│                   │  Signal Engine  │                                    │
│                   │   (Pipeline)    │                                    │
│                   └────────┬────────┘                                    │
│                            │                                             │
│              ┌─────────────┼─────────────┐                               │
│              ▼             ▼             ▼                               │
│       ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│       │  REST    │  │WebSocket │  │ Metrics  │                          │
│       │   API    │  │  Stream  │  │ /Logs    │                          │
│       └──────────┘  └──────────┘  └──────────┘                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. Data Integrity First

- **No silent fallbacks** - System never silently falls back to mock data
- **Explicit mode switching** - LIVE/DEMO mode is explicitly controlled
- **Source verification** - Every signal includes provenance metadata

### 2. Fail Fast, Fail Loud

- **Circuit breakers** - Failing services are isolated
- **Health checks** - Continuous monitoring of all components
- **Audit logging** - All security events are logged

### 3. Production Ready

- **Structured logging** - JSON logs with correlation IDs
- **Prometheus metrics** - Full observability stack
- **Kubernetes ready** - Health/readiness probes

---

## Component Architecture

### Backend (Python/FastAPI)

```
src/omen/
├── main.py                      # Application entry point
├── config.py                    # Configuration management
│
├── api/                         # HTTP API layer
│   ├── routes/                  # Route handlers
│   │   ├── signals.py           # Signal CRUD
│   │   ├── live_mode.py         # LIVE mode control
│   │   ├── health.py            # Health endpoints
│   │   └── websocket.py         # WebSocket handlers
│   ├── security.py              # Route dependencies
│   └── models/                  # Request/Response models
│
├── application/                 # Application services
│   ├── pipeline.py              # Signal processing pipeline
│   └── ports/                   # Interface definitions
│
├── domain/                      # Business logic
│   ├── models/                  # Domain entities
│   │   ├── signal.py            # Signal model
│   │   └── context.py           # Processing context
│   ├── rules/                   # Validation rules
│   └── services/                # Domain services
│
├── infrastructure/              # Infrastructure concerns
│   ├── security/                # Security components
│   │   ├── unified_auth.py      # ★ Single auth source
│   │   ├── config.py            # Security config
│   │   ├── validation.py        # Input validation
│   │   └── headers.py           # Security headers
│   ├── data_integrity/          # Data integrity
│   │   └── source_registry.py   # Source classification
│   ├── resilience/              # Fault tolerance
│   │   └── circuit_breaker.py   # Circuit breaker
│   ├── observability/           # Monitoring
│   │   ├── logging.py           # Structured logging
│   │   └── metrics.py           # Prometheus metrics
│   └── realtime/                # Real-time features
│       ├── redis_pubsub.py      # Pub/Sub
│       └── connection_manager.py # WebSocket mgmt
│
└── adapters/                    # External integrations
    └── inbound/                 # Data source adapters
        ├── polymarket/          # Prediction markets
        ├── stock/               # Stock data
        ├── news/                # News API
        ├── commodity/           # Commodity prices
        ├── weather/             # Weather alerts
        ├── ais/                 # Maritime AIS
        └── freight/             # Freight rates
```

### Frontend (React/TypeScript)

```
omen-demo/src/
├── main.tsx                     # App entry point
├── App.tsx                      # Root component
│
├── context/                     # React contexts
│   ├── DataModeContext.tsx      # ★ LIVE/DEMO state
│   └── DemoModeContext.tsx      # Demo scenes
│
├── hooks/                       # Custom hooks
│   ├── useUnifiedData.ts        # Data fetching
│   ├── useSignalData.ts         # Signal hooks
│   └── useOmenApi.ts            # API client
│
├── components/                  # UI components
│   ├── ui/                      # Base components
│   │   ├── DataModeSwitcher.tsx # Mode toggle
│   │   └── MetricCard.tsx       # Metric display
│   ├── dashboard/               # Dashboard widgets
│   └── Layout/                  # App layout
│
├── screens/                     # Page components
│   ├── CommandCenter.tsx        # Main dashboard
│   └── SignalDeepDive.tsx       # Signal details
│
└── lib/                         # Utilities
    ├── api/                     # API client
    └── websocket/               # WebSocket client
```

---

## Data Flow

### Signal Processing Pipeline

```
┌─────────────┐
│ Data Source │
│  (Adapter)  │
└──────┬──────┘
       │ Raw Data
       ▼
┌─────────────┐
│   Parser    │
│ (Normalize) │
└──────┬──────┘
       │ Normalized Signal
       ▼
┌─────────────┐
│  Validator  │
│  (Rules)    │
└──────┬──────┘
       │ Validated Signal
       ▼
┌─────────────┐
│  Enricher   │
│ (Metadata)  │
└──────┬──────┘
       │ Enriched Signal
       ▼
┌─────────────┐
│   Emitter   │
│ (Publish)   │
└──────┬──────┘
       │
       ├────► REST API
       ├────► WebSocket
       └────► Metrics
```

### Authentication Flow

```
Request
   │
   ▼
┌─────────────────┐
│ Extract API Key │
│ (Header/Query)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────┐
│  Rate Limiter   │────►│   REJECT    │
│   (Check)       │     │   (429)     │
└────────┬────────┘     └─────────────┘
         │ Pass
         ▼
┌─────────────────┐     ┌─────────────┐
│  Validate Key   │────►│   REJECT    │
│   (Config)      │     │   (401)     │
└────────┬────────┘     └─────────────┘
         │ Valid
         ▼
┌─────────────────┐
│  Audit Log      │
│  (Success)      │
└────────┬────────┘
         │
         ▼
     Continue
```

---

## Data Source Classification

### Source Types

| Type | Description | LIVE Mode |
|------|-------------|-----------|
| **REAL** | Production API with valid credentials | ✅ Allowed |
| **MOCK** | Generated/simulated data | ❌ Blocked |
| **DISABLED** | Source turned off | ➖ Ignored |

### Current Sources

| Source | Type | Provider | Notes |
|--------|------|----------|-------|
| Polymarket | REAL | Gamma API | Prediction markets |
| Stock | REAL | yfinance + vnstock | Stock prices |
| News | REAL | NewsAPI | News articles |
| Commodity | REAL | Alpha Vantage | Commodity prices |
| Weather | REAL | OpenWeatherMap | Weather alerts |
| AIS | MOCK | Internal generator | Needs MarineTraffic API |
| Freight | MOCK | Internal generator | Needs Freightos API |

---

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────┐
│            Security Headers             │  ← Layer 1: Transport
│  (HSTS, X-Frame-Options, CSP, etc.)     │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│             Rate Limiting               │  ← Layer 2: DoS Protection
│    (Per-key, Per-IP throttling)         │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           Authentication                │  ← Layer 3: Identity
│       (API Key validation)              │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│          Input Validation               │  ← Layer 4: Data Integrity
│   (SQL injection, XSS prevention)       │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│            Audit Logging                │  ← Layer 5: Accountability
│    (All security events logged)         │
└─────────────────────────────────────────┘
```

### Security Features

- **API Key Authentication** - Configurable via environment
- **Rate Limiting** - In-memory with configurable limits
- **Input Validation** - SQL injection and XSS prevention
- **Security Headers** - Full suite of HTTP security headers
- **Audit Logging** - All auth events logged with correlation IDs
- **CORS** - Environment-aware configuration

---

## Resilience Patterns

### Circuit Breaker

```
      ┌─────────┐
      │ CLOSED  │ ◄─── Normal operation
      └────┬────┘
           │ Failures > threshold
           ▼
      ┌─────────┐
      │  OPEN   │ ◄─── Fail fast (reject requests)
      └────┬────┘
           │ After timeout
           ▼
      ┌─────────┐
      │HALF_OPEN│ ◄─── Test recovery
      └────┬────┘
           │
     ┌─────┴─────┐
     │           │
  Success     Failure
     │           │
     ▼           ▼
  CLOSED       OPEN
```

### Retry with Exponential Backoff

```python
@with_source_retry(max_attempts=3, min_wait=1.0, max_wait=30.0)
async def fetch_data():
    # Attempt 1: immediate
    # Attempt 2: wait 1s
    # Attempt 3: wait 2s
    pass
```

---

## Observability Stack

### Logging

- **Format**: Structured JSON
- **Correlation**: trace_id, request_id per request
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Metrics (Prometheus)

- `omen_signals_emitted_total` - Signal counts
- `omen_http_request_duration_seconds` - Latency histograms
- `omen_data_source_status` - Source health gauges
- `omen_circuit_breaker_state` - Circuit states

### Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/health/` | Basic health |
| `/health/ready` | Kubernetes readiness |
| `/health/live` | Kubernetes liveness |
| `/health/system` | Comprehensive status |
| `/health/auth` | Auth system health |
| `/health/circuit-breakers` | Circuit states |

---

## Deployment

### Environment Variables

```bash
# Core
OMEN_ENV=production          # development|production

# Security
OMEN_SECURITY_API_KEYS=key1,key2
OMEN_SECURITY_CORS_ORIGINS=https://app.omen.io

# Data Sources
NEWS_API_KEY=xxx
ALPHAVANTAGE_API_KEY=xxx
OPENWEATHERMAP_API_KEY=xxx

# Infrastructure (optional)
REDIS_URL=redis://localhost:6379
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
CMD ["uvicorn", "omen.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: omen
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: omen
        image: omen:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
        env:
        - name: OMEN_ENV
          value: production
```

---

## Performance Considerations

### Caching Strategy

- **Signal cache**: 30-second TTL for frequently accessed signals
- **Health cache**: 30-second TTL for source health checks
- **Rate limit**: In-memory with automatic cleanup

### Scaling

- **Horizontal**: Stateless design allows multiple instances
- **Redis**: Optional for shared state (WebSocket, rate limiting)
- **Database**: PostgreSQL for persistent storage (optional)

---

## Future Roadmap

1. **Additional Data Sources**
   - MarineTraffic AIS integration
   - Freightos freight rates
   - Social sentiment analysis

2. **Enhanced Analytics**
   - ML-based signal scoring
   - Historical trend analysis
   - Correlation detection

3. **Enterprise Features**
   - Multi-tenant support
   - Custom alert rules
   - API usage dashboard
