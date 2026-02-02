# OMEN TypeScript SDK

Official TypeScript/JavaScript client for the OMEN Signal Intelligence API.

## Installation

```bash
npm install omen-client
# or
yarn add omen-client
# or
pnpm add omen-client
```

## Quick Start

```typescript
import { OmenClient } from 'omen-client';

const client = new OmenClient({ apiKey: 'your-api-key' });

// Get partner signals
const signals = await client.partnerSignals.list();
for (const partner of signals.partners) {
  console.log(`${partner.symbol}: ${partner.signals.price_change_percent}%`);
  console.log(`  Confidence: ${partner.confidence.overall_confidence}`);
}

// Get specific partner
const hah = await client.partnerSignals.get('HAH');
console.log(`HAH Price: ${hah.signals.price_current}`);
console.log(`Volatility: ${hah.signals.volatility_20d}`);
```

## Features

- **Type-safe**: Full TypeScript types for all responses
- **Tree-shakeable**: ESM support with proper exports
- **Lightweight**: No dependencies (uses native fetch)
- **Node.js & Browser**: Works in both environments

## API Reference

### OmenClient

```typescript
const client = new OmenClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.omen.io',  // Optional
  timeout: 30000,  // Optional, in milliseconds
});
```

### Partner Signals

```typescript
// List all partner signals
const signals = await client.partnerSignals.list({
  symbols: ['HAH', 'GMD'],  // Optional filter
  includeEvidence: true,
  includeMarketContext: true,
});

// Get specific partner
const hah = await client.partnerSignals.get('HAH', {
  includeEvidence: true,
  includeHistory: false,
});
```

### Signals

```typescript
// List recent signals
const result = await client.signals.list({
  limit: 50,
  signalType: 'prediction_market',
});

// Get specific signal
const signal = await client.signals.get('OMEN-123');
```

### Health Check

```typescript
const health = await client.health();
console.log(`Status: ${health.status}`);
```

## Response Types

### PartnerSignalResponse

```typescript
interface PartnerSignalResponse {
  symbol: string;
  company_name: string;
  signals: PartnerSignalMetrics;
  confidence: PartnerSignalConfidence;
  evidence: PartnerSignalEvidence[];
  timestamp: string;
  // ... more fields
}
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

```typescript
import { 
  OmenClient, 
  AuthenticationError, 
  RateLimitError 
} from 'omen-client';

try {
  const signals = await client.partnerSignals.list();
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter} seconds`);
  } else {
    throw error;
  }
}
```

## Node.js Usage

For Node.js < 18, you may need to provide a fetch implementation:

```typescript
import fetch from 'node-fetch';

const client = new OmenClient({
  apiKey: 'your-api-key',
  fetch: fetch as unknown as typeof globalThis.fetch,
});
```

## License

MIT
