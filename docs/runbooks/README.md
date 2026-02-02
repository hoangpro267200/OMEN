# OMEN Runbooks

## Runbook Index

| Runbook | Description |
|---------|-------------|
| [High CPU Usage](high-cpu.md) | High CPU on API or pipeline |
| [High Memory Usage](high-memory.md) | High memory on API or pipeline |
| [Ledger Write Failures](ledger-write-failure.md) | Ledger WAL write errors |
| [RiskCast Unavailable](riskcast-down.md) | RiskCast / downstream unavailable |
| [Reconciliation Failures](reconcile-failure.md) | Reconciliation job failures |
| [Partition Sealing Issues](partition-seal.md) | Ledger partition sealing problems |
| [Deployment Rollback](deployment-rollback.md) | Rollback a bad deployment |

## Incident Response Process

1. **Detect:** Monitoring alerts (CloudWatch, Prometheus, PagerDuty).
2. **Assess:** Check runbook for symptoms and impact.
3. **Mitigate:** Follow runbook steps (restart, scale, switch traffic).
4. **Resolve:** Fix root cause; verify health.
5. **Document:** Post-mortem; update runbook if needed.

## Emergency Contacts

- On-call: PagerDuty rotation (configure in your org).
- Slack: `#omen-incidents`
- Email: incidents@omen.example.com

## Quick Links

- [Architecture](../architecture.md)
- [API Reference](../api.md)
- [Deployment Guide](../deployment.md)
