# OMEN Disaster Recovery Runbook

## Overview

This document describes disaster recovery procedures for the OMEN Signal Intelligence platform.

## RTO/RPO Targets

| Metric | Target | Description |
|--------|--------|-------------|
| **RTO** | 4 hours | Recovery Time Objective - Maximum time to restore service |
| **RPO** | 1 hour | Recovery Point Objective - Maximum acceptable data loss |

## Backup Schedule

| Component | Schedule | Retention | Location |
|-----------|----------|-----------|----------|
| PostgreSQL | Every 6 hours | 30 days | `/backups/postgres_*.sql.gz` |
| SQLite DBs | Every 6 hours | 30 days | `/backups/sqlite_*.db.gz` |
| Ledger | Every 6 hours | 30 days | `/backups/ledger_*.tar.gz` |
| Config | On change | 90 days | Git repository |

## Backup Verification

Backups are automatically verified after creation:
- File exists and non-empty
- Gzip integrity check
- Sample data read test

To manually verify a backup:

```bash
# Verify PostgreSQL backup
gunzip -t /backups/postgres_20260201_120000.sql.gz

# Verify SQLite backup
gunzip -t /backups/sqlite_signals_20260201_120000.db.gz

# Verify ledger backup
tar -tzf /backups/ledger_20260201_120000.tar.gz | head
```

---

## Recovery Procedures

### Scenario 1: Complete System Failure

**Symptoms**: All services down, infrastructure destroyed

**Recovery Steps**:

```bash
# 1. Deploy fresh infrastructure
cd terraform/
terraform init
terraform apply

# 2. Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=omen --timeout=300s

# 3. Identify latest backup
ls -la /backups/ | head -20

# 4. Restore PostgreSQL
export LATEST_PG=$(ls -t /backups/postgres_*.sql.gz | head -1)
gunzip -c $LATEST_PG | psql $DATABASE_URL

# 5. Restore SQLite databases
export LATEST_SQLITE=$(ls -t /backups/sqlite_*.db.gz | head -1)
gunzip -c $LATEST_SQLITE > /data/signals.db

# 6. Restore Ledger
export LATEST_LEDGER=$(ls -t /backups/ledger_*.tar.gz | head -1)
tar -xzf $LATEST_LEDGER -C /data/

# 7. Verify data integrity
python scripts/verify_backup.py --all

# 8. Restart services
kubectl rollout restart deployment/omen
kubectl rollout restart deployment/riskcast

# 9. Verify health
curl http://localhost:8000/health/ready
```

**Estimated Time**: 2-4 hours

---

### Scenario 2: Database Corruption

**Symptoms**: API errors, inconsistent data, database connection failures

**Recovery Steps**:

```bash
# 1. Stop application to prevent further writes
kubectl scale deployment/omen --replicas=0

# 2. Backup corrupted database (for analysis)
pg_dump $DATABASE_URL > /backups/corrupted_$(date +%Y%m%d_%H%M%S).sql

# 3. Drop and recreate database
psql -c "DROP DATABASE omen_db;"
psql -c "CREATE DATABASE omen_db;"

# 4. Restore from latest backup
export LATEST_PG=$(ls -t /backups/postgres_*.sql.gz | head -1)
gunzip -c $LATEST_PG | psql $DATABASE_URL

# 5. Verify restoration
psql $DATABASE_URL -c "SELECT COUNT(*) FROM omen_signals;"

# 6. Restart application
kubectl scale deployment/omen --replicas=3

# 7. Monitor for errors
kubectl logs -f deployment/omen --tail=100
```

**Estimated Time**: 1-2 hours

---

### Scenario 3: Partial Data Loss (Ledger)

**Symptoms**: Missing signals, gaps in timeline, ledger read errors

**Recovery Steps**:

