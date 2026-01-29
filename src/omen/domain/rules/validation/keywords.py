"""
Comprehensive logistics keyword database.

Organized by category for maintainability and reuse across validation rules.
Uses word-boundary matching so "port" does not match "sport", "strike" not "striker".
"""

import re

LOGISTICS_KEYWORDS: dict[str, list[str]] = {
    "maritime": [
        "shipping",
        "ship",
        "vessel",
        "cargo",
        "container",
        "freight",
        "maritime",
        "port",
        "harbor",
        "dock",
        "terminal",
        "berth",
        "tanker",
        "bulk",
        "liner",
        "carrier",
        "fleet",
    ],
    "routes": [
        "red sea",
        "suez",
        "panama",
        "hormuz",
        "malacca",
        "bosphorus",
        "gibraltar",
        "cape",
        "route",
        "strait",
        "canal",
        "passage",
        "bab el-mandeb",
        "taiwan strait",
        "singapore strait",
    ],
    "trade": [
        "trade",
        "export",
        "import",
        "tariff",
        "customs",
        "duty",
        "commerce",
        "commodity",
        "goods",
        "merchandise",
        "supply chain",
        "procurement",
        "sourcing",
        "vendor",
        "supplier",
    ],
    "energy": [
        "oil",
        "gas",
        "lng",
        "petroleum",
        "crude",
        "fuel",
        "bunker",
        "energy",
        "pipeline",
        "refinery",
        "opec",
        "barrel",
    ],
    "geopolitical": [
        "sanction",
        "embargo",
        "blockade",
        "conflict",
        "war",
        "military",
        "attack",
        "threat",
        "security",
        "piracy",
        "houthi",
        "rebel",
        "tension",
        "dispute",
        "crisis",
        "escalation",
        "strike",
        "closure",
    ],
    "infrastructure": [
        "port",
        "airport",
        "rail",
        "railway",
        "road",
        "bridge",
        "warehouse",
        "distribution",
        "logistics",
        "hub",
        "node",
        "infrastructure",
        "capacity",
        "congestion",
    ],
    "weather": [
        "storm",
        "hurricane",
        "typhoon",
        "cyclone",
        "flood",
        "drought",
        "earthquake",
        "tsunami",
        "weather",
        "climate",
        "el nino",
    ],
    "economic": [
        "freight rate",
        "shipping cost",
        "fuel price",
        "insurance",
        "premium",
        "surcharge",
        "fee",
        "cost",
        "price",
        "index",
        "demand",
        "supply",
        "shortage",
        "surplus",
    ],
    "regions": [
        "asia",
        "europe",
        "america",
        "africa",
        "middle east",
        "pacific",
        "atlantic",
        "mediterranean",
        "china",
        "india",
        "vietnam",
        "indonesia",
        "japan",
        "korea",
        "singapore",
        "dubai",
        "rotterdam",
        "los angeles",
        "long beach",
        "shanghai",
        "shenzhen",
        "hong kong",
    ],
}

# Flatten for easy lookup (single set of lowercase keywords)
_ALL_LOGISTICS_KEYWORDS: set[str] = set()
for category_keywords in LOGISTICS_KEYWORDS.values():
    _ALL_LOGISTICS_KEYWORDS.update(kw.lower() for kw in category_keywords)


def get_matched_keywords(text: str) -> list[str]:
    """Find logistics keywords in text using whole-word match (no substring: port≠sport, strike≠striker)."""
    if not text:
        return []
    text_lower = text.lower()
    return [kw for kw in _ALL_LOGISTICS_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]


def get_keyword_categories(keywords: list[str]) -> dict[str, list[str]]:
    """Categorize matched keywords by category name."""
    result: dict[str, list[str]] = {}
    kw_set = set(kw.lower() for kw in keywords)
    for category, category_keywords in LOGISTICS_KEYWORDS.items():
        category_lower = [k.lower() for k in category_keywords]
        matches = [k for k in kw_set if k in category_lower]
        if matches:
            result[category] = matches
    return result


def calculate_relevance_score(keywords: list[str]) -> float:
    """
    Calculate logistics relevance score from matched keywords.

    - 1 keyword: 0.3
    - 2–3 keywords: 0.5
    - 4–5 keywords: 0.7
    - 6+ keywords: 0.9
    - Bonus for routes or geopolitical: +0.1 each (capped at 1.0).
    """
    if not keywords:
        return 0.0
    count = len(keywords)
    if count == 1:
        base_score = 0.3
    elif count <= 3:
        base_score = 0.5
    elif count <= 5:
        base_score = 0.7
    else:
        base_score = 0.9
    categories = get_keyword_categories(keywords)
    bonus = 0.0
    if "routes" in categories:
        bonus += 0.1
    if "geopolitical" in categories:
        bonus += 0.1
    return min(1.0, base_score + bonus)
