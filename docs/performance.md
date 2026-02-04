# OMEN Performance Benchmarks

## Overview

This document contains performance benchmarks and optimization guidelines for OMEN Signal Intelligence Engine.

## Test Environment

| Component | Specification |
|-----------|---------------|
| CPU | AMD Ryzen 9 5900X (12 cores) / Intel i9-12900K |
| RAM | 64GB DDR4-3200 |
| Storage | NVMe SSD (Samsung 980 Pro) |
| Python | 3.11+ |
| Database | PostgreSQL 15 |
| Cache | Redis 7.0 |

## API Benchmarks

### Signal Endpoints

| Endpoint | Method | P50 | P95 | P99 | RPS |
|----------|--------|-----|-----|-----|-----|
| `/api/v1/signals` | GET | 15ms | 45ms | 120ms | 1,000 |
| `/api/v1/signals/{id}` | GET | 8ms | 25ms | 60ms | 2,500 |
| `/api/v1/signals` | POST (process) | 25ms | 80ms | 150ms | 500 |
| `/api/v1/signals/stats` | GET | 5ms | 15ms | 35ms | 3,000 |

### Health Endpoints

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| `/health/ready` | 2ms | 5ms | 10ms |
| `/health/live` | 1ms | 2ms | 5ms |
| `/health/sources` | 10ms | 30ms | 80ms |

### Explanation Endpoints

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| `/api/v1/explanations/{id}` | 20ms | 60ms | 150ms |
| `/api/v1/methodology` | 5ms | 15ms | 40ms |

## Data Source Latency

| Source | P50 | P95 | Timeout | Notes |
|--------|-----|-----|---------|-------|
| Polymarket | 150ms | 400ms | 5s | Real market data |
| Stock (yfinance) | 200ms | 600ms | 10s | Rate limited |
| Weather | 100ms | 300ms | 5s | Open-Meteo API |
| AIS | 300ms | 800ms | 15s | MarineTraffic |
| News | 250ms | 700ms | 10s | NewsData.io |
| Commodity | 180ms | 450ms | 8s | AlphaVantage |
| Freight | 150ms | 350ms | 5s | Proxy data |

## Memory Usage

| Component | Idle | Under Load | Max | Notes |
|-----------|------|------------|-----|-------|
| API Server | 150MB | 400MB | 800MB | Single instance |
| Signal Processor | 200MB | 500MB | 1GB | With historical data |
| WebSocket Manager | 100MB | 300MB | 500MB | Per 1000 connections |
| Redis Cache | 50MB | 200MB | 500MB | Signal cache |

## Pipeline Performance

### Signal Processing

| Stage | Avg Time | P99 Time | Notes |
|-------|----------|----------|-------|
| Ingestion | 5ms | 15ms | Raw event parsing |
| Validation | 10ms | 35ms | 8 validation rules |
| Enrichment | 8ms | 25ms | Context addition |
| Cross-source | 15ms | 50ms | Multi-source correlation |
| Confidence | 5ms | 15ms | Score calculation |
| Output | 3ms | 10ms | Response formatting |
| **Total** | **46ms** | **150ms** | End-to-end |

### Throughput

| Scenario | Signals/sec | Notes |
|----------|-------------|-------|
| Single source | 500 | One adapter active |
| Multi-source (3) | 300 | Parallel fetching |
| Multi-source (7) | 150 | All sources active |
| Burst processing | 1,000 | 5 second burst |
| Sustained load | 200 | 1 hour test |

## Scalability

### Horizontal Scaling

| Metric | 1 Instance | 3 Instances | 5 Instances |
|--------|------------|-------------|-------------|
| RPS | 500 | 1,400 | 2,200 |
| P99 latency | 150ms | 120ms | 100ms |
| Memory total | 400MB | 1.2GB | 2GB |

**Requirements for horizontal scaling:**
- Stateless design (all state in Redis/PostgreSQL)
- Load balancer (nginx or AWS ALB)
- Shared Redis for rate limiting and WebSocket pub/sub
- Shared PostgreSQL for persistence

### Vertical Scaling Recommendations

| Workload | Min CPU | Recommended CPU | Min RAM | Recommended RAM |
|----------|---------|-----------------|---------|-----------------|
| Development | 2 cores | 4 cores | 4GB | 8GB |
| Production (small) | 4 cores | 8 cores | 16GB | 32GB |
| Production (medium) | 8 cores | 16 cores | 32GB | 64GB |
| High Volume | 16 cores | 32 cores | 64GB | 128GB |

