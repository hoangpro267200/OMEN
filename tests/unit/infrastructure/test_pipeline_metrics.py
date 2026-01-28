"""
Tests for real pipeline metrics and activity — no hardcoded values.
"""

import time

import pytest

from omen.infrastructure.metrics.pipeline_metrics import (
    PipelineMetricsCollector,
    get_metrics_collector,
)
from omen.infrastructure.activity.activity_logger import (
    ActivityLogger,
    get_activity_logger,
)


class TestPipelineMetricsCollector:
    """Pipeline metrics must reflect actual processing."""

    def test_stats_empty_when_no_processing(self):
        """When the pipeline has not run, stats show zeros and stale."""
        collector = PipelineMetricsCollector()
        stats = collector.get_stats()

        assert stats["active_signals"] == 0
        assert stats["avg_confidence"] == 0.0
        assert stats.get("avg_confidence_note") == "No recent data"
        assert stats["data_freshness"] == "stale"
        assert stats["events_processed"] == 0

    def test_stats_reflect_actual_processing(self):
        """After complete_batch, stats show real values."""
        collector = PipelineMetricsCollector()

        collector.start_batch()
        time.sleep(0.02)
        collector.complete_batch(
            events_received=100,
            events_validated=70,
            events_translated=50,
            signals_generated=10,
            events_rejected=30,
            avg_confidence=0.82,
            total_risk_exposure_usd=5_000_000,
        )

        stats = collector.get_stats()

        assert stats["active_signals"] == 10
        assert stats["avg_confidence"] == 0.82
        assert stats["events_processed"] == 100
        assert stats["events_validated"] == 70
        assert stats["signals_generated"] == 10
        assert stats["events_rejected"] == 30
        assert stats["system_latency_ms"] > 0
        assert stats["data_freshness"] == "fresh"

    def test_record_from_pipeline_result(self):
        """record_from_pipeline_result updates totals from a single result."""
        collector = PipelineMetricsCollector()

        class FakeSignal:
            confidence_score = 0.75
            current_probability = 0.8
            severity = 0.7
            affected_routes = [None, None]

        collector.record_from_pipeline_result(
            events_received=1,
            events_validated=1,
            events_rejected=0,
            signals_generated=1,
            processing_time_ms=15.0,
            signals=[FakeSignal()],
        )

        stats = collector.get_stats()
        assert stats["events_processed"] == 1
        assert stats["signals_generated"] == 1
        assert stats["active_signals"] == 1
        assert stats["avg_confidence"] == 0.75


class TestActivityLogger:
    """Activity must be real events, not demo data."""

    def test_activity_empty_when_no_events(self):
        """New logger has no events."""
        logger = ActivityLogger()
        events = logger.get_recent(limit=50)
        assert events == []

    def test_activity_after_logging(self):
        """Logging adds real events."""
        logger = ActivityLogger()

        logger.log_signal_generated(
            signal_id="OMEN-TEST-001",
            title="Test Signal",
            severity_label="HIGH",
            confidence_level="HIGH",
        )

        events = logger.get_recent(limit=50)
        assert len(events) >= 1
        assert any(
            e.get("type") in ("signal", "alert") and "OMEN-TEST-001" in e.get("message", "")
            for e in events
        )

    def test_activity_source_fetch_success(self):
        """log_source_fetch(success=True) adds a source event."""
        logger = ActivityLogger()
        logger.log_source_fetch(
            source_name="Polymarket",
            events_count=42,
            latency_ms=100.0,
            success=True,
        )
        events = logger.get_recent(limit=10)
        assert len(events) == 1
        assert events[0]["type"] == "source"
        assert "42" in events[0]["message"]
