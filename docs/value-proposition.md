# OMEN Unique Value Proposition

## Executive Summary

OMEN is a **Signal Intelligence Engine** purpose-built for logistics and supply chain risk assessment.
Unlike traditional risk platforms that provide opaque scores or recommendations, OMEN delivers
**transparent, auditable signals** that empower downstream systems to make informed decisions.

---

## What Makes OMEN Different

### 1. Pure Signal Engine Architecture

**The Problem with Traditional Risk Platforms:**
- Black-box risk scores with no explanation
- One-size-fits-all recommendations
- No ability to customize decision logic
- Vendor lock-in for risk decisions

**OMEN's Approach:**

```
┌─────────────────────────────────────────────────────────────────┐
│                        OMEN DELIVERS                             │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Raw signal metrics      │  ❌ Risk verdicts (SAFE/CRITICAL)  │
│  ✅ Evidence trails         │  ❌ Recommendations                │
│  ✅ Confidence scores       │  ❌ Decisions                      │
│  ✅ Full transparency       │  ❌ Black-box scores               │
└─────────────────────────────────────────────────────────────────┘
```

**Why This Matters:**
- **Auditability**: Every signal has a complete evidence chain
- **Flexibility**: Your risk engine, your rules
- **Compliance**: Full transparency for regulators
- **Integration**: Clean separation of concerns

### 2. Cross-Source Intelligence

OMEN correlates data across **7+ independent sources** to create intelligence no single source provides:

| Source | Data Type | Unique Insight |
|--------|-----------|----------------|
| **Polymarket** | Prediction markets | Crowd-sourced probability for geopolitical events |
| **vnstock** | Vietnam stock data | Native Vietnamese market intelligence |
| **News + NLP** | Sentiment analysis | Tier-1 news processing with logistics focus |
| **AIS/MarineTraffic** | Vessel tracking | Real-time port congestion, vessel routes |
| **OpenWeatherMap** | Weather alerts | Storm impacts on shipping routes |
| **Commodity APIs** | Freight rates | Freight cost correlation |
| **Stock APIs** | Market data | Partner financial health signals |

**Example Cross-Source Signal:**

```json
{
  "signal_id": "OMEN-20260201-001",
  "title": "Red Sea Disruption Affecting Partner GMD",
  "evidence": [
    {
      "source": "polymarket",
      "type": "PROBABILITY_CHANGE",
      "value": "Houthi attack probability increased to 78%"
    },
    {
      "source": "ais",
      "type": "ROUTE_CHANGE",
      "value": "15 vessels diverted to Cape route"
    },
    {
      "source": "vnstock",
      "type": "PRICE_MOVEMENT",
      "value": "GMD down 3.2% on volume spike"
    }
  ],
  "confidence": 0.87
}
```

**No single data provider offers this correlation.**

### 3. Vietnam Market Specialization

OMEN is the **only signal engine with native Vietnam market support**:

| Capability | Implementation |
|------------|----------------|
| **Stock Data** | Direct vnstock integration (HOSE, HNX, UPCOM) |
| **Partner Coverage** | GMD, HAH, VOS, VSC, PVT, VTP, STG, PAN, DPM |
| **Currency** | VND-native pricing |
| **Language** | Vietnamese news processing |
| **Timing** | Vietnam market hours awareness |

**Why Vietnam Matters:**
- Rapidly growing logistics hub
- Critical supply chain node for manufacturing
- Underserved by global platforms
- Unique market dynamics

### 4. Logistics-Focused Intelligence

OMEN is **purpose-built for supply chain risk**, not adapted from general financial tools:

#### Chokepoint Monitoring

| Chokepoint | Metrics Tracked |
|------------|-----------------|
| Suez Canal | Transit times, queue depth, diversions |
| Panama Canal | Water levels, booking status, delays |
| Strait of Malacca | Congestion, security events |
| Cape of Good Hope | Traffic volume (Suez alternative) |

#### Port Congestion Detection

```python
# Example: Port congestion signal
{
    "port": "SGSIN",
    "vessels_waiting": 45,
    "normal_waiting": 15,
    "congestion_ratio": 3.0,
    "avg_wait_hours": 18.5,
    "signal": "PORT_CONGESTION_CRITICAL"
}
```

#### Weather Impact on Shipping

