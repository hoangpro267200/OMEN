"""
Demo signal data with realistic, impressive titles.
These sound like real logistics intelligence.
"""

DEMO_SIGNALS = [
    {
        "id": "OMEN-DEMO001ABCD",
        "title": "Red Sea Shipping Lane Disruption - Houthi Missile Activity",
        "category": "GEOPOLITICAL",
        "probability": 0.78,
        "confidence_level": "HIGH",
        "confidence_score": 0.85,
        "description": "Increased Houthi rebel activity near Bab el-Mandeb strait affecting major shipping routes",
    },
    {
        "id": "OMEN-DEMO002WXYZ",
        "title": "Suez Canal Congestion - 72-Hour Vessel Backlog",
        "category": "INFRASTRUCTURE",
        "probability": 0.65,
        "confidence_level": "MEDIUM",
        "confidence_score": 0.72,
        "description": "Container vessel queue exceeds 100 ships, transit delays expected",
    },
    {
        "id": "OMEN-DEMO003PQRS",
        "title": "Shanghai Port - Typhoon Warning Level 3",
        "category": "CLIMATE",
        "probability": 0.82,
        "confidence_level": "HIGH",
        "confidence_score": 0.88,
        "description": "Typhoon Koinu approaching, potential 48-hour port closure",
    },
    {
        "id": "OMEN-DEMO004LMNO",
        "title": "EU CBAM Phase 2 - Carbon Border Tax Enforcement",
        "category": "COMPLIANCE",
        "probability": 0.95,
        "confidence_level": "HIGH",
        "confidence_score": 0.92,
        "description": "Carbon Border Adjustment Mechanism enforcement begins for steel/aluminum",
    },
    {
        "id": "OMEN-DEMO005HIJK",
        "title": "Panama Canal - Drought Slot Restrictions Extended",
        "category": "CLIMATE",
        "probability": 0.70,
        "confidence_level": "MEDIUM",
        "confidence_score": 0.68,
        "description": "Daily transit slots reduced from 36 to 24 due to water levels",
    },
    {
        "id": "OMEN-DEMO006DEFG",
        "title": "US-China Chip War - AI Semiconductor Ban Expanded",
        "category": "GEOPOLITICAL",
        "probability": 0.88,
        "confidence_level": "HIGH",
        "confidence_score": 0.90,
        "description": "New export controls on advanced AI chips to Chinese entities",
    },
    {
        "id": "OMEN-DEMO007UVWX",
        "title": "Rotterdam Port - Dock Workers Strike 72h Notice",
        "category": "OPERATIONAL",
        "probability": 0.55,
        "confidence_level": "MEDIUM",
        "confidence_score": 0.62,
        "description": "Union negotiations stalled, strike action imminent",
    },
    {
        "id": "OMEN-DEMO008LATE",
        "title": "Baltic Dry Index Collapse - 12% Weekly Decline",
        "category": "FINANCIAL",
        "probability": 0.72,
        "confidence_level": "HIGH",
        "confidence_score": 0.78,
        "description": "Shipping demand indicator at 6-month low",
    },
    {
        "id": "OMEN-DEMO009MNOP",
        "title": "Vietnam Manufacturing Surge - Nike Production Shift",
        "category": "NETWORK",
        "probability": 0.68,
        "confidence_level": "MEDIUM",
        "confidence_score": 0.65,
        "description": "30% production relocation from China to Vietnam underway",
    },
    {
        "id": "OMEN-DEMO010QRST",
        "title": "Singapore Bunker Fuel Spike - +8% Week-over-Week",
        "category": "FINANCIAL",
        "probability": 0.60,
        "confidence_level": "MEDIUM",
        "confidence_score": 0.58,
        "description": "Marine fuel prices surge at world's largest bunkering hub",
    },
]

# IDs that will be "missing" from RiskCast for reconcile demo
MISSING_SIGNAL_IDS = ["OMEN-DEMO005HIJK", "OMEN-DEMO009MNOP"]
