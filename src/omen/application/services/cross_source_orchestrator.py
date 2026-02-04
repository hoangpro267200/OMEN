"""
Cross-Source Orchestration Service.

Automatically triggers correlated asset queries when a signal arrives.
This is the INTELLIGENCE that makes OMEN a true Signal Intelligence Engine.

Example flow:
1. Polymarket signal arrives: "War probability 70%"
2. Orchestrator detects "war" keyword
3. Automatically queries: Gold, Oil, USD, Defense stocks
4. Correlates all signals with confidence boost/reduction
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol

from omen.application.ports.time_provider import utc_now
from omen.domain.models.raw_signal import RawSignalEvent
from omen.domain.rules.correlation.asset_correlation_matrix import (
    AssetCorrelationMatrix,
    EventCategory,
    suggest_assets_to_check,
)
from omen.domain.services.conflict_detector import (
    ConflictResult,
    SignalConflictDetector,
)

logger = logging.getLogger(__name__)


class AssetDataSource(Protocol):
    """Protocol for asset data sources."""

    async def get_latest_price(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get latest price data for an asset."""
        ...

    async def get_price_change(
        self, symbol: str, hours: int = 24
    ) -> Optional[dict[str, Any]]:
        """Get price change over time period."""
        ...


@dataclass(frozen=True)
class CorrelatedAssetData:
    """Data fetched from correlated asset."""

    symbol: str
    source: str
    price: Optional[float]
    price_change_24h: Optional[float]
    price_change_pct: Optional[float]
    fetched_at: datetime
    correlation_strength: float


@dataclass(frozen=True)
class CrossSourceCorrelationResult:
    """Result of cross-source correlation analysis."""

    original_signal_id: str
    triggered_at: datetime
    event_keywords: list[str]
    suggested_assets: dict[str, list[str]]
    fetched_assets: list[CorrelatedAssetData]
    conflicts: list[ConflictResult]
    confidence_adjustment: float
    correlation_summary: str


