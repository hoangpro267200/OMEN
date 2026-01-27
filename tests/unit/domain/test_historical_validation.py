"""Tests for HistoricalValidator and calibration."""

from datetime import datetime

import pytest

from omen.domain.services.historical_validation import (
    HistoricalValidator,
    PredictionRecord,
    OutcomeRecord,
    CalibrationComparison,
    CalibrationReport,
)


def test_record_prediction_and_outcome():
    """Recording prediction and outcome allows validation."""
    v = HistoricalValidator()
    v.record_prediction(
        PredictionRecord(
            signal_id="s1",
            metric_name="transit_time_increase",
            predicted_value=7.0,
            predicted_lower=5.0,
            predicted_upper=9.0,
            prediction_date=datetime(2025, 1, 1),
            event_probability=0.7,
        )
    )
    v.record_outcome(
        OutcomeRecord(
            signal_id="s1",
            metric_name="transit_time_increase",
            actual_value=7.5,
            outcome_date=datetime(2025, 1, 15),
            source="actuals_db",
        )
    )
    results, report = v.validate()
    assert len(results) == 1
    assert results[0].signal_id == "s1"
    assert results[0].metric_name == "transit_time_increase"
    assert results[0].predicted == 7.0
    assert results[0].actual == 7.5
    assert results[0].within_bounds is True
    assert report.total_predictions == 1
    assert report.predictions_within_bounds == 1
    assert report.coverage_rate == 1.0


def test_validation_without_bounds():
    """Predictions without bounds have within_bounds=None."""
    v = HistoricalValidator()
    v.record_prediction(
        PredictionRecord(
            signal_id="s2",
            metric_name="cost",
            predicted_value=10.0,
            predicted_lower=None,
            predicted_upper=None,
            prediction_date=datetime(2025, 1, 1),
            event_probability=0.5,
        )
    )
    v.record_outcome(
        OutcomeRecord(
            signal_id="s2",
            metric_name="cost",
            actual_value=12.0,
            outcome_date=datetime(2025, 1, 10),
            source="db",
        )
    )
    results, report = v.validate()
    assert len(results) == 1
    assert results[0].within_bounds is None
    assert results[0].error == 2.0
    assert report.mean_absolute_error == 2.0


def test_no_outcome_skipped():
    """Predictions without matching outcome are skipped."""
    v = HistoricalValidator()
    v.record_prediction(
        PredictionRecord(
            signal_id="s3",
            metric_name="m",
            predicted_value=1.0,
            predicted_lower=0.5,
            predicted_upper=1.5,
            prediction_date=datetime(2025, 1, 1),
            event_probability=0.5,
        )
    )
    results, report = v.validate()
    assert len(results) == 0
    assert report.total_predictions == 0
    assert report.coverage_rate == 0.0


def test_calibration_report_is_well_calibrated():
    """is_well_calibrated returns True when coverage >= target."""
    r = CalibrationReport(
        total_predictions=10,
        predictions_within_bounds=8,
    )
    assert r.coverage_rate == 0.8
    assert r.is_well_calibrated(0.8) is True
    assert r.is_well_calibrated(0.85) is False


def test_calibration_report_mean_errors():
    """Report aggregates mean_absolute_error and MAPE."""
    v = HistoricalValidator()
    v.record_prediction(
        PredictionRecord("a", "m", 10.0, None, None, datetime(2025, 1, 1), 0.5)
    )
    v.record_outcome(OutcomeRecord("a", "m", 12.0, datetime(2025, 1, 10), "x"))
    _, report = v.validate()
    assert report.mean_absolute_error == 2.0
    assert report.mean_absolute_percent_error == (2.0 / 12.0 * 100)


def test_errors_by_metric_populated():
    """Report.errors_by_metric lists error percents by metric."""
    v = HistoricalValidator()
    v.record_prediction(
        PredictionRecord("s1", "transit", 5.0, None, None, datetime(2025, 1, 1), 0.5)
    )
    v.record_outcome(OutcomeRecord("s1", "transit", 10.0, datetime(2025, 1, 10), "x"))
    _, report = v.validate()
    assert "transit" in report.errors_by_metric
    assert report.errors_by_metric["transit"] == [50.0]  # 5/10 -> 50% error
