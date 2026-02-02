# OMEN Sandbox Environment

## Overview

OMEN provides a **sandbox environment** for testing and development without affecting production data or incurring production-level rate limits.

## Sandbox URL

```
https://sandbox.api.omen.io
```

## Test API Keys

| Key | Scopes | Rate Limits |
|-----|--------|-------------|
| `sandbox_read_key` | `read:signals`, `read:partners` | 100/min |
| `sandbox_write_key` | `read:*`, `write:signals` | 100/min |
| `sandbox_admin_key` | `admin` | 50/min |

> ⚠️ **Note:** These keys only work on the sandbox environment. Production requires separate keys.

## Sandbox Behavior

### Data

- Sandbox uses **mock data** that resets daily at 00:00 UTC
- Partner signals return **synthetic data** based on real market patterns
- No real market data connections
- Signal IDs are prefixed with `sandbox-`

### Rate Limits

- More restrictive than production
- 100 requests/minute per API key
- WebSocket connections limited to 5 concurrent

### Features

| Feature | Sandbox | Production |
|---------|---------|------------|
| All API endpoints | ✅ | ✅ |
| Real market data | ❌ | ✅ |
| WebSocket connections | 5 max | Based on plan |
| Rate limit | 100/min | Based on plan |
| Data persistence | Resets daily | Permanent |
| SLA | None | 99.9% |

## Quick Start

### Python

```python
from omen_client import OmenClient

# Use sandbox environment
client = OmenClient(
    api_key="sandbox_read_key",
    base_url="https://sandbox.api.omen.io",
)

# Fetch partner signals
signals = client.partner_signals.list()
for partner in signals.partners:
    print(f"{partner.symbol}: {partner.signals.price_change_percent}%")

# Get specific partner
gmd = client.partner_signals.get("GMD")
print(f"Confidence: {gmd.confidence.overall_confidence}")
```

### TypeScript

```typescript
import { OmenClient } from 'omen-sdk';

// Use sandbox environment
const client = new OmenClient(
  'sandbox_read_key',
  'https://sandbox.api.omen.io'
);

// Fetch partner signals
const signals = await client.getPartnerSignals();
signals.forEach(partner => {
  console.log(`${partner.symbol}: ${partner.signals.price_change_percent}%`);
});
```

### cURL

```bash
# Health check
curl -H "X-API-Key: sandbox_read_key" \
    https://sandbox.api.omen.io/health

# List partner signals
curl -H "X-API-Key: sandbox_read_key" \
    https://sandbox.api.omen.io/api/v1/partner-signals/

# Get specific partner
curl -H "X-API-Key: sandbox_read_key" \
    https://sandbox.api.omen.io/api/v1/partner-signals/GMD
```

## Testing Scopes

### Read-Only Tests

```bash
# Should succeed (200 OK)
curl -H "X-API-Key: sandbox_read_key" \
    https://sandbox.api.omen.io/api/v1/signals/

# Should fail (403 Forbidden)
curl -H "X-API-Key: sandbox_read_key" \
    -X POST \
    https://sandbox.api.omen.io/api/v1/signals/process

# Response:
# {
#   "error": "INSUFFICIENT_PERMISSIONS",
#   "message": "Missing required scopes: write:signals"
# }
```

### Write Tests

```bash
# Should succeed with write key
curl -H "X-API-Key: sandbox_write_key" \
    -X POST \
    https://sandbox.api.omen.io/api/v1/signals/process
```

### Admin Tests

```bash
# Should succeed with admin key
curl -H "X-API-Key: sandbox_admin_key" \
    https://sandbox.api.omen.io/api/v1/debug/

# Should fail with read key
curl -H "X-API-Key: sandbox_read_key" \
    https://sandbox.api.omen.io/api/v1/debug/
```

## Testing Error Handling

### Authentication Errors (401)

```bash
# Invalid API key
curl -H "X-API-Key: invalid_key" \
    https://sandbox.api.omen.io/api/v1/signals/

# Response:
# {
#   "error": "INVALID_API_KEY",
#   "message": "The provided API key is invalid",
#   "hint": "Check your API key and ensure it's correct"
# }
```

### Rate Limiting (429)

```bash
# Exceed rate limit (100+ requests in 1 minute)
for i in {1..150}; do
  curl -s -H "X-API-Key: sandbox_read_key" \
      https://sandbox.api.omen.io/api/v1/signals/ &
done

# Response (after limit exceeded):
# {
#   "error": "RATE_LIMITED",
#   "message": "Rate limit exceeded",
#   "hint": "Retry after 60 seconds"
# }
```

### Not Found (404)

```bash
curl -H "X-API-Key: sandbox_read_key" \
    https://sandbox.api.omen.io/api/v1/partner-signals/INVALID

# Response:
# {
#   "error": "NOT_FOUND",
#   "message": "Partner 'INVALID' not found"
# }
```

## WebSocket Testing

### Connect to Signal Stream

```javascript
const ws = new WebSocket(
  'wss://sandbox.api.omen.io/ws/signals?api_key=sandbox_read_key'
);

ws.onopen = () => {
  console.log('Connected to sandbox');
};

ws.onmessage = (event) => {
  const signal = JSON.parse(event.data);
  console.log('New signal:', signal);
};
```

### Connection Limits

Sandbox allows maximum 5 concurrent WebSocket connections per API key.

```javascript
// Attempting 6th connection will receive:
// {
//   "type": "error",
//   "message": "Connection limit reached (5 max)"
// }
```

## Mock Data Patterns

### Partner Signals

Sandbox generates realistic mock data with:

- **Price movements**: ±5% daily variation
- **Volume**: Based on historical averages
- **Confidence scores**: 0.7-0.95 range
- **Update frequency**: Every 5 minutes

### Signal Types

Available signal types in sandbox:

- `PRICE_CHANGE` - Price movement signals
- `VOLUME_SPIKE` - Unusual volume activity
- `VOLATILITY_ALERT` - Volatility threshold breached
- `NEWS_EVENT` - Mock news-driven signals

## Best Practices

1. **Use sandbox for integration testing** before production deployment
2. **Test error handling** with various HTTP status codes
3. **Verify rate limit behavior** with burst requests
4. **Test WebSocket reconnection** logic
5. **Validate response parsing** with different data scenarios

## Support

For sandbox-specific issues:

- **Email**: sandbox-support@omen.io
- **Documentation**: https://docs.omen.io/sandbox
- **Status Page**: https://status.omen.io