```bash
# 1. Identify affected time range
python scripts/ledger_audit.py --check-gaps

# 2. Stop ledger writes
kubectl exec -it deployment/omen -- kill -SIGUSR1 1

# 3. Backup current state
tar -czf /backups/ledger_corrupted_$(date +%Y%m%d).tar.gz /data/ledger/

# 4. Restore from backup
export LATEST_LEDGER=$(ls -t /backups/ledger_*.tar.gz | head -1)
rm -rf /data/ledger/*
tar -xzf $LATEST_LEDGER -C /data/

# 5. Replay missing events from Kafka (if available)
python scripts/replay_events.py --since "2026-01-31T00:00:00Z"

# 6. Resume ledger writes
kubectl exec -it deployment/omen -- kill -SIGUSR2 1

# 7. Verify integrity
python scripts/ledger_audit.py --verify
```

**Estimated Time**: 1-2 hours

---

### Scenario 4: API Key Compromise

**Symptoms**: Unauthorized access, suspicious activity, security alerts

**Immediate Actions**:

```bash
# 1. Identify compromised key
grep "INVALID_API_KEY\|401" /var/log/omen/security.log | tail -100

# 2. Revoke compromised key
python -c "
from omen.infrastructure.security.api_key_manager import get_api_key_manager
manager = get_api_key_manager()
manager.revoke_key('key_COMPROMISED_ID')
print('Key revoked')
"

# 3. Generate new key for legitimate user
python -c "
from omen.infrastructure.security.api_key_manager import get_api_key_manager
manager = get_api_key_manager()
key, record = manager.generate_key('replacement-key', scopes=['read:signals'])
print(f'New key: {key}')
"

# 4. Rotate all keys (if widespread compromise)
python scripts/rotate_all_keys.py

# 5. Review audit logs
grep -E "key_COMPROMISED_ID" /var/log/omen/audit.log > /tmp/compromised_activity.log

# 6. Notify affected users
python scripts/notify_key_rotation.py --key-id key_COMPROMISED_ID
```

**Estimated Time**: 30 minutes - 1 hour

---

### Scenario 5: Redis Failure (Rate Limiting Down)

**Symptoms**: Rate limiting not working, all requests passing through

**Recovery Steps**:

```bash
# 1. Check Redis status
redis-cli -u $REDIS_URL ping

# 2. If Redis down, fall back to in-memory rate limiting
kubectl set env deployment/omen OMEN_RATE_LIMIT_BACKEND=memory

# 3. Restart Redis
kubectl rollout restart statefulset/redis

# 4. Verify Redis recovery
redis-cli -u $REDIS_URL ping

# 5. Switch back to Redis rate limiting
kubectl set env deployment/omen OMEN_RATE_LIMIT_BACKEND=redis

# 6. Monitor rate limiting
curl -I http://localhost:8000/api/v1/signals/ | grep -i ratelimit
```

**Estimated Time**: 15-30 minutes

---

## Monitoring & Alerts

### Critical Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| Backup Failed | Any failure | Investigate immediately |
| Database Connection Lost | >30s | Check database, failover if needed |
| Disk Space Low | <10% free | Expand storage, cleanup old data |
| High Error Rate | >5% 5xx | Check logs, scale if needed |

### Health Check Endpoints

```bash
# Application health
curl http://localhost:8000/health/ready

# Database health
curl http://localhost:8000/health/db

# Redis health  
curl http://localhost:8000/health/redis
```

---

## Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | PagerDuty | Auto-escalates after 15 min |
| Database Admin | dba@omen.io | 24/7 support |
| Security Team | security@omen.io | Immediate for compromises |

---

## Post-Incident Review

After any incident:

1. **Document** - Create incident report within 24 hours
2. **Analyze** - Root cause analysis within 48 hours
3. **Action** - Implement fixes and update runbook
4. **Review** - Share learnings with team

---

## Testing Schedule

| Test | Frequency | Last Tested |
|------|-----------|-------------|
| Backup Restore | Monthly | TBD |
| Failover Test | Quarterly | TBD |
| Full DR Drill | Annually | TBD |

---

*Last Updated: 2026-02-01*
*Owner: OMEN Operations Team*
