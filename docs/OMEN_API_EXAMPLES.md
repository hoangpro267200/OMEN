# OMEN API Response Examples

## Tổng quan

Khi OMEN chạy, nó trả về **SignalResponse** - một signal đã được xử lý với:
- **Probability** (xác suất từ thị trường)
- **Confidence** (độ tin cậy của OMEN)
- **Context** (địa lý, thời gian)
- **Evidence** (chuỗi bằng chứng)

**KHÔNG có:** impact assessment, recommendations, urgency, delay_days, severity

---

## API Endpoints

### 1. POST `/api/v1/live/process` - Xử lý nhiều events

**Request:**
```bash
POST http://localhost:8000/api/v1/live/process?limit=10&min_liquidity=1000
```

**Response:** `list[SignalResponse]`

```json
[
  {
    "signal_id": "OMEN-A1B2C3D4E5F6",
    "source_event_id": "polymarket-0x123abc",
    "title": "Will Red Sea shipping be disrupted by Houthi attacks?",
    "description": "Market resolves YES if commercial shipping through Red Sea is significantly disrupted",
    "probability": 0.75,
    "probability_source": "polymarket",
    "probability_is_estimate": false,
    "confidence_score": 0.85,
    "confidence_level": "HIGH",
    "confidence_factors": {
      "liquidity": 0.9,
      "geographic": 0.85,
      "source_reliability": 0.85
    },
    "category": "GEOPOLITICAL",
    "tags": ["red sea", "shipping", "houthi", "suez"],
    "geographic": {
      "regions": ["Red Sea", "Middle East"],
      "chokepoints": ["red_sea", "suez", "bab_el_mandeb"]
    },
    "temporal": {
      "event_horizon": "2026-06-30",
      "resolution_date": "2026-06-30T23:59:59Z"
    },
    "evidence": [
      {
        "source": "Polymarket",
        "source_type": "market",
        "url": "https://polymarket.com/event/0x123abc"
      }
    ],
    "trace_id": "a1b2c3d4e5f67890",
    "ruleset_version": "1.0.0",
    "source_url": "https://polymarket.com/event/0x123abc",
    "generated_at": "2025-01-28T12:34:56.789Z"
  },
  {
    "signal_id": "OMEN-F6E5D4C3B2A1",
    "source_event_id": "polymarket-0x456def",
    "title": "Will Panama Canal water levels cause shipping delays?",
    "description": null,
    "probability": 0.45,
    "probability_source": "polymarket",
    "probability_is_estimate": false,
    "confidence_score": 0.72,
    "confidence_level": "MEDIUM",
    "confidence_factors": {
      "liquidity": 0.75,
      "geographic": 0.7,
      "source_reliability": 0.85
    },
    "category": "INFRASTRUCTURE",
    "tags": ["panama", "canal", "shipping"],
    "geographic": {
      "regions": ["Central America"],
      "chokepoints": ["panama"]
    },
    "temporal": {
      "event_horizon": "2026-03-15",
      "resolution_date": "2026-03-15T23:59:59Z"
    },
    "evidence": [
      {
        "source": "Polymarket",
        "source_type": "market",
        "url": "https://polymarket.com/event/0x456def"
      }
    ],
    "trace_id": "f6e5d4c3b2a10987",
    "ruleset_version": "1.0.0",
    "source_url": "https://polymarket.com/event/0x456def",
    "generated_at": "2025-01-28T12:34:57.123Z"
  }
]
```

---

### 2. POST `/api/v1/live/process-single` - Xử lý 1 event

**Request:**
```bash
POST http://localhost:8000/api/v1/live/process-single?event_id=polymarket-0x123abc
```

**Response khi thành công:**
```json
{
  "signal": {
    "signal_id": "OMEN-A1B2C3D4E5F6",
    "source_event_id": "polymarket-0x123abc",
    "title": "Will Red Sea shipping be disrupted by Houthi attacks?",
    "description": "Market resolves YES if commercial shipping through Red Sea is significantly disrupted",
    "probability": 0.75,
    "probability_source": "polymarket",
    "probability_is_estimate": false,
    "confidence_score": 0.85,
    "confidence_level": "HIGH",
    "confidence_factors": {
      "liquidity": 0.9,
      "geographic": 0.85,
      "source_reliability": 0.85
    },
    "category": "GEOPOLITICAL",
    "tags": ["red sea", "shipping", "houthi"],
    "geographic": {
      "regions": ["Red Sea", "Middle East"],
      "chokepoints": ["red_sea", "suez"]
    },
    "temporal": {
      "event_horizon": "2026-06-30",
      "resolution_date": "2026-06-30T23:59:59Z"
    },
    "evidence": [
      {
        "source": "Polymarket",
        "source_type": "market",
        "url": "https://polymarket.com/event/0x123abc"
      }
    ],
    "trace_id": "a1b2c3d4e5f67890",
    "ruleset_version": "1.0.0",
    "source_url": "https://polymarket.com/event/0x123abc",
    "generated_at": "2025-01-28T12:34:56.789Z"
  },
  "stats": {
    "events_received": 1,
    "events_validated": 1,
    "signals_generated": 1
  }
}
```

