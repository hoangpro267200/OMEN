"""Tests for QualityMetrics."""

import pytest

from omen.domain.models.common import ConfidenceLevel, ValidationStatus
from omen.domain.models.validated_signal import ValidationResult
from omen.domain.services.quality_metrics import QualityMetrics


def _make_result(
    rule_name: str, status: ValidationStatus, score: float, reason: str
) -> ValidationResult:
    return ValidationResult(
        rule_name=rule_name,
        rule_version="1.0.0",
        status=status,
        score=score,
        reason=reason,
    )


def test_record_validation_passed():
    """Recording a passed validation updates counts."""
    m = QualityMetrics()
    results = [
        _make_result("liquidity", ValidationStatus.PASSED, 0.9, "OK"),
        _make_result("semantic", ValidationStatus.PASSED, 0.8, "OK"),
    ]
    m.record_validation(passed=True, results=results)
    assert m.total_received == 1
    assert m.total_validated == 1
    assert m.total_rejected == 0
    assert m.rejection_rate == 0.0
    assert m.validation_rate == 1.0
    assert 0.8 <= m.avg_validation_score <= 0.9


def test_record_validation_rejected():
    """Recording a rejected validation updates reject counts."""
    m = QualityMetrics()
    results = [
        _make_result("liquidity_validation", ValidationStatus.PASSED, 0.9, "OK"),
        _make_result("semantic_relevance", ValidationStatus.REJECTED_IRRELEVANT_SEMANTIC, 0.2, "No keywords"),
    ]
    m.record_validation(passed=False, results=results)
    assert m.total_received == 1
    assert m.total_validated == 0
    assert m.total_rejected == 1
    assert m.rejection_rate == 1.0
    assert m.validation_rate == 0.0
    assert m.rejections_by_rule.get("semantic_relevance", 0) == 1
    assert m.rejections_by_status.get(ValidationStatus.REJECTED_IRRELEVANT_SEMANTIC.value, 0) == 1


def test_record_validation_rejections_by_rule():
    """Rejected outcome updates rejections_by_rule for the failing rule."""
    m = QualityMetrics()
    results = [
        _make_result("liquidity_validation", ValidationStatus.PASSED, 0.9, "OK"),
        _make_result("geographic_relevance", ValidationStatus.REJECTED_IRRELEVANT_GEOGRAPHY, 0.1, "No geo"),
    ]
    m.record_validation(passed=False, results=results)
    assert m.rejections_by_rule.get("geographic_relevance", 0) == 1
    assert m.rejections_by_status.get(ValidationStatus.REJECTED_IRRELEVANT_GEOGRAPHY.value, 0) == 1


def test_record_confidence():
    """Recording confidence updates distribution."""
    m = QualityMetrics()
    m.record_confidence(ConfidenceLevel.HIGH)
    m.record_confidence(ConfidenceLevel.HIGH)
    m.record_confidence(ConfidenceLevel.LOW)
    assert m.confidence_distribution["HIGH"] == 2
    assert m.confidence_distribution["LOW"] == 1


def test_rejection_rate_zero_when_no_events():
    """Rejection and validation rates are 0 when nothing recorded."""
    m = QualityMetrics()
    assert m.rejection_rate == 0.0
    assert m.validation_rate == 0.0


def test_to_dict():
    """to_dict returns serializable structure."""
    m = QualityMetrics()
    m.record_validation(
        passed=True,
        results=[
            _make_result("r1", ValidationStatus.PASSED, 0.7, "OK"),
        ],
    )
    m.record_confidence(ConfidenceLevel.MEDIUM)
    d = m.to_dict()
    assert d["total_received"] == 1
    assert d["total_validated"] == 1
    assert d["total_rejected"] == 0
    assert "rejection_rate" in d
    assert "validation_rate" in d
    assert "avg_validation_score" in d
    assert "rejections_by_rule" in d
    assert "rejections_by_status" in d
    assert "confidence_distribution" in d
    assert d["confidence_distribution"]["MEDIUM"] == 1


def test_avg_score_across_multiple_records():
    """Average validation score is computed over all records."""
    m = QualityMetrics()
    m.record_validation(
        passed=True,
        results=[_make_result("r1", ValidationStatus.PASSED, 0.6, "OK")],
    )
    m.record_validation(
        passed=True,
        results=[_make_result("r1", ValidationStatus.PASSED, 1.0, "OK")],
    )
    assert m.total_received == 2
    assert abs(m.avg_validation_score - 0.8) < 0.01
