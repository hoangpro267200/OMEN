"""Pytest config for benchmarks: disable coverage fail-under when running --benchmark-only."""

import sys

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """When running only benchmarks, do not fail on low coverage."""
    benchmark_only = "--benchmark-only" in sys.argv
    if not benchmark_only:
        try:
            benchmark_only = config.getoption("benchmark_only", default=False)
        except (ValueError, AttributeError):
            pass
    if benchmark_only and hasattr(config.option, "cov_fail_under"):
        config.option.cov_fail_under = 0
