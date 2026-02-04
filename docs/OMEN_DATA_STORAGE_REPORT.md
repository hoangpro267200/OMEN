# OMEN Data Storage System Report

**Generated:** February 3, 2026  
**Status:** ⚠️ Development Mode - Data NOT Persisted

---

## Executive Summary

Hệ thống OMEN **hiện tại đang chạy ở chế độ development** và **KHÔNG lưu trữ dữ liệu vĩnh viễn**. Khi server restart, tất cả signal data sẽ bị mất.

### Current Configuration Analysis

| Setting | Current Value | Impact |
|---------|--------------|--------|
| `OMEN_ENV` | `development` | In-memory storage only |
| `DATABASE_URL` | Not set | PostgreSQL disabled |
| `OMEN_CACHE_BACKEND` | `memory` | No Redis caching |

---

## 1. Tình Trạng Lưu Trữ Hiện Tại

### ❌ Vấn Đề: Data Không Được Lưu Vĩnh Viễn

**Lý do:**
```
OMEN_ENV=development (trong .env)
```

Khi `OMEN_ENV=development`:
- Hệ thống sử dụng **InMemorySignalRepository**
- Tất cả signals được lưu trong Python dictionaries (RAM)
- **Data bị mất hoàn toàn khi restart server**

**Code evidence** (`src/omen/application/container.py` lines 85-120):
```python
if env == "production":
    # Tries PostgreSQL if DATABASE_URL is set
    ...
else:
    repository = InMemorySignalRepository()  # <-- Current state
    logger.debug("Using in-memory repository (development mode)")
```

### ✅ Ledger Files - Có Tồn Tại

Ledger system **có hoạt động** và đang lưu file:

```
.demo/ledger/
└── 2026-01-29/
    ├── _CURRENT
    └── signals-001.wal
```

Tuy nhiên, ledger chỉ là **append-only log** cho audit purposes, không phải database chính để query signals.

---

## 2. Kiến Trúc Storage của OMEN

### 2.1 Storage Backends Có Sẵn

| Backend | Type | Persistence | Current Status |
|---------|------|-------------|----------------|
| **PostgreSQL** | Database | ✅ Permanent | ❌ Not configured |
| **SQLite** | Database | ✅ Permanent | ✅ RiskCast only |
| **Ledger (WAL)** | File-based | ✅ Permanent | ✅ Active in .demo |
| **In-Memory** | RAM | ❌ Lost on restart | ✅ **Active (current)** |

### 2.2 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SIGNAL DATA FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Data Sources]                                                              │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────┐     ┌─────────────────┐     ┌──────────────────────┐       │
│  │  Polymarket │────▶│                 │────▶│ SignalValidator      │       │
│  │  Weather    │     │  API Endpoints  │     │ (Liquidity, Semantic)│       │
│  │  News       │     │  Background Job │     └──────────────────────┘       │
│  │  Stock      │     │                 │              │                      │
│  └─────────────┘     └─────────────────┘              ▼                      │
│                                              ┌────────────────────┐          │
│                                              │ SignalEnricher     │          │
│                                              └────────────────────┘          │
│                                                       │                      │
│                                                       ▼                      │
│                               ┌───────────────────────────────────────┐      │
│                               │         STORAGE LAYER                 │      │
│                               ├───────────────────────────────────────┤      │
│                               │                                       │      │
│  DEVELOPMENT (Current)        │  ┌─────────────────────────────────┐ │      │
│                               │  │  InMemorySignalRepository       │ │      │
│                               │  │  ❌ Data lost on restart        │ │      │
│                               │  └─────────────────────────────────┘ │      │
│                               │                                       │      │
│  PRODUCTION (Recommended)     │  ┌─────────────────────────────────┐ │      │
│                               │  │  PostgresSignalRepository       │ │      │
│                               │  │  ✅ Persistent, scalable        │ │      │
│                               │  └─────────────────────────────────┘ │      │
│                               │                                       │      │
│  LEDGER (Always On)           │  ┌─────────────────────────────────┐ │      │
│                               │  │  Ledger Writer (WAL files)      │ │      │
│                               │  │  ✅ Audit trail, append-only    │ │      │
│                               │  └─────────────────────────────────┘ │      │
│                               │                                       │      │
│                               └───────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Làm Sao Để Kiểm Tra Data Có Được Lưu?

