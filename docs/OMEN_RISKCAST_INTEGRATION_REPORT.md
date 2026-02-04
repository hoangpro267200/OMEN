# BÁO CÁO: OMEN Signal Intelligence Engine
## Những Gì OMEN Cung Cấp Cho RiskCast

**Ngày tạo:** 02/02/2026  
**Phiên bản:** 1.0

---

## 1. TỔNG QUAN HỆ THỐNG

**OMEN** (Signal Intelligence Engine) là một **động cơ trí tuệ tín hiệu** chuyên biệt cho logistics, có nhiệm vụ:

- **Thu thập** dữ liệu từ nhiều nguồn độc lập
- **Xác thực** và lọc nhiễu thông qua các quy tắc nghiêm ngặt
- **Làm giàu** thông tin với ngữ cảnh địa lý và từ khóa logistics
- **Xuất ra** tín hiệu chuẩn hóa để RiskCast đánh giá tác động

### Nguyên Tắc Thiết Kế Quan Trọng

| Nguyên Tắc | Ý Nghĩa |
|------------|---------|
| **Signal-only** | OMEN chỉ tạo tín hiệu, KHÔNG đưa ra quyết định hay khuyến nghị |
| **Deterministic** | Cùng input + cùng ruleset = cùng output (có thể tái tạo) |
| **Transparent** | Mọi tín hiệu đều có chuỗi bằng chứng và giải thích đầy đủ |

---

## 2. NGUỒN DỮ LIỆU (7+ NGUỒN ĐỘC LẬP)

### 2.1 Nguồn Production-Ready

| Nguồn | Loại Dữ Liệu | API | Cập Nhật |
|-------|--------------|-----|----------|
| **Polymarket** | Xác suất sự kiện từ prediction markets | Gamma API, CLOB, WebSocket | Real-time |
| **News (NewsAPI)** | Tin tức + phân tích sentiment | NewsAPI.org | Hàng giờ |
| **Stock Markets** | Chứng khoán global (yfinance) + VN (vnstock) | yfinance, vnstock | Phút |
| **Commodity (AlphaVantage)** | Giá dầu, vàng, lúa mì | AlphaVantage | Hàng ngày |
| **Weather (OpenWeatherMap)** | Cảnh báo bão, điều kiện biển | OpenWeatherMap | Giờ |

### 2.2 Giám Sát Đối Tác Logistics Việt Nam

OMEN tích hợp **vnstock** để giám sát tài chính các công ty logistics VN:

| Mã CK | Công Ty |
|-------|---------|
| **GMD** | Gemadept Corporation |
| **HAH** | Hải An Transport & Stevedoring JSC |
| **VOS** | Vietnam Ocean Shipping JSC |
| **VSC** | Vietnam Container Shipping JSC |
| **PVT** | PetroVietnam Transportation Corporation |
| **VTP** | Viettel Post JSC |
| **STG** | Sotrans Group |
| **PAN** | PAN Group JSC |
| **DPM** | Petrovietnam Fertilizer & Chemicals Corporation |

**Dữ liệu thu thập:** Giá cổ phiếu, khối lượng giao dịch, PE ratio, ROE, volatility, liquidity scores

### 2.3 Nguồn Demo/Mock (Kế Hoạch Tích Hợp)

| Nguồn | Mục Đích | Trạng Thái |
|-------|----------|------------|
| **AIS/MarineTraffic** | Tình trạng tắc nghẽn cảng, vị trí tàu, theo dõi chokepoints | Mock (kế hoạch tích hợp) |
| **Freight Rates** | Giá container FEU/TEU, tỷ lệ sử dụng công suất, blank sailings | Mock |

---

## 3. QUY TRÌNH XỬ LÝ TÍN HIỆU

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ RawSignalEvent  │ ──▶ │   Validation    │ ──▶ │   Enrichment    │
│ (Dữ liệu thô)   │     │   (4 Rules)     │     │ (Geo + Keywords)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   OmenSignal    │
                                                │ (Tín hiệu chuẩn)│
                                                └─────────────────┘
