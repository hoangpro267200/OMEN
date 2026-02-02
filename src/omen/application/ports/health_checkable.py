"""
Health Check Interface for all data sources.

All external data sources MUST implement this interface to enable:
- Proactive failure detection
- Automatic source health monitoring
- Dashboard visibility
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status levels for data sources."""
    
    HEALTHY = "healthy"      # Source responding normally
    DEGRADED = "degraded"    # Partial functionality (e.g., slow, some endpoints down)
    UNHEALTHY = "unhealthy"  # Source is down or unresponsive
    UNKNOWN = "unknown"      # Cannot determine status (e.g., not configured)


class HealthCheckResult(BaseModel):
    """Result of a health check operation."""
    
    status: HealthStatus = Field(..., description="Current health status")
    source_name: str = Field(..., description="Unique identifier for the source")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    last_success: Optional[datetime] = Field(None, description="Timestamp of last successful check")
    last_failure: Optional[datetime] = Field(None, description="Timestamp of last failed check")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    consecutive_failures: int = Field(0, description="Number of consecutive failures")
    details: Optional[dict[str, Any]] = Field(None, description="Additional source-specific details")
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def healthy(
        cls,
        source_name: str,
        latency_ms: float,
        **details: Any,
    ) -> "HealthCheckResult":
        """Factory for healthy result."""
        return cls(
            status=HealthStatus.HEALTHY,
            source_name=source_name,
            latency_ms=latency_ms,
            last_success=datetime.now(timezone.utc),
            details=details if details else None,
        )
    
    @classmethod
    def unhealthy(
        cls,
        source_name: str,
        error_message: str,
        latency_ms: Optional[float] = None,
        **details: Any,
    ) -> "HealthCheckResult":
        """Factory for unhealthy result."""
        return cls(
            status=HealthStatus.UNHEALTHY,
            source_name=source_name,
            latency_ms=latency_ms,
            error_message=error_message,
            last_failure=datetime.now(timezone.utc),
            details=details if details else None,
        )
    
    @classmethod
    def degraded(
        cls,
        source_name: str,
        latency_ms: float,
        reason: str,
        **details: Any,
    ) -> "HealthCheckResult":
        """Factory for degraded result."""
        return cls(
            status=HealthStatus.DEGRADED,
            source_name=source_name,
            latency_ms=latency_ms,
            error_message=reason,
            last_success=datetime.now(timezone.utc),
            details=details if details else None,
        )
    
    @classmethod
    def unknown(
        cls,
        source_name: str,
        reason: str = "Status cannot be determined",
    ) -> "HealthCheckResult":
        """Factory for unknown result."""
        return cls(
            status=HealthStatus.UNKNOWN,
            source_name=source_name,
            error_message=reason,
        )


class HealthCheckable(ABC):
    """
    Interface for health-checkable components.
    
    All data sources MUST implement this interface to enable
    centralized health monitoring.
    
    Example Implementation:
    ```python
    class MyClient(HealthCheckable):
        @property
        def source_name(self) -> str:
            return "my_source"
        
        async def health_check(self) -> HealthCheckResult:
            try:
                start = time.time()
                await self._ping()
                latency = (time.time() - start) * 1000
                return HealthCheckResult.healthy(self.source_name, latency)
            except Exception as e:
                return HealthCheckResult.unhealthy(self.source_name, str(e))
        
        async def is_available(self) -> bool:
            result = await self.health_check()
            return result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    ```
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Unique name of the source.
        
        This should be a stable identifier used for:
        - Metrics collection
        - Configuration lookup
        - Circuit breaker registration
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """
        Perform health check.
        
        Should:
        - Make a lightweight request to the source
        - Measure latency
        - Return HealthCheckResult
        
        Should NOT:
        - Throw exceptions (catch and return UNHEALTHY)
        - Take more than 10 seconds (use timeout)
        - Perform heavy operations (e.g., large data fetches)
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Quick check if source is available.
        
        Returns True if source can accept requests (HEALTHY or DEGRADED).
        """
        pass
