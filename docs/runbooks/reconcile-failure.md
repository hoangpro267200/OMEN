# Runbook: Reconciliation Failures

## Symptoms

- Reconciliation job fails (exit code non-zero or alert).
- Logs: "Reconciliation failed", "Replay error", or timeout.
- Completeness metric stays below 100% for a partition.

## Impact

- Ledger and downstream (e.g. RiskCast) may be out of sync.
- Missing signals in downstream until reconciliation succeeds.

## Diagnosis

1. Check reconciliation job logs: which partition, which step failed (read ledger, query downstream, replay).
2. Check downstream health: reconciliation often fails if downstream is unavailable or slow.
3. Check ledger: partition readable and not corrupted.
4. Check API: `POST /api/ui/partitions/{partition_date}/reconcile` (or equivalent) response and logs.

## Mitigation

1. **Downstream unavailable:** Fix downstream first (see [RiskCast Unavailable](riskcast-down.md)); then re-run reconciliation.
2. **Timeout:** Increase timeout for reconciliation job or run for smaller partitions.
3. **Replay errors:** Check replay endpoint and credentials; fix and re-run.
4. **Ledger read error:** Check ledger partition integrity and permissions; fix and re-run.

## Resolution

- Re-run reconciliation for affected partition(s).
- Verify completeness reaches 100% (overview API or dashboard).
- Monitor for recurrence.

## Post-Incident

- [ ] Tune reconciliation frequency and timeouts.
- [ ] Add alerts for completeness below threshold.
- [ ] Update runbook if new findings.
