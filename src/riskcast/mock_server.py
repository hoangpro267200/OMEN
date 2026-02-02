"""
Mock RiskCast API Server for Testing

Simulates RiskCast API responses for:
1. New order events → Risk assessment
2. Shipping/logistics events → Shipping risk score  
3. Full pipeline → Scoring + Alert

Usage:
    python -m riskcast.mock_server --port 8001
    
Or import and use in tests:
    from riskcast.mock_server import MockRiskCastApp
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# =============================================================================
# MODELS: Risk Signal Responses
# =============================================================================


class RiskLevel(str, Enum):
    """Risk level classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class AlertPriority(str, Enum):
    """Alert priority for notifications."""
    P1_IMMEDIATE = "P1"
    P2_HIGH = "P2"
    P3_MEDIUM = "P3"
    P4_LOW = "P4"


class RiskFactor(BaseModel):
    """Individual risk factor."""
    factor_name: str
    score: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    reasoning: str


class RiskAssessment(BaseModel):
    """Risk assessment result from RiskCast."""
    assessment_id: str
    signal_id: str
    
    # Risk scoring
    risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    
    # Breakdown
    factors: list[RiskFactor]
    weighted_score: float
    
    # Impact
    estimated_impact_usd: float | None = None
    affected_orders: list[str] = []
    affected_routes: list[str] = []
    
    # Alert
    alert_priority: AlertPriority
    alert_generated: bool
    alert_message: str | None = None
    
    # Metadata
    assessed_at: datetime
    model_version: str = "riskcast-v1.0"


class IngestResponse(BaseModel):
    """Response for signal ingest."""
    ack_id: str
    status: str = "accepted"
    duplicate: bool = False
    risk_assessment: RiskAssessment | None = None


class OrderRiskRequest(BaseModel):
    """Request to assess risk for an order."""
    order_id: str
    origin: str
    destination: str
    cargo_type: str
    value_usd: float
    requested_delivery: datetime | None = None


class ShippingEventRequest(BaseModel):
    """Shipping/logistics event."""
    event_type: str  # "port_delay", "route_disruption", "capacity_change"
    location: str
    severity: str  # "low", "medium", "high", "critical"
    details: dict[str, Any] = {}


# =============================================================================
# MOCK DATABASE
# =============================================================================


