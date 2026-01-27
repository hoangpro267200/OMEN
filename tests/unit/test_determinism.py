"""
Phase 3 determinism tests — full replay and bit-identical output.

These tests prove that identical input + same ProcessingContext
produces bit-identical output.
"""

from datetime import datetime

import pytest

from omen.domain.models.context import ProcessingContext
from omen.domain.models.common import RulesetVersion
from omen.domain.models.explanation import ExplanationChain


class TestFullDeterminism:
    """Tests proving bit-identical output for identical input."""

    def test_same_context_produces_identical_explanations(self):
        """ExplanationChain timestamps are deterministic."""
        fixed_time = datetime(2025, 1, 15, 12, 0, 0)
        ctx = ProcessingContext.create_for_replay(
            processing_time=fixed_time,
            ruleset_version=RulesetVersion("v1.0.0"),
        )

        chain1 = ExplanationChain.create(ctx)
        chain2 = ExplanationChain.create(ctx)

        assert chain1.started_at == chain2.started_at
        assert chain1.trace_id == chain2.trace_id

    def test_replay_produces_identical_signal(self, pipeline, red_sea_event):
        """Replaying with same context produces identical output."""
        fixed_time = datetime(2025, 1, 15, 12, 0, 0)
        ctx = ProcessingContext.create_for_replay(
            processing_time=fixed_time,
            ruleset_version=RulesetVersion("v1.0.0"),
        )

        result1 = pipeline.process_single(red_sea_event, context=ctx)
        result2 = pipeline.process_single(red_sea_event, context=ctx)

        assert result1.signals and result2.signals
        signal1 = result1.signals[0]
        signal2 = result2.signals[0]

        assert signal1.signal_id == signal2.signal_id
        assert signal1.deterministic_trace_id == signal2.deterministic_trace_id
        assert signal1.generated_at == signal2.generated_at
        assert (
            signal1.explanation_chain.started_at
            == signal2.explanation_chain.started_at
        )

        json1 = signal1.model_dump_json(indent=2)
        json2 = signal2.model_dump_json(indent=2)
        assert json1 == json2, "Signals are not bit-identical"

    def test_different_description_changes_hash(self, high_quality_event):
        """Events differing only in description have different hashes."""
        event1 = high_quality_event
        event2 = high_quality_event.model_copy(
            update={"description": "Different description"}
        )

        assert event1.input_event_hash != event2.input_event_hash

    def test_different_keywords_changes_hash(self, high_quality_event):
        """Events differing only in keywords have different hashes."""
        event1 = high_quality_event
        event2 = high_quality_event.model_copy(
            update={"keywords": ["different", "keywords"]}
        )

        assert event1.input_event_hash != event2.input_event_hash
