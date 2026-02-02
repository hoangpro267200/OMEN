# Pre-Demo Checklist

## 30 Minutes Before

- [ ] Run `make demo-reset` to reset all data
- [ ] Verify services are running: `curl localhost:8000/health`
- [ ] Open browser to http://localhost:5174
- [ ] Clear browser cache and cookies
- [ ] Test each screen loads correctly
- [ ] Test ingest demo works (send 1, send 5)
- [ ] Test reconcile works (run reconcile)
- [ ] Close all other browser tabs
- [ ] Disable notifications (Do Not Disturb)
- [ ] Check screen resolution (1920x1080 recommended)

## 5 Minutes Before

- [ ] Navigate to Overview screen
- [ ] Enable Demo Mode toggle
- [ ] Verify Scene Stepper appears
- [ ] Take a deep breath
- [ ] Remember: "Ledger first. Nothing lost."

## If Something Breaks

1. Don't panic
2. Acknowledge: "Let me show you this another way"
3. Use fallback screenshots from `/public/fallback/`
4. Continue with the script
5. Offer to show live demo after presentation

## Emergency Reset

```bash
# If demo is in bad state
docker compose restart
sleep 10
make demo-reset
```

Or without Docker:

```bash
python -m scripts.demo_reset
```

(Set `OMEN_LEDGER_BASE_PATH` and `RISKCAST_DB_PATH` to your local paths if not using `/data/...`.)