```

### 3.1 Validation (4 Quy Tắc Tuần Tự)

| # | Rule | Chức Năng | Ngưỡng Loại Bỏ |
|---|------|-----------|----------------|
| 1 | **LiquidityValidationRule** | Kiểm tra thanh khoản thị trường | < $1,000 USD |
| 2 | **AnomalyDetectionRule** | Phát hiện thao túng (xác suất cực đoan, biến động bất thường) | Risk score ≥ 0.5 |
| 3 | **SemanticRelevanceRule** | Lọc nội dung không liên quan (thể thao, giải trí) | Relevance < 0.3 |
| 4 | **GeographicRelevanceRule** | Kiểm tra liên quan đến chokepoints logistics | Không có chokepoint |

**Lưu ý:** Quy tắc chạy tuần tự - nếu một rule fail, signal bị reject ngay lập tức.

### 3.2 Enrichment (Làm Giàu Dữ Liệu)

- **Geographic context:** 
  - Regions: Red Sea, Middle East, Southeast Asia, etc.
  - Chokepoints: Suez, Panama, Hormuz, Malacca, Bab-el-Mandeb, Singapore Strait
  
- **Logistics keywords:** 
  - Maritime: shipping, vessel, port, container
  - Routes: transit, corridor, passage
  - Trade: import, export, tariff
  - Energy: oil, gas, pipeline
  - Geopolitical: conflict, sanctions, blockade

- **Category classification:** GEOPOLITICAL, INFRASTRUCTURE, WEATHER, ECONOMIC, REGULATORY, SECURITY

---

## 4. ĐỊNH DẠNG TÍN HIỆU OMEN (OUTPUT)

### 4.1 Cấu Trúc OmenSignal

```json
{
  "signal_id": "OMEN-RS2024-001",
  "source_event_id": "polymarket-abc123",
  "input_event_hash": "sha256:...",
  "title": "Red Sea Shipping Disruption",
  
  "probability": 0.72,
  "probability_source": "polymarket",
  "probability_is_estimate": false,
  
  "confidence_score": 0.85,
  "confidence_level": "HIGH",
  "confidence_method": "weighted_average",
  "confidence_factors": {
    "liquidity": 0.90,
    "geographic": 0.85,
    "source_reliability": 0.80
  },
  
  "signal_type": "SUPPLY_CHAIN_DISRUPTION",
  "category": "GEOPOLITICAL",
  "status": "ACTIVE",
  "tags": ["red-sea", "shipping", "conflict"],
  "keywords_matched": ["shipping", "disruption", "suez"],
  
  "geographic": {
    "regions": ["Red Sea", "Middle East"],
    "chokepoints": ["suez", "bab-el-mandeb"],
    "coordinates": {"lat": 12.5, "lng": 43.5}
  },
  
  "temporal": {
    "event_horizon": "2026-06-30",
    "resolution_date": "2026-06-30T00:00:00Z",
    "signal_freshness": "current"
  },
  
  "evidence": [
    {
      "source": "polymarket",
      "url": "https://polymarket.com/event/...",
      "observed_at": "2026-02-02T10:00:00Z"
    }
  ],
  
  "validation_scores": [
    {
      "rule_name": "liquidity_validation",
      "rule_version": "1.0.0",
      "score": 0.90,
      "reasoning": "Liquidity $50,000 exceeds minimum $1,000"
    }
  ],
  
  "impact_hints": {
    "domains": ["logistics", "shipping"],
    "direction": "negative",
    "affected_asset_types": ["ports", "vessels"]
  },
  
  "trace_id": "omen-trace-abc123",
  "ruleset_version": "v1.0.0",
  "generated_at": "2026-02-02T10:05:00Z"
}
```

### 4.2 Confidence Levels

| Level | Score | Ý Nghĩa |
|-------|-------|---------|
| **HIGH** | ≥ 0.75 | Tín hiệu đáng tin cậy cao, dữ liệu chất lượng tốt |
| **MEDIUM** | 0.50 - 0.74 | Tín hiệu cần theo dõi, có thể cần xác minh thêm |
| **LOW** | < 0.50 | Tín hiệu sơ bộ, độ tin cậy thấp |

### 4.3 Signal Status

| Status | Confidence | Ý Nghĩa | Hành Động Đề Xuất |
|--------|------------|---------|-------------------|
| **ACTIVE** | ≥ 0.70 | Tín hiệu hoạt động | RiskCast nên xử lý ngay |
| **MONITORING** | 0.50 - 0.69 | Đang theo dõi | Theo dõi cập nhật |
| **CANDIDATE** | 0.30 - 0.49 | Ứng viên | Cần xác minh thêm |
| **DEGRADED** | < 0.30 | Chất lượng thấp | Có thể bỏ qua |

### 4.4 Signal Categories

| Category | Mô Tả | Ví Dụ |
|----------|-------|-------|
| **GEOPOLITICAL** | Xung đột, lệnh trừng phạt, quan hệ quốc tế | Houthi attacks, Russia sanctions |
| **INFRASTRUCTURE** | Cơ sở hạ tầng, cảng, kênh đào | Suez blockage, port strike |
| **WEATHER** | Thời tiết, thiên tai | Typhoon, hurricane, flooding |
| **ECONOMIC** | Kinh tế vĩ mô, giá cả | Oil price spike, currency crash |
| **REGULATORY** | Quy định, chính sách | New tariffs, customs changes |
| **SECURITY** | An ninh, khủng bố, cướp biển | Piracy, terrorism threat |

---

## 5. API ENDPOINTS CHO RISKCAST

### 5.1 Core Signal APIs

| Endpoint | Method | Mô Tả | Parameters |
|----------|--------|-------|------------|
| `/api/v1/signals/` | GET | Lấy danh sách tín hiệu | `since`, `limit`, `offset` |
| `/api/v1/signals/{signal_id}` | GET | Lấy chi tiết tín hiệu | `detail_level`: minimal/standard/full |
| `/api/v1/signals/batch` | POST | Xử lý batch nhiều sự kiện | `limit`, `min_liquidity`, `min_confidence` |
| `/api/v1/signals/stats` | GET | Thống kê pipeline | - |

### 5.2 Live Processing

| Endpoint | Method | Mô Tả |
|----------|--------|-------|
| `/api/v1/live/signals` | POST | Xử lý sự kiện Polymarket live |
| `/api/v1/live/signals/{event_id}` | POST | Xử lý một sự kiện cụ thể |
| `WS /ws` | WebSocket | Real-time signal updates |

### 5.3 Partner Monitoring (Đối Tác Logistics VN)

| Endpoint | Method | Mô Tả |
|----------|--------|-------|
| `/api/v1/partner-signals/` | GET | Tín hiệu tất cả đối tác logistics |
| `/api/v1/partner-signals/{symbol}` | GET | Tín hiệu đối tác cụ thể (GMD, HAH, VOS...) |
| `/api/v1/partner-signals/{symbol}/price` | GET | Dữ liệu giá cổ phiếu |
| `/api/v1/partner-signals/{symbol}/fundamentals` | GET | Các chỉ số cơ bản (PE, ROE) |

### 5.4 Traceability & Explanations

| Endpoint | Method | Mô Tả |
|----------|--------|-------|
| `/api/v1/explanations/{signal_id}` | GET | Chuỗi giải thích cho tín hiệu |
| `/api/v1/activity` | GET | Activity feed |
| `/api/v1/stats` | GET | System statistics |

### 5.5 Health & Metrics

| Endpoint | Method | Mô Tả |
|----------|--------|-------|
| `/health/` | GET | Health check |
| `/health/live` | GET | Liveness probe |
| `/health/ready` | GET | Readiness probe |
| `/metrics` | GET | Prometheus metrics |
| `/api/v1/metrics/circuit-breakers` | GET | Circuit breaker status |

### 5.6 Authentication

```
Header: X-API-Key: <api_key>
```

**RBAC Scopes:**
- `read:signals` - Đọc tín hiệu
- `write:signals` - Tạo/cập nhật tín hiệu

---

## 6. NHỮNG GÌ OMEN **KHÔNG** CUNG CẤP

OMEN có thiết kế "signal-only", nghĩa là **KHÔNG** bao gồm:

| Không Có | Lý Do |
|----------|-------|
| ❌ **Impact severity scores** | RiskCast tự tính dựa trên logistics context |
| ❌ **Delay estimates** (ước tính delay) | RiskCast có logistics models chuyên biệt |
| ❌ **Cost calculations** (tính toán chi phí) | RiskCast có financial models |
| ❌ **Risk verdicts** (phán quyết rủi ro) | RiskCast quyết định dựa trên business rules |
| ❌ **Recommendations** (khuyến nghị hành động) | RiskCast đề xuất cho người dùng |

### Tại Sao Thiết Kế Như Vậy?

1. **Separation of Concerns:** OMEN tập trung vào việc thu thập và xác thực tín hiệu - làm tốt một việc
2. **Objectivity:** Tín hiệu khách quan, không bị bias bởi business logic
3. **Auditability:** Dễ dàng kiểm tra và giải thích nguồn gốc tín hiệu
4. **Flexibility:** RiskCast có thể interpret tín hiệu theo context riêng của từng khách hàng

---

## 7. GIÁ TRỊ OMEN MANG LẠI CHO RISKCAST

| # | Giá Trị | Chi Tiết |
|---|---------|----------|
| 1 | **Cross-source Intelligence** | Tương quan 7+ nguồn độc lập → insight mà không nguồn đơn lẻ nào có |
| 2 | **Vietnam Market Specialization** | Hỗ trợ native thị trường VN qua vnstock - unique capability |
| 3 | **Logistics Focus** | Xây dựng chuyên biệt cho supply chain với keyword database logistics |
| 4 | **Full Transparency** | Evidence trails, confidence scores, explanation chains cho mọi tín hiệu |
| 5 | **Reproducibility** | Deterministic processing với trace IDs - có thể replay và audit |
| 6 | **Real-time Processing** | WebSocket cho cập nhật tức thì, không delay |
| 7 | **RBAC Security** | API key auth với scopes phân quyền, rate limiting |
| 8 | **Observability** | Prometheus metrics, structured logging, circuit breakers |

---

## 8. SƠ ĐỒ TÍCH HỢP OMEN → RISKCAST

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│ Polymarket  │    News     │   Stock     │  Commodity  │   Weather           │
│ (prediction │ (sentiment) │ (VN + Intl) │ (prices)    │ (alerts)            │
│  markets)   │             │             │             │                     │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────────┬──────────┘
       │             │             │             │                 │
       └─────────────┴─────────────┴─────────────┴─────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OMEN ENGINE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────┐    ┌───────────────┐    ┌───────────────┐               │
│   │  Validation   │    │  Enrichment   │    │    Signal     │               │
│   │  (4 Rules)    │ ─▶ │  (Geo + KW)   │ ─▶ │  Generation   │               │
│   └───────────────┘    └───────────────┘    └───────────────┘               │
│                                                                              │
│   OUTPUT: OmenSignal                                                         │
│   • probability (from market)                                                │
│   • confidence_score (OMEN-computed)                                         │
│   • geographic context (regions, chokepoints)                                │
│   • evidence chain (sources, timestamps)                                     │
│   • validation scores (rule results)                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ REST API / WebSocket
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RISKCAST                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. NHẬN TÍN HIỆU                                                           │
│      • Subscribe WebSocket /ws                                               │
│      • Poll GET /api/v1/signals/                                             │
│                                                                              │
│   2. APPLY LOGISTICS CONTEXT                                                 │
│      • Map chokepoints → customer routes                                     │
│      • Map partner signals → customer contracts                              │
│      • Correlate multiple signals                                            │
│                                                                              │
│   3. CALCULATE IMPACT                                                        │
│      • Delay estimates (days)                                                │
│      • Cost impact ($)                                                       │
│      • Alternative routes                                                    │
│                                                                              │
│   4. GENERATE OUTPUT                                                         │
│      • Risk scores                                                           │
│      • Alerts & notifications                                                │
│      • Recommendations                                                       │
│      • Dashboard visualization                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. VÍ DỤ WORKFLOW THỰC TẾ

### Scenario: Red Sea Disruption

**Bước 1: OMEN nhận dữ liệu**
```
Polymarket: "Will Houthi attacks continue through Q2 2026?" - 78% YES
News: Reuters article về tấn công tàu hàng
Commodity: Oil price +5% trong 24h
```

**Bước 2: OMEN xử lý và xuất OmenSignal**
```json
{
  "signal_id": "OMEN-RS2026-042",
  "title": "Red Sea Shipping Disruption - Houthi Attacks",
  "probability": 0.78,
  "confidence_score": 0.85,
  "confidence_level": "HIGH",
  "status": "ACTIVE",
  "category": "GEOPOLITICAL",
  "geographic": {
    "chokepoints": ["suez", "bab-el-mandeb"]
  }
}
```

**Bước 3: RiskCast nhận và xử lý**
```
- Identify affected customers: 15 customers có routes qua Red Sea
- Calculate impact:
  - Average delay: +7-10 days (reroute qua Cape of Good Hope)
  - Cost increase: +$2,000-3,000/TEU