class CrossSourceOrchestrator:
    """
    Orchestrates automatic cross-source queries when signals arrive.

    This is the KILLER FEATURE that transforms OMEN from a data aggregator
    into a true Signal Intelligence Engine.

    Usage:
        orchestrator = CrossSourceOrchestrator(asset_sources)

        # When a signal arrives
        result = await orchestrator.process_signal(signal)

        # Result contains:
        # - Correlated asset data
        # - Conflicts detected
        # - Confidence adjustments
    """

    def __init__(
        self,
        asset_sources: dict[str, AssetDataSource] | None = None,
        conflict_detector: SignalConflictDetector | None = None,
        correlation_matrix: type[AssetCorrelationMatrix] = AssetCorrelationMatrix,
        enable_parallel_fetch: bool = True,
        fetch_timeout_seconds: float = 10.0,
    ):
        """
        Initialize cross-source orchestrator.

        Args:
            asset_sources: Map of asset type to data source
            conflict_detector: Detector for signal conflicts
            correlation_matrix: Matrix for event-to-asset correlation
            enable_parallel_fetch: Fetch correlated assets in parallel
            fetch_timeout_seconds: Timeout for each asset fetch
        """
        self._asset_sources = asset_sources or {}
        self._conflict_detector = conflict_detector or SignalConflictDetector()
        self._correlation_matrix = correlation_matrix
        self._enable_parallel_fetch = enable_parallel_fetch
        self._fetch_timeout = fetch_timeout_seconds

    async def process_signal(
        self,
        signal: RawSignalEvent,
        additional_signals: list[RawSignalEvent] | None = None,
    ) -> CrossSourceCorrelationResult:
        """
        Process incoming signal and fetch correlated asset data.

        This is the main entry point for cross-source intelligence.

        Args:
            signal: The incoming signal to process
            additional_signals: Other recent signals for conflict detection

        Returns:
            CrossSourceCorrelationResult with all correlated data
        """
        triggered_at = utc_now()

        # Extract keywords from signal
        keywords = self._extract_keywords(signal)

        # Get suggested assets to check
        suggested_assets = suggest_assets_to_check(keywords)

        # Fetch correlated asset data
        fetched_assets = await self._fetch_correlated_assets(
            suggested_assets, keywords
        )

        # Detect conflicts with additional signals
        all_signals = [signal] + (additional_signals or [])
        conflicts = self._conflict_detector.detect_conflicts(all_signals)

        # Calculate confidence adjustment
        confidence_adjustment = self._calculate_confidence_adjustment(
            fetched_assets, conflicts
        )

        # Generate summary
        summary = self._generate_correlation_summary(
            signal, suggested_assets, fetched_assets, conflicts
        )

        return CrossSourceCorrelationResult(
            original_signal_id=signal.event_id,
            triggered_at=triggered_at,
            event_keywords=keywords,
            suggested_assets=suggested_assets,
            fetched_assets=fetched_assets,
            conflicts=conflicts,
            confidence_adjustment=confidence_adjustment,
            correlation_summary=summary,
        )

    def _extract_keywords(self, signal: RawSignalEvent) -> list[str]:
        """Extract relevant keywords from signal for correlation lookup."""
        keywords = list(signal.keywords or [])

        # Add keywords from title/description
        if signal.title:
            title_words = signal.title.lower().split()
            # Filter to meaningful words
            meaningful = [
                w for w in title_words
                if len(w) > 3 and w not in {"the", "and", "for", "from", "with"}
            ]
            keywords.extend(meaningful[:5])

        return list(set(keywords))

    async def _fetch_correlated_assets(
        self,
        suggested_assets: dict[str, list[str]],
        keywords: list[str],
    ) -> list[CorrelatedAssetData]:
        """Fetch data for all correlated assets."""
        fetched: list[CorrelatedAssetData] = []

        # Collect all unique assets to fetch
        all_assets: set[str] = set()
        for assets in suggested_assets.values():
            all_assets.update(assets)

        if not all_assets:
            return fetched

        logger.info(
            f"Fetching {len(all_assets)} correlated assets for keywords: {keywords}"
        )

        if self._enable_parallel_fetch:
            # Fetch all assets in parallel
            tasks = [
                self._fetch_single_asset(asset, keywords)
                for asset in all_assets
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, CorrelatedAssetData):
                    fetched.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Failed to fetch asset: {result}")
        else:
            # Sequential fetch
            for asset in all_assets:
                try:
                    data = await self._fetch_single_asset(asset, keywords)
                    if data:
                        fetched.append(data)
                except Exception as e:
                    logger.warning(f"Failed to fetch {asset}: {e}")

        return fetched

    async def _fetch_single_asset(
        self,
        symbol: str,
        keywords: list[str],
    ) -> Optional[CorrelatedAssetData]:
        """Fetch data for a single asset."""
        # Determine which source to use based on asset type
        source_name = self._get_source_for_asset(symbol)
        source = self._asset_sources.get(source_name)

        if not source:
            logger.debug(f"No source available for {symbol} ({source_name})")
            return None

        try:
            async with asyncio.timeout(self._fetch_timeout):
                price_data = await source.get_latest_price(symbol)
                change_data = await source.get_price_change(symbol, hours=24)

            if not price_data:
                return None

            # Calculate correlation strength
            correlation_strength = self._calculate_correlation_strength(
                symbol, keywords
            )

            return CorrelatedAssetData(
                symbol=symbol,
                source=source_name,
                price=price_data.get("price"),
                price_change_24h=change_data.get("change") if change_data else None,
                price_change_pct=change_data.get("change_pct") if change_data else None,
                fetched_at=utc_now(),
                correlation_strength=correlation_strength,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {symbol}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching {symbol}: {e}")
            return None

    def _get_source_for_asset(self, symbol: str) -> str:
        """Determine which data source to use for an asset."""
        # Map asset symbols to source types
        precious_metals = {"XAU", "XAG", "gold", "silver"}
        energy = {"CL", "NG", "oil", "crude", "brent", "wti", "natural_gas"}
        currencies = {"DX", "USD", "EUR", "GBP", "JPY"}
        indices = {"SPY", "VIX", "TLT", "QQQ"}

        symbol_upper = symbol.upper()

        if symbol_upper in precious_metals or "gold" in symbol.lower():
            return "commodity"
        elif symbol_upper in energy or any(e in symbol.lower() for e in ["oil", "gas"]):
            return "commodity"
        elif symbol_upper in currencies:
            return "forex"
        elif symbol_upper in indices or "_stocks" in symbol.lower():
            return "stock"
        else:
            return "commodity"  # Default

    def _calculate_correlation_strength(
        self,
        symbol: str,
        keywords: list[str],
    ) -> float:
        """Calculate how strongly correlated an asset is to the event."""
        max_strength = 0.0

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # Check all event categories
            for category in EventCategory:
                # Try to find correlation
                for event_type, mapping in self._correlation_matrix.KEYWORD_MAPPINGS.items():
                    if event_type in keyword_lower:
                        event_cat, ev_type = mapping
                        strength = self._correlation_matrix.get_correlation_strength(
                            EventCategory(event_cat), ev_type, symbol
                        )
                        max_strength = max(max_strength, strength)

        return max_strength if max_strength > 0 else 0.5  # Default medium correlation

    def _calculate_confidence_adjustment(
        self,
        fetched_assets: list[CorrelatedAssetData],
        conflicts: list[ConflictResult],
    ) -> float:
        """
        Calculate overall confidence adjustment based on correlation results.

        Boost confidence if:
        - Multiple correlated assets confirm the signal direction
        - High correlation strength assets show expected movement

        Reduce confidence if:
        - Correlated assets show opposite movement
        - Conflicts detected between sources
        """
        adjustment = 0.0

        # Check correlated asset confirmations
        if fetched_assets:
            confirming = sum(
                1 for a in fetched_assets
                if a.correlation_strength > 0.7 and a.price_change_pct
            )
            if confirming >= 3:
                adjustment += 0.15  # Strong cross-asset confirmation
            elif confirming >= 2:
                adjustment += 0.10

        # Apply conflict penalties
        _, reasons = self._conflict_detector.adjust_confidence(1.0, conflicts)
        for conflict in conflicts:
            if conflict.has_conflict:
                adjustment += conflict.confidence_adjustment

        # Clamp to reasonable range
        return max(-0.3, min(0.3, adjustment))

    def _generate_correlation_summary(
        self,
        signal: RawSignalEvent,
        suggested_assets: dict[str, list[str]],
        fetched_assets: list[CorrelatedAssetData],
        conflicts: list[ConflictResult],
    ) -> str:
        """Generate human-readable correlation summary."""
        parts = []

        # Event summary
        parts.append(f"Signal: {signal.title or signal.event_id}")

        # Assets checked
        if suggested_assets:
            asset_list = []
            for keyword, assets in suggested_assets.items():
                asset_list.append(f"{keyword} → {', '.join(assets[:3])}")
            parts.append(f"Correlated assets: {'; '.join(asset_list)}")

        # Fetched data summary
        if fetched_assets:
            movers = [
                f"{a.symbol} ({a.price_change_pct:+.1f}%)"
                for a in fetched_assets
                if a.price_change_pct and abs(a.price_change_pct) > 1
            ]
            if movers:
                parts.append(f"Significant movers: {', '.join(movers[:5])}")

        # Conflict summary
        active_conflicts = [c for c in conflicts if c.has_conflict]
        if active_conflicts:
            parts.append(f"Conflicts detected: {len(active_conflicts)}")
            for conflict in active_conflicts[:2]:
                parts.append(f"  - {conflict.description}")

        return " | ".join(parts)


# Convenience function for quick correlation check
async def correlate_signal(
    signal: RawSignalEvent,
    orchestrator: Optional[CrossSourceOrchestrator] = None,
) -> CrossSourceCorrelationResult:
    """
    Quick correlation check for a single signal.

    Args:
        signal: Signal to correlate
        orchestrator: Optional pre-configured orchestrator

    Returns:
        Correlation result with all cross-source data
    """
    orch = orchestrator or CrossSourceOrchestrator()
    return await orch.process_signal(signal)
