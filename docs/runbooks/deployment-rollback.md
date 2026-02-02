# Runbook: Deployment Rollback

## When to Rollback

- Elevated error rate (>1%).
- P99 latency spike (>2x baseline).
- Failed smoke tests.
- Critical bug discovered post-deploy.

## Rollback Procedures

### Kubernetes Deployment

```bash
# 1. Check deployment history
kubectl rollout history deployment/omen-api -n omen

# 2. Rollback to previous version
kubectl rollout undo deployment/omen-api -n omen

# 3. Monitor rollback
kubectl rollout status deployment/omen-api -n omen

# 4. Verify health
curl https://omen.internal/health/
```

### Blue-Green Deployment (ECS + ALB)

```bash
# 1. Switch traffic back to blue
aws elbv2 modify-listener \
  --listener-arn $LISTENER_ARN \
  --default-actions Type=forward,TargetGroupArn=$BLUE_TG_ARN

# 2. Scale blue back up (if scaled down)
aws ecs update-service \
  --cluster omen-production \
  --service omen-api-blue \
  --desired-count 2

# 3. Scale green down
aws ecs update-service \
  --cluster omen-production \
  --service omen-api-green \
  --desired-count 0
```

### Docker Compose (Staging)

```bash
# 1. Stop current version
docker-compose down

# 2. Pull previous image
docker pull omen:previous-tag

# 3. Update docker-compose.yml
# Change image tag to previous version

# 4. Start
docker-compose up -d
```

## Verification

### Health Checks

```bash
# Application health
curl https://omen.internal/health/

# Metrics endpoint
curl https://omen.internal/metrics

# Smoke tests
./scripts/smoke-tests.sh https://omen.internal
```

### Monitoring

- Check error rate in Grafana.
- Verify latency back to normal.
- Check circuit breaker states.
- Review logs for errors.

## Communication

```
Subject: [INCIDENT] OMEN Deployment Rollback - [DATE]

Impact: Production deployment rolled back due to [REASON]
Status: RESOLVED
Duration: [TIME]

Timeline:
- [TIME] Deployment initiated
- [TIME] Issue detected: [DESCRIPTION]
- [TIME] Rollback initiated
- [TIME] Rollback complete
- [TIME] Service verified healthy

Action Items:
- [ ] Root cause analysis
- [ ] Fix and test locally
- [ ] Create new release
- [ ] Post-mortem meeting

Contact: #omen-incidents
```

## Post-Rollback

- [ ] Identify root cause.
- [ ] Create bug ticket.
- [ ] Update tests to catch issue.
- [ ] Schedule post-mortem.
- [ ] Document lessons learned.
