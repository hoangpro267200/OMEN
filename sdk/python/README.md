# OMEN Python SDK

Official Python client for the OMEN Signal Intelligence API.

## Installation

```bash
pip install omen-client
```

## Quick Start

```python
from omen_client import OmenClient

# Initialize client
client = OmenClient(api_key="your-api-key")

# Get partner signals
signals = client.partner_signals.list()
for partner in signals.partners:
    print(f"{partner.symbol}: {partner.signals.price_change_percent}%")
    print(f"  Confidence: {partner.confidence.overall_confidence}")
    print(f"  Volatility: {partner.signals.volatility_20d}")

# Get specific partner
hah = client.partner_signals.get("HAH")
print(f"HAH Price: {hah.signals.price_current}")
```

## Async Usage

```python
from omen_client import AsyncOmenClient

async with AsyncOmenClient(api_key="your-api-key") as client:
    # Get signals
    signals = await client.partner_signals.list()
    
    # Stream real-time signals
    async for signal in client.signals.stream():
        print(f"New signal: {signal.signal_id}")
        process_signal(signal)
```

## Features

- **Type-safe**: Full Pydantic models for all responses
- **Async support**: Both sync and async clients
- **Streaming**: Real-time signal streaming via SSE
- **Comprehensive**: All OMEN API endpoints covered

## Response Models

### PartnerSignalResponse

```python
response = client.partner_signals.get("HAH")

# Signal metrics (NO risk verdict)
response.signals.price_current      # Current price
response.signals.price_change_percent  # % change
response.signals.volatility_20d     # 20-day volatility
response.signals.volume_ratio       # Volume vs average

# Confidence scores
response.confidence.overall_confidence  # 0-1 score
response.confidence.data_completeness   # % data available
response.confidence.data_freshness_seconds  # Data age

# Evidence trail
for evidence in response.evidence:
    print(f"{evidence.evidence_type}: {evidence.title}")
```

### Important: OMEN is a Signal Engine

OMEN provides **signals, not decisions**. The response includes:
- Raw metrics and signals
- Confidence scores
- Evidence trails

**It does NOT include:**
- Risk verdicts (SAFE/WARNING/CRITICAL)
- Recommendations
- Decisions

Use these signals in your own risk assessment logic.

## Error Handling

```python
from omen_client import OmenClient, AuthenticationError, RateLimitError

try:
    client = OmenClient(api_key="invalid-key")
    signals = client.partner_signals.list()
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
```

## Configuration

```python
# Via constructor
client = OmenClient(
    api_key="your-api-key",
    base_url="https://api.omen.io",  # Optional
    timeout=30.0,  # Optional
)

# Via environment variables
# OMEN_API_KEY=your-api-key
# OMEN_BASE_URL=https://api.omen.io
client = OmenClient()
```

## License

MIT
