# OMEN — Động cơ Trí tuệ Tín hiệu (Signal Intelligence Engine)

**Phiên bản:** 0.1.0 · **Python:** 3.10+ · **Trạng thái:** Alpha

---

## Mục lục

1. [Tổng quan OMEN](#1-tổng-quan-omen)
2. [Không nằm trong mục tiêu (Non-goals)](#2-không-nằm-trong-mục-tiêu-non-goals)
3. [Khái niệm cốt lõi](#3-khái-niệm-cốt-lõi)
4. [Kiến trúc hệ thống](#4-kiến-trúc-hệ-thống)
5. [Pipeline 4 lớp](#5-pipeline-4-lớp-trí-tuệ)
6. [Hợp đồng dữ liệu và ví dụ](#6-hợp-đồng-dữ-liệu-data-contracts-và-ví-dụ)
7. [Mô hình tin cậy (Confidence)](#7-mô-hình-tin-cậy-confidence)
8. [Traceability & Reproducibility](#8-traceability--reproducibility)
9. [Mở rộng / Plugin](#9-mở-rộng--plugin)
10. [Chạy cục bộ](#10-chạy-cục-bộ)
11. [Kiểm thử & CI](#11-kiểm-thử--ci)
12. [Triển khai](#12-triển-khai)
13. [Lộ trình & khoảng trống (v0)](#13-lộ-trình--khoảng-trống-v0)

---

## 1. Tổng quan OMEN

**OMEN** là một **động cơ trí tuệ (intelligence engine)**, không phải ứng dụng end-user. Nó đọc **niềm tin tập thể dưới ràng buộc tài chính** (thị trường dự đoán) và biến nó thành **tác động có thể giải thích, xác định và tái lập**.

**Sứ mệnh:**

- **Đầu vào:** Dữ liệu thô từ prediction markets (Polymarket, v.v.) đã được chuẩn hóa.
- **Biến đổi:** Bốn lớp cố định: Thu thập → Kiểm định → Dịch tác động → Xuất bản.
- **Đầu ra:** Đối tượng **OmenSignal** — hợp đồng ổn định cho downstream (RiskCast, BI, webhook, v.v.).

**Nguyên tắc bất di bất dịch:**

| Nguyên tắc | Ý nghĩa |
|------------|---------|
| **Structured** | Mọi đầu ra là Pydantic model, không có blob tự do. |
| **Explainable** | Mỗi tín hiệu có `explanation_chain` (các bước lý do, rule, đóng góp confidence). |
| **Timestamped** | `observed_at`, `generated_at`, `validated_at`… lấy từ `ProcessingContext` khi replay. |
| **Reproducible** | Cùng `RawSignalEvent` + cùng `ruleset_version` → cùng `OmenSignal` (idempotent). |
| **No hidden logic** | Không mô hình đen, không LLM ẩn trong quyết định. Logic nằm trong rules versioned. |

Mã nguồn chính: `src/omen/` — xem `src/omen/application/pipeline.py` cho luồng tổng thể.

---

## 2. Không nằm trong mục tiêu (Non-goals)

- **Không phải dashboard hay app người dùng cuối** — OMEN chỉ là engine; UI demo (`omen-demo/`) chỉ để minh họa.
- **Không phải black-box forecasting** — Mọi con số đều có nguồn gốc từ rules + bằng chứng (evidence), không dự báo mù.
- **Không phải hệ thống thuần LLM** — LLM (nếu có sau này) chỉ hỗ trợ phụ (ví dụ tóm tắt); quyết định emit/reject và metric đến từ rules xác định.
- **Không thay thế con người** — Output là “intelligence artifact” để con người/tích hợp ra quyết định, không tự động trade hay đóng cửa route.

---

## 3. Khái niệm cốt lõi

### 3.1 Belief-as-signal (Niềm tin là tín hiệu)

Giá trên prediction market (ví dụ “75% Yes”) phản ánh niềm tin có tiền đặt cọc. OMEN coi đó là **tín hiệu thô**, chuẩn hóa thành `RawSignalEvent` (Layer 1), rồi mới lọc và dịch sang tác động (xem `src/omen/domain/models/raw_signal.py`).

### 3.2 Liquidity as information (Thanh khoản là thông tin)

`MarketMetadata.total_volume_usd` và `current_liquidity_usd` là proxy cho độ tin cậy của thị trường. Rule **LiquidityValidationRule** (xem `src/omen/domain/rules/validation/liquidity_rule.py`) loại bỏ market quá non: ngưỡng mặc định `min_liquidity_usd` (config, thường $1000).

### 3.3 Deterministic translation (Dịch tác động xác định)

Layer 3 không dùng xác suất ngẫu nhiên. Mỗi **ImpactTranslationRule** nhận `ValidatedSignal` + `ProcessingContext` và trả về `TranslationResult` (metrics, routes, systems, severity, explanation). Cùng input + cùng ruleset → cùng output. Giao diện: `src/omen/domain/rules/translation/base.py` (Protocol `ImpactTranslationRule`).

---

## 4. Kiến trúc hệ thống

OMEN tuân theo **Clean / Hexagonal**: domain độc lập với adapter, giao tiếp qua port (interface).

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    THẾ GIỚI NGOẠI VI                     │
                    ├─────────────────────────────────────────────────────────┤
  CỔNG VÀO          │  SignalSource (port)          │  OutputPublisher (port)   │
  (Inbound)         │  · fetch_events(limit)        │  · publish(signal)        │
                    │  · fetch_by_id(market_id)     │  SignalRepository (port)  │
                    │  Adapter: Polymarket*, Stub   │  · save / find_by_hash    │
                    │  → RawSignalEvent             │  Adapter: InMemory, …     │
                    └─────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LỚP DOMAIN (src/omen/domain/) — không phụ thuộc framework / I/O             │
│  models/     raw_signal, validated_signal, impact_assessment, omen_signal,    │
│              common, context, explanation                                    │
│  rules/      base.Rule, validation/*, translation/base, translation/logistics│
│  services/   signal_validator, impact_translator                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  APPLICATION (src/omen/application/)                                         │
│  pipeline.py     OmenPipeline.process_single(event) → PipelineResult         │
│  container.py    Composition root: validator, translator, repository,        │
│                  publisher, pipeline (xem get_container / create_default)    │
│  ports/          SignalSource, SignalRepository, OutputPublisher             │
└─────────────────────────────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
┌───────────────────────────────┐                 ┌───────────────────────────────┐
│  ADAPTERS INBOUND             │                 │  ADAPTERS OUTBOUND            │
│  adapters/inbound/            │                 │  adapters/outbound/           │
│  · polymarket/ (client,       │                 │  · console_publisher          │
│    mapper, source,            │                 │  · webhook_publisher          │
│    live_client)               │                 │  · kafka_publisher*           │
│  · stub_source.py             │                 │  adapters/persistence/        │
│                               │                 │  · in_memory_repository       │
└───────────────────────────────┘                 └───────────────────────────────┘
```

**Đường dẫn chính:**

| Thành phần | Đường dẫn |
|------------|-----------|
| Port nguồn tín hiệu | `src/omen/application/ports/signal_source.py` |
| Pipeline 4 lớp | `src/omen/application/pipeline.py` |
| Composition / DI | `src/omen/application/container.py` |
| Domain models | `src/omen/domain/models/` |
| Validation rules | `src/omen/domain/rules/validation/` |
| Translation rules | `src/omen/domain/rules/translation/` |
| Adapter Polymarket (live) | `src/omen/adapters/inbound/polymarket/` (live_client, mapper, source) |
| API FastAPI | `src/omen/main.py`, `src/omen/api/routes/` |

---

## 5. Pipeline 4 lớp trí tuệ

Luồng xử lý nằm trong `OmenPipeline._process_single_inner` (xem `src/omen/application/pipeline.py`).

| Lớp | Đầu vào | Đầu ra | Invariant / Điều kiện |
|-----|---------|--------|------------------------|
| **Layer 1** | API thị trường (qua adapter) | **RawSignalEvent** | Chuẩn hóa bắt buộc: `event_id`, `title`, `probability` ∈ [0,1], `market.total_volume_usd`, `market.current_liquidity_usd`. `input_event_hash` tính từ tập trường cố định (xem docstring trong `raw_signal.py`). |
| **Layer 2** | RawSignalEvent | **ValidatedSignal** hoặc reject | Mọi rule validation phải pass (theo cấu hình). Reject → `PipelineResult(signals=[], validation_failures=...)`. Output có `explanation` (ExplanationChain), `overall_validation_score`, `deterministic_trace_id`. |
| **Layer 3** | ValidatedSignal | **ImpactAssessment** (hoặc không có nếu không rule nào áp dụng) | Chỉ rules có `domain` ∈ `target_domains` và `is_applicable(signal)==True` mới chạy. `explanation_chain` và `explanation_steps` bắt buộc không rỗng. |
| **Layer 4** | ImpactAssessment | **OmenSignal** | `OmenSignal.from_impact_assessment(...)`. Chỉ emit nếu `confidence_score >= min_confidence_for_output`. Mỗi signal có `input_event_hash`, `ruleset_version`, `deterministic_trace_id`. |

**Idempotency:** Trước Layer 2, pipeline gọi `repository.find_by_hash(event.input_event_hash)`. Nếu đã có signal cho hash đó thì trả về kết quả cache, không chạy lại (xem `_process_single_inner`).

---

## 6. Hợp đồng dữ liệu (Data Contracts) và ví dụ

Tất cả schema dùng **Pydantic** (strict, frozen khi có thể). Dưới đây là dạng ví dụ, bám sát model thật trong repo.

### 6.1 RawSignalEvent (Layer 1)

Định nghĩa: `src/omen/domain/models/raw_signal.py`.

```json
{
  "event_id": "polymarket-0xabc123",
  "title": "Will the Suez Canal be blocked by Dec 31?",
  "description": "Resolution: Yes if ...",
  "probability": 0.72,
  "movement": null,
  "keywords": ["suez", "canal", "shipping"],
  "inferred_locations": [],
  "market": {
    "source": "polymarket",
    "market_id": "0xabc123",
    "market_url": "https://polymarket.com/event/...",
    "created_at": null,
    "resolution_date": null,
    "total_volume_usd": 150000.0,
    "current_liquidity_usd": 25000.0,
    "num_traders": 1200
  },
  "observed_at": "2025-01-15T10:00:00Z"
}
```

Trường được dùng cho dedupe/replay: `input_event_hash` (computed từ `event_id`, `title`, `description`, `probability`, `movement`, `keywords`, `market.source`, `market.market_id`, `total_volume_usd`, `current_liquidity_usd`).

### 6.2 ValidatedSignal (Layer 2)

Định nghĩa: `src/omen/domain/models/validated_signal.py`.

```json
{
  "event_id": "polymarket-0xabc123",
  "original_event": { "...": "RawSignalEvent subset ..." },
  "category": "GEOPOLITICAL",
  "subcategory": null,
  "relevant_locations": [],
  "affected_chokepoints": ["Suez Canal"],
  "validation_results": [
    {
      "rule_name": "liquidity_validation",
      "rule_version": "1.0.0",
      "status": "PASSED",
      "score": 0.95,
      "reason": "Sufficient liquidity: $25,000 >= $1,000 threshold"
    }
  ],
  "overall_validation_score": 0.9,
  "signal_strength": 0.85,
  "liquidity_score": 0.9,
  "explanation": {
    "trace_id": "a1b2c3d4...",
    "steps": [...],
    "total_steps": 4,
    "started_at": "2025-01-15T10:00:00Z",
    "completed_at": null
  },
  "ruleset_version": "v1.0.0",
  "validated_at": "2025-01-15T10:00:01Z"
}
```

### 6.3 ImpactAssessment (Layer 3)

Định nghĩa: `src/omen/domain/models/impact_assessment.py`.

```json
{
  "event_id": "polymarket-0xabc123",
  "source_signal": { "...": "ValidatedSignal reference ..." },
  "domain": "LOGISTICS",
  "metrics": [
    {
      "name": "transit_time_increase",
      "value": 5.4,
      "unit": "days",
      "uncertainty": { "lower": 4.3, "upper": 7.0, "confidence_interval": 0.8 },
      "confidence": 0.75,
      "evidence_type": "historical",
      "evidence_source": "Drewry Q1 2024"
    }
  ],
  "affected_routes": [
    {
      "route_id": "ASIA-EU-SUEZ",
      "route_name": "Asia to Europe via Suez",
      "origin_region": "East Asia",
      "destination_region": "Northern Europe",
      "impact_severity": 0.72,
      "alternative_routes": ["ASIA-EU-CAPE"],
      "estimated_delay_days": 5.4,
      "delay_uncertainty": null
    }
  ],
  "affected_systems": [],
  "overall_severity": 0.72,
  "severity_label": "High",
  "expected_onset_hours": 24,
  "expected_duration_hours": 720,
  "explanation_steps": [
    {
      "step_id": 1,
      "rule_name": "red_sea_disruption_logistics",
      "rule_version": "1.0.0",
      "reasoning": "Red Sea disruption at 72% adds 5.4 days transit",
      "confidence_contribution": 0.25,
      "timestamp": "2025-01-15T10:00:02Z"
    }
  ],
  "explanation_chain": { "trace_id": "...", "steps": [...], "total_steps": 1, "started_at": "...", "completed_at": null },
  "impact_summary": "Suez blocade probability 72% implies +5.4 days transit Asia–Europe.",
  "assumptions": ["Baseline transit 21 days", "Cape diversion +14 days"],
  "ruleset_version": "v1.0.0",
  "translation_rules_applied": ["red_sea_disruption_logistics"],
  "assessed_at": "2025-01-15T10:00:02Z"
}
```

### 6.4 OmenSignal (Layer 4 — Hợp đồng downstream)

Định nghĩa: `src/omen/domain/models/omen_signal.py`. Đây là **contract** mà sản phẩm downstream (RiskCast, BI, webhook consumer) kỳ vọng.

```json
{
  "signal_id": "OMEN-A1B2C3D4E5F6",
  "event_id": "polymarket-0xabc123",
  "category": "GEOPOLITICAL",
  "subcategory": null,
  "domain": "LOGISTICS",
  "current_probability": 0.72,
  "probability_momentum": "STABLE",
  "probability_change_24h": null,
  "confidence_level": "HIGH",
  "confidence_score": 0.82,
  "confidence_factors": { "signal_strength": 0.85, "liquidity_score": 0.9, "validation_score": 0.9 },
  "severity": 0.72,
  "severity_label": "High",
  "key_metrics": [{ "name": "transit_time_increase", "value": 5.4, "unit": "days", "uncertainty": { "lower": 4.3, "upper": 7.0 }, "confidence": 0.75, "evidence_source": "Drewry Q1 2024" }],
  "affected_routes": [{ "route_id": "ASIA-EU-SUEZ", "route_name": "Asia to Europe via Suez", "origin_region": "East Asia", "destination_region": "Northern Europe", "impact_severity": 0.72 }],
  "affected_systems": [],
  "affected_regions": ["East Asia", "Northern Europe"],
  "expected_onset_hours": 24,
  "expected_duration_hours": 720,
  "title": "Will the Suez Canal be blocked by Dec 31?",
  "summary": "Suez blocade probability 72% implies +5.4 days transit Asia–Europe.",
  "detailed_explanation": "Suez blocade probability 72% implies +5.4 days transit...\n\nAssumptions:\n  • Baseline transit 21 days\n  • Cape diversion +14 days",
  "explanation_chain": { "trace_id": "...", "steps": [...], "total_steps": 3, "started_at": "...", "completed_at": "..." },
  "input_event_hash": "f7e8d9c0b1a2...",
  "ruleset_version": "v1.0.0",
  "deterministic_trace_id": "a1b2c3d4e5f6...",
  "source_market": "polymarket",
  "market_url": "https://polymarket.com/event/...",
  "generated_at": "2025-01-15T10:00:02Z"
}
```

Các trường computed: `is_actionable` (HIGH/MEDIUM confidence + có route/system + severity ≥ 0.3), `urgency` (từ `expected_onset_hours` và severity). Chi tiết: `src/omen/domain/models/omen_signal.py`.

---

## 7. Mô hình tin cậy (Confidence)

- **Confidence score** trong OmenSignal: trung bình của `confidence_factors` (`signal_strength`, `liquidity_score`, `overall_validation_score`) — xem `OmenSignal.from_impact_assessment` trong `src/omen/domain/models/omen_signal.py`.
- **Confidence level:** `ConfidenceLevel.from_score(score)` trong `src/omen/domain/models/common.py`:
  - score ≥ 0.7 → **HIGH**
  - score ≥ 0.4 → **MEDIUM**
  - còn lại → **LOW**
- **Ràng buộc:** Mọi score nằm trong [0, 1]. Mỗi bước trong `explanation_chain` có `confidence_contribution` ∈ [0, 1]. Pipeline chỉ emit signal khi `confidence_score >= min_confidence_for_output` (mặc định 0.3, cấu hình trong `config` / `PipelineConfig`).

---

## 8. Traceability & Reproducibility

| Khái niệm | Vai trò | Nơi định nghĩa / dùng |
|-----------|---------|---------------------------|
| **event_id** | Định danh sự kiện từ nguồn (ví dụ `polymarket-0x...`) | RawSignalEvent, suốt pipeline |
| **input_event_hash** | Hash xác định của đầu vào (dedupe, replay). Thay đổi bất kỳ trường trong docstring → hash đổi | `RawSignalEvent.input_event_hash` (computed), `raw_signal.py` |
| **ruleset_version** | Phiên bản tập rule (Validation + Translation) | ProcessingContext, ValidatedSignal, ImpactAssessment, OmenSignal; config: `OMEN_RULESET_VERSION` |
| **trace_id** | ID trace của lượt xử lý | `ProcessingContext.trace_id` (từ `create()` hoặc `create_for_replay()`), `context.py` |
| **deterministic_trace_id** | Trace tái lập được của signal (từ hash + ruleset + domain) | ValidatedSignal, ImpactAssessment, OmenSignal |
| **signal_id** | Định danh OMEN cho từng signal (dạng `OMEN-{hash12}`) | OmenSignal, sinh trong `from_impact_assessment` |

**Cách replay:** Tạo `ProcessingContext.create_for_replay(processing_time, ruleset_version)` và gọi `pipeline.process_single(event, context=ctx)`. Cùng `event` (ví dụ cùng `input_event_hash`) + cùng `ruleset_version` + cùng `processing_time` → cùng trace và output.

**Gỡ lỗi:** Dùng `explanation_chain` + `explanation_steps` trên từng layer; `validation_failures` trong `PipelineResult` khi Layer 2 reject; logs trong `OmenPipeline` (logger ứng dụng).

---

## 9. Mở rộng / Plugin

### 9.1 Thêm adapter nguồn (Market adapter)

1. Implement port `SignalSource` trong `src/omen/application/ports/signal_source.py`: `source_name`, `fetch_events(limit)`, `fetch_events_async(limit)`, `fetch_by_id(market_id)`.
2. Trả về đối tượng `RawSignalEvent` theo schema trong `src/omen/domain/models/raw_signal.py` (gồm `MarketMetadata`).
3. Tham khảo: `src/omen/adapters/inbound/polymarket/source.py` (PolymarketSignalSource), `src/omen/adapters/inbound/stub_source.py` (test).

### 9.2 Thêm rule validation (Layer 2)

1. Tạo class kế thừa `Rule[RawSignalEvent, ValidationResult]` (base: `src/omen/domain/rules/base.py`).
2. Implement `name`, `version`, `apply(raw) -> ValidationResult`, `explain(raw, result, processing_time) -> ExplanationStep`.
3. ValidationResult: `rule_name`, `rule_version`, `status` (ValidationStatus), `score`, `reason` — xem `src/omen/domain/models/validated_signal.py`.
4. Đăng ký rule trong `SignalValidator(rules=[...])` khi build container. Ví dụ rule có sẵn: `src/omen/domain/rules/validation/liquidity_rule.py`, `geographic_relevance_rule.py`, `semantic_relevance_rule.py`, `anomaly_detection_rule.py`.

### 9.3 Thêm ImpactTranslator plugin (Layer 3)

1. Implement Protocol `ImpactTranslationRule` (hoặc kế thừa `BaseTranslationRule`) trong `src/omen/domain/rules/translation/base.py`.
2. Cung cấp: `name`, `version`, `domain` (ImpactDomain), `applicable_categories`, `is_applicable(signal)`, `translate(signal, processing_time=...) -> TranslationResult`.
3. TranslationResult gồm: `applicable`, `metrics`, `affected_routes`, `affected_systems`, `severity_contribution`, `assumptions`, `explanation` (ExplanationStep).
4. Thêm rule vào `ImpactTranslator(rules=[...])` trong container. Ví dụ: `src/omen/domain/rules/translation/logistics/red_sea_disruption.py`, `port_closure.py`, `strike_impact.py`.
5. Domain mới (ví dụ ENERGY, INSURANCE): thêm enum trong `ImpactDomain` (`common.py`), tạo thư mục `domain/rules/translation/{domain}/` và implement rules tương ứng.

---

## 10. Chạy cục bộ

**Yêu cầu:** Python 3.10+, pip.

```bash
git clone <repo>
cd OMEN
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Chỉnh .env nếu cần (OMEN_*, OMEN_SECURITY_*)
```

**Chạy pipeline (CLI):**

```bash
python scripts/run_pipeline.py --source stub --limit 5
# hoặc: python -m scripts.run_pipeline --source stub --limit 5
```

Script hiện chỉ triển khai nguồn `stub` (`scripts/run_pipeline.py`). Nguồn Polymarket thật dùng qua API: `POST /api/v1/live/process`.

**Chạy API:**

```bash
uvicorn omen.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET /health`
- API có bảo vệ API key: `GET/POST /api/v1/signals`, `GET /api/v1/...` (explanations) — header `X-API-Key`.
- Live Polymarket (demo, không bắt buộc API key): `GET /api/v1/live/events`, `POST /api/v1/live/process`, v.v. — xem `src/omen/api/routes/live.py`.

**Biến môi trường quan trọng:** Xem `.env.example`. Ví dụ:

- `OMEN_RULESET_VERSION`, `OMEN_MIN_LIQUIDITY_USD`, `OMEN_TARGET_DOMAINS`, `OMEN_WEBHOOK_URL`, …
- `OMEN_SECURITY_API_KEYS`, `OMEN_SECURITY_CORS_ENABLED`, `OMEN_SECURITY_RATE_LIMIT_*`, …

Cấu hình ứng dụng: `src/omen/config.py` (OmenConfig, tiền tố `OMEN_`).

---

## 11. Kiểm thử & CI

- **Test:** `pytest` (cấu hình trong `pyproject.toml` và `pytest.ini`). Thư mục: `tests/` (unit, integration, benchmarks).
- **Coverage:** `pytest --cov=src/omen --cov-fail-under=85` (ngưỡng có thể tùy repo).
- **Lint / type-check (cục bộ):** Dự án dùng `ruff` và `mypy` (cấu hình trong `pyproject.toml`). Chạy thủ công:
  - `ruff check src/omen`
  - `mypy src/omen`
- **CI:** `.github/workflows/test.yml` — trên push/PR: setup Python 3.11, `pip install -e ".[dev]"`, chạy `pytest --cov=src/omen --cov-fail-under=85`; upload coverage (Codecov). **Chưa có bước chạy mypy/ruff trong CI** — ghi nhận trong [Lộ trình & khoảng trống](#13-lộ-trình--khoảng-trống-v0).

---

## 12. Triển khai

- **API:** Chạy qua **uvicorn** (hoặc ASGI server tương đương), entrypoint `omen.main:app` (xem `src/omen/main.py`).
- **Persistence:** Hiện chỉ có **InMemorySignalRepository**. PostgreSQL / persistence bền vững chưa tích hợp — xem [Lộ trình & khoảng trống](#13-lộ-trình--khoảng-trống-v0).
- **Message queue:** Adapter **KafkaPublisher** tồn tại nhưng có thể chưa đủ cho production (xem `adapters/outbound/kafka_publisher.py`).
- **Docker:** `docker-compose.yml` chủ yếu để placeholder (Postgres, Kafka bị comment). **Chưa có Dockerfile cho OMEN** — Planned.

---

## 13. Lộ trình & khoảng trống (v0)

| Mục | Trạng thái | Ghi chú |
|-----|------------|---------|
| Pipeline 4 lớp, idempotency, OmenSignal contract | ✅ Có | `application/pipeline.py`, `domain/models/` |
| Validation: Liquidity, Anomaly, Semantic, Geographic | ✅ Có | `domain/rules/validation/`, đăng ký trong `container.py` |
| Translation: Red Sea, Port Closure, Strike (logistics) | ✅ Có | `domain/rules/translation/logistics/` |
| Adapter Polymarket (live Gamma API) | ✅ Có | `adapters/inbound/polymarket/live_client.py`, `source.py`, `mapper.map_event` |
| API FastAPI + Live endpoints (/api/v1/live/*) | ✅ Có | `main.py`, `api/routes/live.py` |
| Stub source, In-memory repo, Console/Webhook publisher | ✅ Có | `adapters/inbound/stub_source.py`, persistence, outbound |
| PostgreSQL / persistence bền vững | ❌ Chưa | Chỉ InMemory. DB URL trong `.env.example` là “Future”. |
| Kafka producer production-ready | ⚠️ Không rõ | Có adapter nhưng cần kiểm tra contract và error handling. |
| CI chạy mypy + ruff | ❌ Chưa | Chỉ pytest + coverage trong `test.yml`. |
| Dockerfile / image OMEN | ❌ Chưa | Planned. |
| Dashboard / app người dùng cuối | Non-goal | Chỉ có `omen-demo` làm demo tích hợp. |
| Domain ENERGY / INSURANCE / FINANCE | Planned | Enum có trong `ImpactDomain`; chưa có rules translation tương ứng. |

---

## Tài liệu thêm

- **Onboarding:** `docs/onboarding.md`
- **ADR:** `docs/adr/` (deterministic processing, hexagonal, evidence-based parameters, validation, security)
- **Evidence / tham số logistics:** `docs/evidence/logistics_parameters.md`
- **Báo cáo audit hệ thống:** `docs/OMEN_SYSTEM_AUDIT_REPORT.md` (có thể chứa nhận xét cũ về từng module; cần đối chiếu với mã hiện tại).

---

**Giấy phép:** MIT · **Đóng góp:** Xem `CONTRIBUTING.md`.
