# OMEN Deployment Guide

## Prerequisites

- Python 3.12+ (backend)
- Node.js 20+ (frontend demo only)
- Docker & Docker Compose (optional)
- AWS CLI and credentials (for ECS/Terraform)

## Local Development

See [Development Guide](development.md) and [Onboarding](onboarding.md).

## Docker

### Build and run API only

```bash
docker build -t omen:latest .
docker run -p 8000:8000 \
  -e OMEN_SECURITY_API_KEYS='["your-key"]' \
  -e OMEN_LEDGER_BASE_PATH=/data/ledger \
  -v omen-ledger:/data/ledger \
  omen:latest
```

### Docker Compose

```bash
# Development
docker-compose up -d

# Production-style
docker-compose -f docker-compose.prod.yml up -d
```

Configure `.env` from `.env.example` (API keys, ledger path, etc.).

## Production (AWS ECS + Terraform)

### Infrastructure as Code

1. **Terraform:** Provision VPC, ECS cluster, ALB, EFS, ECR, security groups, CloudWatch.

   ```bash
   cd terraform
   terraform init
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

2. **Variables:** Set `aws_region`, `environment`, `acm_certificate_arn` (for HTTPS), `api_keys_secret_name`, and optionally `ecr_repository_url`. See [terraform/README.md](../terraform/README.md).

3. **Secrets:** Store API keys in AWS Secrets Manager at the secret name set in `api_keys_secret_name`. Value must be a JSON array of strings, e.g. `["key1","key2"]`.

### CI/CD

- **Staging:** Push to `develop` triggers `.github/workflows/cd-staging.yml` (build, push to ECR, update ECS service, smoke tests).
- **Production:** Publish a release triggers `.github/workflows/cd-production.yml` (build, push, blue-green deploy, smoke tests, rollback on failure).

Required secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`. Optional: `ECR_REPOSITORY`, `ECS_CLUSTER_*`, `ECS_SERVICE_*`, `STAGING_URL`, `PRODUCTION_URL`.

### Blue-Green Deployment

1. Deploy new image to **green** ECS service.
2. Wait for green to be stable; run smoke tests against green.
3. Switch ALB listener default action to **green** target group.
4. Scale **blue** to 0; keep green at desired count.
5. **Rollback:** Switch listener back to blue, scale blue up, scale green to 0. See [Runbook: Deployment Rollback](runbooks/deployment-rollback.md).

## Frontend Demo (omen-demo)

The demo UI is a separate Vite/React app in `omen-demo/`.

- **Build:** `cd omen-demo && npm ci && npm run build`
- **Preview:** `npm run preview` (serves `dist/` on a local port)
- **Deploy:** Serve `dist/` with any static host or CDN; set API base URL via env.

## Health Checks

- **Liveness:** `GET /health/live` — use for Kubernetes liveness probe.
- **Readiness:** `GET /health/ready` — use for readiness probe (checks ledger, downstream).
- **Smoke script:** `./scripts/smoke-tests.sh https://your-omen-url`

## Monitoring

- **Metrics:** Prometheus scrape `GET /metrics`.
- **Logs:** JSON to stdout; in ECS, use CloudWatch Logs (log group from Terraform output).
- **Alarms:** Terraform creates CloudWatch alarms for CPU and memory; SNS topic for alerts.

## Security Checklist

- [ ] API keys in Secrets Manager (or env in dev only).
- [ ] HTTPS only in production (ACM + ALB listener).
- [ ] Security headers enabled (middleware in `main.py`).
- [ ] Rate limiting enabled (`OMEN_SECURITY_RATE_LIMIT_*`).
- [ ] VPC and security groups restrict access.

---

See also: [terraform/README.md](../terraform/README.md), [Runbooks](runbooks/README.md).
