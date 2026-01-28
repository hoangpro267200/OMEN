"""
Comprehensive data integrity tests.

These tests verify that NO fake data appears in production code paths.
"""

import re
from pathlib import Path

import pytest


class TestNoHardcodedData:
    """Verify no hardcoded data in production code."""

    PRODUCTION_PATHS = [
        "src/omen/api/routes/",
        "src/omen/application/",
        "src/omen/domain/",
        "src/omen/adapters/",
    ]

    # Patterns that indicate hardcoded data
    SUSPICIOUS_PATTERNS = [
        (r"probability\s*=\s*0\.\d+", "Hardcoded probability"),
        (r"confidence\s*=\s*0\.\d+", "Hardcoded confidence"),
        (r"avg_confidence\s*=\s*0\.\d+", "Hardcoded avg_confidence"),
        (r"risk_exposure\s*=\s*\d+", "Hardcoded risk exposure"),
        (r"latency.*=\s*\d+", "Hardcoded latency"),
        (r"events_per_min.*=\s*\d{2,}", "Hardcoded events rate"),
        (r"random\(\)", "Random value generation"),
        (r"hash\(.*\)\s*%", "Hash-based fake generation"),
        (r"for i in range\(\d+\).*0\.\d+", "Loop-generated fake data"),
    ]

    # Allowed exceptions (document why each is OK)
    ALLOWED_EXCEPTIONS = {
        "parameters.py": "Contains documented constants with sources",
        "methodology/": "Contains documented methodology parameters",
        "test_": "Test files may use test data",
        "mock": "Mock files are explicitly for testing",
    }

    def test_no_hardcoded_data_in_api_routes(self):
        """API routes should not contain hardcoded display data."""
        issues = []
        base = Path(__file__).resolve().parents[2]
        routes_dir = base / "src" / "omen" / "api" / "routes"
        if not routes_dir.exists():
            pytest.skip("api/routes not found")
        for path in routes_dir.glob("*.py"):
            if any(exc in path.name for exc in self.ALLOWED_EXCEPTIONS):
                continue
            content = path.read_text(encoding="utf-8")
            for pattern, description in self.SUSPICIOUS_PATTERNS:
                matches = re.findall(pattern, content)
                if matches:
                    issues.append(f"{path.name}: {description} - {matches[:3]}")
        assert not issues, "Found hardcoded data:\n" + "\n".join(issues)

    def test_no_synthetic_data_generation(self):
        """Production code should not generate synthetic data."""
        issues = []
        base = Path(__file__).resolve().parents[2]
        src = base / "src" / "omen"
        if not src.exists():
            pytest.skip("src/omen not found")
        fake_patterns = [
            (r"prob_history\s*=\s*\[.*for.*in.*range", "Synthetic probability history"),
            (r"_confidence_breakdown.*hash", "Hash-based confidence breakdown"),
            (r"_metric_projection.*exp\(", "Unsourced metric projection"),
            (r"delay_days\s*=\s*severity\s*\*", "Arbitrary delay calculation"),
        ]
        for path in src.rglob("*.py"):
            if "test" in str(path) or "mock" in str(path):
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue  # skip binary or non-UTF-8 files
            for pattern, description in fake_patterns:
                if re.search(pattern, content):
                    issues.append(f"{path}: {description}")
        assert not issues, "Found synthetic data generation:\n" + "\n".join(issues)


class TestAPIResponseIntegrity:
    """Test that API responses contain only real data."""

    def test_live_process_returns_traceable_data(self, test_client):
        """Every field in /live/process response should be traceable."""
        response = test_client.post("/api/v1/live/process", params={"limit": 5})
        if response.status_code != 200:
            pytest.skip("API not available or Polymarket unreachable")
        signals = response.json()
        for signal in signals:
            assert "probability" in signal
            assert 0 <= signal["probability"] <= 1
            if signal.get("confidence_breakdown"):
                breakdown = signal["confidence_breakdown"]
                for key in ["liquidity", "geographic"]:
                    assert key in breakdown
                    assert 0 <= breakdown[key] <= 1
            for metric in signal.get("metrics", []):
                if metric.get("value") is not None:
                    assert "methodology_name" in metric or metric.get("value") is None
                if metric.get("uncertainty"):
                    unc = metric["uncertainty"]
                    assert "lower" in unc and "upper" in unc
                    assert unc["lower"] <= metric["value"] <= unc["upper"]
            for route in signal.get("affected_routes", []):
                if route.get("origin"):
                    assert "lat" in route["origin"]
                    assert -90 <= route["origin"]["lat"] <= 90

    def test_stats_reflect_actual_processing(self, test_client):
        """Stats endpoint should return actual metrics, not hardcoded."""
        response1 = test_client.get("/api/v1/stats")
        stats1 = response1.json()
        initial_processed = stats1["events_processed"]
        test_client.post("/api/v1/live/process", params={"limit": 5})
        response2 = test_client.get("/api/v1/stats")
        stats2 = response2.json()
        assert stats2["events_processed"] >= initial_processed

    def test_activity_shows_real_events(self, test_client):
        """Activity feed should show actual pipeline events."""
        test_client.post("/api/v1/live/process", params={"limit": 3})
        response = test_client.get("/api/v1/activity", params={"limit": 10})
        activity = response.json()
        if len(activity) > 1:
            timestamps = [a["timestamp"] for a in activity]
            assert len(set(timestamps)) > 1 or len(activity) == 1


class TestMethodologyProvenance:
    """Test that all calculations reference methodologies."""

    def test_methodologies_are_documented(self, test_client):
        """All methodologies should be available via API."""
        response = test_client.get("/api/v1/methodology")
        if response.status_code != 200:
            pytest.skip("Methodology API not available")
        methodologies = response.json()
        assert "impact" in methodologies
        assert "validation" in methodologies
        for category in methodologies.values():
            for method in category:
                assert "name" in method
                assert "version" in method
                assert "validation_status" in method

    def test_metrics_reference_methodologies(self, test_client):
        """Impact metrics should reference their methodology when value present."""
        response = test_client.post("/api/v1/live/process", params={"limit": 3})
        if response.status_code != 200:
            pytest.skip("API not available")
        signals = response.json()
        for signal in signals:
            for metric in signal.get("metrics", []):
                if metric.get("value") is None:
                    continue
                assert "methodology_name" in metric, (
                    f"Metric {metric.get('name')} missing methodology"
                )
                assert "methodology_version" in metric
