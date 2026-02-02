# Fallback Screenshots

If live demo fails (network issues, bugs), use these static screenshots.

## Files

- **overview.png** — Overview dashboard
- **ingest-before.png** — Ingest demo initial state
- **ingest-after.png** — Ingest demo with 1×200, 5×409
- **partition-before.png** — Partition with 10 vs 8
- **partition-after.png** — Partition after reconcile 10 vs 10
- **ledger-proof.png** — WAL frame structure
- **crash-demo.png** — Crash-tail simulator result

## Usage

1. Capture screenshots from a successful run: Overview, Ingest Demo (before/after), Partition Detail (before/after), Ledger Proof, crash simulator.
2. Save as the filenames above in this folder.
3. During presentation, if live demo fails: open images in presentation software and walk through the same script as the live demo.
4. Emphasize: "This is what you would see live."

## Quick capture (optional)

Run the app, reset demo (`make demo-reset`), then:

1. Go to Overview → screenshot as `overview.png`
2. Go to Ingest Demo → screenshot as `ingest-before.png` → Send 1 → Send 5 → screenshot as `ingest-after.png`
3. Go to Partition Detail → screenshot as `partition-before.png` → Run Reconcile → screenshot as `partition-after.png`
4. Go to Ledger Proof → screenshot as `ledger-proof.png` → Simulate Crash → Run Read → screenshot as `crash-demo.png`
