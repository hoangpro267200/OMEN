"""
Event Fingerprinting for Cross-Source Correlation.

Generates comparable fingerprints that enable matching similar events
from different data sources, enabling confidence boosts when multiple
sources confirm the same signal.

Example:
    - Polymarket: "Red Sea shipping disruption"
    - News: "Houthi attacks disrupt Red Sea trade"
    - AIS: "Vessel rerouting in Red Sea"
    
    All three would generate similar fingerprints, enabling cross-validation.
"""

import re
from hashlib import sha256
from typing import Optional
from datetime import datetime, timezone

from omen.domain.models.raw_signal import RawSignalEvent


class EventFingerprint:
    """
    Generate comparable fingerprints for event matching across sources.
    
    Fingerprint components:
    1. Normalized title keywords (sorted, lowercased)
    2. Sorted keywords
    3. Geographic locations (normalized)
    4. Date bucket (same day = same bucket)
    
    Two events with >70% fingerprint similarity likely refer to the same
    underlying event and can be used for cross-source validation.
    """
    
    # Stop words to filter out
    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "this", "that", "these", "those", "it", "its",
    }
    
    # High-value keywords for logistics/disruption events
    HIGH_VALUE_KEYWORDS = {
        # Geopolitical
        "war", "conflict", "attack", "houthi", "rebel", "military", "missile",
        "drone", "strike", "blockade", "sanction", "tariff",
        # Geographic
        "red sea", "suez", "panama", "malacca", "strait", "canal", "gulf",
        "china", "russia", "ukraine", "iran", "yemen", "asia", "europe",
        # Infrastructure
        "port", "shipping", "vessel", "cargo", "container", "freight",
        "supply chain", "disruption", "delay", "congestion", "closure",
        # Economic
        "oil", "gas", "commodity", "price", "spike", "surge", "crash",
        # Weather
        "storm", "typhoon", "hurricane", "flood", "drought",
    }
    
    @classmethod
    def generate(cls, event: RawSignalEvent) -> str:
        """
        Generate a 16-character fingerprint for an event.
        
        The fingerprint is designed to be similar for events describing
        the same underlying situation from different sources.
        
        Args:
            event: Raw signal event to fingerprint
            
        Returns:
            16-character hex string fingerprint
        """
        # Component 1: Normalized title words
        title_component = cls._normalize_title(event.title or "")
        
        # Component 2: Keywords
        keyword_component = cls._normalize_keywords(event.keywords or [])
        
        # Component 3: Location
        location_component = cls._normalize_location(event)
        
        # Component 4: Date bucket (same day)
        date_component = cls._get_date_bucket(event)
        
        # Combine components
        fingerprint_input = "|".join([
            title_component,
            keyword_component,
            location_component,
            date_component,
        ])
        
        # Hash to fixed-length fingerprint
        return sha256(fingerprint_input.encode()).hexdigest()[:16]
    
    @classmethod
    def _normalize_title(cls, title: str) -> str:
        """Extract and normalize key words from title."""
        # Lowercase and remove punctuation
        title_clean = re.sub(r'[^a-z0-9\s]', '', title.lower())
        
        # Split into words
        words = title_clean.split()
        
        # Filter stop words and short words
        meaningful = [
            w for w in words
            if len(w) > 2 and w not in cls.STOP_WORDS
        ]
        
        # Prioritize high-value keywords
        high_value = [w for w in meaningful if w in cls.HIGH_VALUE_KEYWORDS]
        
        # Take top words (prefer high-value)
        if high_value:
            selected = sorted(high_value)[:3] + sorted(set(meaningful) - set(high_value))[:2]
        else:
            selected = sorted(meaningful)[:5]
        
        return " ".join(selected)
    
    @classmethod
    def _normalize_keywords(cls, keywords: list[str]) -> str:
        """Normalize and sort keywords."""
        # Lowercase and filter
        normalized = [k.lower().strip() for k in keywords if k]
        
        # Take top keywords alphabetically
        return " ".join(sorted(set(normalized))[:5])
    
    @classmethod
    def _normalize_location(cls, event: RawSignalEvent) -> str:
        """Extract location from event."""
        locations = []
        
        # From inferred_locations
        if event.inferred_locations:
            for loc in event.inferred_locations[:3]:
                if hasattr(loc, 'name') and loc.name:
                    locations.append(loc.name.lower())
        
        # From title/keywords
        title_lower = (event.title or "").lower()
        for keyword in cls.HIGH_VALUE_KEYWORDS:
            if keyword in title_lower and keyword in [
                "red sea", "suez", "panama", "malacca", "strait", "canal",
                "china", "russia", "ukraine", "iran", "yemen", "asia", "europe", "gulf"
            ]:
                locations.append(keyword)
        
        return " ".join(sorted(set(locations))[:3])
    
    @classmethod
    def _get_date_bucket(cls, event: RawSignalEvent) -> str:
        """Get date bucket for temporal grouping."""
        timestamp = event.observed_at or datetime.now(timezone.utc)
        return timestamp.strftime("%Y-%m-%d")
    
    @classmethod
    def similarity(cls, fp1: str, fp2: str) -> float:
        """
        Calculate similarity between two fingerprints.
        
        Uses character-level comparison for speed.
        
        Args:
            fp1: First fingerprint
            fp2: Second fingerprint
            
        Returns:
            Similarity score 0.0 to 1.0
        """
        if fp1 == fp2:
            return 1.0
        
        if not fp1 or not fp2:
            return 0.0
        
        # Character-level Jaccard similarity
        set1 = set(fp1)
        set2 = set(fp2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union


class EventFingerprintCache:
    """
    In-memory cache of recent event fingerprints for cross-source matching.
    
    This enables O(1) lookup for matching events when a new signal arrives.
    For distributed deployments, use Redis-backed cache instead.
    """
    
    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        """
        Initialize fingerprint cache.
        
        Args:
            max_size: Maximum number of fingerprints to cache
            ttl_hours: Time-to-live for cached fingerprints
        """
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self._cache: dict[str, dict] = {}  # fingerprint -> event info
        self._fingerprint_to_events: dict[str, list[str]] = {}  # fingerprint -> event_ids
    
    def add(self, event: RawSignalEvent) -> str:
        """
        Add event to cache and return its fingerprint.
        
        Args:
            event: Event to cache
            
        Returns:
            Generated fingerprint
        """
        fingerprint = EventFingerprint.generate(event)
        
        # Store event info
        self._cache[event.event_id] = {
            "fingerprint": fingerprint,
            "source": event.market.source,
            "title": event.title,
            "added_at": datetime.now(timezone.utc),
        }
        
        # Index by fingerprint
        if fingerprint not in self._fingerprint_to_events:
            self._fingerprint_to_events[fingerprint] = []
        self._fingerprint_to_events[fingerprint].append(event.event_id)
        
        # Enforce size limit (LRU-style)
        while len(self._cache) > self.max_size:
            oldest_id = next(iter(self._cache))
            self._remove_event(oldest_id)
        
        return fingerprint
    
    def find_similar(
        self,
        event: RawSignalEvent,
        min_similarity: float = 0.7,
        exclude_source: Optional[str] = None,
    ) -> list[dict]:
        """
        Find cached events similar to the given event.
        
        Args:
            event: Event to match
            min_similarity: Minimum similarity threshold
            exclude_source: Source to exclude (to find cross-source matches)
            
        Returns:
            List of matching event info dicts
        """
        fingerprint = EventFingerprint.generate(event)
        matches = []
        
        # Check exact fingerprint match first (fastest)
        if fingerprint in self._fingerprint_to_events:
            for event_id in self._fingerprint_to_events[fingerprint]:
                if event_id == event.event_id:
                    continue
                    
                cached = self._cache.get(event_id)
                if not cached:
                    continue
                    
                if exclude_source and cached["source"] == exclude_source:
                    continue
                    
                matches.append({
                    "event_id": event_id,
                    "source": cached["source"],
                    "title": cached["title"],
                    "similarity": 1.0,
                    "fingerprint": fingerprint,
                })
        
        # Check similar fingerprints (slower but catches variations)
        for cached_fp, event_ids in self._fingerprint_to_events.items():
            if cached_fp == fingerprint:
                continue
                
            similarity = EventFingerprint.similarity(fingerprint, cached_fp)
            if similarity >= min_similarity:
                for event_id in event_ids:
                    if event_id == event.event_id:
                        continue
                        
                    cached = self._cache.get(event_id)
                    if not cached:
                        continue
                        
                    if exclude_source and cached["source"] == exclude_source:
                        continue
                    
                    matches.append({
                        "event_id": event_id,
                        "source": cached["source"],
                        "title": cached["title"],
                        "similarity": similarity,
                        "fingerprint": cached_fp,
                    })
        
        # Sort by similarity descending
        matches.sort(key=lambda m: m["similarity"], reverse=True)
        
        return matches
    
    def _remove_event(self, event_id: str) -> None:
        """Remove event from cache."""
        if event_id not in self._cache:
            return
            
        cached = self._cache.pop(event_id)
        fingerprint = cached.get("fingerprint")
        
        if fingerprint and fingerprint in self._fingerprint_to_events:
            self._fingerprint_to_events[fingerprint] = [
                eid for eid in self._fingerprint_to_events[fingerprint]
                if eid != event_id
            ]
            if not self._fingerprint_to_events[fingerprint]:
                del self._fingerprint_to_events[fingerprint]
    
    def clear_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.ttl_hours)
        expired = [
            event_id for event_id, info in self._cache.items()
            if info["added_at"] < cutoff
        ]
        
        for event_id in expired:
            self._remove_event(event_id)
        
        return len(expired)
    
    @property
    def size(self) -> int:
        """Current cache size."""
        return len(self._cache)


# Global cache instance
_fingerprint_cache: Optional[EventFingerprintCache] = None


def get_fingerprint_cache() -> EventFingerprintCache:
    """Get or create the global fingerprint cache."""
    global _fingerprint_cache
    if _fingerprint_cache is None:
        _fingerprint_cache = EventFingerprintCache()
    return _fingerprint_cache


def reset_fingerprint_cache() -> None:
    """Reset the global fingerprint cache (for testing)."""
    global _fingerprint_cache
    _fingerprint_cache = None
