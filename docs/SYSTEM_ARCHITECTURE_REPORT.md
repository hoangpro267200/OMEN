# OMEN System Architecture Report
## Báo cáo Kiến trúc Hệ thống OMEN - Chuẩn bị Tích hợp API Chứng khoán

**Ngày tạo:** 2026-02-01  
**Phiên bản:** 2.0.0  
**Mục đích:** Tài liệu tham khảo cho thiết kế tích hợp API chứng khoán

---

## 1. Tổng quan Hệ thống

### 1.1 Mục đích
OMEN (Operations Market Event Network) là hệ thống **Signal Intelligence Engine** chuyên:
- Chuyển đổi dữ liệu thị trường prediction (Polymarket) thành tín hiệu xác suất có cấu trúc
- Xác thực và làm giàu dữ liệu với ngữ cảnh địa lý và thời gian
- Cung cấp tín hiệu với độ tin cậy (confidence) và bằng chứng (evidence)

### 1.2 Nguyên tắc thiết kế
1. **Signal-only Contract**: Chỉ cung cấp xác suất + độ tin cậy, KHÔNG đưa ra đánh giá tác động (impact)
2. **Deterministic Processing**: Cùng input + ruleset → cùng output
3. **Idempotency**: Hash-based deduplication
4. **Hexagonal Architecture**: Domain độc lập với adapters

---

## 2. Kiến trúc Tổng thể

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OMEN SYSTEM                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │   INBOUND        │    │     DOMAIN       │    │    OUTBOUND      │   │
│  │   ADAPTERS       │───▶│     CORE         │───▶│    ADAPTERS      │   │
│  │                  │    │                  │    │                  │   │
│  │ • Polymarket     │    │ • Pipeline       │    │ • REST API       │   │
│  │ • [Stock API]    │    │ • Validator      │    │ • WebSocket      │   │
│  │                  │    │ • Enricher       │    │ • Ledger         │   │
│  │                  │    │ • Classifier     │    │ • Webhook        │   │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Cấu trúc Thư mục

```
src/omen/
├── main.py                    # Entry point, FastAPI app
├── config.py                  # Configuration (OmenConfig)
├── polymarket_settings.py     # Polymarket-specific settings
│
├── adapters/                  # External adapters
│   ├── inbound/               # Data sources
│   │   ├── polymarket/        # Polymarket adapter
│   │   │   ├── client.py      # Base HTTP client
│   │   │   ├── live_client.py # Gamma API client
│   │   │   ├── clob_client.py # CLOB API client
│   │   │   ├── websocket_client.py
│   │   │   ├── mapper.py      # API → RawSignalEvent
│   │   │   └── source.py      # SignalSource implementation
│   │   └── stub_source.py     # Test adapter
│   │
│   ├── outbound/              # Output publishers
│   │   └── console_publisher.py
│   │
│   └── persistence/           # Storage adapters
│       └── in_memory_repository.py
│
├── api/                       # REST API layer
│   ├── routes/                # All API endpoints
│   │   ├── signals.py         # /api/v1/signals (protected)
│   │   ├── live.py            # /api/v1/live (public)
│   │   ├── stats.py           # /api/v1/stats
│   │   ├── health.py          # /health
│   │   ├── realtime.py        # /api/v1/realtime (SSE)
│   │   ├── websocket.py       # /ws
│   │   ├── methodology.py     # /api/v1/methodology
│   │   └── ...
│   ├── dependencies.py        # DI for FastAPI
│   └── models/                # API schemas
│
├── application/               # Application services
│   ├── pipeline.py            # OmenPipeline (orchestration)
│   ├── async_pipeline.py      # Async version
│   ├── container.py           # Dependency injection
│   ├── ports/                 # Interface definitions
│   │   ├── signal_repository.py
│   │   ├── signal_source.py
│   │   └── output_publisher.py
│   └── dto/
│       └── pipeline_result.py
│
├── domain/                    # Business logic (CORE)
│   ├── models/                # Domain entities
│   │   ├── raw_signal.py      # RawSignalEvent (Layer 1)
│   │   ├── validated_signal.py # ValidatedSignal (Layer 2)
│   │   ├── omen_signal.py     # OmenSignal (Layer 4)
│   │   ├── common.py          # Shared types, enums
│   │   └── enums.py
│   │
│   ├── services/              # Domain services
│   │   ├── signal_validator.py
│   │   ├── signal_enricher.py
│   │   └── signal_classifier.py
│   │
│   └── rules/                 # Validation rules
│       ├── validation/
│       │   ├── liquidity_rule.py
│       │   ├── geographic_relevance_rule.py
│       │   ├── semantic_relevance_rule.py
│       │   └── anomaly_detection_rule.py
│       └── registry.py        # Rule parameter registry
│
└── infrastructure/            # Technical concerns
    ├── security/
    │   ├── auth.py            # API key verification
    │   ├── config.py          # SecurityConfig
    │   ├── rate_limit.py
    │   └── redaction.py
    │
    ├── ledger/                # Append-only log
    │   ├── writer.py
    │   ├── reader.py
    │   └── lifecycle.py
    │
    ├── realtime/
    │   └── price_streamer.py  # SSE streaming
    │
    ├── metrics/
    │   └── pipeline_metrics.py
    │
    └── resilience/
        └── circuit_breaker.py
```

