# Runbook: RiskCast Unavailable

## Symptoms

- Circuit breaker **OPEN** for RiskCast / downstream.
- Alerts: `riskcast_ingest_requests_total{status_code="500"}` high.
- Logs: "Circuit 'riskcast_hot_path' is OPEN".

## Impact

- Signals written to Ledger only (LEDGER_ONLY status).
- No immediate data loss.
- Reconciliation will replay later when downstream is back.

## Diagnosis

### 1. Check downstream health

```bash
curl https://riskcast.internal/health
```

### 2. Check recent errors

```bash
kubectl logs -n omen deployment/riskcast --tail=100 | grep ERROR
```

Or for ECS:

```bash
aws logs tail /ecs/omen-api --since 1h --format short | grep ERROR
```

### 3. Check circuit breaker status

```bash
curl -H "X-API-Key: $API_KEY" https://omen.internal/api/v1/metrics/circuit-breakers
```

## Mitigation

### If downstream is down

```bash
# 1. Check pod / task status
kubectl get pods -n omen | grep riskcast
# or: aws ecs describe-services --cluster omen-production --services riskcast

# 2. Restart if unhealthy
kubectl rollout restart deployment/riskcast -n omen

# 3. Monitor recovery
kubectl rollout status deployment/riskcast -n omen
```

### If database corrupted (downstream)

```bash
# 1. Stop downstream
kubectl scale deployment/riskcast --replicas=0

# 2. Restore from backup (example)
aws s3 cp s3://omen-backups/riskcast/latest.db /data/signals.db

# 3. Restart
kubectl scale deployment/riskcast --replicas=2
```

## Resolution

### 1. Verify downstream healthy

```bash
curl https://riskcast.internal/health
# Expected: {"status": "healthy"}
```

### 2. Trigger reconciliation (if applicable)

```bash
curl -X POST https://omen.internal/api/ui/partitions/2026-01-30/reconcile \
  -H "X-API-Key: $API_KEY"
```

### 3. Monitor completeness

- Check Grafana dashboard or overview API.
- Verify completeness → 100% for affected partitions.

## Prevention

- [ ] Enable database backups for downstream.
- [ ] Set up database and downstream health monitoring.
- [ ] Configure auto-scaling and resource limits.
- [ ] Review circuit breaker thresholds.

## Post-Incident

- [ ] Update runbook with lessons learned.
- [ ] Review alert thresholds.
- [ ] Conduct post-mortem meeting.
