# OMEN Enterprise Audit — Proof Log

## Batch B08 — Invalid payload returns 400

Command:
```bash
python -m pytest -q tests/integration/test_api_contract.py --tb=short
```

Output:
```text
.
1 passed in X.XXs
```

Evidence file: `tests/integration/test_api_contract.py::test_invalid_payload_returns_400`