- Typhoon/hurricane tracking
- Storm path predictions
- Port closure probabilities
- Affected vessel counts

---

## Competitive Comparison

| Feature | OMEN | Bloomberg Terminal | Refinitiv Eikon | Generic API |
|---------|------|-------------------|-----------------|-------------|
| **Signal-only (no verdict)** | ✅ | ❌ | ❌ | ❌ |
| **Vietnam market native** | ✅ | ❌ | ❌ | ❌ |
| **Logistics focus** | ✅ | ❌ | ❌ | ❌ |
| **Prediction market data** | ✅ | ❌ | ❌ | ❌ |
| **Cross-source correlation** | ✅ | Partial | Partial | ❌ |
| **Evidence trails** | ✅ | ❌ | ❌ | ❌ |
| **Confidence scores** | ✅ | ❌ | ❌ | Varies |
| **Open API** | ✅ | ❌ | ❌ | ✅ |
| **Transparent pricing** | ✅ | ❌ | ❌ | ✅ |
| **Self-hosted option** | ✅ | ❌ | ❌ | Varies |

### Pricing Comparison

| Platform | Entry Cost | Typical Annual |
|----------|------------|----------------|
| Bloomberg Terminal | $24,000/year | $24,000+ |
| Refinitiv Eikon | $15,000/year | $15,000+ |
| OMEN API | **$0** (open source) | Hosting only |
| OMEN Cloud | TBD | TBD |

---

## Use Cases

### 1. Supply Chain Risk Assessment

**Scenario**: RiskCast needs to assess risk for a shipment from Vietnam to Rotterdam.

**OMEN Provides**:
- Partner financial health signals (vnstock)
- Route chokepoint status (Suez/Cape)
- Weather disruption probability
- Port congestion at origin/destination

**RiskCast Decides**:
- Risk level based on business rules
- Premium adjustments
- Route recommendations

### 2. Partner Monitoring

**Scenario**: Continuous monitoring of logistics partners.

**OMEN Provides**:
- Real-time stock signals
- Volume anomalies
- Trend indicators
- Fundamental changes

**Your System Decides**:
- Partner tier adjustments
- Credit limit changes
- Alert thresholds

### 3. Event Response

**Scenario**: Red Sea disruption detected.

**OMEN Provides**:
- Probability signals from prediction markets
- AIS data showing diversions
- Freight rate changes
- Affected partner signals

**Your System Decides**:
- Customer notifications
- Route changes
- Pricing adjustments

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                             │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────┤
│ Polymarket│ vnstock  │   AIS    │ Weather  │   News   │ Freight │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬────┘
     │          │          │          │          │          │
     └──────────┴──────────┴──────────┴──────────┴──────────┘
                              │
                    ┌─────────▼─────────┐
                    │                   │
                    │       OMEN        │
                    │  Signal Engine    │
                    │                   │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │RiskCast │     │ Your    │     │ Partner │
        │(Decision│     │ System  │     │ Portal  │
        │ Engine) │     │         │     │         │
        └─────────┘     └─────────┘     └─────────┘
```

---

## Getting Started

### 1. API Access

```bash
# Get your API key
curl -X POST https://api.omen.io/auth/register

# Fetch signals
curl -H "X-API-Key: your-key" https://api.omen.io/api/v1/partner-signals/
```

### 2. SDK Installation

```python
# Python
pip install omen-client

from omen_client import OmenClient
client = OmenClient(api_key="your-key")
signals = client.partner_signals.list()
```

```typescript
// TypeScript
npm install omen-client

import { OmenClient } from 'omen-client';
const client = new OmenClient({ apiKey: 'your-key' });
const signals = await client.partnerSignals.list();
```

### 3. Self-Hosted

```bash
# Clone and run
git clone https://github.com/omen/omen
docker-compose up -d
```

---

## Summary

**OMEN is the only signal intelligence platform that:**

1. ✅ Delivers **signals, not decisions** (pure Signal Engine)
2. ✅ Correlates **7+ data sources** for unique intelligence
3. ✅ Provides **native Vietnam market support**
4. ✅ Is **purpose-built for logistics** risk assessment
5. ✅ Offers **full transparency** with evidence trails
6. ✅ Is **open source** with transparent pricing

**Use OMEN to power your risk decisions with confidence.**

---

*Contact: sales@omen.io | docs.omen.io | github.com/omen/omen*
