"""
Determinism tests — Core reproducibility contract.

These tests verify that OMEN produces identical outputs for identical inputs.
"""

import pytest


class TestDeterminism:
    """Determinism and idempotency contracts."""

    def test_same_event_produces_same_hash(self, high_quality_event):
        """input_event_hash must be stable."""
        hash1 = high_quality_event.input_event_hash
        hash2 = high_quality_event.input_event_hash
        assert hash1 == hash2

    def test_same_event_produces_same_trace_id(self, pipeline, high_quality_event):
        """deterministic_trace_id must be stable across runs."""
        result1 = pipeline.process_single(high_quality_event)
        result2 = pipeline.process_single(high_quality_event)
        assert result1.signals and result2.signals
        assert (
            result1.signals[0].deterministic_trace_id
            == result2.signals[0].deterministic_trace_id
        )

    def test_same_event_produces_same_metrics(self, pipeline, red_sea_event):
        """Impact metrics must be identical for same input."""
        result1 = pipeline.process_single(red_sea_event)
        result2 = pipeline.process_single(red_sea_event)
        assert result1.signals and result2.signals
        metrics1 = [(m.name, m.value) for m in result1.signals[0].key_metrics]
        metrics2 = [(m.name, m.value) for m in result2.signals[0].key_metrics]
        assert metrics1 == metrics2

    def test_pipeline_is_idempotent(self, pipeline, high_quality_event):
        """Processing same event twice returns cached result."""
        result1 = pipeline.process_single(high_quality_event)
        result2 = pipeline.process_single(high_quality_event)
        assert result2.cached is True
        assert result1.signals[0].signal_id == result2.signals[0].signal_id