class MockDatabase:
    """In-memory database for mock server."""
    
    def __init__(self):
        self.signals: dict[str, dict] = {}
        self.assessments: dict[str, RiskAssessment] = {}
        self.alerts: list[dict] = []
        self.orders: dict[str, dict] = {}
    
    def has_signal(self, signal_id: str) -> bool:
        return signal_id in self.signals
    
    def store_signal(self, signal_id: str, data: dict) -> str:
        ack_id = f"riskcast-ack-{uuid.uuid4().hex[:12]}"
        self.signals[signal_id] = {
            "data": data,
            "ack_id": ack_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        return ack_id
    
    def get_ack_id(self, signal_id: str) -> str | None:
        rec = self.signals.get(signal_id)
        return rec["ack_id"] if rec else None
    
    def store_assessment(self, assessment: RiskAssessment) -> None:
        self.assessments[assessment.assessment_id] = assessment
    
    def add_alert(self, alert: dict) -> None:
        self.alerts.append(alert)
    
    def clear(self) -> None:
        self.signals.clear()
        self.assessments.clear()
        self.alerts.clear()
        self.orders.clear()


db = MockDatabase()


# =============================================================================
# RISK CALCULATION ENGINE (Mock)
# =============================================================================


class MockRiskEngine:
    """Mock risk calculation engine."""
    
    # Risk keywords and their base scores
    RISK_KEYWORDS = {
        # High risk
        "disruption": 0.8,
        "blockade": 0.9,
        "attack": 0.85,
        "war": 0.95,
        "strike": 0.7,
        "shutdown": 0.75,
        # Medium risk
        "congestion": 0.5,
        "delay": 0.45,
        "backlog": 0.5,
        "shortage": 0.6,
        # Low risk
        "slow": 0.3,
        "minor": 0.2,
        "temporary": 0.25,
    }
    
    # Chokepoint risk multipliers
    CHOKEPOINT_MULTIPLIERS = {
        "suez_canal": 1.5,
        "red_sea": 1.4,
        "panama_canal": 1.3,
        "malacca_strait": 1.4,
        "bab_el_mandeb": 1.5,
        "strait_of_hormuz": 1.6,
    }
    
    @classmethod
    def calculate_risk(
        cls,
        signal: dict,
        context: dict | None = None,
    ) -> RiskAssessment:
        """Calculate risk assessment for a signal."""
        signal_id = signal.get("signal_id", "unknown")
        nested_signal = signal.get("signal", signal)
        
        # Extract signal data
        title = nested_signal.get("title", "").lower()
        probability = nested_signal.get("probability", 0.5)
        confidence = nested_signal.get("confidence_score", 0.5)
        category = nested_signal.get("category", "UNKNOWN")
        geographic = nested_signal.get("geographic", {})
        chokepoints = geographic.get("chokepoints", [])
        
        # Calculate base risk from keywords
        keyword_scores = []
        for keyword, score in cls.RISK_KEYWORDS.items():
            if keyword in title:
                keyword_scores.append(score)
        
        base_risk = max(keyword_scores) if keyword_scores else 0.3
        
        # Apply probability factor
        prob_factor = probability * 0.4 + 0.3  # Scale 0.3-0.7
        
        # Apply chokepoint multiplier
        chokepoint_multiplier = 1.0
        for cp in chokepoints:
            cp_lower = cp.lower().replace(" ", "_")
            if cp_lower in cls.CHOKEPOINT_MULTIPLIERS:
                chokepoint_multiplier = max(
                    chokepoint_multiplier,
                    cls.CHOKEPOINT_MULTIPLIERS[cp_lower]
                )
        
        # Calculate final risk score (0-100)
        raw_score = base_risk * prob_factor * chokepoint_multiplier * 100
        risk_score = min(100, max(0, raw_score))
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        elif risk_score >= 20:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.NEGLIGIBLE
        
        # Calculate alert priority
        if risk_level == RiskLevel.CRITICAL:
            alert_priority = AlertPriority.P1_IMMEDIATE
        elif risk_level == RiskLevel.HIGH:
            alert_priority = AlertPriority.P2_HIGH
        elif risk_level == RiskLevel.MEDIUM:
            alert_priority = AlertPriority.P3_MEDIUM
        else:
            alert_priority = AlertPriority.P4_LOW
        
        # Build risk factors
        factors = [
            RiskFactor(
                factor_name="probability_factor",
                score=probability,
                weight=0.3,
                reasoning=f"Market probability {probability*100:.1f}%",
            ),
            RiskFactor(
                factor_name="keyword_severity",
                score=base_risk,
                weight=0.3,
                reasoning=f"Event severity from keywords: {base_risk:.2f}",
            ),
            RiskFactor(
                factor_name="geographic_exposure",
                score=min(1.0, chokepoint_multiplier - 0.5),
                weight=0.25,
                reasoning=f"Chokepoint multiplier: {chokepoint_multiplier:.2f}x",
            ),
            RiskFactor(
                factor_name="confidence_factor",
                score=confidence,
                weight=0.15,
                reasoning=f"Signal confidence: {confidence:.2f}",
            ),
        ]
        
        weighted_score = sum(f.score * f.weight for f in factors)
        
        # Estimate impact (mock)
        estimated_impact = None
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            estimated_impact = random.uniform(100000, 5000000)
        elif risk_level == RiskLevel.MEDIUM:
            estimated_impact = random.uniform(10000, 100000)
        
        # Generate alert message
        alert_generated = risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        alert_message = None
        if alert_generated:
            alert_message = (
                f"[{alert_priority.value}] Risk Alert: {nested_signal.get('title', 'Unknown event')} "
                f"- Risk Score: {risk_score:.1f}/100 ({risk_level.value})"
            )
        
        return RiskAssessment(
            assessment_id=f"assess-{uuid.uuid4().hex[:12]}",
            signal_id=signal_id,
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            confidence=confidence,
            factors=factors,
            weighted_score=round(weighted_score, 4),
            estimated_impact_usd=estimated_impact,
            affected_routes=chokepoints,
            alert_priority=alert_priority,
            alert_generated=alert_generated,
            alert_message=alert_message,
            assessed_at=datetime.now(timezone.utc),
        )
    
    @classmethod
    def assess_order_risk(cls, order: OrderRiskRequest) -> RiskAssessment:
        """Assess risk for a specific order."""
        # Mock: check if route passes through high-risk areas
        high_risk_origins = ["shanghai", "shenzhen", "ningbo", "hong kong"]
        high_risk_destinations = ["rotterdam", "los angeles", "long beach"]
        
        base_risk = 0.3
        
        if order.origin.lower() in high_risk_origins:
            base_risk += 0.2
        if order.destination.lower() in high_risk_destinations:
            base_risk += 0.1
        
        # Value-based risk
        if order.value_usd > 1000000:
            base_risk += 0.15
        elif order.value_usd > 100000:
            base_risk += 0.1
        
        risk_score = min(100, base_risk * 100)
        
        if risk_score >= 60:
            risk_level = RiskLevel.HIGH
            alert_priority = AlertPriority.P2_HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
            alert_priority = AlertPriority.P3_MEDIUM
        else:
            risk_level = RiskLevel.LOW
            alert_priority = AlertPriority.P4_LOW
        
        return RiskAssessment(
            assessment_id=f"order-assess-{uuid.uuid4().hex[:8]}",
            signal_id=f"order-{order.order_id}",
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            confidence=0.75,
            factors=[
                RiskFactor(
                    factor_name="route_risk",
                    score=base_risk,
                    weight=0.5,
                    reasoning=f"Route {order.origin} → {order.destination}",
                ),
                RiskFactor(
                    factor_name="value_exposure",
                    score=min(1.0, order.value_usd / 1000000),
                    weight=0.3,
                    reasoning=f"Order value: ${order.value_usd:,.2f}",
                ),
                RiskFactor(
                    factor_name="cargo_sensitivity",
                    score=0.5,
                    weight=0.2,
                    reasoning=f"Cargo type: {order.cargo_type}",
                ),
            ],
            weighted_score=round(base_risk * 0.8, 4),
            estimated_impact_usd=order.value_usd * base_risk,
            affected_orders=[order.order_id],
            affected_routes=[f"{order.origin} → {order.destination}"],
            alert_priority=alert_priority,
            alert_generated=risk_score >= 50,
            alert_message=(
                f"Order {order.order_id}: Risk score {risk_score:.1f}"
                if risk_score >= 50 else None
            ),
            assessed_at=datetime.now(timezone.utc),
        )
    
    @classmethod
    def assess_shipping_event(cls, event: ShippingEventRequest) -> RiskAssessment:
        """Assess risk from shipping/logistics event."""
        severity_scores = {
            "critical": 0.9,
            "high": 0.7,
            "medium": 0.5,
            "low": 0.3,
        }
        
        event_type_scores = {
            "port_delay": 0.6,
            "route_disruption": 0.8,
            "capacity_change": 0.4,
            "weather_alert": 0.5,
            "strike": 0.7,
        }
        
        base_score = severity_scores.get(event.severity.lower(), 0.5)
        type_score = event_type_scores.get(event.event_type.lower(), 0.5)
        
        risk_score = min(100, (base_score * 0.6 + type_score * 0.4) * 100)
        
        if risk_score >= 70:
            risk_level = RiskLevel.HIGH
            alert_priority = AlertPriority.P2_HIGH
        elif risk_score >= 50:
            risk_level = RiskLevel.MEDIUM
            alert_priority = AlertPriority.P3_MEDIUM
        else:
            risk_level = RiskLevel.LOW
            alert_priority = AlertPriority.P4_LOW
        
        return RiskAssessment(
            assessment_id=f"shipping-{uuid.uuid4().hex[:8]}",
            signal_id=f"shipping-event-{uuid.uuid4().hex[:6]}",
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            confidence=0.8,
            factors=[
                RiskFactor(
                    factor_name="event_severity",
                    score=base_score,
                    weight=0.6,
                    reasoning=f"Severity: {event.severity}",
                ),
                RiskFactor(
                    factor_name="event_type",
                    score=type_score,
                    weight=0.4,
                    reasoning=f"Event type: {event.event_type}",
                ),
            ],
            weighted_score=round(base_score * 0.6 + type_score * 0.4, 4),
            affected_routes=[event.location],
            alert_priority=alert_priority,
            alert_generated=risk_score >= 60,
            alert_message=(
                f"Shipping Alert [{event.event_type}] at {event.location}: {event.severity}"
                if risk_score >= 60 else None
            ),
            assessed_at=datetime.now(timezone.utc),
        )


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================


def create_mock_riskcast_app() -> FastAPI:
    """Create Mock RiskCast FastAPI app."""
    
    app = FastAPI(
        title="Mock RiskCast API",
        description="Mock RiskCast API for testing OMEN integration",
        version="1.0.0-mock",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # -------------------------------------------------------------------------
    # HEALTH ENDPOINTS
    # -------------------------------------------------------------------------
    
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "mock-riskcast",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @app.get("/health/ready")
    async def ready():
        return {"ready": True}
    
    # -------------------------------------------------------------------------
    # SIGNAL INGEST (Main OMEN → RiskCast endpoint)
    # -------------------------------------------------------------------------
    
    @app.post("/api/v1/signals/ingest")
    async def ingest_signal(request: Request) -> JSONResponse:
        """
        Ingest signal from OMEN.
        
        - First request: 200 + ack_id + risk_assessment
        - Duplicate: 409 + original ack_id
        """
        try:
            body = await request.json()
        except Exception as e:
            return JSONResponse(
                {"detail": f"Invalid JSON: {e}"},
                status_code=400,
            )
        
        signal_id = body.get("signal_id")
        if not signal_id:
            return JSONResponse(
                {"detail": "Missing signal_id"},
                status_code=400,
            )
        
        # Check duplicate
        if db.has_signal(signal_id):
            existing_ack = db.get_ack_id(signal_id)
            return JSONResponse(
                {"ack_id": existing_ack, "duplicate": True},
                status_code=409,
            )
        
        # Store signal
        ack_id = db.store_signal(signal_id, body)
        
        # Calculate risk assessment
        assessment = MockRiskEngine.calculate_risk(body)
        db.store_assessment(assessment)
        
        # Generate alert if needed
        if assessment.alert_generated:
            db.add_alert({
                "alert_id": f"alert-{uuid.uuid4().hex[:8]}",
                "signal_id": signal_id,
                "priority": assessment.alert_priority.value,
                "message": assessment.alert_message,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        
        return JSONResponse({
            "ack_id": ack_id,
            "status": "accepted",
            "risk_assessment": assessment.model_dump(mode="json"),
        })
    
    # -------------------------------------------------------------------------
    # ORDER RISK ASSESSMENT
    # -------------------------------------------------------------------------
    
    @app.post("/api/v1/orders/assess-risk")
    async def assess_order_risk(order: OrderRiskRequest) -> RiskAssessment:
        """
        Assess risk for a new order.
        
        Use case: Khi có đơn hàng mới, gọi endpoint này để nhận risk assessment.
        """
        assessment = MockRiskEngine.assess_order_risk(order)
        db.store_assessment(assessment)
        db.orders[order.order_id] = {
            "order": order.model_dump(mode="json"),
            "assessment": assessment.model_dump(mode="json"),
        }
        return assessment
    
    # -------------------------------------------------------------------------
    # SHIPPING/LOGISTICS EVENTS
    # -------------------------------------------------------------------------
    
    @app.post("/api/v1/shipping/events")
    async def handle_shipping_event(event: ShippingEventRequest) -> RiskAssessment:
        """
        Handle shipping/logistics event.
        
        Use case: Port delay, route disruption, capacity changes.
        """
        assessment = MockRiskEngine.assess_shipping_event(event)
        db.store_assessment(assessment)
        return assessment
    
    # -------------------------------------------------------------------------
    # QUERY ENDPOINTS
    # -------------------------------------------------------------------------
    
    @app.get("/api/v1/signals")
    async def list_signals(limit: int = 50):
        """List ingested signals."""
        signals = list(db.signals.values())[-limit:]
        return {"signals": signals, "total": len(db.signals)}
    
    @app.get("/api/v1/assessments")
    async def list_assessments(limit: int = 50):
        """List risk assessments."""
        assessments = list(db.assessments.values())[-limit:]
        return {
            "assessments": [a.model_dump(mode="json") for a in assessments],
            "total": len(db.assessments),
        }
    
    @app.get("/api/v1/alerts")
    async def list_alerts(limit: int = 50):
        """List generated alerts."""
        return {"alerts": db.alerts[-limit:], "total": len(db.alerts)}
    
    @app.get("/api/v1/assessments/{signal_id}")
    async def get_assessment(signal_id: str):
        """Get risk assessment for a signal."""
        for assessment in db.assessments.values():
            if assessment.signal_id == signal_id:
                return assessment
        raise HTTPException(404, "Assessment not found")
    
    # -------------------------------------------------------------------------
    # ADMIN ENDPOINTS
    # -------------------------------------------------------------------------
    
    @app.post("/api/v1/admin/reset")
    async def reset_database():
        """Reset mock database (for testing)."""
        db.clear()
        return {"status": "reset", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    @app.get("/api/v1/admin/stats")
    async def get_stats():
        """Get mock server statistics."""
        return {
            "signals_ingested": len(db.signals),
            "assessments_generated": len(db.assessments),
            "alerts_generated": len(db.alerts),
            "orders_assessed": len(db.orders),
        }
    
    return app


# Singleton app instance
MockRiskCastApp = create_mock_riskcast_app()


# =============================================================================
# CLI RUNNER
# =============================================================================


if __name__ == "__main__":
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description="Mock RiskCast API Server")
    parser.add_argument("--port", type=int, default=8001, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    args = parser.parse_args()
    
    print(f"\n🚀 Starting Mock RiskCast API on http://{args.host}:{args.port}")
    print("\nAvailable endpoints:")
    print("  POST /api/v1/signals/ingest     - Ingest OMEN signal")
    print("  POST /api/v1/orders/assess-risk - Assess order risk")
    print("  POST /api/v1/shipping/events    - Handle shipping event")
    print("  GET  /api/v1/alerts             - List alerts")
    print("  GET  /api/v1/assessments        - List assessments")
    print("  POST /api/v1/admin/reset        - Reset database")
    print()
    
    uvicorn.run(MockRiskCastApp, host=args.host, port=args.port)
