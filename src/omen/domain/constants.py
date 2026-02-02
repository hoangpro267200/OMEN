"""
OMEN Domain Constants.

Central location for all magic numbers and configuration constants.
This promotes maintainability and makes it easy to adjust thresholds.

Naming convention:
- *_THRESHOLD: Minimum/maximum values for validation
- *_LIMIT: Maximum count limits
- *_TIMEOUT_*: Timeout values
- *_TTL_*: Cache time-to-live values
- *_FACTOR: Multipliers and weights
"""

from enum import Enum
from typing import Final

# ═══════════════════════════════════════════════════════════════════════════════
# LIQUIDITY & MARKET THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

# Minimum liquidity in USD for a signal to be considered valid
MIN_LIQUIDITY_USD: Final[float] = 1000.0

# Minimum liquidity for high-confidence signals
MIN_LIQUIDITY_HIGH_CONFIDENCE: Final[float] = 10000.0

# Volume threshold for market significance
MIN_TRADING_VOLUME: Final[int] = 1000

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

# Confidence level boundaries
CONFIDENCE_HIGH_THRESHOLD: Final[float] = 0.75
CONFIDENCE_MEDIUM_THRESHOLD: Final[float] = 0.50
CONFIDENCE_LOW_THRESHOLD: Final[float] = 0.25

# Minimum confidence for signal emission
MIN_CONFIDENCE_FOR_EMISSION: Final[float] = 0.3

# Confidence intervals for statistical calculations
CONFIDENCE_INTERVAL_95: Final[float] = 1.960  # Z-score for 95% CI
CONFIDENCE_INTERVAL_99: Final[float] = 2.576  # Z-score for 99% CI

# ═══════════════════════════════════════════════════════════════════════════════
# PROBABILITY THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

# Probability must be in [0, 1]
PROBABILITY_MIN: Final[float] = 0.0
PROBABILITY_MAX: Final[float] = 1.0

# Significant probability thresholds
PROBABILITY_HIGH_THRESHOLD: Final[float] = 0.75
PROBABILITY_MEDIUM_THRESHOLD: Final[float] = 0.50
PROBABILITY_LOW_THRESHOLD: Final[float] = 0.25

# Movement thresholds (percentage points)
PROBABILITY_MOVEMENT_SIGNIFICANT: Final[float] = 0.05  # 5pp
PROBABILITY_MOVEMENT_MAJOR: Final[float] = 0.10  # 10pp

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RULE WEIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

# Weight factors for validation rules
LIQUIDITY_RULE_WEIGHT: Final[float] = 0.25
GEOGRAPHIC_RULE_WEIGHT: Final[float] = 0.25
SEMANTIC_RULE_WEIGHT: Final[float] = 0.25
ANOMALY_RULE_WEIGHT: Final[float] = 0.20
NEWS_QUALITY_WEIGHT: Final[float] = 0.10
COMMODITY_CONTEXT_WEIGHT: Final[float] = 0.08

# Maximum confidence boost from context sources
MAX_NEWS_CONFIDENCE_BOOST: Final[float] = 0.10
MAX_COMMODITY_CONFIDENCE_BOOST: Final[float] = 0.08

# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Z-score thresholds for anomaly detection
ZSCORE_ANOMALY_THRESHOLD: Final[float] = 2.0
ZSCORE_SEVERE_ANOMALY_THRESHOLD: Final[float] = 3.0
ZSCORE_MAX_SAFE_VALUE: Final[float] = 10.0  # Cap for JSON safety

# Spike detection thresholds (percentage change)
SPIKE_MINOR_THRESHOLD: Final[float] = 5.0  # 5%
SPIKE_MODERATE_THRESHOLD: Final[float] = 10.0  # 10%
SPIKE_SEVERE_THRESHOLD: Final[float] = 20.0  # 20%

# ═══════════════════════════════════════════════════════════════════════════════
# PAGINATION & LIMITS
# ═══════════════════════════════════════════════════════════════════════════════

# Default pagination settings
DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 500
DEFAULT_OFFSET: Final[int] = 0

# Signal limits
MAX_SIGNALS_PER_REQUEST: Final[int] = 1000
MAX_SIGNALS_PER_BATCH: Final[int] = 500
MAX_EVIDENCE_ITEMS: Final[int] = 50
MAX_KEYWORDS: Final[int] = 20
MAX_TAGS: Final[int] = 10

# ═══════════════════════════════════════════════════════════════════════════════
# CACHE & TTL
# ═══════════════════════════════════════════════════════════════════════════════

# Cache TTL in seconds
CACHE_TTL_SHORT: Final[int] = 60  # 1 minute
CACHE_TTL_MEDIUM: Final[int] = 300  # 5 minutes
CACHE_TTL_LONG: Final[int] = 3600  # 1 hour
CACHE_TTL_DAY: Final[int] = 86400  # 24 hours

