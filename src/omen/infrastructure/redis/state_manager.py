"""
Centralized Redis State Manager.

Provides a single Redis connection pool and state management for:
- Caching (with TTL)
- Session state
- Distributed locks
- Counter/metrics
- Any stateful data that needs to be shared across instances

Usage:
    from omen.infrastructure.redis.state_manager import get_redis_state_manager
    
    manager = get_redis_state_manager()
    await manager.initialize()
    
    # Caching
    await manager.cache_set("key", {"data": "value"}, ttl=300)
    value = await manager.cache_get("key")
    
    # Counters
    await manager.counter_incr("requests:total")
    count = await manager.counter_get("requests:total")
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class RedisStateManager:
    """
    Centralized Redis state manager for distributed state.
    
    Provides:
    - Connection pooling
    - Caching with TTL
    - Counters
    - Hash storage
    - Distributed locks
    - Health checking
    
    Falls back gracefully to in-memory storage if Redis is unavailable.
    """
    
    # Key prefixes
    PREFIX_CACHE = "omen:cache:"
    PREFIX_COUNTER = "omen:counter:"
    PREFIX_HASH = "omen:hash:"
    PREFIX_LOCK = "omen:lock:"
    PREFIX_SESSION = "omen:session:"
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis state manager.
        
        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var.
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis = None
        self._connected = False
        self._fallback_cache: Dict[str, Any] = {}
        self._fallback_counters: Dict[str, int] = {}
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection.
        
        Returns:
            True if connected to Redis, False if using fallback mode.
        """
        if not self.redis_url:
            logger.warning(
                "REDIS_URL not configured. Using in-memory fallback. "
                "State will NOT be shared across instances."
            )
            return False
        
        try:
            import redis.asyncio as redis
            
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            # Test connection
            await self._redis.ping()
            self._connected = True
            
            logger.info("Redis state manager initialized: %s", self.redis_url[:30] + "...")
            return True
            
        except ImportError:
            logger.warning(
                "redis package not installed. Install with: pip install redis[hiredis]"
            )
            return False
        except Exception as e:
            logger.warning(
                "Failed to connect to Redis: %s. Using in-memory fallback.",
                e,
            )
            self._connected = False
            return False
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False
            logger.info("Redis state manager closed")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CACHING
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
    ) -> bool:
        """
        Set cache value with TTL.
        
        Args:
            key: Cache key
            value: Value (will be JSON serialized)
            ttl: Time-to-live in seconds (default 5 minutes)
            
        Returns:
            True if successful
        """
        full_key = f"{self.PREFIX_CACHE}{key}"
        serialized = json.dumps(value, default=str)
        
        if self._connected and self._redis:
            try:
                await self._redis.setex(full_key, ttl, serialized)
                return True
            except Exception as e:
                logger.error("Redis cache_set error: %s", e)
                
        # Fallback to in-memory
        self._fallback_cache[full_key] = {
            "value": serialized,
            "expires_at": datetime.now(timezone.utc).timestamp() + ttl,
        }
        return True
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """
        Get cache value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        full_key = f"{self.PREFIX_CACHE}{key}"
        
        if self._connected and self._redis:
            try:
                value = await self._redis.get(full_key)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.error("Redis cache_get error: %s", e)
        
        # Fallback to in-memory
        entry = self._fallback_cache.get(full_key)
        if entry:
            if datetime.now(timezone.utc).timestamp() < entry["expires_at"]:
                return json.loads(entry["value"])
            else:
                # Expired
                del self._fallback_cache[full_key]
        return None
    
    async def cache_delete(self, key: str) -> bool:
        """Delete cache key."""
        full_key = f"{self.PREFIX_CACHE}{key}"
        
        if self._connected and self._redis:
            try:
                await self._redis.delete(full_key)
                return True
            except Exception as e:
                logger.error("Redis cache_delete error: %s", e)
        
        self._fallback_cache.pop(full_key, None)
        return True
    
    async def cache_exists(self, key: str) -> bool:
        """Check if cache key exists."""
        full_key = f"{self.PREFIX_CACHE}{key}"
        
        if self._connected and self._redis:
            try:
                return await self._redis.exists(full_key) > 0
            except Exception as e:
                logger.error("Redis cache_exists error: %s", e)
        
        entry = self._fallback_cache.get(full_key)
        if entry and datetime.now(timezone.utc).timestamp() < entry["expires_at"]:
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COUNTERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def counter_incr(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.
        
        Args:
            key: Counter key
            amount: Amount to increment (default 1)
            
        Returns:
            New counter value
        """
        full_key = f"{self.PREFIX_COUNTER}{key}"
        
        if self._connected and self._redis:
            try:
                return await self._redis.incrby(full_key, amount)
            except Exception as e:
                logger.error("Redis counter_incr error: %s", e)
        
        # Fallback
        self._fallback_counters[full_key] = self._fallback_counters.get(full_key, 0) + amount
        return self._fallback_counters[full_key]
    
    async def counter_get(self, key: str) -> int:
        """Get counter value."""
        full_key = f"{self.PREFIX_COUNTER}{key}"
        
        if self._connected and self._redis:
            try:
                value = await self._redis.get(full_key)
                return int(value) if value else 0
            except Exception as e:
                logger.error("Redis counter_get error: %s", e)
        
        return self._fallback_counters.get(full_key, 0)
    
    async def counter_reset(self, key: str) -> None:
        """Reset counter to 0."""
        full_key = f"{self.PREFIX_COUNTER}{key}"
        
        if self._connected and self._redis:
            try:
                await self._redis.delete(full_key)
            except Exception as e:
                logger.error("Redis counter_reset error: %s", e)
        
        self._fallback_counters.pop(full_key, None)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HASH STORAGE
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def hash_set(self, key: str, field: str, value: Any) -> bool:
        """Set hash field value."""
        full_key = f"{self.PREFIX_HASH}{key}"
        serialized = json.dumps(value, default=str)
        
        if self._connected and self._redis:
            try:
                await self._redis.hset(full_key, field, serialized)
                return True
            except Exception as e:
                logger.error("Redis hash_set error: %s", e)
        
        # Fallback
        if full_key not in self._fallback_cache:
            self._fallback_cache[full_key] = {}
        self._fallback_cache[full_key][field] = serialized
        return True
    
    async def hash_get(self, key: str, field: str) -> Optional[Any]:
        """Get hash field value."""
        full_key = f"{self.PREFIX_HASH}{key}"
        
        if self._connected and self._redis:
            try:
                value = await self._redis.hget(full_key, field)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.error("Redis hash_get error: %s", e)
        
        # Fallback
        hash_data = self._fallback_cache.get(full_key, {})
        value = hash_data.get(field)
        return json.loads(value) if value else None
    
    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """Get all hash fields."""
        full_key = f"{self.PREFIX_HASH}{key}"
        
        if self._connected and self._redis:
            try:
                data = await self._redis.hgetall(full_key)
                return {k: json.loads(v) for k, v in data.items()}
            except Exception as e:
                logger.error("Redis hash_get_all error: %s", e)
        
        # Fallback
        hash_data = self._fallback_cache.get(full_key, {})
        return {k: json.loads(v) for k, v in hash_data.items()}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DISTRIBUTED LOCKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def lock_acquire(self, key: str, ttl: int = 30) -> bool:
        """
        Acquire distributed lock.
        
        Args:
            key: Lock name
            ttl: Lock timeout in seconds
            
        Returns:
            True if lock acquired, False if already locked
        """
        full_key = f"{self.PREFIX_LOCK}{key}"
        
        if self._connected and self._redis:
            try:
                # SET NX (only if not exists)
                result = await self._redis.set(full_key, "1", nx=True, ex=ttl)
                return result is not None
            except Exception as e:
                logger.error("Redis lock_acquire error: %s", e)
        
        # Fallback - simple in-memory lock
        if full_key in self._fallback_cache:
            return False
        self._fallback_cache[full_key] = True
        return True
    
    async def lock_release(self, key: str) -> bool:
        """Release distributed lock."""
        full_key = f"{self.PREFIX_LOCK}{key}"
        
        if self._connected and self._redis:
            try:
                await self._redis.delete(full_key)
                return True
            except Exception as e:
                logger.error("Redis lock_release error: %s", e)
        
        self._fallback_cache.pop(full_key, None)
        return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH & STATS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health."""
        if self._connected and self._redis:
            try:
                start = datetime.now(timezone.utc)
                await self._redis.ping()
                latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                
                info = await self._redis.info("memory")
                
                return {
                    "status": "healthy",
                    "connected": True,
                    "latency_ms": round(latency_ms, 2),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "max_memory": info.get("maxmemory_human", "unlimited"),
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": str(e),
                }
        
        return {
            "status": "fallback",
            "connected": False,
            "mode": "in-memory",
            "cache_entries": len(self._fallback_cache),
            "counter_entries": len(self._fallback_counters),
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        health = await self.health_check()
        
        if self._connected and self._redis:
            try:
                info = await self._redis.info()
                return {
                    **health,
                    "uptime_seconds": info.get("uptime_in_seconds", 0),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
            except Exception as e:
                logger.error("Redis get_stats error: %s", e)
        
        return health


# Global instance
_state_manager: Optional[RedisStateManager] = None


def get_redis_state_manager() -> RedisStateManager:
    """Get or create the global Redis state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = RedisStateManager()
    return _state_manager


async def initialize_redis() -> bool:
    """Initialize the global Redis state manager."""
    manager = get_redis_state_manager()
    return await manager.initialize()


async def shutdown_redis() -> None:
    """Shutdown the global Redis state manager."""
    global _state_manager
    if _state_manager:
        await _state_manager.close()
        _state_manager = None
