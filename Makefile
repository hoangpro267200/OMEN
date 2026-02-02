# ═══════════════════════════════════════════════════════════════════════════════
# OMEN Makefile
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help build up down logs test lint clean build-prod up-prod down-prod demo-reset demo-seed

# Default target
help:
	@echo "OMEN Commands:"
	@echo "  make build      - Build Docker images (dev)"
	@echo "  make build-prod - Build Docker images (prod)"
	@echo "  make up         - Start all services (dev)"
	@echo "  make up-prod    - Start all services (prod)"
	@echo "  make down       - Stop all services"
	@echo "  make down-prod  - Stop all services (prod)"
	@echo "  make demo-reset - Reset demo state (ledger + RiskCast, seed 10 signals, 8 processed)"
	@echo "  make demo-seed  - Seed demo data only (no clear)"
	@echo "  make logs       - View logs"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make clean      - Clean up"

# Build
build:
	docker compose build

build-prod:
	docker compose -f docker-compose.prod.yml build

# Start/Stop
up:
	docker compose up -d

up-prod:
	docker compose -f docker-compose.prod.yml up -d

down:
	docker compose down

down-prod:
	docker compose -f docker-compose.prod.yml down

# Demo (run from repo root; set OMEN_LEDGER_BASE_PATH, RISKCAST_DB_PATH, RISKCAST_INGEST_URL if needed)
demo-reset:
	PYTHONPATH=src python -m scripts.demo_reset

demo-seed:
	PYTHONPATH=src python -m scripts.seed_demo_data

# Logs
logs:
	docker compose logs -f

logs-omen:
	docker compose logs -f omen

logs-riskcast:
	docker compose logs -f riskcast

# Testing
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=src --cov-report=html

# Linting
lint:
	ruff check src/ tests/
	mypy src/

# Cleanup
clean:
	docker compose down -v 2>/dev/null || true
	docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov 2>/dev/null || true
