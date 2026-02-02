"""
Stock adapter package.

Provides data from:
- yfinance: Global stocks, indices, forex, commodities, bonds
- vnstock: Vietnamese stocks and indices
"""

from omen.adapters.inbound.stock.source import StockSignalSource, create_stock_source

__all__ = ["StockSignalSource", "create_stock_source"]