### 3.1 Kiểm Tra Quick

**Cách 1: Restart server và check signals**
```bash
# 1. Tạo/fetch một số signals
# 2. Restart server  
# 3. Nếu signals biến mất → Không persist
# 4. Nếu signals còn → Đang persist
```

**Cách 2: Check environment variable**
```bash
# Trong .env file, check:
OMEN_ENV=development  # ❌ Không persist
OMEN_ENV=production   # ✅ CÓ THỂ persist (nếu có DATABASE_URL)
```

**Cách 3: Check logs khi start server**
```
# Nếu thấy:
"Using in-memory repository (development mode)" → ❌ Không persist

# Nếu thấy:
"Using PostgreSQL repository for production" → ✅ Đang persist
```

### 3.2 Kiểm Tra Ledger Files

```bash
# Check ledger directory
ls -la .demo/ledger/

# Nếu có files → Ledger đang ghi (audit trail)
# Ledger là append-only, không dùng để query signals
```

---

## 4. Làm Sao Để Bật Lưu Trữ Vĩnh Viễn?

### Option A: Production Mode với PostgreSQL (Recommended)

**Bước 1: Cài đặt PostgreSQL**
```bash
# Docker way (dễ nhất)
docker run -d \
  --name omen-postgres \
  -e POSTGRES_USER=omen \
  -e POSTGRES_PASSWORD=omen_secure_password \
  -e POSTGRES_DB=omen \
  -p 5432:5432 \
  -v omen_pgdata:/var/lib/postgresql/data \
  postgres:15
```

**Bước 2: Cập nhật .env**
```env
# Change environment
OMEN_ENV=production

# Add database URL
DATABASE_URL=postgresql://omen:omen_secure_password@localhost:5432/omen
```

**Bước 3: Install async PostgreSQL driver**
```bash
pip install asyncpg
```

**Bước 4: Restart OMEN**
```bash
# Server sẽ log:
# "Using PostgreSQL repository for production"
```

### Option B: Giữ Development Mode + Add SQLite (Custom)

Nếu muốn giữ development mode nhưng có persistence, cần tạo SQLite repository mới. Code có sẵn framework nhưng chưa implement cho main signals.

---

## 5. Storage Components Chi Tiết

### 5.1 InMemorySignalRepository (Current)

**Location:** `src/omen/adapters/persistence/in_memory_repository.py`

```python
class InMemorySignalRepository(SignalRepository):
    _signals_by_id: Dict[str, OmenSignal] = {}
    _signals_by_hash: Dict[str, OmenSignal] = {}
    _signals_by_event_id: Dict[str, list[OmenSignal]] = {}
    _signals_list: list[OmenSignal] = []
```

**Characteristics:**
- Fast reads/writes
- No disk I/O
- ❌ All data lost on restart
- Suitable for: Development, testing

### 5.2 PostgresSignalRepository (Production)

**Location:** `src/omen/adapters/persistence/postgres_repository.py`

**Table Schema:**
```sql
CREATE TABLE IF NOT EXISTS omen_signals (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(64) UNIQUE NOT NULL,
    input_event_hash VARCHAR(64),
    source_event_id VARCHAR(128),
    generated_at TIMESTAMP WITH TIME ZONE,
    signal_type VARCHAR(32),
    probability FLOAT,
    confidence FLOAT,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_signals_hash ON omen_signals(input_event_hash);
CREATE INDEX idx_signals_event_id ON omen_signals(source_event_id);
CREATE INDEX idx_signals_generated_at ON omen_signals(generated_at);
```

**Characteristics:**
- ACID compliant
- UPSERT for idempotency
- JSONB for flexible payload
- ✅ Full persistence
- Connection pooling (asyncpg)

