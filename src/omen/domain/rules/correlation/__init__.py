"""
Cross-Source Asset Correlation.

Defines relationships between events and assets for intelligent signal routing.
"""

from .asset_correlation_matrix import (
    EventCategory,
    AssetCorrelationMatrix,
    get_correlated_assets,
    suggest_assets_to_check,
)

__all__ = [
    "EventCategory",
    "AssetCorrelationMatrix",
    "get_correlated_assets",
    "suggest_assets_to_check",
]
