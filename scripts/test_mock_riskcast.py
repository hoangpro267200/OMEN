#!/usr/bin/env python3
"""
Test Script: Mock RiskCast Integration

Demonstrates all three use cases:
1. New order → Risk assessment
2. Shipping/logistics events → Risk signal
3. Full pipeline test → Scoring + Alert

Usage:
    # Start mock server first:
    python -m riskcast.mock_server --port 8001
    
    # Then run tests:
    python scripts/test_mock_riskcast.py
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import httpx

# Configuration
MOCK_RISKCAST_URL = "http://localhost:8001"


def print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_response(label: str, data: Any) -> None:
    print(f"\n📦 {label}:")
    print(json.dumps(data, indent=2, default=str))


async def test_health() -> bool:
    """Test server health."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{MOCK_RISKCAST_URL}/health")
            return resp.status_code == 200
        except Exception:
            return False


# =============================================================================
# USE CASE 1: New Order → Risk Assessment
# =============================================================================

async def test_new_order_risk():
    """
    Scenario: Đơn hàng mới được tạo, cần assess risk.
    
    Flow:
    1. Order system tạo order mới
    2. Gọi RiskCast API để assess risk
    3. Nhận risk score + alert nếu cần
    """
    print_section("USE CASE 1: New Order Risk Assessment")
    
    # Sample orders
    orders = [
        {
            "order_id": "ORD-2026-001234",
            "origin": "Shanghai",
            "destination": "Rotterdam",
            "cargo_type": "Electronics",
            "value_usd": 2500000.0,
            "requested_delivery": "2026-03-15T00:00:00Z",
        },
        {
            "order_id": "ORD-2026-001235",
            "origin": "Shenzhen",
            "destination": "Los Angeles",
            "cargo_type": "Consumer Goods",
            "value_usd": 850000.0,
        },
        {
            "order_id": "ORD-2026-001236",
            "origin": "Tokyo",
            "destination": "Singapore",
            "cargo_type": "Auto Parts",
            "value_usd": 125000.0,
        },
    ]
    
    async with httpx.AsyncClient() as client:
        for order in orders:
            print(f"\n🛒 Assessing order: {order['order_id']}")
            print(f"   Route: {order['origin']} → {order['destination']}")
            print(f"   Value: ${order['value_usd']:,.2f}")
            
            resp = await client.post(
                f"{MOCK_RISKCAST_URL}/api/v1/orders/assess-risk",
                json=order,
            )
            
            if resp.status_code == 200:
                assessment = resp.json()
                print(f"\n   ✅ Risk Assessment:")
                print(f"      Risk Score: {assessment['risk_score']:.1f}/100")
                print(f"      Risk Level: {assessment['risk_level']}")
                print(f"      Alert: {assessment['alert_priority']} - Generated: {assessment['alert_generated']}")
                if assessment['alert_message']:
                    print(f"      📢 Alert: {assessment['alert_message']}")
            else:
                print(f"   ❌ Failed: {resp.status_code}")


# =============================================================================
# USE CASE 2: Shipping/Logistics Event → Risk Signal
# =============================================================================

async def test_shipping_events():
    """
    Scenario: Có shipping/logistics event xảy ra.
    
    Events:
    - Port delay
    - Route disruption
    - Capacity change
    """
    print_section("USE CASE 2: Shipping/Logistics Events")
    
    events = [
        {
            "event_type": "port_delay",
            "location": "Port of Shanghai",
            "severity": "high",
            "details": {
                "delay_hours": 48,
                "cause": "Typhoon warning",
                "vessels_affected": 35,
            },
        },
        {
            "event_type": "route_disruption",
            "location": "Red Sea - Bab el-Mandeb",
            "severity": "critical",
            "details": {
                "cause": "Security threat",
                "reroute_required": True,
                "additional_days": 10,
            },
        },
        {
            "event_type": "capacity_change",
            "location": "Suez Canal",
            "severity": "medium",
            "details": {
                "capacity_reduction_pct": 25,
                "duration_days": 7,
            },
        },
    ]
    
    async with httpx.AsyncClient() as client:
        for event in events:
            print(f"\n🚢 Shipping Event: {event['event_type']}")
            print(f"   Location: {event['location']}")
            print(f"   Severity: {event['severity']}")
            
            resp = await client.post(
                f"{MOCK_RISKCAST_URL}/api/v1/shipping/events",
                json=event,
            )
            
            if resp.status_code == 200:
                assessment = resp.json()
                print(f"\n   ✅ Risk Assessment:")
                print(f"      Risk Score: {assessment['risk_score']:.1f}/100")
                print(f"      Risk Level: {assessment['risk_level']}")
                print(f"      Alert Priority: {assessment['alert_priority']}")
                if assessment['alert_message']:
                    print(f"      📢 {assessment['alert_message']}")
            else:
                print(f"   ❌ Failed: {resp.status_code}")


