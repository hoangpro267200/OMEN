# OMEN Development Guide

## Prerequisites

- Python 3.10+ (3.12 recommended)
- Node.js 20+ (for frontend demo only)
- Git

## Setup

### Backend

```bash
git clone <repo>
cd OMEN
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env if needed (OMEN_*, OMEN_SECURITY_*)
```

### Frontend (demo)

```bash
cd omen-demo
npm ci
npm run dev   # http://localhost:5174
```

## Running the API

```bash
uvicorn omen.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/health/
- API docs: http://localhost:8000/docs
- Protected routes need `X-API-Key` (set `OMEN_SECURITY_API_KEYS` in `.env`).

## Running the Pipeline (CLI)

```bash
python scripts/run_pipeline.py --source stub --limit 5
```

Live Polymarket processing: `POST /api/v1/live/process` (see [api.md](api.md)).

## Code Standards

- **Formatting:** Black (line length 100). `black src tests`
- **Linting:** Ruff. `ruff check src tests`
- **Types:** Mypy. `mypy src`
- **Tests:** Pytest. `pytest tests/`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full guidelines.

## Testing

```bash
# Unit and integration
pytest tests/ -v
pytest tests/ --cov=src/omen --cov-report=html

# Integration only
pytest tests/integration/ -v

# Frontend
cd omen-demo && npm run test
cd omen-demo && npm run test:coverage

# E2E (Playwright)
cd omen-demo && npx playwright install && npm run test:e2e
```

## Project Layout

| Path | Purpose |
|------|---------|
| `src/omen/` | Core API and pipeline (domain, application, adapters, infrastructure) |
| `src/omen_impact/` | Impact assessment (downstream, optional) |
| `src/riskcast/` | RiskCast / reconciliation (when used) |
| `omen-demo/` | Demo React UI |
| `tests/` | Backend tests (unit, integration, performance) |
| `terraform/` | AWS infrastructure (ECS, ALB, EFS) |
| `docs/` | Architecture, API, runbooks, ADRs |

## Key Config (env)

- `OMEN_SECURITY_API_KEYS` — Comma-separated or JSON array of API keys.
- `OMEN_LEDGER_BASE_PATH` — Ledger directory (default: `./.demo/ledger` or similar).
- `OMEN_RULESET_VERSION` — Ruleset version for reproducibility.
- `OMEN_MIN_LIQUIDITY_USD` — Min liquidity for validation (default 1000).

See `.env.example` and `src/omen/config.py`.

## Documentation

- [Architecture](architecture.md)
- [API](api.md)
- [Deployment](deployment.md)
- [Runbooks](runbooks/README.md)
- [ADRs](adr/README.md)
- [Onboarding](onboarding.md)
- [Contributing](../CONTRIBUTING.md)
