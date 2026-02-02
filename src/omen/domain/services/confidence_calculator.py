"""
Enhanced Confidence Calculator with Intervals.

Provides uncertainty quantification for downstream systems like RiskCast.
Confidence intervals help clients understand the precision of our estimates.
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field


class ConfidenceInterval(BaseModel):
    """
    Confidence interval for a signal's confidence score.
    
    Provides uncertainty bounds to help downstream systems
    make risk-appropriate decisions.
    
    Example:
        If point_estimate is 0.85 with [0.78, 0.92] at 95% confidence,
        we're 95% confident the true confidence lies in that range.
    """
    
    point_estimate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Best estimate of confidence score",
    )
    lower_bound: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Lower bound of confidence interval",
    )
    upper_bound: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Upper bound of confidence interval",
    )
    confidence_level: float = Field(
        0.95,
        ge=0.0,
        le=1.0,
        description="Confidence level (e.g., 0.95 for 95% CI)",
    )
    method: str = Field(
        "weighted_bayesian",
        description="Method used to calculate interval",
    )
    
    @property
    def width(self) -> float:
        """Width of the confidence interval."""
        return self.upper_bound - self.lower_bound
    
    @property
    def is_precise(self) -> bool:
        """Check if interval is reasonably precise (width < 0.2)."""
        return self.width < 0.2


class EnhancedConfidenceCalculator:
    """
    Calculates confidence scores WITH intervals.
    
    Provides uncertainty quantification for downstream systems to make
    informed risk decisions.
    
    Key Features:
    - Point estimates with confidence intervals
    - Adjustable confidence levels (90%, 95%, 99%)
    - Multiple calculation methods
    
    Usage:
        calculator = EnhancedConfidenceCalculator()
        
        result = calculator.calculate_confidence_with_interval(
            base_confidence=0.85,
            data_completeness=0.90,
            source_reliability=0.95,
        )
        
        print(f"Confidence: {result.point_estimate}")
        print(f"95% CI: [{result.lower_bound}, {result.upper_bound}]")
    """
    
    # Weight factors for combining confidence components
    WEIGHTS = {
        "base": 0.40,          # Base signal quality
        "completeness": 0.30,  # Data completeness
        "reliability": 0.30,   # Source reliability
    }
    
    # Z-scores for common confidence levels
    Z_SCORES = {
        0.90: 1.645,
        0.95: 1.960,
        0.99: 2.576,
    }
    
    def calculate_confidence_with_interval(
        self,
        base_confidence: float,
        data_completeness: float,
        source_reliability: float,
        sample_size: Optional[int] = None,
        confidence_level: float = 0.95,
    ) -> ConfidenceInterval:
        """
        Calculate confidence score with confidence interval.
        
        Args:
            base_confidence: Base confidence from signal quality (0-1)
            data_completeness: Fraction of expected data present (0-1)
            source_reliability: Historical reliability of source (0-1)
            sample_size: Number of data points (for statistical CI)
            confidence_level: Desired confidence level (default 95%)
        
        Returns:
            ConfidenceInterval with point estimate and bounds
        
        Example:
            >>> calc = EnhancedConfidenceCalculator()
            >>> result = calc.calculate_confidence_with_interval(
            ...     base_confidence=0.85,
            ...     data_completeness=0.90,
            ...     source_reliability=0.95,
            ... )
            >>> print(f"Confidence: {result.point_estimate:.2f}")
            >>> print(f"95% CI: [{result.lower_bound:.2f}, {result.upper_bound:.2f}]")
        """
        # Validate inputs
        base_confidence = max(0.0, min(1.0, base_confidence))
        data_completeness = max(0.0, min(1.0, data_completeness))
        source_reliability = max(0.0, min(1.0, source_reliability))
        
        # Calculate point estimate
        point_estimate = self._calculate_point_estimate(
            base_confidence,
            data_completeness,
            source_reliability,
        )
        
        # Calculate uncertainty (standard error approximation)
        uncertainty = self._calculate_uncertainty(
            data_completeness,
            source_reliability,
            sample_size,
        )
        
        # Get z-score for confidence level
        z_score = self._get_z_score(confidence_level)
        
        # Calculate bounds
        margin = z_score * uncertainty
        lower = max(0.0, point_estimate - margin)
        upper = min(1.0, point_estimate + margin)
        
        return ConfidenceInterval(
            point_estimate=round(point_estimate, 4),
            lower_bound=round(lower, 4),
            upper_bound=round(upper, 4),
            confidence_level=confidence_level,
            method="weighted_bayesian",
        )
    
    def _calculate_point_estimate(
        self,
        base_confidence: float,
        data_completeness: float,
        source_reliability: float,
    ) -> float:
        """
        Calculate point estimate of confidence using weighted average.
        
        The formula combines:
        - Base confidence (signal quality)
        - Data completeness (how much data we have)
        - Source reliability (historical accuracy)
        """
        estimate = (
            self.WEIGHTS["base"] * base_confidence +
            self.WEIGHTS["completeness"] * data_completeness +
            self.WEIGHTS["reliability"] * source_reliability
        )
        
        return min(1.0, max(0.0, estimate))
    
    def _calculate_uncertainty(
        self,
        data_completeness: float,
        source_reliability: float,
        sample_size: Optional[int],
    ) -> float:
        """
        Calculate uncertainty (standard error approximation).
        
        Higher uncertainty when:
        - Data is incomplete
        - Source is less reliable
        - Sample size is small
        """
        # Base uncertainty
        base_uncertainty = 0.05
        
        # Increase uncertainty for incomplete data
        if data_completeness < 1.0:
            completeness_penalty = (1.0 - data_completeness) * 0.10
            base_uncertainty += completeness_penalty
        
        # Increase uncertainty for less reliable sources
        if source_reliability < 0.9:
            reliability_penalty = (0.9 - source_reliability) * 0.10
            base_uncertainty += reliability_penalty
        
        # Statistical adjustment for sample size (if provided)
        if sample_size and sample_size > 0:
            # Standard error decreases with sqrt(n)
            # This follows the Central Limit Theorem
            base_uncertainty /= math.sqrt(sample_size)
        
        # Cap uncertainty at reasonable maximum
        return min(0.25, base_uncertainty)
    
    def _get_z_score(self, confidence_level: float) -> float:
        """Get z-score for given confidence level."""
        return self.Z_SCORES.get(confidence_level, 1.960)
    
    def calculate_combined_confidence(
        self,
        intervals: list[ConfidenceInterval],
    ) -> ConfidenceInterval:
        """
        Combine multiple confidence intervals into one.
        
        Uses inverse-variance weighting to give more weight to
        more precise estimates.
        
        Args:
            intervals: List of ConfidenceInterval objects
        
        Returns:
            Combined ConfidenceInterval
        """
        if not intervals:
            return ConfidenceInterval(
                point_estimate=0.5,
                lower_bound=0.0,
                upper_bound=1.0,
                confidence_level=0.95,
                method="default",
            )
        
        if len(intervals) == 1:
            return intervals[0]
        
        # Calculate weights (inverse variance)
        weights = []
        for interval in intervals:
            width = interval.width
            if width > 0:
                # Weight by inverse of width squared (proxy for variance)
                weights.append(1.0 / (width ** 2))
            else:
                weights.append(100.0)  # High weight for very precise estimates
        
        total_weight = sum(weights)
        
        # Weighted average of point estimates
        combined_estimate = sum(
            w * interval.point_estimate
            for w, interval in zip(weights, intervals)
        ) / total_weight
        
        # Combined standard error (using inverse variance formula)
        combined_variance = 1.0 / total_weight
        combined_se = math.sqrt(combined_variance)
        
        # Calculate bounds
        z_score = 1.960  # 95% CI
        margin = z_score * combined_se
        
        return ConfidenceInterval(
            point_estimate=round(combined_estimate, 4),
            lower_bound=round(max(0.0, combined_estimate - margin), 4),
            upper_bound=round(min(1.0, combined_estimate + margin), 4),
            confidence_level=0.95,
            method="inverse_variance_weighted",
        )
    
    def adjust_for_conflicts(
        self,
        interval: ConfidenceInterval,
        conflict_severity: str,
    ) -> ConfidenceInterval:
        """
        Adjust confidence interval based on detected conflicts.
        
        Conflicts between sources widen the confidence interval
        and may lower the point estimate.
        
        Args:
            interval: Original confidence interval
            conflict_severity: "none", "low", "medium", or "high"
        
        Returns:
            Adjusted ConfidenceInterval
        """
        adjustments = {
            "none": (0.0, 1.0),      # No change
            "low": (-0.03, 1.1),     # Small reduction, slightly wider
            "medium": (-0.08, 1.3),  # Moderate reduction, wider
            "high": (-0.15, 1.5),    # Significant reduction, much wider
        }
        
        point_adj, width_mult = adjustments.get(conflict_severity, (0.0, 1.0))
        
        # Adjust point estimate
        new_estimate = max(0.1, min(1.0, interval.point_estimate + point_adj))
        
        # Widen interval
        current_width = interval.width
        new_width = current_width * width_mult
        
        # Recalculate bounds
        new_lower = max(0.0, new_estimate - new_width / 2)
        new_upper = min(1.0, new_estimate + new_width / 2)
        
        return ConfidenceInterval(
            point_estimate=round(new_estimate, 4),
            lower_bound=round(new_lower, 4),
            upper_bound=round(new_upper, 4),
            confidence_level=interval.confidence_level,
            method=f"{interval.method}_conflict_adjusted",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_calculator: Optional[EnhancedConfidenceCalculator] = None


def get_confidence_calculator() -> EnhancedConfidenceCalculator:
    """Get or create the global confidence calculator."""
    global _calculator
    if _calculator is None:
        _calculator = EnhancedConfidenceCalculator()
    return _calculator


def calculate_confidence_interval(
    base_confidence: float,
    data_completeness: float = 1.0,
    source_reliability: float = 0.9,
    sample_size: Optional[int] = None,
) -> ConfidenceInterval:
    """
    Quick function to calculate confidence with interval.
    
    Args:
        base_confidence: Base confidence from signal quality
        data_completeness: Fraction of expected data present
        source_reliability: Historical reliability of source
        sample_size: Number of data points
    
    Returns:
        ConfidenceInterval object
    """
    calculator = get_confidence_calculator()
    return calculator.calculate_confidence_with_interval(
        base_confidence=base_confidence,
        data_completeness=data_completeness,
        source_reliability=source_reliability,
        sample_size=sample_size,
    )
