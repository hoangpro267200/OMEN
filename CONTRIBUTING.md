# Contributing to OMEN

Thank you for your interest in contributing. This document summarizes how to work with the repo and what we expect from contributions.

## Development setup

1. Fork and clone the repo.
2. Create a virtual environment and install in editable mode with dev extras:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   ```
3. Copy `.env.example` to `.env` and adjust if needed for local runs.

## Code standards

- **Python:** 3.10+
- **Style:** Black (line length 100). Run `black src/ tests/` before committing.
- **Linting:** Ruff. Run `ruff check src/ tests/`.
- **Types:** Type hints on public APIs; mypy clean on `src/`: `mypy src/`.
- **Tests:** Pytest. Prefer unit tests under `tests/unit/`; use `tests/integration/` for multi-component flows. New code should have tests.
- **Docs:** Docstrings for public modules, classes, and functions. For design changes, consider adding or updating an [ADR](docs/adr/README.md).

## Architecture rules

- **Domain** (`src/omen/domain/`): No I/O, no framework dependencies. Pure business logic.
- **Application** (`src/omen/application/`): Use cases and port interfaces only. Depends only on domain.
- **Adapters** (`src/omen/adapters/`): Implement ports. All I/O and external calls go here.
- **Infrastructure** (`src/omen/infrastructure/`): Cross-cutting (security, monitoring, retries, etc.).

See [ADR-002: Hexagonal Architecture](docs/adr/002-hexagonal-architecture.md) for details.

## Pull request process

1. Create a branch from `main` (or the current default branch).
2. Make your changes and add or update tests.
3. Run:
   - `pytest`
   - `pytest --cov` (coverage should not drop unnecessarily)
   - `black src/ tests/`
   - `ruff check src/ tests/`
   - `mypy src/`
4. Update docs (including docstrings and ADRs) if behavior or design changes.
5. Open a PR with a short description of the change and how to verify it.
6. Address review comments. Once approved, maintainers will merge.

## Areas where help is welcome

- **Tests:** Broader coverage, property-based tests (Hypothesis), and performance benchmarks.
- **Adapters:** Additional signal sources (e.g. Kalshi) or publishers (e.g. Kafka) that implement existing ports.
- **Documentation:** Clearer examples, onboarding steps, or ADRs for new decisions.
- **Performance:** Profiling, async pipeline tuning, and backpressure behavior.

## Questions

- Open a [GitHub Discussion](https://github.com/your-org/omen/discussions) for design or usage questions.
- Use [GitHub Issues](https://github.com/your-org/omen/issues) for bugs and feature requests.

Thank you for contributing.
