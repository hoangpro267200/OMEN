# Runbook: High Memory Usage

## Symptoms

- CloudWatch / Prometheus: Memory utilization > 80% for OMEN API or pipeline.
- Alerts: `omen_memory_high` or equivalent.
- OOMKilled (Kubernetes) or task stopped (ECS).

## Impact

- Increased latency; possible OOM and restarts.
- Risk of data loss only if in-memory state is not persisted (OMEN uses repository/ledger for durability).

## Diagnosis

1. Check metrics: Memory by task/pod over last 15–30 minutes.
2. Check logs: Large batches, big payloads, or memory leaks (e.g. unbounded caches).
3. Check pipeline stats: High `limit` on process or large result sets held in memory.

## Mitigation

1. **Scale out:** Add replicas to reduce memory per instance.
2. **Reduce batch size:** Lower `limit` for `POST /api/v1/signals/process` and similar.
3. **Restart:** Restart the service to free memory (short-term); verify health after.
4. **Increase memory:** Raise task/pod memory limit in ECS task definition or Kubernetes manifest if consistently high.

## Resolution

- Verify memory drops and no OOM after changes.
- Tune alarms and resource limits.

## Post-Incident

- [ ] Review batch sizes and in-memory caches.
- [ ] Consider streaming or pagination for large responses.
- [ ] Update runbook if new findings.