### 5.3 Ledger System (Audit Trail)

**Location:** `src/omen/infrastructure/ledger/`

**Structure:**
```
/data/ledger/ (or .demo/ledger/)
└── YYYY-MM-DD/
    ├── _CURRENT           # Marker for active segment
    ├── signals-001.wal    # WAL segment files
    └── signals-002.wal
```

**Frame Format:**
```
[u32 length][u32 crc32][payload bytes]
```

**Retention Policy:**
- Hot: 7 days (active, fast access)
- Warm: 30 days (compressed)
- Cold: 365 days (archived)

### 5.4 RiskCast SQLite Store

**Location:** `src/riskcast/infrastructure/signal_store.py`

**Database:** `/data/riskcast/signals.db` (configurable via `RISKCAST_DB_PATH`)

**Used for:** RiskCast reconciliation, separate from main OMEN signals

---

## 6. Data Retention Policies

### 6.1 Signal History (Probability Tracking)

**Location:** `src/omen/infrastructure/storage/signal_history.py`

| Setting | Value |
|---------|-------|
| TTL | 168 hours (7 days) |
| Max points per signal | 1000 |
| Storage | In-memory only |
| Persistence | ❌ None |

### 6.2 Documented Retention (docs/security/data-retention.md)

| Data Type | Retention Period |
|-----------|-----------------|
| Signal Data (hot) | 90 days |
| Signal Data (archive) | 1 year |
| Partner Signals | 30 days |
| Market Data | 1 year |
| Ledger Records | 7 years |
| API Access Logs | 90 days |
| Audit Trail | 7 years |
| Database Backups | 30 days |

---

## 7. Recommendations

### 7.1 For Development/Demo

Current setup is fine for demo purposes:
- Fast startup
- No database dependencies
- Data reset on each restart (can be useful for demos)

### 7.2 For Production Deployment

**Must Do:**
1. ✅ Set `OMEN_ENV=production`
2. ✅ Configure `DATABASE_URL` for PostgreSQL
3. ✅ Set up database backups
4. ✅ Configure proper retention policies

**Should Do:**
1. Add PostgreSQL service to `docker-compose.yml`
2. Enable Redis for distributed rate limiting
3. Set up monitoring for database health

### 7.3 Suggested docker-compose.yml Addition

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: omen
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-omen_secure_password}
      POSTGRES_DB: omen
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U omen"]
      interval: 10s
      timeout: 5s
      retries: 5

  omen-api:
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - OMEN_ENV=production
      - DATABASE_URL=postgresql://omen:${POSTGRES_PASSWORD:-omen_secure_password}@postgres:5432/omen

volumes:
  postgres_data:
```

---

## 8. Summary

| Question | Answer |
|----------|--------|
| **Hiện tại có lưu data không?** | ❌ KHÔNG - Data trong RAM, mất khi restart |
| **Code có support lưu data không?** | ✅ CÓ - PostgreSQL repository đã implement |
| **Cần làm gì để lưu data?** | Set `OMEN_ENV=production` + `DATABASE_URL` |
| **Ledger có lưu không?** | ✅ CÓ - Nhưng chỉ là audit trail, không query được |
| **RiskCast có lưu không?** | ✅ CÓ - SQLite riêng biệt |

---

## Appendix: Key File Locations

| Component | Path |
|-----------|------|
| Environment Config | `.env` |
| Container/DI | `src/omen/application/container.py` |
| In-Memory Repo | `src/omen/adapters/persistence/in_memory_repository.py` |
| PostgreSQL Repo | `src/omen/adapters/persistence/postgres_repository.py` |
| Ledger Writer | `src/omen/infrastructure/ledger/writer.py` |
| Signal History | `src/omen/infrastructure/storage/signal_history.py` |
| RiskCast SQLite | `src/riskcast/infrastructure/signal_store.py` |
| Migrations | `src/omen/infrastructure/database/migrations.py` |
| Data Retention Policy | `docs/security/data-retention.md` |

---

*Report generated by OMEN System Analysis Tool*
