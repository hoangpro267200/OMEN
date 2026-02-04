# OMEN - Hướng Dẫn Chi Tiết Về Cách Hoạt Động

**Phiên bản:** 1.0  
**Cập nhật:** 2026-02-03

---

## 📖 Mục Lục

1. [OMEN Là Gì?](#1-omen-là-gì)
2. [Tổng Quan Kiến Trúc](#2-tổng-quan-kiến-trúc)
3. [Các Nguồn Dữ Liệu](#3-các-nguồn-dữ-liệu)
4. [Luồng Xử Lý Tín Hiệu (Signal Pipeline)](#4-luồng-xử-lý-tín-hiệu-signal-pipeline)
5. [Các Lớp Tín Hiệu](#5-các-lớp-tín-hiệu)
6. [Backend (Python/FastAPI)](#6-backend-pythonfastapi)
7. [Frontend (React/TypeScript)](#7-frontend-reacttypescript)
8. [Tính Năng Real-time](#8-tính-năng-real-time)
9. [Chế Độ LIVE vs DEMO](#9-chế-độ-live-vs-demo)
10. [Bảo Mật](#10-bảo-mật)
11. [Ví Dụ Thực Tế](#11-ví-dụ-thực-tế)

---

## 1. OMEN Là Gì?

### Định Nghĩa Đơn Giản

**OMEN** (Opportunity & Market Event Navigator) là một nền tảng **tín hiệu thông minh thời gian thực** giúp:

- 🔍 **Thu thập** dữ liệu từ nhiều nguồn khác nhau (thị trường dự đoán, tin tức, thời tiết, vận tải...)
- 🧠 **Xử lý & Phân tích** dữ liệu để tạo ra các tín hiệu có ý nghĩa
- 📊 **Hiển thị** tín hiệu trên giao diện web trực quan
- 🔔 **Cảnh báo** khi có sự kiện quan trọng

### Ví Dụ Cụ Thể

Hãy tưởng tượng bạn muốn biết:
- "Liệu Bitcoin có vượt $100K trong tháng này không?"
- "Có bão lớn sắp ảnh hưởng đến chuỗi cung ứng không?"
- "Giá dầu sẽ biến động như thế nào?"

OMEN sẽ:
1. Lấy dữ liệu từ Polymarket (thị trường dự đoán) → Xem mọi người đang đặt cược gì
2. Lấy dữ liệu thời tiết → Xem có bão hay thiên tai không
3. Lấy tin tức → Xem có sự kiện gì đang xảy ra
4. **Tổng hợp tất cả** → Tạo ra "Tín hiệu OMEN" với độ tin cậy

---

## 2. Tổng Quan Kiến Trúc

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HỆ THỐNG OMEN                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌────────────────── NGUỒN DỮ LIỆU ──────────────────┐                    │
│   │                                                    │                    │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ │                    │
│   │  │Polymarket│ │   Tin    │ │ Thời tiết│ │ AIS  │ │                    │
│   │  │(Dự đoán) │ │   Tức    │ │          │ │(Tàu) │ │                    │
│   │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬───┘ │                    │
│   │       │            │            │           │      │                    │
│   └───────┼────────────┼────────────┼───────────┼──────┘                    │
│           │            │            │           │                           │
│           └────────────┴─────┬──────┴───────────┘                           │
│                              ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                    BACKEND (Python/FastAPI)                       │     │
│   │                                                                   │     │
│   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │     │
│   │  │   Adapter   │──►│  Pipeline   │──►│   Emitter   │            │     │
│   │  │(Chuẩn hóa)  │   │(Xử lý/Lọc)  │   │(Phát tín hiệu)│          │     │
│   │  └─────────────┘   └─────────────┘   └─────────────┘            │     │
│   │                                                                   │     │
│   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │     │
│   │  │  REST API   │   │  WebSocket  │   │   Database  │            │     │
│   │  │  /api/v1/   │   │  (Realtime) │   │  (Lưu trữ)  │            │     │
│   │  └─────────────┘   └─────────────┘   └─────────────┘            │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                              │                                              │
│                              ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                   FRONTEND (React/TypeScript)                     │     │
│   │                                                                   │     │
│   │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │     │
│   │  │  Dashboard  │   │  Signals    │   │  Pipeline   │            │     │
│   │  │  (Tổng quan)│   │  (Chi tiết) │   │  (Monitor)  │            │     │
│   │  └─────────────┘   └─────────────┘   └─────────────┘            │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Giải Thích Đơn Giản

Hãy nghĩ OMEN như một **nhà máy xử lý thông tin**:

| Bộ phận | Vai trò | Ví dụ thực tế |
|---------|---------|---------------|
| **Nguồn Dữ Liệu** | Nguyên liệu thô | Polymarket, tin tức, thời tiết |
| **Adapter** | Chuẩn hóa nguyên liệu | Biến dữ liệu khác nhau thành format chung |
| **Pipeline** | Dây chuyền sản xuất | Lọc, kiểm tra, làm giàu dữ liệu |
| **Emitter** | Bộ phận xuất hàng | Gửi tín hiệu đến nơi cần |
| **Frontend** | Showroom | Hiển thị cho người dùng xem |

---

## 3. Các Nguồn Dữ Liệu

OMEN thu thập dữ liệu từ nhiều nguồn khác nhau:

### 3.1 Polymarket (Thị Trường Dự Đoán)

```
┌─────────────────────────────────────────────────────────────────┐
│                        POLYMARKET                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📊 "Sẽ có chiến tranh ở X không?"          → Xác suất: 15%     │
│  📊 "Bitcoin vượt $100K trước tháng 6?"     → Xác suất: 67%     │
│  📊 "Trump thắng cử 2024?"                  → Xác suất: 52%     │
│                                                                  │
│  Dữ liệu bao gồm:                                               │
│  • Xác suất (probability)                                       │
│  • Khối lượng giao dịch (volume)                                │
│  • Thanh khoản (liquidity)                                      │
│  • Lịch sử giá                                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Cách hoạt động:**
```python
# File: src/omen/adapters/inbound/polymarket/live_client.py

# 1. Kết nối đến Polymarket API
client = PolymarketSignalSource(api_key="...")

# 2. Lấy các market đang hoạt động
markets = client.fetch_events(limit=100)

# 3. Mỗi market được chuyển thành RawSignalEvent
# Ví dụ kết quả:
{
    "event_id": "btc_100k_june",
    "title": "Bitcoin vượt $100K trước tháng 6?",
    "probability": 0.67,
    "volume": 1_500_000,  # $1.5M đã giao dịch
    "source": "polymarket"
}
```

### 3.2 Nguồn Tin Tức

```
┌─────────────────────────────────────────────────────────────────┐
│                          TIN TỨC                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📰 "Ngân hàng Fed tăng lãi suất 0.25%"                         │
│  📰 "Bão lớn đổ bộ vào Texas"                                   │
│  📰 "OPEC cắt giảm sản lượng dầu"                               │
│                                                                  │
│  OMEN sẽ:                                                       │
│  1. Lọc tin theo từ khóa liên quan                              │
│  2. Đánh giá mức độ quan trọng                                  │
│  3. Liên kết với tín hiệu thị trường                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Dữ Liệu Thời Tiết

```
┌─────────────────────────────────────────────────────────────────┐
│                        THỜI TIẾT                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🌀 Bão cấp 4 đang tiến vào Biển Đông                          │
│  🌡️  Nhiệt độ bất thường tại vùng sản xuất                     │
│  🌊 Cảnh báo sóng lớn tại eo biển Malacca                       │
│                                                                  │
│  Ảnh hưởng:                                                     │
│  • Vận tải biển bị gián đoạn                                    │
│  • Giá hàng hóa tăng                                            │
│  • Chuỗi cung ứng bị ảnh hưởng                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Tổng Hợp Các Nguồn

| Nguồn | Loại Dữ Liệu | Trạng Thái | API |
|-------|--------------|------------|-----|
| **Polymarket** | Thị trường dự đoán | ✅ REAL | Gamma API |
| **News** | Tin tức | ✅ REAL | NewsData API |
| **Weather** | Thời tiết | ✅ REAL | OpenMeteo |
| **Stock** | Chứng khoán | ✅ REAL | yfinance |
| **Commodity** | Hàng hóa | ✅ REAL | Alpha Vantage |
| **AIS** | Vận tải biển | 🔶 MOCK | (Cần API MarineTraffic) |
| **Freight** | Cước vận tải | 🔶 MOCK | (Cần API Freightos) |

---

## 4. Luồng Xử Lý Tín Hiệu (Signal Pipeline)

### Sơ Đồ Tổng Quan

```
                         PIPELINE XỬ LÝ TÍN HIỆU
 
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Nguồn    │───►│ Adapter  │───►│ Validate │───►│ Enrich   │───►│ Emit     │
  │ Dữ Liệu  │    │          │    │          │    │          │    │          │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
       │               │               │               │               │
       │               │               │               │               │
       ▼               ▼               ▼               ▼               ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Dữ liệu  │    │RawSignal │    │Validated │    │ Omen     │    │ REST API │
  │ thô      │    │ Event    │    │ Signal   │    │ Signal   │    │WebSocket │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Bước 1: Thu Thập Dữ Liệu (Adapter)

```python
# Mỗi nguồn có một Adapter riêng
# Adapter chuyển dữ liệu thô → RawSignalEvent

# Ví dụ: Polymarket Adapter
class PolymarketSignalSource:
    def fetch_events(self, limit=100):
        # 1. Gọi API Polymarket
        raw_data = self.api.get_markets()
        
        # 2. Chuyển đổi thành RawSignalEvent
        for market in raw_data:
            yield RawSignalEvent(
                event_id=market["condition_id"],
                title=market["question"],
                probability=market["outcomePrices"]["Yes"],
                volume=market["volume"],
                source="polymarket"
            )
```

### Bước 2: Kiểm Tra & Xác Thực (Validation)

```
                          QUÁ TRÌNH VALIDATION
 
     RawSignalEvent
           │
           ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                  VALIDATION RULES                            │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  ┌─────────────────┐                                        │
    │  │ 1. LIQUIDITY    │ Kiểm tra thanh khoản đủ lớn không?     │
    │  │    RULE         │ Volume > $10,000? Spread < 5%?          │
    │  └────────┬────────┘                                        │
    │           │ ✅ Pass                                          │
    │           ▼                                                  │
    │  ┌─────────────────┐                                        │
    │  │ 2. ANOMALY      │ Dữ liệu có bất thường không?           │
    │  │    RULE         │ Xác suất hợp lý? Không có spike lạ?    │
    │  └────────┬────────┘                                        │
    │           │ ✅ Pass                                          │
    │           ▼                                                  │
    │  ┌─────────────────┐                                        │
    │  │ 3. SEMANTIC     │ Nội dung có liên quan không?           │
    │  │    RULE         │ Có từ khóa quan trọng?                  │
    │  └────────┬────────┘                                        │
    │           │ ✅ Pass                                          │
    │           ▼                                                  │
    │  ┌─────────────────┐                                        │
    │  │ 4. GEOGRAPHIC   │ Có liên quan đến vùng quan tâm?        │
    │  │    RULE         │ Chokepoint? Khu vực chiến lược?        │
    │  └────────┬────────┘                                        │
    │           │                                                  │
    └───────────┼──────────────────────────────────────────────────┘
                │
                ▼
         ValidatedSignal (nếu pass tất cả rules)
```

**Giải thích các Rule:**

| Rule | Mục đích | Ví dụ |
|------|----------|-------|
| **Liquidity Rule** | Lọc market có thanh khoản quá thấp | Loại bỏ market chỉ có $100 volume |
| **Anomaly Rule** | Phát hiện dữ liệu bất thường | Cảnh báo nếu xác suất nhảy từ 10% → 90% trong 1 phút |
| **Semantic Rule** | Kiểm tra nội dung liên quan | Chỉ giữ tin về "vận tải", "dầu", "địa chính trị" |
| **Geographic Rule** | Lọc theo vùng địa lý | Ưu tiên eo biển Malacca, kênh Suez |

### Bước 3: Làm Giàu Dữ Liệu (Enrichment)

```python
# Sau khi validate, tín hiệu được ENRICH với thông tin bổ sung

class SignalEnricher:
    def enrich(self, validated_signal):
        return OmenSignal(
            # Thông tin gốc
            probability=validated_signal.probability,
            
            # Thêm ngữ cảnh địa lý
            geographic_context={
                "regions": ["Southeast Asia", "Pacific"],
                "chokepoints": ["Strait of Malacca"],
                "coordinates": [103.8, 1.3]
            },
            
            # Thêm độ tin cậy
            confidence_score=0.85,
            confidence_factors={
                "liquidity": 0.9,
                "source_reliability": 0.8,
                "data_freshness": 0.85
            },
            
            # Thêm keywords
            keywords=["shipping", "oil", "geopolitics"],
            
            # Thêm chuỗi giải thích
            explanation_chain=[
                "Signal passed liquidity check: $1.5M volume",
                "Geographic match: Strait of Malacca",
                "High confidence due to multiple source validation"
            ]
        )
```

### Bước 4: Phát Tín Hiệu (Emission)

```
                         SIGNAL EMISSION
 
         OmenSignal
              │
              ├──────────────────────────────────────────────┐
              │                                               │
              ▼                                               ▼
    ┌─────────────────┐                           ┌─────────────────┐
    │   REST API      │                           │   WebSocket     │
    │   /api/v1/      │                           │   Real-time     │
    │   signals/      │                           │   Stream        │
    └────────┬────────┘                           └────────┬────────┘
             │                                              │
             │                                              │
             ▼                                              ▼
    ┌─────────────────┐                           ┌─────────────────┐
    │   Database      │                           │   Price         │
    │   (PostgreSQL)  │                           │   Streamer      │
    │                 │                           │   (SSE)         │
    └─────────────────┘                           └─────────────────┘
```

---

## 5. Các Lớp Tín Hiệu

OMEN sử dụng hệ thống **3 lớp tín hiệu** để đảm bảo chất lượng:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HỆ THỐNG 3 LỚP TÍN HIỆU                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LỚP 1: RawSignalEvent (Tín hiệu thô)                                │   │
│  │                                                                      │   │
│  │ • Dữ liệu gốc từ nguồn                                               │   │
│  │ • Chưa qua kiểm tra                                                  │   │
│  │ • Format chuẩn hóa                                                   │   │
│  │                                                                      │   │
│  │ Ví dụ:                                                               │   │
│  │ {                                                                    │   │
│  │   "event_id": "btc_100k",                                           │   │
│  │   "title": "BTC > $100K?",                                          │   │
│  │   "probability": 0.67,                                               │   │
│  │   "source": "polymarket"                                             │   │
│  │ }                                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼ Validation                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LỚP 2: ValidatedSignal (Tín hiệu đã xác thực)                       │   │
│  │                                                                      │   │
│  │ • Đã pass các validation rules                                       │   │
│  │ • Có kết quả kiểm tra chi tiết                                       │   │
│  │ • Có trace_id để theo dõi                                            │   │
│  │                                                                      │   │
│  │ Ví dụ:                                                               │   │
│  │ {                                                                    │   │
│  │   "raw_event": {...},                                                │   │
│  │   "validation_results": {                                            │   │
│  │     "liquidity": "PASS",                                             │   │
│  │     "anomaly": "PASS",                                               │   │
│  │     "semantic": "PASS"                                               │   │
│  │   },                                                                 │   │
│  │   "trace_id": "abc123"                                               │   │
│  │ }                                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼ Enrichment                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LỚP 3: OmenSignal (Tín hiệu hoàn chỉnh)                             │   │
│  │                                                                      │   │
│  │ • Sản phẩm cuối cùng                                                 │   │
│  │ • Có đầy đủ context                                                  │   │
│  │ • Sẵn sàng để sử dụng                                                │   │
│  │                                                                      │   │
│  │ Ví dụ:                                                               │   │
│  │ {                                                                    │   │
│  │   "signal_id": "omen_btc_100k_abc123",                              │   │
│  │   "probability": 0.67,                                               │   │
│  │   "confidence_score": 0.85,                                          │   │
│  │   "geographic_context": {...},                                       │   │
│  │   "explanation_chain": [...],                                        │   │
│  │   "keywords": ["bitcoin", "crypto"],                                 │   │
│  │   "created_at": "2026-02-03T10:30:00Z"                              │   │
│  │ }                                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Backend (Python/FastAPI)

### Cấu Trúc Thư Mục

```
src/omen/
│
├── 📁 main.py                    ← Điểm khởi động ứng dụng
│
├── 📁 api/                       ← API Layer (giao tiếp với client)
│   ├── routes/
│   │   ├── signals.py           ← GET/POST /api/v1/signals
│   │   ├── live.py              ← Dữ liệu live
│   │   ├── health.py            ← Health check
│   │   └── websocket.py         ← WebSocket handlers
│   └── security.py              ← Authentication
│
├── 📁 domain/                    ← Business Logic (logic nghiệp vụ)
│   ├── models/
│   │   ├── signal.py            ← RawSignalEvent, OmenSignal
│   │   └── context.py           ← ProcessingContext
│   ├── rules/                   ← Validation Rules
│   │   ├── liquidity_rule.py
│   │   ├── anomaly_rule.py
│   │   └── semantic_rule.py
│   └── services/
│       ├── validator.py         ← SignalValidator
│       ├── enricher.py          ← SignalEnricher
│       └── classifier.py        ← SignalClassifier
│
├── 📁 application/               ← Use Cases (kịch bản sử dụng)
│   ├── pipeline.py              ← OmenPipeline
│   └── container.py             ← Dependency Injection
│
├── 📁 infrastructure/            ← External Services
│   ├── storage/                 ← Database
│   ├── realtime/                ← WebSocket, SSE
│   ├── security/                ← Auth, Rate Limit
│   └── observability/           ← Logging, Metrics
│
└── 📁 adapters/                  ← Data Source Adapters
    └── inbound/
        ├── polymarket/          ← Polymarket API
        ├── news/                ← News API
        ├── weather/             ← Weather API
        └── ais/                 ← AIS (Ship tracking)
```

### API Endpoints Chính

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/v1/signals/` | GET | Lấy danh sách tín hiệu |
| `/api/v1/signals/{id}` | GET | Lấy chi tiết 1 tín hiệu |
| `/api/v1/signals/batch` | POST | Xử lý batch tín hiệu |
| `/api/v1/signals/refresh` | POST | Refresh dữ liệu live |
| `/api/v1/live/status` | GET | Trạng thái chế độ LIVE |
| `/api/v1/health/` | GET | Health check |
| `/api/v1/health/system` | GET | System status chi tiết |
| `/ws/` | WebSocket | Real-time updates |

### Ví Dụ Gọi API

```bash
# Lấy 10 tín hiệu mới nhất
curl -H "X-API-Key: your_key" \
     "http://localhost:8000/api/v1/signals/?limit=10"

# Response:
{
  "signals": [
    {
      "signal_id": "omen_btc_100k_abc123",
      "title": "Bitcoin vượt $100K trước tháng 6?",
      "probability": 0.67,
      "confidence_score": 0.85,
      "source": "polymarket",
      "created_at": "2026-02-03T10:30:00Z"
    },
    ...
  ],
  "total": 150,
  "mode": "LIVE"
}
```

---

## 7. Frontend (React/TypeScript)

### Cấu Trúc Thư Mục

```
omen-demo/src/
│
├── 📁 main.tsx                   ← Điểm khởi động React app
│
├── 📁 screens/                   ← Các màn hình chính
│   ├── CommandCenter.tsx        ← Dashboard tổng quan
│   ├── SignalsPage.tsx          ← Danh sách tín hiệu
│   ├── SignalDeepDive.tsx       ← Chi tiết 1 tín hiệu
│   ├── PipelineMonitor.tsx      ← Theo dõi pipeline
│   └── SourcesObservatory.tsx   ← Theo dõi nguồn dữ liệu
│
├── 📁 components/                ← Components tái sử dụng
│   ├── Layout/
│   │   ├── AppShell.tsx         ← Layout chính
│   │   ├── AppSidebar.tsx       ← Sidebar navigation
│   │   └── StatusBar.tsx        ← Status bar
│   ├── dashboard/
│   │   ├── ActivityFeed.tsx     ← Feed hoạt động
│   │   └── PrioritySignals.tsx  ← Tín hiệu ưu tiên
│   ├── signals/
│   │   ├── SignalsTable.tsx     ← Bảng tín hiệu
│   │   └── SignalRow.tsx        ← 1 dòng tín hiệu
│   └── ui/
│       ├── MetricCard.tsx       ← Card hiển thị số liệu
│       ├── DataModeSwitcher.tsx ← Toggle LIVE/DEMO
│       └── ErrorState.tsx       ← Hiển thị lỗi
│
├── 📁 hooks/                     ← Custom React Hooks
│   ├── useSignalData.ts         ← Hook lấy dữ liệu signal
│   ├── useUnifiedData.ts        ← Hook unified data
│   └── useRealtimePrices.ts     ← Hook real-time prices
│
├── 📁 context/                   ← React Context
│   ├── DataModeContext.tsx      ← LIVE/DEMO mode state
│   └── DemoModeContext.tsx      ← Demo presentation mode
│
└── 📁 lib/                       ← Utilities
    ├── api/
    │   ├── httpClient.ts        ← HTTP client
    │   └── hooks.ts             ← React Query hooks
    └── websocket/
        └── WebSocketProvider.tsx ← WebSocket context
```

### Các Màn Hình Chính

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GIAO DIỆN OMEN                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────┐                                                              │
│  │ SIDEBAR   │  ┌─────────────────────────────────────────────────────┐    │
│  │           │  │                                                      │    │
│  │ 🏠 Home   │  │  COMMAND CENTER (Dashboard)                         │    │
│  │           │  │                                                      │    │
│  │ 📊 Signals│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│    │
│  │           │  │  │Tín hiệu  │ │Pipeline  │ │Nguồn     │ │Hoạt động ││    │
│  │ 🔧 Pipeline│ │  │hôm nay   │ │hoạt động │ │online    │ │gần đây   ││    │
│  │           │  │  │   47     │ │  12/15   │ │  5/7     │ │   156    ││    │
│  │ 🌐 Sources│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘│    │
│  │           │  │                                                      │    │
│  │ ⚙️ Ops    │  │  ┌────────────────────────────────────────────────┐│    │
│  │           │  │  │           PRIORITY SIGNALS TABLE               ││    │
│  └───────────┘  │  │  ─────────────────────────────────────────────  ││    │
│                 │  │  📈 BTC > $100K | 67% | High | polymarket      ││    │
│                 │  │  🌀 Bão Biển Đông | 45% | Medium | weather     ││    │
│                 │  │  📰 OPEC cắt giảm | 72% | High | news          ││    │
│                 │  │  └────────────────────────────────────────────┘ │    │
│                 │  │                                                  │    │
│                 │  └─────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STATUS BAR: 🟢 LIVE MODE | 5 sources online | Last update: 10:30   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Luồng Dữ Liệu Frontend

```
                        LUỒNG DỮ LIỆU FRONTEND

     ┌─────────────────────────────────────────────────────────────────┐
     │                        USER INTERFACE                           │
     │                                                                  │
     │    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │
     │    │  Component   │     │  Component   │     │  Component   │  │
     │    │  (Signal     │     │  (Dashboard) │     │  (Pipeline)  │  │
     │    │   Table)     │     │              │     │              │  │
     │    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘  │
     │           │                    │                    │           │
     └───────────┼────────────────────┼────────────────────┼───────────┘
                 │                    │                    │
                 └────────────────────┼────────────────────┘
                                      │
                                      ▼
     ┌─────────────────────────────────────────────────────────────────┐
     │                        CUSTOM HOOKS                             │
     │                                                                  │
     │    ┌──────────────────────────────────────────────────────┐    │
     │    │  useSignalData() / useUnifiedData()                  │    │
     │    │                                                       │    │
     │    │  - Kiểm tra DataMode (LIVE hay DEMO?)                │    │
     │    │  - LIVE → Gọi API thật                               │    │
     │    │  - DEMO → Dùng mock data                             │    │
     │    └──────────────────────────────────────────────────────┘    │
     │                                                                  │
     └─────────────────────────────────────────────────────────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
                 ▼                    ▼                    ▼
     ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
     │  DataModeContext│  │  React Query    │  │  WebSocket      │
     │                 │  │  (Caching)      │  │  Provider       │
     │  LIVE ◄──► DEMO │  │                 │  │                 │
     └─────────────────┘  └────────┬────────┘  └────────┬────────┘
                                   │                    │
                                   ▼                    ▼
                         ┌─────────────────────────────────────┐
                         │           BACKEND API               │
                         │      http://localhost:8000          │
                         └─────────────────────────────────────┘
```

---

## 8. Tính Năng Real-time

OMEN hỗ trợ 2 cơ chế real-time:

### 8.1 WebSocket - Thông Báo Sự Kiện

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WEBSOCKET FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     BACKEND                                      FRONTEND                    │
│                                                                              │
│  ┌──────────────┐                            ┌──────────────┐              │
│  │ New Signal   │                            │  Browser     │              │
│  │ Created      │                            │              │              │
│  └──────┬───────┘                            └──────┬───────┘              │
│         │                                           │                       │
│         │ 1. Emit event                             │                       │
│         ▼                                           │                       │
│  ┌──────────────┐      WebSocket Message     ┌──────┴───────┐              │
│  │ WebSocket    │ ─────────────────────────► │  WebSocket   │              │
│  │ Server       │  {                         │  Client      │              │
│  │              │    "type": "signal_emitted"│              │              │
│  │              │    "signal_id": "abc123"   │              │              │
│  └──────────────┘  }                         └──────┬───────┘              │
│                                                      │                       │
│                                                      │ 2. Invalidate cache   │
│                                                      ▼                       │
│                                              ┌──────────────┐              │
│                                              │ React Query  │              │
│                                              │ Refetch      │              │
│                                              └──────┬───────┘              │
│                                                      │                       │
│                                                      │ 3. Update UI          │
│                                                      ▼                       │
│                                              ┌──────────────┐              │
│                                              │ UI Updated   │              │
│                                              │ Instantly    │              │
│                                              └──────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 SSE (Server-Sent Events) - Cập Nhật Giá

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PRICE STREAMING (SSE)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     POLYMARKET                    BACKEND                    FRONTEND       │
│                                                                              │
│  ┌──────────────┐           ┌──────────────┐           ┌──────────────┐    │
│  │ Price: 0.67  │           │ Price        │   SSE     │ useRealtime  │    │
│  │ Price: 0.68  │ ────────► │ Streamer     │ ────────► │ Prices()     │    │
│  │ Price: 0.69  │           │              │           │              │    │
│  │ ...          │           │              │           │ Probability: │    │
│  └──────────────┘           └──────────────┘           │ 67% → 68%    │    │
│                                                         │ ↑ INCREASING │    │
│                                                         └──────────────┘    │
│                                                                              │
│  Lợi ích của SSE:                                                           │
│  • Nhẹ hơn WebSocket cho one-way data                                       │
│  • Tự động reconnect                                                        │
│  • Tính momentum (INCREASING/DECREASING/STABLE)                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Chế Độ LIVE vs DEMO

### Tại Sao Có 2 Chế Độ?

| Chế độ | Mục đích | Dữ liệu |
|--------|----------|---------|
| **LIVE** | Sử dụng thực tế | API thật, dữ liệu real-time |
| **DEMO** | Trình diễn, test | Mock data, không cần API key |

### Quy Tắc Quan Trọng

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     NGUYÊN TẮC TÁCH BIỆT NGHIÊM NGẶT                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ❌ KHÔNG CÓ HYBRID MODE                                                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  LIVE MODE:                                                          │   │
│  │  • CHỈ dùng dữ liệu từ API thật                                     │   │
│  │  • Nếu API fail → Hiện lỗi (KHÔNG fallback sang mock)               │   │
│  │  • Yêu cầu tất cả nguồn phải là REAL (không mock)                   │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  DEMO MODE:                                                          │   │
│  │  • CHỈ dùng mock data                                                │   │
│  │  • Không gọi API thật                                               │   │
│  │  • An toàn cho trình diễn                                           │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Tại sao nghiêm ngặt như vậy?                                               │
│  → Tránh nhầm lẫn: Người dùng luôn biết họ đang xem dữ liệu gì             │
│  → Data Integrity: Dữ liệu thật không bị trộn với mock                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cách Chuyển Đổi Chế Độ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MODE SWITCHING                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User clicks "LIVE" button                                               │
│                     │                                                        │
│                     ▼                                                        │
│  2. Frontend gọi API: GET /api/v1/live/status                               │
│                     │                                                        │
│                     ▼                                                        │
│  3. Backend kiểm tra:                                                       │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ Source Registry:                                                 │    │
│     │   - Polymarket: REAL ✅                                          │    │
│     │   - News: REAL ✅                                                 │    │
│     │   - Weather: REAL ✅                                              │    │
│     │   - AIS: MOCK ❌                                                  │    │
│     │                                                                   │    │
│     │ Kết quả: Có nguồn MOCK → LIVE mode bị BLOCKED                    │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                     │                                                        │
│                     ▼                                                        │
│  4. Response: { "live_eligible": false, "reason": "AIS source is mock" }    │
│                     │                                                        │
│                     ▼                                                        │
│  5. Frontend: Hiện thông báo "Không thể bật LIVE mode"                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Bảo Mật

### Các Lớp Bảo Vệ

```
                          DEFENSE IN DEPTH
 
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Layer 1: SECURITY HEADERS                    │
    │                                                                  │
    │  • HSTS (HTTPS only)                                            │
    │  • X-Frame-Options (chống clickjacking)                         │
    │  • Content-Security-Policy                                      │
    │  • X-Content-Type-Options                                       │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Layer 2: RATE LIMITING                       │
    │                                                                  │
    │  • Giới hạn request/phút                                        │
    │  • Theo API key hoặc IP                                         │
    │  • Chống DDoS                                                   │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Layer 3: AUTHENTICATION                      │
    │                                                                  │
    │  • API Key validation                                           │
    │  • Header: X-API-Key                                            │
    │  • Hoặc Query param: ?api_key=xxx                               │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Layer 4: INPUT VALIDATION                    │
    │                                                                  │
    │  • Chống SQL Injection                                          │
    │  • Chống XSS                                                    │
    │  • Validate data types                                          │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Layer 5: AUDIT LOGGING                       │
    │                                                                  │
    │  • Log tất cả security events                                   │
    │  • Correlation IDs                                              │
    │  • Trace requests                                               │
    └─────────────────────────────────────────────────────────────────┘
```

### Ví Dụ Request Flow

```
Client Request
      │
      │ 1. Check Headers
      ▼
┌─────────────┐
│ Security    │──────► Missing headers? → Add secure defaults
│ Headers     │
└──────┬──────┘
       │ 2. Check Rate
       ▼
┌─────────────┐
│ Rate        │──────► Over limit? → 429 Too Many Requests
│ Limiter     │
└──────┬──────┘
       │ 3. Check API Key
       ▼
┌─────────────┐
│ Auth        │──────► Invalid key? → 401 Unauthorized
│             │
└──────┬──────┘
       │ 4. Validate Input
       ▼
┌─────────────┐
│ Validator   │──────► Bad input? → 400 Bad Request
│             │
└──────┬──────┘
       │ 5. Log & Continue
       ▼
┌─────────────┐
│ Audit Log   │──────► Log request details
│             │
└──────┬──────┘
       │
       ▼
   Route Handler
```

---

## 11. Ví Dụ Thực Tế

### Kịch Bản: "Theo Dõi Rủi Ro Bitcoin Vượt $100K"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     KỊCH BẢN: BITCOIN $100K                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BƯỚC 1: Thu thập dữ liệu                                                   │
│  ─────────────────────────                                                  │
│                                                                              │
│  ┌─────────────────┐                                                        │
│  │   POLYMARKET    │  "Will BTC hit $100K by June 2026?"                   │
│  │                 │  → Probability: 67%                                    │
│  │                 │  → Volume: $1.5M                                       │
│  │                 │  → Spread: 2%                                          │
│  └─────────────────┘                                                        │
│                                                                              │
│  ┌─────────────────┐                                                        │
│  │    TIN TỨC      │  "Fed signals no more rate hikes in 2026"             │
│  │                 │  → Sentiment: Bullish                                  │
│  │                 │  → Relevance: High                                     │
│  └─────────────────┘                                                        │
│                                                                              │
│  BƯỚC 2: Xử lý Pipeline                                                     │
│  ─────────────────────                                                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ VALIDATION:                                                         │    │
│  │   ✅ Liquidity: $1.5M volume > $10K threshold                      │    │
│  │   ✅ Anomaly: 67% probability is reasonable                        │    │
│  │   ✅ Semantic: "bitcoin", "crypto" keywords matched                │    │
│  │   ✅ Geographic: Global relevance                                  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ ENRICHMENT:                                                         │    │
│  │   • Confidence: 0.85 (high liquidity + multiple source validation) │    │
│  │   • Keywords: ["bitcoin", "crypto", "fed", "rates"]                │    │
│  │   • Cross-validation: News confirms market sentiment               │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  BƯỚC 3: Output Signal                                                      │
│  ─────────────────────                                                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ OMEN SIGNAL:                                                        │    │
│  │ {                                                                   │    │
│  │   "signal_id": "omen_btc_100k_2026",                               │    │
│  │   "title": "Bitcoin vượt $100K trước tháng 6/2026",                │    │
│  │   "probability": 0.67,                                              │    │
│  │   "confidence_score": 0.85,                                         │    │
│  │   "trend": "INCREASING",                                            │    │
│  │   "keywords": ["bitcoin", "crypto", "fed"],                        │    │
│  │   "explanation_chain": [                                            │    │
│  │     "High market liquidity ($1.5M)",                               │    │
│  │     "Bullish sentiment from Fed news",                             │    │
│  │     "67% probability with 2% spread"                               │    │
│  │   ],                                                                │    │
│  │   "sources": ["polymarket", "news"],                               │    │
│  │   "updated_at": "2026-02-03T10:30:00Z"                             │    │
│  │ }                                                                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  BƯỚC 4: Hiển thị trên Dashboard                                            │
│  ────────────────────────────────                                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  📈 BTC > $100K by June 2026                                       │    │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                │    │
│  │                                                                     │    │
│  │  Probability: ████████████████████░░░░░░░░░░ 67%                  │    │
│  │  Confidence:  ████████████████████████░░░░░░ 85%                  │    │
│  │  Trend: ↑ INCREASING                                               │    │
│  │                                                                     │    │
│  │  Sources: 🟢 Polymarket  🟢 News                                   │    │
│  │  Last Update: 2 minutes ago                                        │    │
│  │                                                                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tóm Tắt

### OMEN Hoạt Động Như Thế Nào?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TÓM TẮT NGẮN GỌN                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1️⃣  THU THẬP: Lấy dữ liệu từ nhiều nguồn (Polymarket, News, Weather...)   │
│                                                                              │
│  2️⃣  CHUẨN HÓA: Chuyển đổi tất cả về format chung (RawSignalEvent)         │
│                                                                              │
│  3️⃣  KIỂM TRA: Chạy qua 4 validation rules (Liquidity, Anomaly, etc.)      │
│                                                                              │
│  4️⃣  LÀM GIÀU: Thêm context, tính confidence, phân loại                    │
│                                                                              │
│  5️⃣  PHÁT HÀNH: Gửi qua REST API, WebSocket, lưu Database                  │
│                                                                              │
│  6️⃣  HIỂN THỊ: Dashboard React hiển thị real-time                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Điểm Mạnh Của OMEN

| Tính năng | Mô tả |
|-----------|-------|
| **Multi-Source** | Kết hợp nhiều nguồn dữ liệu khác nhau |
| **Real-time** | Cập nhật giá và sự kiện tức thì |
| **Validation** | Lọc dữ liệu kém chất lượng |
| **Transparency** | Giải thích tại sao tín hiệu được tạo |
| **Data Integrity** | Tách biệt rõ LIVE/DEMO mode |
| **Production Ready** | Logging, metrics, health checks đầy đủ |

---

**Cuối báo cáo**

*Được tạo tự động bởi hệ thống tài liệu OMEN*
