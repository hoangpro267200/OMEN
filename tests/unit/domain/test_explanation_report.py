"""Tests for explanation report generators (pure OmenSignal contract)."""

from datetime import datetime

import pytest

from omen.domain.models.omen_signal import (
    OmenSignal,
    ConfidenceLevel,
    SignalCategory,
    GeographicContext,
    TemporalContext,
    ValidationScore,
    EvidenceItem,
)
from omen.domain.services.explanation_report import (
    generate_json_audit_report,
    generate_text_report,
)


def _minimal_pure_signal(
    validation_scores: list[ValidationScore] | None = None,
    evidence: list[EvidenceItem] | None = None,
) -> OmenSignal:
    """Build a minimal pure OmenSignal for report tests."""
    return OmenSignal(
        signal_id="OMEN-TEST001",
        source_event_id="ev-1",
        input_event_hash="abc123",
        title="Test signal title",
        description="Short description",
        probability=0.75,
        probability_source="test",
        probability_is_estimate=False,
        confidence_score=0.85,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_factors={"liquidity": 0.9, "geographic": 0.8},
        category=SignalCategory.GEOPOLITICAL,
        tags=[],
        keywords_matched=[],
        geographic=GeographicContext(regions=["Red Sea"], chokepoints=["suez"]),
        temporal=TemporalContext(signal_freshness="current"),
        evidence=evidence or [],
        validation_scores=validation_scores
        or [
            ValidationScore(
                rule_name="liquidity_validation",
                rule_version="1.0.0",
                score=0.9,
                reasoning="Sufficient liquidity",
            ),
        ],
        trace_id="trace-xyz",
        ruleset_version="v1.0.0",
        source_url="https://example.com/m",
        generated_at=datetime(2025, 1, 15, 12, 0, 0),
    )


def test_generate_text_report_contains_sections() -> None:
    """generate_text_report includes summary, validation scores, and reproducibility."""
    signal = _minimal_pure_signal()
    report = generate_text_report(signal)
    assert "OMEN SIGNAL REPORT: OMEN-TEST001" in report
    assert "SUMMARY" in report
    assert "Title: Test signal title" in report
    assert "Confidence:" in report
    assert "Probability:" in report
    assert "VALIDATION SCORES" in report
    assert "liquidity_validation" in report
    assert "Sufficient liquidity" in report
    assert "REPRODUCIBILITY" in report
    assert "Input Hash: abc123" in report
    assert "Trace ID: trace-xyz" in report
    assert "Ruleset: v1.0.0" in report


def test_generate_text_report_includes_evidence() -> None:
    """generate_text_report includes evidence when present."""
    evidence = [
        EvidenceItem(source="Polymarket", source_type="market", url="https://poly.example/x"),
    ]
    signal = _minimal_pure_signal(evidence=evidence)
    report = generate_text_report(signal)
    assert "EVIDENCE" in report
    assert "Polymarket" in report


def test_generate_json_audit_report_structure() -> None:
    """generate_json_audit_report returns pure-contract structure."""
    signal = _minimal_pure_signal()
    out = generate_json_audit_report(signal)
    assert out["signal_id"] == "OMEN-TEST001"
    assert out["source_event_id"] == "ev-1"
    assert "reproducibility" in out
    assert out["reproducibility"]["input_event_hash"] == "abc123"
    assert out["reproducibility"]["trace_id"] == "trace-xyz"
    assert out["reproducibility"]["ruleset_version"] == "v1.0.0"
    assert "classification" in out
    assert out["classification"]["category"] == "GEOPOLITICAL"
    assert "assessment" in out
    assert out["assessment"]["confidence_level"] == "HIGH"
    assert "probability" in out
    assert out["probability"]["value"] == 0.75
    assert "validation_scores" in out
    assert len(out["validation_scores"]) >= 1
    assert "evidence" in out
    assert "geographic" in out
    assert "temporal" in out
    assert "generated_at" in out
