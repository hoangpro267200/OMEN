# Runbook: Ledger Write Failures

## Symptoms

- Logs: "Failed to write to ledger", "Ledger write error", or similar.
- API returns 500 for operations that write to the ledger.
- Alerts: Ledger write latency or error rate high.

## Impact

- Signals may not be persisted to the ledger.
- Risk of data loss if writes fail consistently.

## Diagnosis

1. Check disk space and I/O on the node/volume used for ledger (e.g. EFS, host path).
2. Check permissions: process must have write access to `OMEN_LEDGER_BASE_PATH`.
3. Check logs: exact error message (e.g. "disk full", "permission denied", "file locked").
4. Check NFS/EFS: if using EFS, verify mount targets and connectivity.

## Mitigation

1. **Disk full:** Free space or expand volume; restart writer after space is available.
2. **Permissions:** Fix ownership/permissions on ledger directory; restart API.
3. **EFS:** Verify EFS mount targets and security groups; restart tasks if mount was lost.
4. **Lock/file conflict:** Ensure only one writer per partition; restart if a stale lock is suspected.

## Resolution

- Verify writes succeed (check logs and ledger directory for new segments).
- Re-run any failed operations or replay from source if applicable.

## Post-Incident

- [ ] Set up disk/volume monitoring and alerts.
- [ ] Document ledger path and backup strategy.
- [ ] Update runbook if new findings.
