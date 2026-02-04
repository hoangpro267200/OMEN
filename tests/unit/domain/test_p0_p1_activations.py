"""
Tests for P0/P1 Activations.

Verifies:
- P0-2: EnhancedConfidenceCalculator is in hot path
- P1-3: Explanation attached when EXPLANATIONS_HOT_PATH=1
- P1-4: Outcomes/Calibration endpoints work with in-memory storage
- P1-5: InMemoryJobScheduler runs cleanup
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from omen.domain.models.omen_signal import (
    OmenSignal,
    ConfidenceLevel,
    EXPLANATIONS_HOT_PATH,
)
from omen.domain.models.validated_signal import ValidatedSignal, ValidationResult
from omen.domain.models.raw_signal import RawSignalEvent, MarketMetadata
from omen.domain.models.common import (
    EventId,
    SignalCategory,
    ValidationStatus,
    RulesetVersion,
)
from omen.domain.models.explanation import ExplanationChain, ExplanationStep
from omen.domain.models.context import ProcessingContext
from omen.domain.services.confidence_calculator import (
    EnhancedConfidenceCalculator,
    get_confidence_calculator,
    ConfidenceInterval,
)


class TestEnhancedConfidenceCalculatorIntegration:
    """P0-2: Verify EnhancedConfidenceCalculator is called in hot path."""

    def test_confidence_calculator_produces_interval(self):
        """Test that the confidence calculator returns proper intervals."""
        calculator = get_confidence_calculator()
        
        result = calculator.calculate_confidence_with_interval(
            base_confidence=0.8,
            data_completeness=0.9,
            source_reliability=0.85,
        )
        
        assert isinstance(result, ConfidenceInterval)
        assert 0 <= result.point_estimate <= 1
        assert result.lower_bound <= result.point_estimate <= result.upper_bound
        assert result.confidence_level == 0.95
        assert result.method == "weighted_bayesian"

    def test_confidence_calculator_weights(self):
        """Test that confidence is properly weighted."""
        calculator = EnhancedConfidenceCalculator()
        
        # High inputs should give high confidence
        high_result = calculator.calculate_confidence_with_interval(
            base_confidence=0.9,
            data_completeness=0.95,
            source_reliability=0.9,
        )
        
        # Low inputs should give low confidence
        low_result = calculator.calculate_confidence_with_interval(
            base_confidence=0.3,
            data_completeness=0.5,
            source_reliability=0.6,
        )
        
        assert high_result.point_estimate > low_result.point_estimate
        assert high_result.width < low_result.width  # More precise when data is better

    def test_omen_signal_has_confidence_interval(self):
        """Test that OmenSignal includes confidence_interval field."""
        # Check the model has the field
        assert hasattr(OmenSignal, "model_fields")
        fields = OmenSignal.model_fields
        assert "confidence_interval" in fields

    def test_confidence_interval_populated_on_signal_creation(self):
        """Test that confidence interval is populated when creating OmenSignal."""
        # Create a minimal validated signal for testing
        event = _create_test_raw_event()
        validated = _create_test_validated_signal(event)
        enrichment = _create_test_enrichment()
        
        signal = OmenSignal.from_validated_event(validated, enrichment)
        
        # Verify confidence_interval is populated
        assert signal.confidence_interval is not None
        assert "point_estimate" in signal.confidence_interval
        assert "lower_bound" in signal.confidence_interval
        assert "upper_bound" in signal.confidence_interval
        assert "confidence_level" in signal.confidence_interval
        assert "method" in signal.confidence_interval
        
        # Verify interval values are valid
        ci = signal.confidence_interval
        assert ci["lower_bound"] <= ci["point_estimate"] <= ci["upper_bound"]
        assert ci["confidence_level"] == 0.95

    def test_confidence_score_matches_interval_point_estimate(self):
        """Test that confidence_score equals the interval's point_estimate."""
        event = _create_test_raw_event()
        validated = _create_test_validated_signal(event)
        enrichment = _create_test_enrichment()
        
        signal = OmenSignal.from_validated_event(validated, enrichment)
        
        # confidence_score should match point_estimate
        assert signal.confidence_score == signal.confidence_interval["point_estimate"]


