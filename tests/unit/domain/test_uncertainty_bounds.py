"""Tests for UncertaintyBounds and ImpactMetric with uncertainty."""

import pytest

from omen_impact.assessment import (
    UncertaintyBounds,
    ImpactMetric,
    create_transit_time_metric,
    create_cost_increase_metric,
)


def test_uncertainty_bounds_contains():
    """UncertaintyBounds.contains returns True when value in range."""
    ub = UncertaintyBounds(lower=10.0, upper=20.0)
    assert ub.contains(15.0) is True
    assert ub.contains(10.0) is True
    assert ub.contains(20.0) is True
    assert ub.contains(9.9) is False
    assert ub.contains(20.1) is False


def test_uncertainty_bounds_range_and_midpoint():
    """UncertaintyBounds.range and .midpoint are correct."""
    ub = UncertaintyBounds(lower=10.0, upper=30.0)
    assert ub.range == 20.0
    assert ub.midpoint == 20.0


def test_uncertainty_bounds_default_confidence_interval():
    """UncertaintyBounds defaults to 0.8 confidence_interval."""
    ub = UncertaintyBounds(lower=0, upper=1)
    assert ub.confidence_interval == 0.8


def test_impact_metric_has_uncertainty():
    """ImpactMetric.has_uncertainty reflects presence of uncertainty."""
    with_unc = ImpactMetric(
        name="x",
        value=5.0,
        unit="days",
        uncertainty=UncertaintyBounds(4.0, 6.0),
        confidence=0.8,
    )
    without_unc = ImpactMetric(
        name="y",
        value=5.0,
        unit="days",
        confidence=0.8,
    )
    assert with_unc.has_uncertainty is True
    assert without_unc.has_uncertainty is False


def test_impact_metric_scale_by_probability():
    """scale_by_probability scales value and uncertainty."""
    m = ImpactMetric(
        name="transit",
        value=10.0,
        unit="days",
        uncertainty=UncertaintyBounds(8.0, 12.0),
        confidence=0.8,
        sensitivity_to_probability=1.0,
    )
    scaled = m.scale_by_probability(0.5)
    assert scaled.value == 5.0
    assert scaled.uncertainty is not None
    assert scaled.uncertainty.lower == 4.0
    assert scaled.uncertainty.upper == 6.0


def test_impact_metric_change_from_baseline():
    """change_from_baseline returns percent change when baseline set."""
    m = ImpactMetric(
        name="cost",
        value=120.0,
        unit="percent",
        confidence=0.7,
        baseline=100.0,
    )
    assert m.change_from_baseline == 20.0
    m_nobase = ImpactMetric(name="x", value=1, unit="u", confidence=0.5)
    assert m_nobase.change_from_baseline is None


def test_create_transit_time_metric():
    """create_transit_time_metric produces metric with uncertainty."""
    m = create_transit_time_metric(days=10.0, probability=0.6, evidence_source="Test 2024")
    assert m.name == "transit_time_increase"
    assert m.value == 6.0
    assert m.unit == "days"
    assert m.uncertainty is not None
    assert m.uncertainty.lower <= m.value <= m.uncertainty.upper
    assert m.evidence_type == "historical"
    assert m.evidence_source == "Test 2024"
    assert m.confidence == 0.75


def test_create_cost_increase_metric():
    """create_cost_increase_metric produces metric with uncertainty."""
    m = create_cost_increase_metric(
        percent=20.0,
        probability=0.5,
        metric_name="freight_increase",
        evidence_source="Index 2024",
    )
    assert m.name == "freight_increase"
    assert m.value == 10.0
    assert m.unit == "percent"
    assert m.uncertainty is not None
    assert m.sensitivity_to_probability == 1.2
    assert m.evidence_source == "Index 2024"


def test_impact_metric_evidence_type_default():
    """ImpactMetric defaults evidence_type to assumption when no source."""
    m = create_transit_time_metric(days=5.0, probability=0.4)
    assert m.evidence_type == "assumption"
    assert m.evidence_source is None
