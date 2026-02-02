"""
Partner Signal Engine - Vietnamese Logistics Financial Monitor.

Monitors Vietnamese logistics companies and emits SIGNALS (not decisions).
This is a PURE SIGNAL ENGINE - it does NOT classify risk.

OMEN provides:
- Raw metrics (price, volume, fundamentals)
- Evidence trail
- Confidence scores
- Market context

OMEN does NOT provide:
- Risk verdicts (SAFE/WARNING/CRITICAL)
- Risk status
- Overall risk assessment

Risk decisions are made by RiskCast based on:
- Order context
- User risk appetite
- Business rules
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    PartnerSignalMetrics,
    PartnerSignalConfidence,
    PartnerSignalEvidence,
    PartnerSignalResponse,
    PartnerSignalsListResponse,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DEPRECATED CLASSES - For backward compatibility only
# ═══════════════════════════════════════════════════════════════════════════════


class RiskLevel:
    """
    ⚠️ DEPRECATED - Risk levels should be determined by RiskCast, not OMEN.

    This class exists ONLY for backward compatibility.
    New code should NOT use risk levels - OMEN is a Signal Engine.
    """

    SAFE = "SAFE"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class PartnerRiskAssessment(BaseModel):
    """
    ⚠️ DEPRECATED - Use PartnerSignalResponse instead.

    This class exists ONLY for backward compatibility.
    Risk assessment should be done by RiskCast, not OMEN.

    Migration:
        - Use LogisticsSignalMonitor.get_partner_signals() instead
        - This returns PartnerSignalResponse with metrics, evidence, confidence
        - Risk decisions should be made by RiskCast based on context
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    company_name: str
    price: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    pe_ratio: Optional[float] = None
    roe: Optional[float] = None
    risk_status: str = Field(default="CAUTION")  # DEPRECATED field
    message: str = ""
    timestamp: str = ""

    def __init__(self, **data):
        import warnings

        warnings.warn(
            "PartnerRiskAssessment is deprecated. Use PartnerSignalResponse instead. "
            "Risk decisions should be made by RiskCast, not OMEN.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (deprecated)."""
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "price": self.price,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "pe_ratio": self.pe_ratio,
            "roe": self.roe,
            "risk_status": self.risk_status,
            "message": self.message,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANY METADATA
# ═══════════════════════════════════════════════════════════════════════════════

# Company metadata for Vietnamese logistics tickers
LOGISTICS_COMPANIES = {
    "GMD": {
        "name": "Gemadept Corporation",
        "sector": "Port Operator",
        "exchange": "HOSE",
        "description": "Largest private port operator in Vietnam",
    },
    "HAH": {
        "name": "Hai An Transport & Stevedoring",
        "sector": "Shipping Line",
        "exchange": "HOSE",
        "description": "Container shipping and stevedoring services",
    },
    "VOS": {
        "name": "Vietnam Ocean Shipping",
        "sector": "Shipping Line",
        "exchange": "HOSE",
        "description": "Ocean shipping and logistics services",
    },
    "VSC": {
        "name": "Vietnam Container Shipping",
        "sector": "Container Shipping",
        "exchange": "HOSE",
        "description": "Container transportation services",
    },
    "PVT": {
        "name": "PetroVietnam Transportation",
        "sector": "Tanker Fleet",
        "exchange": "HOSE",
        "description": "Oil and gas transportation services",
    },
}


class PartnerSignalCalculator:
    """
    Calculate signal metrics from raw market data.
    Does NOT make risk decisions - only calculates metrics.
    """

    def __init__(self):
        self.volatility_window = 20
        self.volume_window = 20

    def calculate_signals(
        self,
        price_data: dict[str, Any],
        health_data: dict[str, Any],
        historical_prices: Optional[list[float]] = None,
        historical_volumes: Optional[list[int]] = None,
    ) -> PartnerSignalMetrics:
        """
        Calculate signal metrics from raw data.

        Returns:
            PartnerSignalMetrics - normalized metrics, NO verdict
        """
        # Price signals
        price = price_data.get("price")
        change_pct = price_data.get("change_percent")
        volume = price_data.get("volume")

        # Volume signals
        volume_ratio = None
        volume_zscore = None
        volume_avg = None
        if historical_volumes and len(historical_volumes) > 0:
            volume_avg = sum(historical_volumes) / len(historical_volumes)
            if volume_avg > 0 and volume:
                volume_ratio = volume / volume_avg
            if volume:
                volume_zscore = self._calculate_zscore(
                    float(volume), [float(v) for v in historical_volumes]
                )

        # Volatility signals
        volatility = None
        volatility_percentile = None
        if historical_prices and len(historical_prices) >= self.volatility_window:
            volatility = self._calculate_volatility(historical_prices)
            volatility_percentile = self._calculate_volatility_percentile(volatility)

        # Trend signals
        trend_7d = self._calculate_trend(historical_prices, 7) if historical_prices else None
        trend_30d = self._calculate_trend(historical_prices, 30) if historical_prices else None

        # Liquidity score
        liquidity = self._calculate_liquidity_score(volume, historical_volumes)

        return PartnerSignalMetrics(
            price_current=price,
            price_open=price_data.get("open"),
            price_high=price_data.get("high"),
            price_low=price_data.get("low"),
            price_close_previous=price_data.get("previous_close"),
            price_change_percent=change_pct,
            price_change_absolute=price_data.get("change"),
            volume=volume,
            volume_avg_20d=volume_avg,
            volume_ratio=volume_ratio,
            volume_anomaly_zscore=volume_zscore,
            volatility_20d=volatility,
            volatility_percentile=volatility_percentile,
            trend_1d=change_pct,
            trend_7d=trend_7d,
            trend_30d=trend_30d,
            pe_ratio=health_data.get("pe_ratio"),
            pb_ratio=health_data.get("pb_ratio"),
            roe=health_data.get("roe"),
            roa=health_data.get("roa"),
            debt_to_equity=health_data.get("debt_to_equity"),
            current_ratio=health_data.get("current_ratio"),
            liquidity_score=liquidity,
        )

    def _calculate_volatility(self, prices: list[float]) -> float:
        """Standard deviation of returns."""
        if len(prices) < 2:
            return 0.0
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                returns.append((prices[i] - prices[i - 1]) / prices[i - 1])
        if not returns:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return variance**0.5

    def _calculate_volatility_percentile(self, volatility: float) -> float:
        """Calculate volatility percentile (simplified)."""
        # Typical stock volatility ranges: 0.01 (1%) to 0.10 (10%)
        # Normalize to 0-1 percentile
        return min(1.0, max(0.0, volatility / 0.05))

    def _calculate_zscore(self, value: float, historical: list[float]) -> float:
        """Z-score calculation."""
        if not historical:
            return 0.0
        mean = sum(historical) / len(historical)
        variance = sum((x - mean) ** 2 for x in historical) / len(historical)
        std = variance**0.5
        if std == 0:
            return 0.0
        return (value - mean) / std

    def _calculate_liquidity_score(
        self, volume: Optional[int], historical_volumes: Optional[list[int]]
    ) -> float:
        """
        Liquidity score 0-1.
        Based on: volume ratio, trading frequency
        """
        if volume is None:
            return 0.5  # Default score

        score = 0.5  # Base score

        if historical_volumes and len(historical_volumes) > 0:
            avg_vol = sum(historical_volumes) / len(historical_volumes)
            if avg_vol > 0:
                ratio = volume / avg_vol
                # Higher volume = better liquidity
                score = min(1.0, 0.3 + (ratio * 0.35))

        return round(score, 3)

    def _calculate_trend(self, prices: Optional[list[float]], days: int) -> Optional[float]:
        """Calculate % change over N days."""
        if not prices or len(prices) < days:
            return None
        if prices[-days] == 0:
            return None
        return round(((prices[-1] - prices[-days]) / prices[-days]) * 100, 2)


class EvidenceBuilder:
    """Build evidence trail for signals."""

    def build_evidence(
        self,
        symbol: str,
        signals: PartnerSignalMetrics,
        thresholds: Optional[dict] = None,
    ) -> list[PartnerSignalEvidence]:
        """Generate evidence list from signals."""
        evidence = []
        now = datetime.now(timezone.utc)

        # Price change evidence
        if signals.price_change_percent is not None and abs(signals.price_change_percent) > 0.5:
            direction = "increased" if signals.price_change_percent > 0 else "decreased"
            evidence.append(
                PartnerSignalEvidence(
                    evidence_id=f"{symbol}-PRICE-{now.strftime('%Y%m%d%H%M%S')}",
                    evidence_type="PRICE_CHANGE",
                    title=f"{symbol} price {direction} {abs(signals.price_change_percent):.2f}%",
                    description="Daily price movement detected",
                    raw_value=signals.price_change_percent,
                    normalized_value=min(1.0, abs(signals.price_change_percent) / 10),
                    threshold_reference=thresholds.get("price_change") if thresholds else None,
                    source="vnstock",
                    observed_at=now,
                )
            )

        # Volume anomaly evidence
        if signals.volume_anomaly_zscore is not None and abs(signals.volume_anomaly_zscore) > 2:
            evidence.append(
                PartnerSignalEvidence(
                    evidence_id=f"{symbol}-VOLUME-{now.strftime('%Y%m%d%H%M%S')}",
                    evidence_type="VOLUME_ANOMALY",
                    title=f"{symbol} volume anomaly (z-score: {signals.volume_anomaly_zscore:.2f})",
                    description="Unusual trading volume detected",
                    raw_value=signals.volume_anomaly_zscore,
                    normalized_value=min(1.0, abs(signals.volume_anomaly_zscore) / 5),
                    source="vnstock",
                    observed_at=now,
                )
            )

        # Volatility evidence
        if signals.volatility_20d is not None and signals.volatility_20d > 0.03:
            evidence.append(
                PartnerSignalEvidence(
                    evidence_id=f"{symbol}-VOLATILITY-{now.strftime('%Y%m%d%H%M%S')}",
                    evidence_type="HIGH_VOLATILITY",
                    title=f"{symbol} elevated volatility ({signals.volatility_20d*100:.1f}%)",
                    description="20-day volatility above normal levels",
                    raw_value=signals.volatility_20d,
                    normalized_value=min(1.0, signals.volatility_20d / 0.1),
                    source="calculated",
                    observed_at=now,
                )
            )

        # Low ROE evidence
        if signals.roe is not None and signals.roe < 5.0:
            evidence.append(
                PartnerSignalEvidence(
                    evidence_id=f"{symbol}-ROE-{now.strftime('%Y%m%d%H%M%S')}",
                    evidence_type="LOW_PROFITABILITY",
                    title=f"{symbol} low ROE ({signals.roe:.1f}%)",
                    description="Return on equity below typical threshold",
                    raw_value=signals.roe,
                    normalized_value=max(0.0, min(1.0, 1.0 - (signals.roe / 10))),
                    source="vnstock",
                    observed_at=now,
                )
            )

        # High PE evidence
        if signals.pe_ratio is not None and signals.pe_ratio > 30:
            evidence.append(
                PartnerSignalEvidence(
                    evidence_id=f"{symbol}-PE-{now.strftime('%Y%m%d%H%M%S')}",
                    evidence_type="HIGH_VALUATION",
                    title=f"{symbol} high PE ratio ({signals.pe_ratio:.1f})",
                    description="Price-to-earnings ratio above typical range",
                    raw_value=signals.pe_ratio,
                    normalized_value=min(1.0, signals.pe_ratio / 50),
                    source="vnstock",
                    observed_at=now,
                )
            )

        return evidence


class ConfidenceCalculator:
    """Calculate confidence scores for signal data."""

    def calculate_confidence(
        self,
        signals: PartnerSignalMetrics,
        data_timestamp: datetime,
        data_source: str = "vnstock",
    ) -> PartnerSignalConfidence:
        """Calculate confidence based on data completeness and freshness."""

        # Calculate data completeness
        fields = [
            signals.price_current,
            signals.price_change_percent,
            signals.volume,
            signals.pe_ratio,
            signals.roe,
            signals.volatility_20d,
        ]
        non_null = sum(1 for f in fields if f is not None)
        completeness = non_null / len(fields)

        # Calculate freshness
        now = datetime.now(timezone.utc)
        if data_timestamp.tzinfo is None:
            data_timestamp = data_timestamp.replace(tzinfo=timezone.utc)
        freshness_seconds = int((now - data_timestamp).total_seconds())

        # Missing fields
        missing = []
        if signals.price_current is None:
            missing.append("price_current")
        if signals.pe_ratio is None:
            missing.append("pe_ratio")
        if signals.roe is None:
            missing.append("roe")
        if signals.volatility_20d is None:
            missing.append("volatility_20d")

        # Calculate confidence scores
        price_confidence = 1.0 if signals.price_current is not None else 0.0
        fundamental_confidence = (
            1.0
            if (signals.pe_ratio is not None and signals.roe is not None)
            else 0.5 if (signals.pe_ratio is not None or signals.roe is not None) else 0.0
        )
        volume_confidence = 1.0 if signals.volume is not None else 0.0

        # Overall confidence
        overall = (
            price_confidence * 0.4
            + fundamental_confidence * 0.3
            + volume_confidence * 0.2
            + completeness * 0.1
        )

        # Reduce confidence for stale data
        if freshness_seconds > 3600:  # > 1 hour
            overall *= 0.8
        if freshness_seconds > 86400:  # > 1 day
            overall *= 0.7

        return PartnerSignalConfidence(
            overall_confidence=round(overall, 3),
            data_completeness=round(completeness, 3),
            data_freshness_seconds=freshness_seconds,
            price_data_confidence=price_confidence,
            fundamental_data_confidence=fundamental_confidence,
            volume_data_confidence=volume_confidence,
            missing_fields=missing,
            data_source=data_source,
            data_source_reliability=0.85,  # vnstock reliability estimate
        )


class LogisticsSignalMonitor:
    """
    Monitor Vietnamese logistics companies and emit SIGNALS.

    This is a PURE SIGNAL ENGINE:
    - Fetches real-time price data
    - Gets fundamental health indicators
    - Calculates signal metrics
    - Builds evidence trail

    This does NOT:
    - Classify risk levels (SAFE/WARNING/CRITICAL)
    - Make risk decisions
    - Provide risk verdicts

    Risk decisions are RiskCast's responsibility.

    Example:
        monitor = LogisticsSignalMonitor()
        signal = monitor.get_partner_signals("HAH")
        # signal contains metrics, evidence, confidence - NO verdict
    """

    DEFAULT_SYMBOLS = ["GMD", "HAH", "VOS", "VSC", "PVT"]

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        timeout_seconds: float = 30.0,
    ):
        self.symbols = symbols or self.DEFAULT_SYMBOLS
        self.timeout_seconds = timeout_seconds
        self._vnstock = None
        self._calculator = PartnerSignalCalculator()
        self._evidence_builder = EvidenceBuilder()
        self._confidence_calculator = ConfidenceCalculator()

    def _get_vnstock(self):
        """Lazy load vnstock library."""
        if self._vnstock is None:
            try:
                from vnstock import Vnstock

                self._vnstock = Vnstock
                logger.info("vnstock library loaded successfully")
            except ImportError:
                logger.error("vnstock not installed. Run: pip install vnstock")
                raise ImportError("vnstock library is required. Install with: pip install vnstock")
        return self._vnstock

    def _get_stock(self, symbol: str):
        """Get vnstock stock object for a symbol."""
        Vnstock = self._get_vnstock()
        try:
            return Vnstock().stock(symbol=symbol, source="VCI")
        except Exception as e:
            logger.warning(f"Failed to create stock object for {symbol} with VCI: {e}")
            try:
                return Vnstock().stock(symbol=symbol, source="TCBS")
            except Exception as e2:
                logger.warning(f"Failed with TCBS: {e2}")
                raise

    def _generate_signal_id(self, symbol: str, timestamp: datetime) -> str:
        """Generate unique signal ID."""
        data = f"{symbol}:{timestamp.isoformat()}"
        return f"PS-{hashlib.sha256(data.encode()).hexdigest()[:12]}"

    def fetch_price_data(self, symbol: str) -> dict[str, Any]:
        """Fetch the latest price data."""
        try:
            stock = self._get_stock(symbol)

            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

            history = stock.quote.history(start=start_date, end=end_date)

            if history is None or history.empty:
                logger.warning(f"No price data available for {symbol}")
                return {
                    "symbol": symbol,
                    "price": None,
                    "change": None,
                    "change_percent": None,
                    "volume": None,
                    "timestamp": datetime.now(timezone.utc),
                    "error": "No data available",
                }

            latest = history.iloc[-1]
            previous = history.iloc[-2] if len(history) > 1 else latest

            price = float(latest.get("close", 0))
            prev_close = float(previous.get("close", price))
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            volume = int(latest.get("volume", 0))

            return {
                "symbol": symbol,
                "price": price,
                "open": float(latest.get("open", 0)),
                "high": float(latest.get("high", 0)),
                "low": float(latest.get("low", 0)),
                "previous_close": prev_close,
                "change": change,
                "change_percent": round(change_percent, 2),
                "volume": volume,
                "timestamp": datetime.now(timezone.utc),
            }

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return {
                "symbol": symbol,
                "price": None,
                "change": None,
                "change_percent": None,
                "volume": None,
                "timestamp": datetime.now(timezone.utc),
                "error": str(e),
            }

    def fetch_health_indicators(self, symbol: str) -> dict[str, Any]:
        """Fetch fundamental ratios (PE, ROE)."""
        try:
            stock = self._get_stock(symbol)

            try:
                ratios = stock.finance.ratio(period="year", lang="en")

                if ratios is not None and not ratios.empty:
                    latest = ratios.iloc[-1] if len(ratios) > 0 else {}

                    return {
                        "symbol": symbol,
                        "pe_ratio": self._extract_ratio(latest, ["PE", "P/E", "priceToEarning"]),
                        "pb_ratio": self._extract_ratio(latest, ["PB", "P/B", "priceToBook"]),
                        "roe": self._extract_ratio(latest, ["ROE", "returnOnEquity"]),
                        "roa": self._extract_ratio(latest, ["ROA", "returnOnAsset"]),
                        "debt_to_equity": self._extract_ratio(latest, ["D/E", "debtToEquity"]),
                        "current_ratio": self._extract_ratio(latest, ["currentRatio"]),
                        "timestamp": datetime.now(timezone.utc),
                    }
            except Exception as ratio_error:
                logger.warning(f"Could not fetch ratios for {symbol}: {ratio_error}")

            return {
                "symbol": symbol,
                "pe_ratio": None,
                "pb_ratio": None,
                "roe": None,
                "roa": None,
                "debt_to_equity": None,
                "current_ratio": None,
                "timestamp": datetime.now(timezone.utc),
                "error": "Ratio data not available",
            }

        except Exception as e:
            logger.error(f"Error fetching health indicators for {symbol}: {e}")
            return {
                "symbol": symbol,
                "pe_ratio": None,
                "pb_ratio": None,
                "roe": None,
                "roa": None,
                "debt_to_equity": None,
                "current_ratio": None,
                "timestamp": datetime.now(timezone.utc),
                "error": str(e),
            }

    def _extract_ratio(self, data: Any, possible_keys: list[str]) -> Optional[float]:
        """Extract ratio value from data using possible key names."""
        if data is None:
            return None

        for key in possible_keys:
            try:
                if hasattr(data, "get"):
                    value = data.get(key)
                elif hasattr(data, key):
                    value = getattr(data, key)
                else:
                    continue

                if value is not None and not (isinstance(value, float) and value != value):
                    return float(value)
            except (KeyError, TypeError, ValueError):
                continue

        return None

    def get_partner_signals(self, symbol: str) -> PartnerSignalResponse:
        """
        Get signals for a logistics partner.

        Returns:
            PartnerSignalResponse with metrics, evidence, confidence - NO verdict
        """
        symbol = symbol.upper()
        company_info = LOGISTICS_COMPANIES.get(
            symbol,
            {
                "name": symbol,
                "sector": "Unknown",
                "exchange": "HOSE",
            },
        )

        # Fetch data
        price_data = self.fetch_price_data(symbol)
        health_data = self.fetch_health_indicators(symbol)

        now = datetime.now(timezone.utc)

        # Calculate signals
        signals = self._calculator.calculate_signals(
            price_data=price_data,
            health_data=health_data,
        )

        # Build evidence
        evidence = self._evidence_builder.build_evidence(symbol, signals)

        # Calculate confidence
        confidence = self._confidence_calculator.calculate_confidence(
            signals=signals,
            data_timestamp=now,
            data_source="vnstock",
        )

        # Generate suggestion (optional, with disclaimer)
        suggestion = self._generate_suggestion(signals)

        return PartnerSignalResponse(
            symbol=symbol,
            company_name=company_info.get("name", symbol),
            sector=company_info.get("sector", "logistics"),
            exchange=company_info.get("exchange", "HOSE"),
            signals=signals,
            confidence=confidence,
            evidence=evidence,
            market_context=None,  # Could add VNINDEX context here
            omen_suggestion=suggestion,
            suggestion_confidence=0.6 if suggestion else None,
            signal_id=self._generate_signal_id(symbol, now),
            timestamp=now,
        )

    def _generate_suggestion(self, signals: PartnerSignalMetrics) -> Optional[str]:
        """
        Generate a suggestion based on signals.
        This is NOT a decision - just a signal-based observation.
        """
        observations = []

        if signals.price_change_percent is not None:
            if signals.price_change_percent <= -7.0:
                observations.append(f"significant price drop ({signals.price_change_percent:.1f}%)")
            elif signals.price_change_percent <= -4.0:
                observations.append(f"notable price decline ({signals.price_change_percent:.1f}%)")

        if signals.roe is not None and signals.roe < 0:
            observations.append(f"negative ROE ({signals.roe:.1f}%)")

        if signals.volume_anomaly_zscore is not None and abs(signals.volume_anomaly_zscore) > 2:
            observations.append(f"unusual volume (z-score: {signals.volume_anomaly_zscore:.1f})")

        if not observations:
            return None

        return f"Signals indicate: {', '.join(observations)}. RiskCast should evaluate based on context."

    def get_all_signals(self) -> PartnerSignalsListResponse:
        """
        Get signals for all monitored logistics partners.

        Returns:
            PartnerSignalsListResponse with all partner signals - NO risk verdict
        """
        partners = []

        for symbol in self.symbols:
            try:
                signal = self.get_partner_signals(symbol)
                partners.append(signal)
            except Exception as e:
                logger.error(f"Error getting signals for {symbol}: {e}")

        # Calculate aggregated metrics (NO verdict)
        avg_volatility = None
        avg_liquidity = None
        volatilities = [
            p.signals.volatility_20d for p in partners if p.signals.volatility_20d is not None
        ]
        liquidities = [
            p.signals.liquidity_score for p in partners if p.signals.liquidity_score is not None
        ]

        if volatilities:
            avg_volatility = sum(volatilities) / len(volatilities)
        if liquidities:
            avg_liquidity = sum(liquidities) / len(liquidities)

        return PartnerSignalsListResponse(
            timestamp=datetime.now(timezone.utc),
            total_partners=len(partners),
            market_context={},
            partners=partners,
            aggregated_metrics={
                "avg_volatility": avg_volatility or 0.0,
                "avg_liquidity": avg_liquidity or 0.5,
            },
            data_quality={
                "partners_with_price": sum(
                    1 for p in partners if p.signals.price_current is not None
                ),
                "partners_with_fundamentals": sum(
                    1 for p in partners if p.signals.pe_ratio is not None
                ),
            },
        )


# Keep old class name as alias for backward compatibility
LogisticsFinancialMonitor = LogisticsSignalMonitor


# Convenience functions (updated to use new signal-based approach)
def get_partner_signals(symbol: str) -> dict[str, Any]:
    """
    Get signals for a single logistics partner.

    Args:
        symbol: Stock ticker symbol (e.g., 'HAH')

    Returns:
        Signal response dictionary (NO risk verdict)
    """
    monitor = LogisticsSignalMonitor()
    return monitor.get_partner_signals(symbol).model_dump(mode="json")


def get_all_partner_signals() -> dict[str, Any]:
    """
    Get signals for all default logistics partners.

    Returns:
        List response with all partner signals (NO risk verdict)
    """
    monitor = LogisticsSignalMonitor()
    return monitor.get_all_signals().model_dump(mode="json")
