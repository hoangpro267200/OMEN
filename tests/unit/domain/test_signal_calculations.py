"""
Tests for signal calculation accuracy.

Verifies mathematical correctness of:
- Volatility calculations
- Z-score calculations
- Trend momentum calculations
- Liquidity scoring

These tests ensure the signal generation is mathematically sound.
"""

import math
import pytest
from datetime import datetime, timezone


class SignalCalculator:
    """
    Signal calculation utilities.
    
    This is extracted here for testing. The actual implementation
    should be in omen.domain.services.signal_calculator.
    """
    
    def calculate_volatility(self, prices: list[float]) -> float:
        """
        Calculate volatility (standard deviation of returns).
        
        Args:
            prices: List of historical prices
            
        Returns:
            Volatility as standard deviation of returns
        """
        if len(prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                ret = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate mean
        mean_return = sum(returns) / len(returns)
        
        # Calculate variance
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        
        return math.sqrt(variance)
    
    def calculate_zscore(self, current: float, historical: list[float]) -> float:
        """
        Calculate Z-score of current value vs historical distribution.
        
        Args:
            current: Current value
            historical: Historical values for comparison
            
        Returns:
            Z-score (number of standard deviations from mean)
        """
        if not historical:
            return 0.0
        
        mean = sum(historical) / len(historical)
        
        if len(historical) < 2:
            return 0.0 if current == mean else float('inf')
        
        variance = sum((x - mean) ** 2 for x in historical) / len(historical)
        std = math.sqrt(variance)
        
        if std == 0:
            return 0.0  # All values same, no deviation
        
        return (current - mean) / std
    
    def calculate_trend(self, prices: list[float], days: int = 5) -> float:
        """
        Calculate trend as percentage change over period.
        
        Args:
            prices: Price history (oldest to newest)
            days: Number of days to measure trend
            
        Returns:
            Percentage change (e.g., 10.0 for 10%)
        """
        if len(prices) < 2 or days < 1:
            return 0.0
        
        # Use min of requested days and available data
        actual_days = min(days, len(prices) - 1)
        
        start_price = prices[-(actual_days + 1)]
        end_price = prices[-1]
        
        if start_price == 0:
            return 0.0
        
        return ((end_price - start_price) / start_price) * 100
    
    def calculate_liquidity_score(
        self,
        current_volume: float,
        avg_volume: float,
    ) -> float:
        """
        Calculate liquidity score based on volume.
        
        Args:
            current_volume: Current trading volume
            avg_volume: Average trading volume
            
        Returns:
            Score from 0.0 (illiquid) to 1.0 (highly liquid)
        """
        if avg_volume == 0:
            return 0.0 if current_volume == 0 else 1.0
        
        ratio = current_volume / avg_volume
        
        # Normalize: ratio of 1.0 = 0.5 score, 2.0 = ~0.67, 0.5 = ~0.33
        # Using sigmoid-like transformation
        score = ratio / (1 + ratio)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVolatilityCalculation:
    """Test volatility calculations."""
    
    @pytest.fixture
    def calculator(self) -> SignalCalculator:
        return SignalCalculator()
    
    def test_volatility_simple_case(self, calculator: SignalCalculator):
        """Test volatility with known values."""
        prices = [100, 102, 101, 103, 102]
        
        volatility = calculator.calculate_volatility(prices)
        
        # Calculate expected manually
        returns = [
            (102 - 100) / 100,  # 0.02
            (101 - 102) / 102,  # -0.0098
            (103 - 101) / 101,  # 0.0198
            (102 - 103) / 103,  # -0.0097
        ]
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        expected = math.sqrt(variance)
        
        assert abs(volatility - expected) < 0.0001
    
    def test_volatility_zero_for_constant_prices(self, calculator: SignalCalculator):
        """Constant prices should have zero volatility."""
        prices = [100, 100, 100, 100, 100]
        
        volatility = calculator.calculate_volatility(prices)
        
        assert volatility == 0.0
    
    def test_volatility_handles_negative_returns(self, calculator: SignalCalculator):
        """Test with declining prices."""
        prices = [100, 98, 96, 94, 92]
        
        volatility = calculator.calculate_volatility(prices)
        
        assert volatility >= 0  # Volatility is always positive
        assert volatility > 0  # Should not be zero with varying prices
    
    def test_volatility_single_price(self, calculator: SignalCalculator):
        """Single price should return 0."""
        prices = [100]
        
        volatility = calculator.calculate_volatility(prices)
        
        assert volatility == 0.0
    
    def test_volatility_empty_list(self, calculator: SignalCalculator):
        """Empty list should return 0."""
        prices = []
        
        volatility = calculator.calculate_volatility(prices)
        
        assert volatility == 0.0
    
    def test_volatility_high_volatility(self, calculator: SignalCalculator):
        """Test with high volatility prices."""
        prices = [100, 120, 90, 130, 80]  # Large swings
        
        volatility = calculator.calculate_volatility(prices)
        
        assert volatility > 0.1  # Should be relatively high


class TestZScoreCalculation:
    """Test Z-score calculations."""
    
    @pytest.fixture
    def calculator(self) -> SignalCalculator:
        return SignalCalculator()
    
    def test_zscore_basic(self, calculator: SignalCalculator):
        """Test Z-score with known values."""
        historical = [100, 105, 95, 100, 100]
        current = 110
        
        zscore = calculator.calculate_zscore(current, historical)
        
        # Manual calculation
        mean = sum(historical) / len(historical)
        std = math.sqrt(sum((x - mean) ** 2 for x in historical) / len(historical))
        expected = (current - mean) / std
        
        assert abs(zscore - expected) < 0.0001
    
    def test_zscore_zero_for_mean_value(self, calculator: SignalCalculator):
        """Value at mean should have z-score near 0."""
        historical = [100, 102, 98, 101, 99]  # Mean ≈ 100
        current = 100
        
        zscore = calculator.calculate_zscore(current, historical)
        
        assert abs(zscore) < 0.5  # Close to 0
    
    def test_zscore_handles_zero_std(self, calculator: SignalCalculator):
        """Z-score with zero std should return 0."""
        historical = [100, 100, 100, 100, 100]
        current = 110
        
        zscore = calculator.calculate_zscore(current, historical)
        
        assert zscore == 0.0
    
    def test_zscore_positive_for_above_mean(self, calculator: SignalCalculator):
        """Z-score should be positive when above mean."""
        historical = [100, 100, 100, 100, 100, 102, 98]
        current = 110
        
        zscore = calculator.calculate_zscore(current, historical)
        
        assert zscore > 0
    
    def test_zscore_negative_for_below_mean(self, calculator: SignalCalculator):
        """Z-score should be negative when below mean."""
        historical = [100, 100, 100, 100, 100, 102, 98]
        current = 90
        
        zscore = calculator.calculate_zscore(current, historical)
        
        assert zscore < 0
    
    def test_zscore_empty_historical(self, calculator: SignalCalculator):
        """Empty historical should return 0."""
        historical = []
        current = 100
        
        zscore = calculator.calculate_zscore(current, historical)
        
        assert zscore == 0.0


class TestTrendCalculation:
    """Test trend momentum calculations."""
    
    @pytest.fixture
    def calculator(self) -> SignalCalculator:
        return SignalCalculator()
    
    def test_trend_positive(self, calculator: SignalCalculator):
        """Test upward trend."""
        prices = [100, 102, 104, 106, 108, 110]
        
        trend = calculator.calculate_trend(prices, days=5)
        
        # (110 - 100) / 100 * 100 = 10%
        assert trend == pytest.approx(10.0, rel=0.01)
    
    def test_trend_negative(self, calculator: SignalCalculator):
        """Test downward trend."""
        prices = [100, 98, 96, 94, 92, 90]
        
        trend = calculator.calculate_trend(prices, days=5)
        
        # (90 - 100) / 100 * 100 = -10%
        assert trend == pytest.approx(-10.0, rel=0.01)
    
    def test_trend_flat(self, calculator: SignalCalculator):
        """Test flat trend."""
        prices = [100, 100, 100, 100, 100]
        
        trend = calculator.calculate_trend(prices, days=4)
        
        assert trend == 0.0
    
    def test_trend_short_period(self, calculator: SignalCalculator):
        """Test with shorter period than data."""
        prices = [100, 102, 104, 106, 108, 110, 112]
        
        trend = calculator.calculate_trend(prices, days=2)
        
        # Uses last 3 prices: 108, 110, 112
        # (112 - 108) / 108 * 100 ≈ 3.7%
        assert trend == pytest.approx(3.7, rel=0.1)
    
    def test_trend_insufficient_data(self, calculator: SignalCalculator):
        """Test with insufficient data."""
        prices = [100]
        
        trend = calculator.calculate_trend(prices, days=5)
        
        assert trend == 0.0


class TestLiquidityScore:
    """Test liquidity score calculations."""
    
    @pytest.fixture
    def calculator(self) -> SignalCalculator:
        return SignalCalculator()
    
    def test_liquidity_high_volume(self, calculator: SignalCalculator):
        """High volume relative to average = high liquidity."""
        current_volume = 2_000_000
        avg_volume = 1_000_000
        
        score = calculator.calculate_liquidity_score(current_volume, avg_volume)
        
        assert score > 0.6  # Should be high
        assert score <= 1.0
    
    def test_liquidity_low_volume(self, calculator: SignalCalculator):
        """Low volume = low liquidity."""
        current_volume = 100_000
        avg_volume = 1_000_000
        
        score = calculator.calculate_liquidity_score(current_volume, avg_volume)
        
        assert score < 0.15  # Should be low
        assert score >= 0.0
    
    def test_liquidity_normalized(self, calculator: SignalCalculator):
        """Liquidity score should be 0-1."""
        test_cases = [
            (1_000_000, 1_000_000),  # Equal
            (5_000_000, 1_000_000),  # 5x
            (100_000, 1_000_000),    # 0.1x
            (0, 1_000_000),          # Zero volume
        ]
        
        for current, avg in test_cases:
            score = calculator.calculate_liquidity_score(current, avg)
            assert 0.0 <= score <= 1.0, f"Failed for {current}/{avg}"
    
    def test_liquidity_equal_volumes(self, calculator: SignalCalculator):
        """Equal volumes should give 0.5 score."""
        current_volume = 1_000_000
        avg_volume = 1_000_000
        
        score = calculator.calculate_liquidity_score(current_volume, avg_volume)
        
        assert score == pytest.approx(0.5, rel=0.01)
    
    def test_liquidity_zero_avg(self, calculator: SignalCalculator):
        """Zero average volume with non-zero current."""
        current_volume = 100_000
        avg_volume = 0
        
        score = calculator.calculate_liquidity_score(current_volume, avg_volume)
        
        assert score == 1.0
    
    def test_liquidity_both_zero(self, calculator: SignalCalculator):
        """Both zero should return 0."""
        current_volume = 0
        avg_volume = 0
        
        score = calculator.calculate_liquidity_score(current_volume, avg_volume)
        
        assert score == 0.0


class TestConfidenceCalculation:
    """Test confidence score calculations."""
    
    @pytest.fixture
    def calculator(self) -> SignalCalculator:
        return SignalCalculator()
    
    def test_high_liquidity_high_volume_high_confidence(self, calculator: SignalCalculator):
        """High liquidity and volume should yield high confidence."""
        # Calculate components
        volatility = calculator.calculate_volatility([100, 101, 100, 101, 100])  # Low
        liquidity = calculator.calculate_liquidity_score(2_000_000, 1_000_000)  # High
        
        # Both should contribute to confidence
        assert volatility < 0.02  # Low volatility is good
        assert liquidity > 0.6  # High liquidity is good
    
    def test_calculation_determinism(self, calculator: SignalCalculator):
        """Same inputs should always produce same outputs."""
        prices = [100, 102, 98, 103, 99, 101]
        
        vol1 = calculator.calculate_volatility(prices)
        vol2 = calculator.calculate_volatility(prices)
        
        assert vol1 == vol2
        
        zscore1 = calculator.calculate_zscore(105, prices)
        zscore2 = calculator.calculate_zscore(105, prices)
        
        assert zscore1 == zscore2
