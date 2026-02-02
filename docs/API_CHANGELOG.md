# OMEN API Changelog

All notable changes to the OMEN API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-02-01

### ⚠️ Breaking Changes

- **Partner Risk API deprecated** - All `/api/v1/partner-risk/*` endpoints now return `410 Gone`
  - **Migration**: Use `/api/v1/partner-signals/*` instead
  - Risk decisions (SAFE/WARNING/CRITICAL) should be made by RiskCast, not OMEN
  - See [Migration Guide](https://docs.omen.io/migration/v2-signals)

- **Risk verdict fields removed** from all API responses:
  - `risk_status` - No longer returned
  - `overall_risk` - No longer returned
  - `risk_breakdown` - No longer returned
  - **Reason**: OMEN is a Signal Engine, not a Decision Engine

### Added

- **New Signal Contract Headers**:
  - `X-OMEN-Contract-Version: 2.0.0` - API contract version
  - `X-OMEN-Contract-Type: signal-only` - Indicates signal-only responses

- **Partner Signals API** (`/api/v1/partner-signals/`):
  - `GET /api/v1/partner-signals/` - List all partner signals
  - `GET /api/v1/partner-signals/{symbol}` - Get signals for specific partner
  - `GET /api/v1/partner-signals/{symbol}/price` - Get price signals
  - `GET /api/v1/partner-signals/{symbol}/fundamentals` - Get fundamental signals

- **Confidence Intervals** in signal responses:
  - `confidence.point_estimate` - Best estimate
  - `confidence.lower_bound` - 95% CI lower bound
  - `confidence.upper_bound` - 95% CI upper bound

- **Evidence Trail** for all signals:
  - `evidence[]` array with source, timestamp, raw_value, normalized_value

- **WebSocket Real-time Streaming** (`/api/v1/ws/signals`):
  - Real-time signal updates via WebSocket
  - Authentication via query parameter `?api_key=xxx`

- **Multi-Source Intelligence API** (`/api/v1/multi-source/`):
  - Cross-source correlation
  - Conflict detection
  - Unified signal view

### Changed

- **Response structure standardized**:
  - All responses now include `schema_version: "2.0.0"`
  - All responses include `omen_version: "2.x.x"`
  - Timestamps are always ISO 8601 with timezone (UTC)

- **Pagination** changed from offset-based to cursor-based:
  - Old: `?page=2&per_page=20`
  - New: `?cursor=<opaque_cursor>&limit=20`
  - Better performance and consistency

- **Error responses** standardized:
  ```json
  {
    "error": "ERROR_CODE",
    "message": "Human readable message",
    "error_code": "ERR_4XX_XXX",
    "hint": "How to fix",
    "documentation_url": "https://docs.omen.io/errors#error-code"
  }
  ```

### Security

- **RBAC (Role-Based Access Control)** introduced:
  - Scopes: `read:signals`, `write:signals`, `read:partners`, etc.
  - API keys can be scoped to specific permissions

- **Rate limiting** enhanced:
  - Default: 600 requests/minute
  - Burst: 50 requests
  - Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Deprecated

- `/api/v1/partner-risk/*` - Use `/api/v1/partner-signals/*` instead (returns 410)
- `RiskLevel` class in SDK - No replacement (OMEN doesn't determine risk)
- `PartnerRiskAssessment` - Use `PartnerSignalResponse` instead

---

## [1.0.0] - 2025-06-15

### Added

- Initial API release
- Partner risk assessment endpoints
- Signal validation pipeline
- Polymarket data source integration

---

## Migration Guide: v1 → v2

### Before (v1 - DEPRECATED)

```python
# Old way - getting risk verdict (DEPRECATED)
response = client.get("/api/v1/partner-risk/partners/HAH")
risk_status = response["risk_status"]  # "WARNING" - OMEN made decision
```

### After (v2 - CORRECT)

```python
# New way - getting signals (RiskCast decides)
response = client.get("/api/v1/partner-signals/HAH")
signals = response["signals"]  # Raw metrics
confidence = response["confidence"]  # Data quality
evidence = response["evidence"]  # Audit trail

# RiskCast evaluates signals based on context
# risk_decision = riskcast.evaluate(signals, order_context, user_risk_appetite)
```

### Key Differences

| Aspect | v1 (Deprecated) | v2 (Current) |
|--------|-----------------|--------------|
| Risk Verdict | OMEN decides | RiskCast decides |
| Response | `risk_status: "WARNING"` | `signals: {...metrics}` |
| Evidence | Minimal | Full audit trail |
| Confidence | Single number | Interval with bounds |
| Pagination | Offset-based | Cursor-based |

---

## Versioning Policy

- **Major version (X.0.0)**: Breaking changes - requires client updates
- **Minor version (0.X.0)**: New features, backward compatible
- **Patch version (0.0.X)**: Bug fixes, no API changes

We maintain backward compatibility for at least 6 months after deprecation.