**Response khi bị reject:**
```json
{
  "signal": null,
  "rejection_reason": "Insufficient liquidity: $500 < $1000 minimum"
}
```

---

### 3. POST `/api/v1/signals/process` - Xử lý batch với API key

**Request:**
```bash
POST http://localhost:8000/api/v1/signals/process?limit=50&min_liquidity=1000&min_confidence=0.5
Headers: X-API-Key: your-api-key
```

**Response:** `SignalListResponse`
```json
{
  "signals": [
    {
      "signal_id": "OMEN-A1B2C3D4E5F6",
      "source_event_id": "polymarket-0x123abc",
      "title": "Will Red Sea shipping be disrupted?",
      "probability": 0.75,
      "confidence_score": 0.85,
      "confidence_level": "HIGH",
      "confidence_factors": {
        "liquidity": 0.9,
        "geographic": 0.85,
        "source_reliability": 0.85
      },
      "category": "GEOPOLITICAL",
      "tags": ["red sea", "shipping"],
      "geographic": {
        "regions": ["Red Sea"],
        "chokepoints": ["red_sea", "suez"]
      },
      "temporal": {
        "event_horizon": "2026-06-30",
        "resolution_date": "2026-06-30T23:59:59Z"
      },
      "evidence": [
        {
          "source": "Polymarket",
          "source_type": "market",
          "url": "https://polymarket.com/event/0x123abc"
        }
      ],
      "trace_id": "a1b2c3d4e5f67890",
      "ruleset_version": "1.0.0",
      "source_url": "https://polymarket.com/event/0x123abc",
      "generated_at": "2025-01-28T12:34:56.789Z"
    }
  ],
  "total": 1,
  "processed": 50,
  "passed": 1,
  "rejected": 49,
  "pass_rate": 0.02
}
```

---

### 4. GET `/api/v1/signals/stats` - Thống kê pipeline

**Request:**
```bash
GET http://localhost:8000/api/v1/signals/stats
Headers: X-API-Key: your-api-key
```

**Response:** `PipelineStatsResponse`
```json
{
  "total_processed": 1000,
  "total_passed": 150,
  "total_rejected": 850,
  "pass_rate": 0.15,
  "rejection_by_stage": {
    "validation": 800,
    "generation": 50
  },
  "latency_ms": 125.5,
  "uptime_seconds": 86400
}
```

---

## Cấu trúc SignalResponse

### Các trường bắt buộc:

| Field | Type | Mô tả |
|-------|------|-------|
| `signal_id` | string | ID duy nhất của signal (OMEN-...) |
| `source_event_id` | string | ID event từ nguồn (Polymarket) |
| `title` | string | Tiêu đề event |
| `probability` | float | Xác suất từ thị trường (0-1) |
| `probability_source` | string | Nguồn xác suất ("polymarket") |
| `confidence_score` | float | Độ tin cậy của OMEN (0-1) |
| `confidence_level` | string | HIGH / MEDIUM / LOW |
| `confidence_factors` | object | Breakdown: liquidity, geographic, source_reliability |
| `category` | string | GEOPOLITICAL / INFRASTRUCTURE / WEATHER / ... |
| `geographic` | object | regions, chokepoints |
| `temporal` | object | event_horizon, resolution_date |
| `evidence` | array | Danh sách bằng chứng |
| `trace_id` | string | ID để trace/reproduce |
| `ruleset_version` | string | Version của rules |
| `generated_at` | string | ISO timestamp |

### Các trường KHÔNG có (forbidden):

- ❌ `delay_days` - Impact simulation
- ❌ `severity` - Consequence assessment
- ❌ `urgency` - Decision steering
- ❌ `is_actionable` - Action judgment
- ❌ `risk_exposure` - Financial calculation
- ❌ `recommended_action` - Advice
- ❌ `impact_metrics` - Consequence data

---

## Test với curl

```bash
# Process live events (không cần API key)
curl -X POST "http://localhost:8000/api/v1/live/process?limit=5&min_liquidity=1000"

# Process single event
curl -X POST "http://localhost:8000/api/v1/live/process-single?event_id=polymarket-0x123abc"

# Process với API key
curl -X POST "http://localhost:8000/api/v1/signals/process?limit=10" \
  -H "X-API-Key: your-api-key"

# Get stats
curl "http://localhost:8000/api/v1/signals/stats" \
  -H "X-API-Key: your-api-key"
```

---

## Headers trả về

Mỗi response có headers:
```
X-OMEN-Contract-Version: 2.0.0
X-OMEN-Contract-Type: signal-only
```

---

## Lưu ý

- OMEN chỉ trả về **signal** (probability, confidence, context)
- **KHÔNG** tính impact (delay, cost, severity)
- **KHÔNG** đưa ra recommendations
- Downstream systems (như RiskCast) tự tính impact từ signal này
