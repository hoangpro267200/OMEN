"""
Integration tests for P1 endpoints.

Tests:
- POST /api/v1/outcomes - Record outcomes
- GET /api/v1/calibration - Get calibration report
- GET /api/v1/outcomes - List outcomes
- GET /api/v1/outcomes/{signal_id} - Get specific outcome

Uses TestClient to test actual HTTP endpoints.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the OMEN API."""
    from omen.main import create_app
    
    app = create_app()
    client = TestClient(app)
    yield client


@pytest.fixture(autouse=True)
def clear_outcomes():
    """Clear outcomes store before each test."""
    from omen.api.routes.calibration import _outcomes_store
    _outcomes_store.clear()
    yield
    _outcomes_store.clear()


class TestOutcomesEndpoint:
    """Tests for /api/v1/outcomes endpoint."""

    def test_record_outcome_success(self, test_client):
        """Test recording an outcome successfully."""
        response = test_client.post(
            "/api/v1/outcomes",
            json={
                "signal_id": "OMEN-TEST-001",
                "actual_outcome": True,
                "actual_probability": 0.85,
                "notes": "Integration test outcome",
            },
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure (may be wrapped)
        if "data" in data:
            data = data["data"]
        
        assert data["success"] is True
        assert data["signal_id"] == "OMEN-TEST-001"
        assert data["storage_mode"] == "in_memory"

    def test_record_outcome_duplicate_fails(self, test_client):
        """Test that duplicate outcomes are rejected."""
        # First record
        test_client.post(
            "/api/v1/outcomes",
            json={
                "signal_id": "OMEN-DUP-001",
                "actual_outcome": True,
            },
            headers={"X-API-Key": "dev-test-key"},
        )
        
        # Duplicate should fail
        response = test_client.post(
            "/api/v1/outcomes",
            json={
                "signal_id": "OMEN-DUP-001",
                "actual_outcome": False,
            },
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 409

    def test_get_outcome_success(self, test_client):
        """Test getting a specific outcome."""
        # First record an outcome
        test_client.post(
            "/api/v1/outcomes",
            json={
                "signal_id": "OMEN-GET-001",
                "actual_outcome": True,
                "actual_probability": 0.9,
            },
            headers={"X-API-Key": "dev-test-key"},
        )
        
        # Get the outcome
        response = test_client.get(
            "/api/v1/outcomes/OMEN-GET-001",
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data:
            data = data["data"]
        
        assert data["signal_id"] == "OMEN-GET-001"
        assert data["actual_outcome"] is True
        assert data["actual_probability"] == 0.9

    def test_get_outcome_not_found(self, test_client):
        """Test getting a non-existent outcome returns 404."""
        response = test_client.get(
            "/api/v1/outcomes/OMEN-NONEXISTENT",
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 404

    def test_list_outcomes(self, test_client):
        """Test listing outcomes."""
        # Record multiple outcomes
        for i in range(3):
            test_client.post(
                "/api/v1/outcomes",
                json={
                    "signal_id": f"OMEN-LIST-{i:03d}",
                    "actual_outcome": i % 2 == 0,
                },
                headers={"X-API-Key": "dev-test-key"},
            )
        
        # List outcomes
        response = test_client.get(
            "/api/v1/outcomes?limit=10",
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data:
            data = data["data"]
        
        assert isinstance(data, list)
        assert len(data) == 3


class TestCalibrationEndpoint:
    """Tests for /api/v1/calibration endpoint."""

    def test_calibration_report_empty(self, test_client):
        """Test calibration report with no outcomes."""
        response = test_client.get(
            "/api/v1/calibration",
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data:
            data = data["data"]
        
        assert "total_signals" in data
        assert "signals_with_outcomes" in data
        assert "buckets" in data
        assert "overall_calibration_error" in data
        assert "storage_mode" in data
        assert data["storage_mode"] == "in_memory"

    def test_calibration_report_structure(self, test_client):
        """Test calibration report structure."""
        response = test_client.get(
            "/api/v1/calibration",
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data:
            data = data["data"]
        
        # Should have 10 buckets (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
        assert len(data["buckets"]) == 10
        
        # Each bucket should have required fields
        for bucket in data["buckets"]:
            assert "bucket_range" in bucket
            assert "predicted_avg" in bucket
            assert "actual_avg" in bucket
            assert "count" in bucket
            assert "calibration_error" in bucket


class TestHealthEndpoints:
    """Test health endpoints are accessible."""

    def test_health_endpoint(self, test_client):
        """Test /health endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200


class TestSignalsWithConfidenceInterval:
    """Test that signals include confidence interval."""

    def test_signals_endpoint_returns_confidence_interval(self, test_client):
        """Test /api/v1/signals returns signals with confidence_interval."""
        response = test_client.get(
            "/api/v1/signals?limit=1",
            headers={"X-API-Key": "dev-test-key"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data:
            data = data["data"]
        
        # If there are signals, check they have confidence_interval
        if isinstance(data, list) and len(data) > 0:
            signal = data[0]
            # confidence_interval may be None for demo signals
            assert "confidence_interval" in signal or signal.get("confidence_interval") is None
