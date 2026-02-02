"""Load tests for API endpoints."""

import asyncio
import os
import time

import httpx
import pytest

# Default base URL for load tests (override with OMEN_LOAD_TEST_BASE_URL)
BASE_URL = os.environ.get("OMEN_LOAD_TEST_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("OMEN_SECURITY_API_KEYS", "test-key-integration").split(",")[0].strip()


async def request_health(client: httpx.AsyncClient) -> tuple[int, float]:
    """GET /health/ and return (status_code, latency_seconds)."""
    start = time.perf_counter()
    try:
        response = await client.get(f"{BASE_URL}/health/")
        latency = time.perf_counter() - start
        return response.status_code, latency
    except Exception:
        return 0, time.perf_counter() - start


async def request_signals_list(client: httpx.AsyncClient) -> tuple[int, float]:
    """GET /api/v1/signals/ with API key; return (status_code, latency_seconds)."""
    start = time.perf_counter()
    try:
        response = await client.get(
            f"{BASE_URL}/api/v1/signals/",
            headers={"X-API-Key": API_KEY},
        )
        latency = time.perf_counter() - start
        return response.status_code, latency
    except Exception:
        return 0, time.perf_counter() - start


@pytest.mark.asyncio
@pytest.mark.performance
async def test_health_load_concurrent():
    """Health endpoint handles concurrent requests."""
    num_requests = 50
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [request_health(client) for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    errors = sum(1 for r in results if isinstance(r, Exception))
    latencies = [r[1] for r in results if isinstance(r, tuple) and len(r) == 2]

    assert errors < num_requests * 0.1, f"Too many errors: {errors}/{num_requests}"
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 1.0, f"Avg latency too high: {avg_latency:.3f}s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_signals_list_load():
    """Signals list endpoint latency under load (skip if server not running)."""
    num_requests = 20
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [request_signals_list(client) for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    statuses = []
    latencies = []
    for r in results:
        if isinstance(r, Exception):
            statuses.append(0)
            continue
        if isinstance(r, tuple) and len(r) == 2:
            statuses.append(r[0])
            latencies.append(r[1])

    ok = sum(1 for s in statuses if s == 200)
    if ok == 0:
        pytest.skip("Server not reachable or API key invalid (run against live server)")

    assert ok >= num_requests * 0.5, f"Success rate too low: {ok}/{num_requests}"
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 2.0, f"Avg latency > 2s: {avg_latency:.3f}s"


def run_load_test_emit_style():
    """
    Standalone load test script (run with: python -m tests.performance.test_load).
    Hits health and signals list; prints throughput and latency percentiles.
    """
    async def _run():
        num_requests = 100
        concurrency = 10
        async with httpx.AsyncClient(timeout=10.0) as client:
            start = time.perf_counter()
            latencies = []
            for i in range(0, num_requests, concurrency):
                batch = min(concurrency, num_requests - i)
                tasks = [request_health(client) for _ in range(batch)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, tuple) and len(r) == 2:
                        latencies.append(r[1])
            total = time.perf_counter() - start

        if not latencies:
            print("No successful requests")
            return
        latencies.sort()
        n = len(latencies)
        print("\n=== Load Test Results (health) ===")
        print(f"Requests: {num_requests}, Concurrency: {concurrency}")
        print(f"Total time: {total:.2f}s")
        print(f"Throughput: {n / total:.1f} req/s")
        print(f"Avg latency: {sum(latencies) / n:.3f}s")
        print(f"P50: {latencies[n // 2]:.3f}s")
        print(f"P95: {latencies[int(n * 0.95)]:.3f}s")
        print(f"P99: {latencies[int(n * 0.99)]:.3f}s")

    asyncio.run(_run())


if __name__ == "__main__":
    run_load_test_emit_style()