# =============================================================================
# USE CASE 3: Full Pipeline Test (OMEN Signal → Scoring → Alert)
# =============================================================================

async def test_full_pipeline():
    """
    Scenario: OMEN generates signals, sends to RiskCast for scoring.
    
    Flow:
    1. OMEN processes market data
    2. Generates OmenSignal
    3. Wraps in SignalEvent
    4. POST to /api/v1/signals/ingest
    5. Receive risk_assessment + alert
    """
    print_section("USE CASE 3: Full Pipeline - OMEN Signal Ingestion")
    
    # Sample OMEN signals (SignalEvent format)
    signals = [
        {
            "schema_version": "1.0.0",
            "signal_id": "OMEN-TEST001ABC",
            "deterministic_trace_id": "trace-001abc",
            "input_event_hash": "sha256:abc123",
            "source_event_id": "polymarket-12345",
            "ruleset_version": "v1.0.0",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "ledger_partition": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "ledger_sequence": 1,
            "signal": {
                "signal_id": "OMEN-TEST001ABC",
                "signal_type": "SHIPPING_ROUTE_RISK",
                "status": "ACTIVE",
                "title": "Red Sea Shipping Disruption - Houthi Attack Risk",
                "description": "High probability of shipping disruption in Red Sea corridor",
                "probability": 0.78,
                "confidence_score": 0.85,
                "confidence_level": "HIGH",
                "category": "GEOPOLITICAL",
                "geographic": {
                    "regions": ["middle_east", "red_sea"],
                    "chokepoints": ["bab_el_mandeb", "suez_canal"],
                },
                "impact_hints": {
                    "domains": ["logistics", "shipping"],
                    "direction": "negative",
                    "keywords": ["disruption", "shipping", "attack"],
                },
            },
        },
        {
            "schema_version": "1.0.0",
            "signal_id": "OMEN-TEST002XYZ",
            "deterministic_trace_id": "trace-002xyz",
            "input_event_hash": "sha256:xyz789",
            "source_event_id": "polymarket-67890",
            "ruleset_version": "v1.0.0",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "ledger_partition": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "ledger_sequence": 2,
            "signal": {
                "signal_id": "OMEN-TEST002XYZ",
                "signal_type": "PORT_OPERATIONS",
                "status": "MONITORING",
                "title": "Panama Canal Congestion - Drought Restrictions",
                "description": "Reduced transit capacity due to water levels",
                "probability": 0.65,
                "confidence_score": 0.72,
                "confidence_level": "MEDIUM",
                "category": "CLIMATE",
                "geographic": {
                    "regions": ["central_america"],
                    "chokepoints": ["panama_canal"],
                },
                "impact_hints": {
                    "domains": ["logistics", "shipping"],
                    "direction": "negative",
                    "keywords": ["congestion", "delay", "capacity"],
                },
            },
        },
        {
            "schema_version": "1.0.0",
            "signal_id": "OMEN-TEST003DEF",
            "deterministic_trace_id": "trace-003def",
            "input_event_hash": "sha256:def456",
            "source_event_id": "polymarket-11111",
            "ruleset_version": "v1.0.0",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "ledger_partition": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "ledger_sequence": 3,
            "signal": {
                "signal_id": "OMEN-TEST003DEF",
                "signal_type": "LABOR_DISRUPTION",
                "status": "CANDIDATE",
                "title": "Rotterdam Port Strike - 72h Notice",
                "description": "Dock workers union strike action imminent",
                "probability": 0.55,
                "confidence_score": 0.62,
                "confidence_level": "MEDIUM",
                "category": "OPERATIONAL",
                "geographic": {
                    "regions": ["europe", "netherlands"],
                    "chokepoints": [],
                },
                "impact_hints": {
                    "domains": ["logistics", "shipping"],
                    "direction": "negative",
                    "keywords": ["strike", "delay"],
                },
            },
        },
    ]
    
    async with httpx.AsyncClient() as client:
        for signal in signals:
            nested_signal = signal["signal"]
            print(f"\n📡 Ingesting Signal: {signal['signal_id']}")
            print(f"   Title: {nested_signal['title']}")
            print(f"   Probability: {nested_signal['probability']*100:.1f}%")
            print(f"   Confidence: {nested_signal['confidence_score']:.2f}")
            
            resp = await client.post(
                f"{MOCK_RISKCAST_URL}/api/v1/signals/ingest",
                json=signal,
                headers={"X-Idempotency-Key": signal["signal_id"]},
            )
            
            if resp.status_code == 200:
                data = resp.json()
                assessment = data.get("risk_assessment", {})
                print(f"\n   ✅ Accepted (ack_id: {data['ack_id']})")
                print(f"   📊 Risk Assessment:")
                print(f"      Risk Score: {assessment.get('risk_score', 'N/A')}/100")
                print(f"      Risk Level: {assessment.get('risk_level', 'N/A')}")
                print(f"      Alert Priority: {assessment.get('alert_priority', 'N/A')}")
                if assessment.get("alert_generated"):
                    print(f"      🚨 ALERT: {assessment.get('alert_message')}")
                print(f"\n   Risk Factors:")
                for factor in assessment.get("factors", []):
                    print(f"      - {factor['factor_name']}: {factor['score']:.2f} (weight: {factor['weight']})")
                    print(f"        {factor['reasoning']}")
                    
            elif resp.status_code == 409:
                data = resp.json()
                print(f"   ⚠️ Duplicate (ack_id: {data['ack_id']})")
            else:
                print(f"   ❌ Failed: {resp.status_code}")
        
        # Test duplicate detection
        print("\n\n🔄 Testing Idempotency (re-sending first signal)...")
        resp = await client.post(
            f"{MOCK_RISKCAST_URL}/api/v1/signals/ingest",
            json=signals[0],
            headers={"X-Idempotency-Key": signals[0]["signal_id"]},
        )
        if resp.status_code == 409:
            print("   ✅ Duplicate correctly detected (409)")
        else:
            print(f"   ❌ Expected 409, got {resp.status_code}")