# Source health cache
SOURCE_HEALTH_CACHE_TTL: Final[int] = 30  # 30 seconds

# ═══════════════════════════════════════════════════════════════════════════════
# TIMEOUTS
# ═══════════════════════════════════════════════════════════════════════════════

# HTTP request timeouts (seconds)
HTTP_TIMEOUT_SHORT: Final[float] = 5.0
HTTP_TIMEOUT_MEDIUM: Final[float] = 15.0
HTTP_TIMEOUT_LONG: Final[float] = 30.0
HTTP_TIMEOUT_VERY_LONG: Final[float] = 60.0

# Database operation timeouts
DB_TIMEOUT_QUERY: Final[float] = 10.0
DB_TIMEOUT_WRITE: Final[float] = 30.0

# ═══════════════════════════════════════════════════════════════════════════════
# RESILIENCE
# ═══════════════════════════════════════════════════════════════════════════════

# Retry configuration
MAX_RETRY_ATTEMPTS: Final[int] = 3
RETRY_BASE_DELAY: Final[float] = 1.0  # seconds
RETRY_MAX_DELAY: Final[float] = 30.0  # seconds
RETRY_EXPONENTIAL_BASE: Final[float] = 2.0

# Circuit breaker configuration
CIRCUIT_FAILURE_THRESHOLD: Final[int] = 5
CIRCUIT_RECOVERY_TIMEOUT: Final[float] = 30.0  # seconds
CIRCUIT_SUCCESS_THRESHOLD: Final[int] = 3

# Rate limiting
DEFAULT_RATE_LIMIT: Final[int] = 300  # requests per minute
DEFAULT_BURST_LIMIT: Final[int] = 50  # burst requests

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FRESHNESS
# ═══════════════════════════════════════════════════════════════════════════════

# Maximum age for data to be considered fresh (seconds)
DATA_FRESHNESS_REALTIME: Final[int] = 60  # 1 minute
DATA_FRESHNESS_NEAR_REALTIME: Final[int] = 300  # 5 minutes
DATA_FRESHNESS_STALE_WARNING: Final[int] = 3600  # 1 hour
DATA_FRESHNESS_STALE_CRITICAL: Final[int] = 86400  # 24 hours

# Staleness thresholds per source type
MARKET_DATA_MAX_STALENESS: Final[int] = 300  # 5 minutes
NEWS_MAX_STALENESS: Final[int] = 3600  # 1 hour
COMMODITY_MAX_STALENESS: Final[int] = 86400  # 24 hours

# ═══════════════════════════════════════════════════════════════════════════════
# GEOGRAPHIC
# ═══════════════════════════════════════════════════════════════════════════════

# Distance thresholds (kilometers)
DISTANCE_LOCAL: Final[float] = 100.0
DISTANCE_REGIONAL: Final[float] = 500.0
DISTANCE_GLOBAL: Final[float] = 5000.0

# Relevance score thresholds
GEO_RELEVANCE_HIGH: Final[float] = 0.8
GEO_RELEVANCE_MEDIUM: Final[float] = 0.5
GEO_RELEVANCE_LOW: Final[float] = 0.2

# ═══════════════════════════════════════════════════════════════════════════════
# NEWS QUALITY
# ═══════════════════════════════════════════════════════════════════════════════

# Credibility thresholds
NEWS_CREDIBILITY_HIGH: Final[float] = 0.8
NEWS_CREDIBILITY_MEDIUM: Final[float] = 0.5
NEWS_CREDIBILITY_MIN: Final[float] = 0.3

# Recency scoring
NEWS_RECENCY_FRESH: Final[int] = 3600  # 1 hour
NEWS_RECENCY_RECENT: Final[int] = 86400  # 24 hours
NEWS_RECENCY_STALE: Final[int] = 604800  # 7 days

# Combined score thresholds
NEWS_MIN_COMBINED_SCORE: Final[float] = 0.2

# ═══════════════════════════════════════════════════════════════════════════════
# TRADING HOURS (for annualization)
# ═══════════════════════════════════════════════════════════════════════════════

# Trading days per year for volatility annualization
TRADING_DAYS_PER_YEAR: Final[int] = 252

# Hours per trading day
TRADING_HOURS_PER_DAY: Final[int] = 8

# ═══════════════════════════════════════════════════════════════════════════════
# API KEY FORMAT
# ═══════════════════════════════════════════════════════════════════════════════

# API key prefix
API_KEY_PREFIX: Final[str] = "omen_"

# API key display prefix length
API_KEY_PREFIX_DISPLAY_LENGTH: Final[int] = 12

# Minimum API key random part length (bytes)
API_KEY_MIN_RANDOM_BYTES: Final[int] = 32
