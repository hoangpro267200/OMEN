"""
Tests for Partner Signal Engine - Logistics Signal Monitor.

Tests the LogisticsSignalMonitor class and signal generation logic.

NOTE: The module has been refactored from "risk assessment" to "signal generation".
Risk decisions are now made by downstream systems (RiskCast), not OMEN.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import json

# Try to import pandas, skip if not available
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from omen.adapters.inbound.partner_risk.monitor import (
    LogisticsSignalMonitor,
    RiskLevel,
    PartnerRiskAssessment,
    LOGISTICS_COMPANIES,
    PartnerSignalCalculator,
    EvidenceBuilder,
    ConfidenceCalculator,
)
from omen.adapters.inbound.partner_risk.models import (
    PartnerSignalMetrics,
    PartnerSignalConfidence,
    PartnerSignalResponse,
)

# Backward-compatible alias for tests
LogisticsFinancialMonitor = LogisticsSignalMonitor


class TestRiskLevel:
    """Test RiskLevel class (deprecated, backward compatibility only)."""
    
    def test_risk_levels_exist(self):
        """Verify all risk levels are defined."""
        assert RiskLevel.SAFE == "SAFE"
        assert RiskLevel.CAUTION == "CAUTION"
        assert RiskLevel.WARNING == "WARNING"
        assert RiskLevel.CRITICAL == "CRITICAL"
    
    def test_risk_level_ordering(self):
        """Verify risk levels as strings can be compared."""
        levels = [RiskLevel.SAFE, RiskLevel.CAUTION, RiskLevel.WARNING, RiskLevel.CRITICAL]
        assert len(levels) == 4
        # Just verify they exist as strings
        assert all(isinstance(level, str) for level in levels)


class TestPartnerRiskAssessment:
    """Test PartnerRiskAssessment dataclass (deprecated, backward compatibility only)."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        with pytest.warns(DeprecationWarning):
            assessment = PartnerRiskAssessment(
                symbol="HAH",
                company_name="Hai An Transport",
                price=42000.0,
                change_percent=-5.0,
                volume=1234567,
                pe_ratio=12.5,
                roe=15.0,
                risk_status=RiskLevel.WARNING,
                message="Test message",
                timestamp="2026-02-01T12:00:00Z",
            )
        
        result = assessment.to_dict()
        
        assert result["symbol"] == "HAH"
        assert result["company_name"] == "Hai An Transport"
        assert result["price"] == 42000.0
        assert result["change_percent"] == -5.0
        assert result["risk_status"] == "WARNING"
        assert result["message"] == "Test message"
    
    def test_to_dict_with_none_values(self):
        """Test conversion when some values are None."""
        with pytest.warns(DeprecationWarning):
            assessment = PartnerRiskAssessment(
                symbol="TEST",
                company_name="Test Company",
                price=None,
                change_percent=None,
                volume=None,
                pe_ratio=None,
                roe=None,
                risk_status=RiskLevel.CAUTION,
                message="Data unavailable",
                timestamp="2026-02-01T12:00:00Z",
            )
        
        result = assessment.to_dict()
        
        assert result["price"] is None
        assert result["change_percent"] is None
        assert result["risk_status"] == "CAUTION"


class TestLogisticsSignalMonitor:
    """Test LogisticsSignalMonitor class."""
    
    def test_default_symbols(self):
        """Test default symbols are set correctly."""
        monitor = LogisticsSignalMonitor()
        
        assert "GMD" in monitor.symbols
        assert "HAH" in monitor.symbols
        assert "VOS" in monitor.symbols
        assert "VSC" in monitor.symbols
        assert "PVT" in monitor.symbols
    
    def test_custom_symbols(self):
        """Test custom symbols can be provided."""
        custom_symbols = ["ABC", "XYZ"]
        monitor = LogisticsSignalMonitor(symbols=custom_symbols)
        
        assert monitor.symbols == custom_symbols
    
    def test_logistics_companies_metadata(self):
        """Test company metadata is complete."""
        for symbol in LogisticsSignalMonitor.DEFAULT_SYMBOLS:
            assert symbol in LOGISTICS_COMPANIES
            assert "name" in LOGISTICS_COMPANIES[symbol]
            assert "sector" in LOGISTICS_COMPANIES[symbol]


class TestPartnerSignalCalculator:
    """Test PartnerSignalCalculator class."""
    
    @pytest.fixture
    def calculator(self):
        return PartnerSignalCalculator()
    
    def test_calculate_signals_with_full_data(self, calculator):
        """Test signal calculation with full data."""
        price_data = {
            "price": 50000.0,
            "change_percent": 2.5,
            "volume": 1000000,
            "open": 49000.0,
            "high": 51000.0,
            "low": 48500.0,
        }
        health_data = {
            "pe_ratio": 15.0,
            "roe": 18.0,
        }
        
        signals = calculator.calculate_signals(price_data, health_data)
        
        assert signals.price_current == 50000.0
        assert signals.price_change_percent == 2.5
        assert signals.volume == 1000000
        assert signals.pe_ratio == 15.0
        assert signals.roe == 18.0
    
    def test_calculate_signals_with_missing_data(self, calculator):
        """Test signal calculation with missing data."""
        price_data = {"price": None, "volume": None}
        health_data = {}
        
        signals = calculator.calculate_signals(price_data, health_data)
        
        assert signals.price_current is None
        assert signals.volume is None
        assert signals.pe_ratio is None
    
    def test_volatility_calculation(self, calculator):
        """Test volatility calculation."""
        prices = [100, 102, 101, 103, 102, 104, 103, 105, 104, 106,
                  105, 107, 106, 108, 107, 109, 108, 110, 109, 111]
        
        volatility = calculator._calculate_volatility(prices)
        
        assert volatility > 0
        assert volatility < 0.5  # Reasonable volatility range
    
    def test_liquidity_score_calculation(self, calculator):
        """Test liquidity score calculation."""
        historical = [1000000, 1100000, 900000, 1050000]
        
        score = calculator._calculate_liquidity_score(1200000, historical)
        
        assert 0 <= score <= 1
    
    def test_liquidity_score_with_no_data(self, calculator):
        """Test liquidity score with no historical data."""
        score = calculator._calculate_liquidity_score(None, None)
        assert score == 0.5  # Default score