---

## 3. Data Flow (Luồng Dữ liệu)

### 3.1 Pipeline xử lý tín hiệu

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   INGEST    │──▶│  VALIDATE   │──▶│   ENRICH    │──▶│  GENERATE   │──▶│   PUBLISH   │
│             │   │             │   │             │   │             │   │             │
│ Layer 1     │   │ Layer 2     │   │ Layer 3     │   │ Layer 4     │   │ Layer 5     │
│ RawSignal   │   │ Validated   │   │ Enriched    │   │ OmenSignal  │   │ Ledger+API  │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

### 3.2 Chi tiết từng bước

| Layer | Input | Process | Output |
|-------|-------|---------|--------|
| **1. Ingest** | API Response | Mapper normalize | `RawSignalEvent` |
| **2. Validate** | `RawSignalEvent` | 4 validation rules | `ValidatedSignal` hoặc reject |
| **3. Enrich** | `ValidatedSignal` | Geographic + Temporal | Enriched signal |
| **4. Generate** | Enriched | Transform + classify | `OmenSignal` |
| **5. Publish** | `OmenSignal` | Repository + Webhook | Persisted + emitted |

### 3.3 Validation Rules

```python
# Thứ tự thực hiện:
1. LiquidityValidationRule    # Min liquidity USD
2. AnomalyDetectionRule       # Phát hiện thao túng
3. SemanticRelevanceRule      # Liên quan đến logistics
4. GeographicRelevanceRule    # Địa điểm có ý nghĩa
```

---

## 4. Domain Models (Mô hình Dữ liệu)

### 4.1 RawSignalEvent (Layer 1 - Input)

```python
class RawSignalEvent(BaseModel):
    """Normalized input from any data source"""
    
    # Identification
    event_id: str               # Unique event ID
    
    # Content
    title: str                  # Event title (1-500 chars)
    description: str | None     # Extended description (max 5000)
    
    # Probability
    probability: float          # 0.0 - 1.0 (YES probability)
    probability_is_fallback: bool
    movement: ProbabilityMovement | None  # Change over time
    
    # Classification
    keywords: list[str]         # Lowercase, deduplicated
    inferred_locations: list[GeoLocation]
    
    # Source metadata
    market: MarketMetadata
    observed_at: datetime
    
    # Computed
    @property
    def input_event_hash(self) -> str:  # For deduplication
```

### 4.2 OmenSignal (Layer 4 - Output)

```python
class OmenSignal(BaseModel):
    """Final structured signal output"""
    
    # Identification
    signal_id: str              # "OMEN-RS2024-001"
    source_event_id: str
    input_event_hash: str | None
    
    # Classification
    signal_type: SignalType     # GEOPOLITICAL, CLIMATE, etc.
    status: SignalStatus        # ACTIVE, MONITORING, etc.
    impact_hints: ImpactHints   # Routing metadata only
    
    # Content
    title: str
    description: str | None
    
    # PROBABILITY (from source market)
    probability: float          # 0.0 - 1.0
    probability_source: str     # "polymarket"
    probability_is_estimate: bool
    
    # CONFIDENCE (OMEN-computed)
    confidence_score: float     # 0.0 - 1.0
    confidence_method: str      # "weighted_factors_v1"
    confidence_level: ConfidenceLevel  # HIGH/MEDIUM/LOW
    confidence_factors: dict[str, float]  # Breakdown
    
    # Context
    geographic: GeographicContext
    temporal: TemporalContext
    
    # Evidence
    evidence: list[EvidenceItem]
    validation_scores: list[ValidationScore]
    
    # Traceability
    trace_id: str               # Reproducibility
    ruleset_version: str
    generated_at: datetime
```

### 4.3 Supporting Types

