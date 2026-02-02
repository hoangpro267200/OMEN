# OMEN Data Retention Policy

## Overview

This document defines OMEN's data retention and disposal policies in compliance with
SOC 2, GDPR, and industry best practices.

---

## Retention Periods

### Operational Data

| Data Type | Retention Period | Disposal Method | Justification |
|-----------|------------------|-----------------|---------------|
| **Signal Data** | 90 days (hot), 1 year (archive) | Automated deletion | Operational relevance |
| **Partner Signals** | 30 days | Automated deletion | Real-time relevance |
| **Market Data** | 1 year | Automated archive | Historical analysis |
| **Ledger Records** | 7 years | Secure archive | Audit compliance |

### Security & Audit Data

| Data Type | Retention Period | Disposal Method | Justification |
|-----------|------------------|-----------------|---------------|
| **API Access Logs** | 90 days | Log rotation | Security monitoring |
| **Authentication Events** | 1 year | Secure archive | Incident response |
| **Audit Trail** | 7 years | Immutable storage | Compliance |
| **Error Logs** | 30 days | Log rotation | Debugging |

### Backup Data

| Data Type | Retention Period | Disposal Method | Justification |
|-----------|------------------|-----------------|---------------|
| **Database Backups** | 30 days | Automated deletion | Recovery point |
| **Ledger Backups** | 30 days | Automated deletion | Recovery point |
| **Configuration Backups** | 90 days | Automated deletion | Change recovery |

---

## Automated Disposal

### Backup Cleanup

```python
# scripts/backup.py
def cleanup_old_backups():
    """Remove backups older than retention period."""
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    # Automated deletion of files older than cutoff
```

### Log Rotation

```yaml
# Kubernetes ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: omen-logrotate
data:
  omen:
    rotate 7
    daily
    compress
    missingok
    notifempty
```

---

## Data Classification

### Classification Levels

| Level | Description | Examples | Handling |
|-------|-------------|----------|----------|
| **Public** | Non-sensitive | API documentation | No restrictions |
| **Internal** | Business data | Signal metrics | Access control |
| **Confidential** | Sensitive | API keys, credentials | Encryption required |
| **Restricted** | Highly sensitive | PII (if any) | Strict access, encryption |

### Signal Data Classification

OMEN signal data is classified as **Internal**:
- Contains market data from public sources
- No PII by design
- Access controlled via API keys

---

## Right to Deletion

### API Key Data

Customers can request deletion of:
- API keys and associated metadata
- Access logs tied to their keys
- Any configuration data

### Process

1. Submit deletion request to compliance@omen.io
2. Verification of identity (48 hours)
3. Data deletion (within 30 days)
4. Confirmation email sent

---

## Compliance

### SOC 2

- C1.2: Data disposed after retention period
- A1.3: Backups maintained per schedule

### GDPR (if applicable)

- Article 17: Right to erasure supported
- Article 5(1)(e): Storage limitation principle

---

*Last Updated: 2026-02-01*
*Document Owner: OMEN Compliance Team*