# =============================================================================
# SUMMARY: List all alerts and assessments
# =============================================================================

async def show_summary():
    """Show summary of all alerts and assessments."""
    print_section("SUMMARY: Alerts & Assessments")
    
    async with httpx.AsyncClient() as client:
        # Get alerts
        resp = await client.get(f"{MOCK_RISKCAST_URL}/api/v1/alerts")
        if resp.status_code == 200:
            alerts = resp.json()
            print(f"\n🚨 Total Alerts Generated: {alerts['total']}")
            for alert in alerts["alerts"]:
                print(f"   [{alert['priority']}] {alert['message']}")
        
        # Get stats
        resp = await client.get(f"{MOCK_RISKCAST_URL}/api/v1/admin/stats")
        if resp.status_code == 200:
            stats = resp.json()
            print(f"\n📊 Server Statistics:")
            print(f"   Signals Ingested: {stats['signals_ingested']}")
            print(f"   Assessments Generated: {stats['assessments_generated']}")
            print(f"   Alerts Generated: {stats['alerts_generated']}")
            print(f"   Orders Assessed: {stats['orders_assessed']}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    print("\n" + "="*60)
    print("  MOCK RISKCAST INTEGRATION TEST")
    print("="*60)
    
    # Check server health
    print("\n🔍 Checking Mock RiskCast server...")
    if not await test_health():
        print(f"❌ Mock RiskCast server not running at {MOCK_RISKCAST_URL}")
        print("   Start it with: python -m riskcast.mock_server --port 8001")
        return
    print("✅ Server is healthy")
    
    # Reset database
    async with httpx.AsyncClient() as client:
        await client.post(f"{MOCK_RISKCAST_URL}/api/v1/admin/reset")
        print("✅ Database reset")
    
    # Run all tests
    await test_new_order_risk()
    await test_shipping_events()
    await test_full_pipeline()
    await show_summary()
    
    print("\n" + "="*60)
    print("  TEST COMPLETED")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