```python
class MarketMetadata(BaseModel):
    source: str                 # "polymarket"
    market_id: str
    market_url: str | None
    total_volume_usd: float
    current_liquidity_usd: float
    condition_token_id: str | None  # For WebSocket
    clob_token_ids: list[str] | None

class GeographicContext(BaseModel):
    regions: list[str]          # ["Red Sea", "Middle East"]
    chokepoints: list[str]      # ["suez", "bab_el_mandeb"]
    coordinates: dict | None    # {lat, lng}

class TemporalContext(BaseModel):
    event_horizon: str | None   # "2026-06-30"
    resolution_date: datetime | None
    signal_freshness: str       # "current", "recent", "stale"

class EvidenceItem(BaseModel):
    source: str
    source_type: str            # "market", "research", "news"
    value: str | None
    url: str | None
    observed_at: datetime | None
```

---

## 5. API Endpoints

### 5.1 Tổng quan Endpoints

| Category | Path | Auth | Purpose |
|----------|------|------|---------|
| **Health** | `/health` | No | Healthcheck |
| **Signals** | `/api/v1/signals` | API Key | CRUD signals |
| **Live** | `/api/v1/live` | No | Process live events |
| **Stats** | `/api/v1/stats` | No | System statistics |
| **Realtime** | `/api/v1/realtime` | No | SSE price stream |
| **WebSocket** | `/ws` | No | Real-time events |
| **Methodology** | `/api/v1/methodology` | No | Rule documentation |

### 5.2 Key Endpoints

#### POST `/api/v1/live/process`
```json
// Response
[
  {
    "signal_id": "OMEN-001",
    "probability": 0.75,
    "probability_source": "polymarket",
    "confidence_score": 0.85,
    "confidence_level": "HIGH",
    "confidence_factors": {
      "liquidity": 0.9,
      "geographic_relevance": 0.8,
      "source_reliability": 0.85
    },
    "geographic": {
      "regions": ["Middle East"],
      "chokepoints": ["suez"]
    },
    "evidence": [...]
  }
]
```

#### GET `/api/v1/stats`
```json
{
  "total_signals": 1000,
  "signals_by_confidence": {"HIGH": 600, "MEDIUM": 300, "LOW": 100},
  "average_confidence_score": 0.75,
  "validation_pass_rate": 0.85,
  "polymarket_status": "connected"
}
```

### 5.3 Authentication

```python
# API Key header
X-API-Key: dev-key-1

# Environment config
OMEN_SECURITY_API_KEYS=dev-key-1,dev-key-2
OMEN_SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE=300
```

---

## 6. Adapter Interface (Port Definitions)

### 6.1 SignalSource (Inbound Port)

```python
class SignalSource(Protocol):
    """Interface for data sources"""
    
    async def fetch_events(
        self,
        limit: int = 100,
        min_liquidity: float | None = None
    ) -> list[RawSignalEvent]:
        """Fetch market events"""
        ...
    
    async def fetch_by_id(self, event_id: str) -> RawSignalEvent | None:
        """Fetch single event by ID"""
        ...
    
    async def search(
        self,
        query: str,
        limit: int = 50
    ) -> list[RawSignalEvent]:
        """Search events by query"""
        ...
```

### 6.2 SignalRepository (Persistence Port)

```python
class SignalRepository(Protocol):
    """Interface for signal storage"""
    
    def save(self, signal: OmenSignal) -> None: ...
    def find_by_id(self, signal_id: str) -> OmenSignal | None: ...
    def find_by_hash(self, hash: str) -> OmenSignal | None: ...
    def find_recent(self, limit: int, offset: int) -> list[OmenSignal]: ...
    def count(self) -> int: ...
```

### 6.3 OutputPublisher (Outbound Port)

```python
class OutputPublisher(Protocol):
    """Interface for signal publishing"""
    
    async def publish(self, signal: OmenSignal) -> None: ...
```

---

## 7. Current Data Source: Polymarket

### 7.1 Configuration

```python
# Environment variables
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_CLOB_API_URL=https://clob.polymarket.com
POLYMARKET_WS_URL=wss://ws-subscriptions-clob.polymarket.com/ws/market
POLYMARKET_TIMEOUT_S=10
POLYMARKET_RETRY_MAX=3
```

### 7.2 Polymarket Adapter Structure

```
adapters/inbound/polymarket/
├── client.py           # Base HTTP client
├── live_client.py      # Gamma API (events/markets)
├── clob_client.py      # CLOB API (orderbook)
├── websocket_client.py # Real-time prices
├── mapper.py           # API → RawSignalEvent
├── source.py           # SignalSource implementation
└── http_retry.py       # Retry logic
```

