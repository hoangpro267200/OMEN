# Runbook: High CPU Usage

## Symptoms

- CloudWatch / Prometheus: CPU utilization > 80% for OMEN API or pipeline.
- Alerts: `omen_cpu_high` or equivalent.

## Impact

- Increased latency; possible timeouts.
- Risk of OOM or instance instability if sustained.

## Diagnosis

1. Check metrics: CPU by task/pod over last 15–30 minutes.
2. Check logs: High request volume, long-running pipeline batches, or tight loops.
3. Check `/api/v1/signals/stats` and `/api/v1/metrics/circuit-breakers` for load and errors.

## Mitigation

1. **Scale out:** Increase ECS desired count or Kubernetes replicas to spread load.
2. **Throttle:** If traffic is bursty, ensure rate limiting is enabled (`OMEN_SECURITY_RATE_LIMIT_*`).
3. **Pipeline:** Reduce batch size or frequency of `POST /api/v1/signals/process` if it is the main consumer.
4. **Restart:** As a short-term measure, restart the service to clear any stuck work (use with caution).

## Resolution

- Verify CPU drops after scaling or throttling.
- Set or tune alarms (e.g. threshold, evaluation periods).

## Post-Incident

- [ ] Review scaling and resource limits.
- [ ] Consider horizontal scaling or larger instance size.
- [ ] Update runbook if new findings.