- Generate alerts cho affected customers
- Suggest alternative routes
```

---

## 10. KẾT LUẬN

**OMEN** đóng vai trò là "mắt và tai" của RiskCast trong việc thu thập và xác thực thông tin rủi ro từ nhiều nguồn. 

### OMEN Cung Cấp:

| # | Capability | Benefit cho RiskCast |
|---|------------|---------------------|
| 1 | **Tín hiệu chuẩn hóa** | Format nhất quán, dễ integrate |
| 2 | **Confidence scores** | Biết độ tin cậy để prioritize |
| 3 | **Geographic context** | Map vào routes logistics |
| 4 | **Evidence trails** | Audit và giải thích cho khách hàng |
| 5 | **Real-time updates** | Phản ứng nhanh với sự kiện |
| 6 | **Partner monitoring** | Giám sát đối tác logistics VN |

### Phân Công Trách Nhiệm:

| OMEN | RiskCast |
|------|----------|
| Thu thập dữ liệu | Nhận tín hiệu |
| Xác thực & lọc nhiễu | Apply business context |
| Làm giàu thông tin | Tính toán impact |
| Xuất tín hiệu chuẩn | Đưa ra khuyến nghị |
| Đảm bảo transparency | Phục vụ end-user |

**Kết quả:** Một hệ thống modular, có thể audit, với separation of concerns rõ ràng giữa signal intelligence (OMEN) và risk assessment (RiskCast).

---

*Báo cáo này được tạo tự động từ phân tích codebase OMEN.*