### 7.3 Key Features
- Circuit breaker for resilience
- Rate limit handling (429)
- Proxy support (HTTP_PROXY/HTTPS_PROXY)
- WebSocket for real-time price updates

---

## 8. Infrastructure Components

### 8.1 Ledger (Append-only Log)

```
ledger/
├── 2026-01-29/
│   ├── _CURRENT           # Current partition marker
│   └── signals-001.wal    # WAL file
├── 2026-01-30/
│   └── ...
```

### 8.2 Metrics (Prometheus)

```python
# Tracked metrics
- events_received_total
- events_validated_total
- events_rejected_total
- signals_generated_total
- processing_time_seconds
- source_health_status
```

### 8.3 Real-time Streaming

```
SSE: /api/v1/realtime/prices
WebSocket: /ws

Events:
- signal_emitted
- signal_ingested
- reconcile_started
- reconcile_completed
- partition_sealed
- stats_update
```

---

## 9. Điểm Mở rộng cho Stock API Integration

### 9.1 Cần tạo mới

```
src/omen/adapters/inbound/stock/
├── __init__.py
├── client.py           # HTTP client cho stock API
├── websocket_client.py # Real-time stock prices (nếu có)
├── mapper.py           # Stock API → RawSignalEvent
├── source.py           # SignalSource implementation
└── settings.py         # Stock API config
```

### 9.2 Interface cần implement

```python
class StockSignalSource(SignalSource):
    """Stock market data source"""
    
    async def fetch_events(
        self,
        limit: int = 100,
        symbols: list[str] | None = None,  # Stock symbols
        min_volume: float | None = None,   # Min trading volume
    ) -> list[RawSignalEvent]:
        ...
    
    async def fetch_by_symbol(self, symbol: str) -> RawSignalEvent | None:
        ...
```

### 9.3 Mapping yêu cầu

```python
# Stock data → RawSignalEvent mapping
{
    "event_id": "{STOCK_SYMBOL}_{DATE}",
    "title": "Stock: {SYMBOL} - {COMPANY_NAME}",
    "probability": calculate_from_price_movement(),  # Custom logic
    "market": {
        "source": "stock_api",
        "market_id": symbol,
        "total_volume_usd": volume * price,
        "current_liquidity_usd": calculate_liquidity()
    }
}
```

### 9.4 Validation rules cần điều chỉnh

```python
# Có thể cần tạo rules mới cho stock:
- StockVolumeRule           # Min trading volume
- StockVolatilityRule       # Price movement thresholds
- StockSectorRelevanceRule  # Filter by sector
```

---

## 10. Tóm tắt Kỹ thuật

| Component | Technology | Notes |
|-----------|------------|-------|
| **Framework** | FastAPI | Async, OpenAPI |
| **Validation** | Pydantic v2 | Type-safe models |
| **HTTP Client** | httpx | Async, retry |
| **WebSocket** | websockets | Real-time |
| **Storage** | In-memory | PostgreSQL planned |
| **Metrics** | Prometheus | /metrics endpoint |
| **Auth** | API Key | JWT optional |
| **Rate Limit** | Token bucket | 300 req/min |

---

## 11. Quick Reference

### Environment Variables

```bash
# Core
OMEN_RULESET_VERSION=v1.0.0
OMEN_MIN_LIQUIDITY_USD=1000
OMEN_MIN_CONFIDENCE_FOR_OUTPUT=0.3

# Security
OMEN_SECURITY_API_KEYS=key1,key2
OMEN_SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE=300

# Polymarket
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_TIMEOUT_S=10

# Logging
OMEN_LOG_LEVEL=INFO
OMEN_LOG_FORMAT=json
```

### Start Commands

```bash
# Backend
$env:PYTHONPATH="src"; python -m uvicorn omen.main:app --reload --port 8002

# Frontend
cd omen-demo && npm run dev
```

### API Test

```powershell
# Health
Invoke-RestMethod http://127.0.0.1:8002/health

# Stats
Invoke-RestMethod http://127.0.0.1:8002/api/v1/stats

# Signals (auth required)
$h = @{"X-API-Key"="dev-key-1"}
Invoke-RestMethod http://127.0.0.1:8002/api/v1/signals -Headers $h
```

---

**Document End**

*Báo cáo này cung cấp đầy đủ thông tin kiến trúc, data models, và điểm mở rộng để thiết kế tích hợp API chứng khoán vào hệ thống OMEN.*