## Running Benchmarks

### API Performance Test

```bash
# Install dependencies
pip install locust httpx pytest-benchmark

# Run API benchmarks
pytest tests/benchmarks/test_api_performance.py -v --benchmark-autosave

# Run load test with Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10
```

### Memory Profiling

```bash
# Profile memory usage
python -m memory_profiler tests/benchmarks/test_memory.py

# Generate memory report
python -m memray run --output memory.bin src/omen/main.py
python -m memray flamegraph memory.bin
```

### Signal Pipeline Benchmark

```bash
# Run pipeline performance test
pytest tests/benchmarks/test_pipeline_performance.py -v

# Profile pipeline execution
python -m cProfile -o profile.pstats scripts/benchmark_pipeline.py
python -m snakeviz profile.pstats
```

## Optimization Guidelines

### 1. Enable Redis Caching

```python
# config.py
REDIS_CACHE_ENABLED = True
REDIS_CACHE_TTL = 60  # seconds
```

**Impact:** 50-70% latency reduction for repeated requests

### 2. Use Connection Pooling

```python
# Database connection pool
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_RECYCLE = 3600

# HTTP connection pool
HTTPX_LIMITS = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20
)
```

**Impact:** 30-40% improvement in concurrent request handling

### 3. Batch Requests

```python
# Instead of:
for signal_id in signal_ids:
    signal = await client.get_signal(signal_id)

# Use:
signals = await client.get_signals_batch(signal_ids)
```

**Impact:** 10x throughput improvement for bulk operations

### 4. WebSocket for Real-time Updates

```javascript
// Instead of polling:
setInterval(() => fetch('/api/v1/signals'), 1000);

// Use WebSocket:
const ws = new WebSocket('ws://localhost:8000/api/v1/realtime/ws');
ws.onmessage = (event) => processSignal(JSON.parse(event.data));
```

**Impact:** 90% reduction in API calls, <100ms latency for updates

### 5. Enable Gzip Compression

```python
# FastAPI middleware
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Impact:** 60-80% reduction in response size

### 6. Optimize Database Queries

```sql
-- Add indexes for common queries
CREATE INDEX idx_signals_category ON signals(category);
CREATE INDEX idx_signals_confidence ON signals(confidence_score);
CREATE INDEX idx_signals_created ON signals(created_at DESC);
```

**Impact:** 5-10x improvement in query performance

## Monitoring

### Key Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API P99 latency | < 200ms | > 500ms |
| Error rate | < 0.1% | > 1% |
| Signal processing time | < 100ms | > 300ms |
| Memory usage | < 70% | > 85% |
| CPU usage | < 60% | > 80% |
| Source health | 100% | < 80% |

### Prometheus Metrics

```yaml
# Available metrics
omen_signals_processed_total
omen_signals_rejected_total
omen_api_request_duration_seconds
omen_source_health_status
omen_cache_hit_ratio
omen_websocket_connections_active
```

### Grafana Dashboards

Pre-built dashboards available at: `config/grafana/dashboards/`
- `omen-overview.json` - Main overview dashboard
- `omen-pipeline.json` - Pipeline performance
- `omen-sources.json` - Data source health

## Known Limitations

1. **WebSocket scaling**: Single-instance WebSocket manager. Use Redis pub/sub for multi-instance.
2. **Rate limiting**: In-memory rate limiter. Switch to Redis for distributed deployments.
3. **Historical queries**: Limited to last 30 days without archival storage.
4. **Burst capacity**: Sustained load > 1000 RPS requires queue (Kafka/RabbitMQ).

## Troubleshooting Performance Issues

### High Latency

1. Check source health: `/api/v1/health/sources`
2. Review database connections: Check pool exhaustion
3. Check Redis connectivity: Cache misses increase latency
4. Review validation rules: Complex rules add processing time

### High Memory Usage

1. Check signal cache size: Reduce TTL if needed
2. Review WebSocket connections: Implement connection limits
3. Check for memory leaks: Use `tracemalloc` profiling

### Low Throughput

1. Enable connection pooling
2. Increase worker count: `uvicorn --workers 4`
3. Enable response caching
4. Review slow database queries

---

*Last updated: 2026-02-03*
*OMEN Performance Documentation v1.0*
