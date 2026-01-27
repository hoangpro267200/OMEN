# OMEN Onboarding Guide

Welcome to OMEN. This guide will get you productive on day one.

## Prerequisites

- Python 3.10+
- Git
- Basic understanding of prediction markets
- Familiarity with logistics or supply chain is helpful but not required

## Day 1: Setup and First Run

### 1. Clone and install (about 15 min)

```bash
git clone https://github.com/your-org/omen.git
cd omen
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

### 2. Run tests (about 5 min)

```bash
pytest -v
```

All tests should pass. If not, confirm your Python version is 3.10+.

### 3. Run the pipeline (about 10 min)

```bash
python scripts/run_pipeline.py --source stub --limit 5
```

You should see output along the lines of:

```
Processing event: test-red-sea-001
Generated OMEN signal: OMEN-... [HIGH] severity=0.75
```

### 4. Start the API (about 5 min)

```bash
uvicorn omen.main:app --reload
```

Visit http://localhost:8000/docs to explore the API.

### 5. Understand the data flow (about 30 min)

Read these files in order:

1. `src/omen/domain/models/raw_signal.py` — input format
2. `src/omen/domain/rules/validation/liquidity_rule.py` — validation example
3. `src/omen/domain/rules/translation/logistics/red_sea_disruption.py` — translation example
4. `src/omen/domain/models/omen_signal.py` — output format
5. `src/omen/application/pipeline.py` — orchestration

## Day 2: Deeper understanding

### Architecture

Read these ADRs:

- [ADR-001: Deterministic Processing](adr/001-deterministic-processing.md)
- [ADR-002: Hexagonal Architecture](adr/002-hexagonal-architecture.md)
- [ADR-003: Evidence-Based Parameters](adr/003-evidence-based-impact-parameters.md)

### Key concepts

| Concept | Definition |
|--------|------------|
| **RawSignalEvent** | Normalized prediction market event (Layer 1 output) |
| **ValidatedSignal** | Event that passed all validation rules (Layer 2 output) |
| **ImpactAssessment** | Quantified consequences with uncertainty (Layer 3 output) |
| **OmenSignal** | Final output for downstream systems (Layer 4) |
| **ProcessingContext** | Carries processing time and trace ID for determinism |

### Adding a new validation rule

1. Add a file under `domain/rules/validation/`, e.g. `my_rule.py`.
2. Implement the `Rule` protocol (or base used by existing rules).
3. Register the rule in `SignalValidator.create_default()` or in pipeline wiring.
4. Add tests under `tests/unit/domain/`.

### Adding a new translation rule

1. Add a file under `domain/rules/translation/logistics/` (or another domain), e.g. `my_rule.py`.
2. Extend the translation rule base and implement `translate()` returning a `TranslationResult`.
3. Add parameters to `parameters.py` with `EvidenceRecord` where applicable.
4. Register the rule in the `ImpactTranslator` used by the pipeline.
5. Add tests under `tests/unit/domain/`.

## Day 3: Contributing

### Code style

- Use type hints on public functions and in new code.
- Add docstrings for public modules, classes, and functions.
- Keep domain code free of I/O; use ports and adapters for I/O.
- Add tests for new behavior.

### PR checklist

- [ ] Tests pass: `pytest`
- [ ] Coverage is maintained: `pytest --cov`
- [ ] Types check: `mypy src/`
- [ ] Formatting: `black src/ tests/`
- [ ] Linting: `ruff check src/ tests/`
- [ ] Documentation: docstrings and, for design changes, an ADR if needed

## Getting help

- **Documentation:** This folder, [README](../README.md), [ADR index](adr/README.md), [API overview](api/README.md)
- **Issues:** GitHub Issues
- **Code:** `README.md` and `CONTRIBUTING.md` in the repo root

## Testing the system

| Goal | Command |
|------|---------|
| Run all tests | `pytest -v` |
| Tests with coverage | `pytest --cov=src/omen --cov-report=html` |
| Run pipeline (stub data) | `python scripts/run_pipeline.py --source stub --limit 5` |
| Exercise API manually | `uvicorn omen.main:app --reload` then open http://localhost:8000/docs |
| Run benchmarks | `pytest tests/benchmarks/ -c pytest_benchmark.ini -v` |
| Benchmark timings only | `pytest tests/benchmarks/ -c pytest_benchmark.ini --benchmark-only` (requires `pytest-benchmark`) |

**Coverage:** The default `pytest` run enforces a minimum coverage (see `pytest.ini`). To run tests without failing on coverage, use `pytest -v --no-cov`. Benchmark-only runs use little code, so use `-c pytest_benchmark.ini` or `--no-cov` to avoid coverage failure.

See [Day 1](#day-1-setup-and-first-run) for the full first-run flow.

Welcome aboard.