class TestExplanationHotPath:
    """P1-3: Verify explanation is attached when EXPLANATIONS_HOT_PATH=1."""

    def test_explanation_fields_exist(self):
        """Test that explanation fields exist in OmenSignal."""
        fields = OmenSignal.model_fields
        assert "explanation_text" in fields
        assert "explanation_summary" in fields

    def test_explanation_not_populated_by_default(self):
        """Test that explanation is not populated when flag is off."""
        # EXPLANATIONS_HOT_PATH should be False by default
        event = _create_test_raw_event()
        validated = _create_test_validated_signal(event)
        enrichment = _create_test_enrichment()
        
        signal = OmenSignal.from_validated_event(validated, enrichment)
        
        # Without the flag, explanation should be None
        if not EXPLANATIONS_HOT_PATH:
            assert signal.explanation_text is None
            assert signal.explanation_summary is None

    @patch.dict(os.environ, {"EXPLANATIONS_HOT_PATH": "1"})
    def test_explanation_populated_with_flag(self):
        """Test that explanation is populated when EXPLANATIONS_HOT_PATH=1."""
        # Need to reload the module to pick up the env var
        # For this test, we'll simulate the behavior
        from omen.domain.models import omen_signal
        
        # Create validated signal with explanation chain
        event = _create_test_raw_event()
        
        # Create explanation chain
        ctx = ProcessingContext.create(RulesetVersion("v1.0.0"))
        explanation_chain = ExplanationChain.create(ctx)
        step = ExplanationStep.create(
            step_id=1,
            rule_name="liquidity_validation",
            rule_version="1.0.0",
            reasoning="Liquidity check passed with score 0.85",
            confidence_contribution=0.85,
            processing_time=ctx.processing_time,
        )
        explanation_chain = explanation_chain.add_step(step)
        explanation_chain = explanation_chain.finalize(ctx)
        
        validated = _create_test_validated_signal(event, explanation_chain=explanation_chain)
        enrichment = _create_test_enrichment()
        
        # Manually simulate flag being on
        original_flag = omen_signal.EXPLANATIONS_HOT_PATH
        omen_signal.EXPLANATIONS_HOT_PATH = True
        
        try:
            signal = OmenSignal.from_validated_event(validated, enrichment)
            
            # With the flag on, explanation should be populated
            assert signal.explanation_text is not None
            assert signal.explanation_summary is not None
            assert "liquidity_validation" in signal.explanation_text
        finally:
            # Restore original flag
            omen_signal.EXPLANATIONS_HOT_PATH = original_flag


class TestCalibrationEndpoints:
    """P1-4: Verify outcomes/calibration endpoints work."""

    @pytest.fixture
    def clear_outcomes(self):
        """Clear outcomes store before each test."""
        from omen.api.routes.calibration import _outcomes_store
        _outcomes_store.clear()
        yield
        _outcomes_store.clear()

    def test_outcome_record_creation(self, clear_outcomes):
        """Test creating an outcome record."""
        from omen.api.routes.calibration import OutcomeRecord
        
        record = OutcomeRecord(
            signal_id="OMEN-TEST-001",
            actual_outcome=True,
            actual_probability=0.85,
            notes="Test outcome",
        )
        
        assert record.signal_id == "OMEN-TEST-001"
        assert record.actual_outcome is True
        assert record.actual_probability == 0.85
        assert record.recorded_at is not None

    def test_storage_mode_detection(self):
        """Test that storage mode is correctly detected."""
        from omen.api.routes.calibration import _get_storage_mode
        
        # Without DATABASE_URL, should be in_memory
        with patch.dict(os.environ, {}, clear=True):
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]
            assert _get_storage_mode() == "in_memory"
        
        # With DATABASE_URL, should be database
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
            assert _get_storage_mode() == "database"

    def test_calibration_bucket_calculation(self):
        """Test calibration bucket statistics."""
        from omen.api.routes.calibration import CalibrationBucket
        
        bucket = CalibrationBucket(
            bucket_range="0.7-0.8",
            predicted_avg=0.75,
            actual_avg=0.72,
            count=10,
            calibration_error=0.03,
        )
        
        assert bucket.bucket_range == "0.7-0.8"
        # Use approximate comparison for floating point
        assert abs(bucket.calibration_error - abs(bucket.predicted_avg - bucket.actual_avg)) < 0.001


