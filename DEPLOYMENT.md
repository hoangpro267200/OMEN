# OMEN Production Deployment Guide

## Overview

This guide covers deploying OMEN Signal Intelligence Engine to production.

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- PostgreSQL 15+ (or use provided container)
- Redis 7+ (or use provided container)
- At least one data source API key (Polymarket recommended)

## Quick Start

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/omen.git
cd omen

# Create production environment file
cp .env.production.example .env.production

# Edit configuration
vim .env.production
```

### 2. Generate Secrets

```bash
# Generate secure API key
openssl rand -hex 32

# Generate database password
openssl rand -base64 24

# Generate Redis password
openssl rand -base64 24

# Generate JWT secret (if using JWT auth)
openssl rand -hex 32
```

### 3. Set Required Variables

Edit `.env.production` with your values:

```bash
# Required
OMEN_SECURITY_API_KEYS=<your-32-char-api-key>
DB_PASSWORD=<generated-db-password>
REDIS_PASSWORD=<generated-redis-password>
POLYMARKET_API_KEY=<your-polymarket-key>

# Optional but recommended
SENTRY_DSN=<your-sentry-dsn>
GRAFANA_PASSWORD=<grafana-admin-password>
```

### 4. Start Services

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f omen
```

### 5. Verify Deployment

```bash
# Run verification script
chmod +x scripts/verify-deployment.sh
./scripts/verify-deployment.sh http://localhost:8000

# Or manually check
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

## Configuration Reference

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `OMEN_SECURITY_API_KEYS` | Comma-separated API keys (min 32 chars each) |
| `DB_PASSWORD` | PostgreSQL password |
| `REDIS_PASSWORD` | Redis password |
| `POLYMARKET_API_KEY` | Polymarket API key |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OMEN_ENV` | `development` | Environment (development/production) |
| `OMEN_LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `OMEN_LOG_FORMAT` | `json` | Log format (json/pretty) |
| `AIS_API_KEY` | - | AIS data provider API key |
| `NEWS_API_KEY` | - | News API key |
| `SENTRY_DSN` | - | Sentry error tracking |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   OMEN API  │  │   OMEN API  │  │   OMEN API  │  (replicas) │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │               │               │                       │
│         └───────────────┼───────────────┘                       │
│                         ▼                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  PostgreSQL │  │    Redis    │  │   RiskCast  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │  Prometheus │  │   Grafana   │  (monitoring)                │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Load balancer check | `{"status": "healthy"}` |
| `/health/ready` | Kubernetes readiness | `{"ready": true, ...}` |
| `/health/live` | Kubernetes liveness | `{"status": "alive"}` |
| `/health/sources` | Data source health | Full source status |

## Scaling

### Horizontal Scaling

```bash
# Scale OMEN API to 3 replicas
docker-compose -f docker-compose.prod.yml up -d --scale omen=3
```

### Vertical Scaling

Edit resource limits in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

## Monitoring

### Prometheus

Access at: http://localhost:9090

OMEN exposes metrics at `/metrics`:
- `omen_signals_processed_total` - Total signals processed
- `omen_signal_processing_seconds` - Processing latency
- `omen_validation_rules_executed_total` - Rules executed
- `omen_source_health_status` - Data source health

### Grafana

Access at: http://localhost:3001
Default credentials: `admin` / `${GRAFANA_PASSWORD}`

Pre-configured dashboard: `OMEN Overview`

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs omen

# Common issues:
# - Missing environment variables (check .env.production)
# - Database not ready (wait for health check)
# - Invalid API key format (must be 32+ chars)
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.prod.yml exec db psql -U omen -c "SELECT 1"

# Check connection from OMEN
docker-compose -f docker-compose.prod.yml exec omen curl -sf localhost:8000/health/ready
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping
```

### Health Check Failures

```bash
# Check all dependencies
curl http://localhost:8000/health/ready | jq .

# Check specific components
curl http://localhost:8000/health/sources | jq .
```

## Security Checklist

Before going live:

- [ ] Generate strong API keys (32+ chars)
- [ ] Set strong database password
- [ ] Set strong Redis password
- [ ] Configure CORS for your domain only
- [ ] Enable rate limiting
- [ ] Disable debug endpoints (`OMEN_DEBUG_ENDPOINTS=false`)
- [ ] Configure HTTPS/TLS (load balancer or reverse proxy)
- [ ] Set up log aggregation
- [ ] Configure Sentry for error tracking
- [ ] Review firewall rules

## Backup & Recovery

### Database Backup

```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U omen omen > backup.sql

# Restore backup
docker-compose -f docker-compose.prod.yml exec -T db psql -U omen omen < backup.sql
```

### Ledger Backup

The ledger is stored in the `ledger_data` Docker volume:

```bash
# Backup ledger
docker run --rm -v omen_ledger_data:/data -v $(pwd):/backup alpine tar czf /backup/ledger-backup.tar.gz /data

# Restore ledger
docker run --rm -v omen_ledger_data:/data -v $(pwd):/backup alpine tar xzf /backup/ledger-backup.tar.gz -C /
```

## Support

- Documentation: `/docs/`
- API Reference: `/docs/API_REFERENCE.md`
- Architecture: `/docs/architecture.md`
