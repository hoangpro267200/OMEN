# OMEN Demo Presentation Scripts

## 30-Second Elevator Pitch

> "OMEN is a logistics signal intelligence system that ensures no market signal is ever lost.
>
> We use a dual-path architecture: every signal is written to an immutable ledger FIRST,
> then pushed to downstream systems. If the downstream fails, our reconcile engine
> automatically replays missing signals.
>
> The result? Exactly-once delivery semantics with zero data loss.
>
> Let me show you how it works."

---

## 2-Minute Demo Script

### Scene 1: Overview (20s)
"This is OMEN's control center. You can see we've processed 247 signals today with
a 99.2% hot path success rate. The system is healthy."

*Point to KPI cards*

"Notice the three proof cards below - these aren't just claims, they're verifiable
guarantees we can demonstrate."

### Scene 2: The Core Innovation (30s)
*Point to pipeline diagram*

"Here's our dual-path architecture. Every signal flows through the ledger FIRST -
this is our source of truth. Then it goes to the hot path for real-time processing.

If the hot path fails - and it will fail in production - our reconcile engine
catches up from the ledger. Nothing is lost."

### Scene 3: Live Demo - Idempotency (30s)
*Navigate to Ingest Demo*

"Let me prove exactly-once semantics. I'll send the same signal 6 times."

*Click Send 1, then Send 5 Duplicates*

"First request: 200 OK, we get an ack_id.
Next 5 requests: all 409 Conflict, but notice - SAME ack_id every time.
The database has exactly ONE row. Deduplication works."

### Scene 4: Live Demo - Reconcile (30s)
*Navigate to Partition Detail*

"Now the reconcile demo. This partition has 10 signals in the ledger,
but only 8 made it to processing. 2 are missing."

*Click Run Reconcile*

"Watch the bars... and now we have 10 for 10. Zero loss.
The missing signals were OMEN-DEMO005 and OMEN-DEMO009.
Both are now in the system with their ack_ids."

### Scene 5: Closing (10s)
"That's OMEN: ledger-first, reconcile-always, nothing lost.
Questions?"

---

## 5-Minute Technical Deep Dive

### Additional Scenes for Technical Audience

**Ledger Proof (60s)**
*Navigate to Ledger Proof*

"Let me show you the WAL framing. Each record is: 4 bytes length, 4 bytes CRC32,
then the JSON payload.

This crash-tail simulator shows what happens if we lose power mid-write.
*Click Simulate Crash*
The reader truncates the partial frame - we get 2 valid records, not 3.
No corruption ever surfaces."

**Concurrent Dedupe (30s)**
"The 409 behavior isn't just for sequential requests. We tested 20 concurrent
requests with the same signal_id. Result: 1 wins with 200, 19 get 409,
all return the SAME ack_id. One row in the database."

---

## Q&A Preparation

### "What if the ledger disk is full?"
"The emit fails with FAILED status before any hot path attempt. The ledger-first
invariant is preserved. We alert and the signal can be retried after disk space
is freed."

### "What about ordering?"
"Order is preserved within a partition (per emitted_at date). Cross-partition
ordering is not guaranteed, which matches the eventual consistency model of
distributed systems."

### "How does this scale?"
"The ledger is append-only with segment rollover at 10MB. Each partition is
independent. We can shard by partition date. The SQLite at RiskCast handles
concurrent ingest via busy_timeout and WAL mode."

### "Why not use Kafka?"
"We could, but for this scale, the file-based ledger is simpler to deploy,
debug, and reason about. The same dual-path pattern works with Kafka as the ledger."

### "What's the latency?"
"Emit is typically under 100ms including ledger fsync. The fsync is the cost of
durability - we don't sacrifice correctness for speed."

---

## Final Notes

Remember the three things judges should remember:

1. **"Ledger first, hot path second"**
2. **"Exactly-once semantics: 1×200, N×409, same ack_id"**
3. **"Reconcile recovers everything: 10 vs 8 → 10 vs 10"**

If they remember these three things, you've won.