class TestInMemoryJobScheduler:
    """P1-5: Verify InMemoryJobScheduler runs cleanup."""

    @pytest.mark.asyncio
    async def test_scheduler_creation(self):
        """Test that scheduler can be created."""
        from omen.jobs.in_memory_scheduler import InMemoryJobScheduler
        
        scheduler = InMemoryJobScheduler(
            signal_retention_hours=1,
            calibration_retention_days=1,
            activity_retention_hours=1,
        )
        
        assert not scheduler._running
        assert len(scheduler._jobs) == 3
        assert "cleanup_old_signals" in scheduler._jobs
        assert "cleanup_calibration_data" in scheduler._jobs
        assert "cleanup_activity_logs" in scheduler._jobs

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test scheduler start and stop."""
        from omen.jobs.in_memory_scheduler import InMemoryJobScheduler
        
        scheduler = InMemoryJobScheduler()
        
        await scheduler.start()
        assert scheduler._running
        
        await scheduler.stop()
        assert not scheduler._running

    @pytest.mark.asyncio
    async def test_scheduler_status(self):
        """Test scheduler status reporting."""
        from omen.jobs.in_memory_scheduler import InMemoryJobScheduler
        
        scheduler = InMemoryJobScheduler()
        
        status = scheduler.get_status()
        assert status["running"] is False
        assert status["mode"] == "in_memory"
        assert "jobs" in status
        assert len(status["jobs"]) == 3

    @pytest.mark.asyncio
    async def test_cleanup_calibration_data(self):
        """Test calibration data cleanup job."""
        from omen.jobs.in_memory_scheduler import InMemoryJobScheduler
        from omen.api.routes.calibration import _outcomes_store, OutcomeRecord
        
        # Add old and new outcomes
        old_time = datetime.now(timezone.utc) - timedelta(days=60)
        new_time = datetime.now(timezone.utc)
        
        _outcomes_store["old-signal"] = OutcomeRecord(
            signal_id="old-signal",
            actual_outcome=True,
            recorded_at=old_time,
        )
        _outcomes_store["new-signal"] = OutcomeRecord(
            signal_id="new-signal",
            actual_outcome=False,
            recorded_at=new_time,
        )
        
        scheduler = InMemoryJobScheduler(calibration_retention_days=30)
        result = await scheduler._cleanup_calibration_data()
        
        assert result.status == "SUCCESS"
        assert result.items_cleaned == 1
        assert "old-signal" not in _outcomes_store
        assert "new-signal" in _outcomes_store
        
        # Cleanup
        _outcomes_store.clear()

    def test_job_list(self):
        """Test listing available jobs."""
        from omen.jobs.in_memory_scheduler import InMemoryJobScheduler
        
        scheduler = InMemoryJobScheduler()
        jobs = scheduler.list_jobs()
        
        assert "cleanup_old_signals" in jobs
        assert "cleanup_calibration_data" in jobs
        assert "cleanup_activity_logs" in jobs


# === Test Helpers ===

def _create_test_raw_event() -> RawSignalEvent:
    """Create a test RawSignalEvent."""
    return RawSignalEvent(
        event_id=EventId("test-event-001"),
        source="polymarket",
        title="Test Event: Will X happen by 2026?",
        description="A test event for unit testing",
        probability=0.75,
        keywords=["test", "logistics"],
        inferred_locations=[],
        market=MarketMetadata(
            market_id="test-market-001",
            source="polymarket",
            market_url="https://polymarket.com/test",
            current_liquidity_usd=50000.0,
            volume_24h_usd=10000.0,
            total_volume_usd=100000.0,  # Required field
        ),
        observed_at=datetime.now(timezone.utc),
    )


def _create_test_validated_signal(
    event: RawSignalEvent,
    explanation_chain: ExplanationChain | None = None,
) -> ValidatedSignal:
    """Create a test ValidatedSignal."""
    ctx = ProcessingContext.create(RulesetVersion("v1.0.0"))
    
    if explanation_chain is None:
        explanation_chain = ExplanationChain.create(ctx)
        explanation_chain = explanation_chain.finalize(ctx)
    
    return ValidatedSignal(
        event_id=event.event_id,
        original_event=event,
        category=SignalCategory.INFRASTRUCTURE,
        validation_results=[
            ValidationResult(
                rule_name="liquidity_validation",
                rule_version="1.0.0",
                status=ValidationStatus.PASSED,
                score=0.85,
                reason="Liquidity check passed",
            ),
            ValidationResult(
                rule_name="geographic_relevance",
                rule_version="1.0.0",
                status=ValidationStatus.PASSED,
                score=0.75,
                reason="Geographic relevance check passed",
            ),
        ],
        overall_validation_score=0.80,
        signal_strength=0.80,
        liquidity_score=0.85,
        explanation=explanation_chain,
        ruleset_version=RulesetVersion("v1.0.0"),
    )


def _create_test_enrichment() -> dict:
    """Create test enrichment context."""
    return {
        "matched_regions": ["Asia"],
        "matched_chokepoints": ["Strait of Malacca"],
        "matched_keywords": ["shipping", "logistics"],
        "keyword_categories": {"infrastructure": ["shipping"]},
        "confidence_factors": {
            "liquidity": 0.85,
            "geographic": 0.75,
            "source_reliability": 0.90,
        },
    }