class TestEvidenceBuilder:
    """Test EvidenceBuilder class."""
    
    @pytest.fixture
    def builder(self):
        return EvidenceBuilder()
    
    def test_build_evidence_with_price_change(self, builder):
        """Test evidence building for price change."""
        signals = PartnerSignalMetrics(
            price_current=50000.0,
            price_change_percent=-5.0,
            volume=1000000,
            liquidity_score=0.8,
        )
        
        evidence = builder.build_evidence("HAH", signals)
        
        assert len(evidence) >= 1
        price_evidence = [e for e in evidence if e.evidence_type == "PRICE_CHANGE"]
        assert len(price_evidence) == 1
        assert "HAH" in price_evidence[0].evidence_id
    
    def test_build_evidence_with_volume_anomaly(self, builder):
        """Test evidence building for volume anomaly."""
        signals = PartnerSignalMetrics(
            price_current=50000.0,
            price_change_percent=0.5,
            volume=1000000,
            volume_anomaly_zscore=3.5,
            liquidity_score=0.8,
        )
        
        evidence = builder.build_evidence("GMD", signals)
        
        volume_evidence = [e for e in evidence if e.evidence_type == "VOLUME_ANOMALY"]
        assert len(volume_evidence) == 1
    
    def test_no_evidence_for_normal_signals(self, builder):
        """Test no evidence generated for normal signals."""
        signals = PartnerSignalMetrics(
            price_current=50000.0,
            price_change_percent=0.2,  # Small change
            volume=1000000,
            volume_anomaly_zscore=0.5,  # Normal
            volatility_20d=0.02,  # Normal
            roe=15.0,  # Good ROE
            pe_ratio=15.0,  # Normal PE
            liquidity_score=0.8,
        )
        
        evidence = builder.build_evidence("VOS", signals)
        
        assert len(evidence) == 0


class TestConfidenceCalculator:
    """Test ConfidenceCalculator class."""
    
    @pytest.fixture
    def calculator(self):
        return ConfidenceCalculator()
    
    def test_calculate_confidence_full_data(self, calculator):
        """Test confidence calculation with full data."""
        signals = PartnerSignalMetrics(
            price_current=50000.0,
            price_change_percent=2.5,
            volume=1000000,
            pe_ratio=15.0,
            roe=18.0,
            volatility_20d=0.02,
            liquidity_score=0.8,
        )
        
        confidence = calculator.calculate_confidence(
            signals=signals,
            data_timestamp=datetime.now(timezone.utc),
        )
        
        assert confidence.overall_confidence > 0.5
        assert confidence.data_completeness == 1.0
        assert confidence.price_data_confidence == 1.0
        assert confidence.fundamental_data_confidence == 1.0
        assert len(confidence.missing_fields) == 0
    
    def test_calculate_confidence_missing_data(self, calculator):
        """Test confidence calculation with missing data."""
        signals = PartnerSignalMetrics(
            price_current=None,
            price_change_percent=None,
            volume=None,
            liquidity_score=0.5,
        )
        
        confidence = calculator.calculate_confidence(
            signals=signals,
            data_timestamp=datetime.now(timezone.utc),
        )
        
        assert confidence.overall_confidence < 0.5
        assert confidence.data_completeness < 1.0
        assert confidence.price_data_confidence == 0.0
        assert "price_current" in confidence.missing_fields


class TestJSONSafety:
    """Test JSON serialization safety."""
    
    def test_to_dict_is_json_safe(self):
        """Test that to_dict output is JSON serializable."""
        with pytest.warns(DeprecationWarning):
            assessment = PartnerRiskAssessment(
                symbol="HAH",
                company_name="Hai An Transport",
                price=42000.0,
                change_percent=-5.0,
                volume=1234567,
                pe_ratio=12.5,
                roe=15.0,
                risk_status=RiskLevel.WARNING,
                message="Test message with Vietnamese: Cảnh báo",
                timestamp="2026-02-01T12:00:00Z",
            )
        
        result = assessment.to_dict()
        
        # Should not raise
        json_str = json.dumps(result, ensure_ascii=False)
        assert json_str is not None
        
        # Verify round-trip
        parsed = json.loads(json_str)
        assert parsed["symbol"] == "HAH"
        assert parsed["risk_status"] == "WARNING"
    
    def test_partner_signal_metrics_serialization(self):
        """Test PartnerSignalMetrics is JSON serializable."""
        signals = PartnerSignalMetrics(
            price_current=50000.0,
            price_change_percent=2.5,
            volume=1000000,
            liquidity_score=0.8,
        )
        
        # Should not raise
        json_str = signals.model_dump_json()
        assert json_str is not None
        
        parsed = json.loads(json_str)
        assert parsed["price_current"] == 50000.0
