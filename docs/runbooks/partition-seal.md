# Runbook: Partition Sealing Issues

## Symptoms

- Partition expected to be sealed remains OPEN.
- Logs: "Seal failed", "Partition seal timeout", or similar.
- Late-arriving data or lifecycle job errors.

## Impact

- Partition may accept writes longer than intended or stay in inconsistent state.
- Downstream reconciliation or archival may assume sealed partitions.

## Diagnosis

1. Check lifecycle job / seal job logs: which partition, error message.
2. Check ledger directory: presence of `_SEALED` or seal marker for the partition.
3. Check disk and I/O: seal may involve finalizing files or moving data.
4. Check time: seal often runs on a schedule (e.g. after 24h); verify job ran for the partition date.

## Mitigation

1. **Manual seal:** If supported, trigger seal via API or admin script for the partition.
2. **Fix permissions or disk:** Resolve any "permission denied" or "disk full" errors; re-run seal.
3. **Stuck writer:** Ensure no process holds the partition open for write; restart writer if needed, then re-run seal.
4. **Late arrivals:** If partition was intentionally left open for late data, seal after cutoff; update schedule if needed.

## Resolution

- Verify partition shows as SEALED (API or ledger metadata).
- Verify downstream and reconciliation see partition as sealed where applicable.

## Post-Incident

- [ ] Review seal schedule and cutoff times.
- [ ] Set alerts for partitions not sealed within expected window.
- [ ] Update runbook if new findings.
