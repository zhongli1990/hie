"""
LI Health Checks

Provides health check infrastructure for monitoring LI Engine components.
Supports Kubernetes liveness and readiness probes.

Health checks include:
- Host status (running, stopped, error)
- Adapter connectivity
- Queue depth thresholds
- WAL pending entries
- External system connectivity
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger(__name__)


# Global health registry
_registry: "HealthRegistry | None" = None


def get_health_registry() -> "HealthRegistry":
    """Get the global health registry."""
    global _registry
    if _registry is None:
        _registry = HealthRegistry()
    return _registry


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_time_ms: float = 0.0


@dataclass
class HealthResult:
    """Overall health check result."""
    status: HealthStatus
    components: list[ComponentHealth] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                    "response_time_ms": c.response_time_ms,
                }
                for c in self.components
            ],
        }
    
    @property
    def is_healthy(self) -> bool:
        """Check if overall status is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def is_ready(self) -> bool:
        """Check if system is ready to accept traffic."""
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


class HealthCheck:
    """
    A single health check.
    
    Health checks are async functions that return a ComponentHealth.
    """
    
    def __init__(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[ComponentHealth]],
        critical: bool = True,
        timeout: float = 5.0,
    ):
        """
        Initialize a health check.
        
        Args:
            name: Check name
            check_fn: Async function that performs the check
            critical: If True, failure makes overall status unhealthy
            timeout: Check timeout in seconds
        """
        self.name = name
        self.check_fn = check_fn
        self.critical = critical
        self.timeout = timeout
        
        self._last_result: ComponentHealth | None = None
        self._last_check_time: float = 0
    
    async def run(self) -> ComponentHealth:
        """Run the health check."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self.check_fn(),
                timeout=self.timeout,
            )
            result.response_time_ms = (time.time() - start_time) * 1000
            self._last_result = result
            self._last_check_time = time.time()
            return result
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        
        except Exception as e:
            return ComponentHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                response_time_ms=(time.time() - start_time) * 1000,
            )


class HealthRegistry:
    """
    Registry for health checks.
    
    Manages all health checks and provides aggregated health status.
    """
    
    def __init__(self):
        self._checks: dict[str, HealthCheck] = {}
        self._log = logger.bind(component="HealthRegistry")
    
    def register(self, check: HealthCheck) -> None:
        """Register a health check."""
        self._checks[check.name] = check
        self._log.debug("health_check_registered", name=check.name)
    
    def unregister(self, name: str) -> None:
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
    
    def add_check(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[ComponentHealth]],
        critical: bool = True,
        timeout: float = 5.0,
    ) -> None:
        """Add a health check function."""
        self.register(HealthCheck(name, check_fn, critical, timeout))
    
    async def check_all(self) -> HealthResult:
        """Run all health checks and return aggregated result."""
        components = []
        
        # Run all checks concurrently
        tasks = [check.run() for check in self._checks.values()]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for check, result in zip(self._checks.values(), results):
                if isinstance(result, Exception):
                    components.append(ComponentHealth(
                        name=check.name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(result),
                    ))
                else:
                    components.append(result)
        
        # Determine overall status
        status = self._aggregate_status(components)
        
        return HealthResult(
            status=status,
            components=components,
        )
    
    async def check_liveness(self) -> HealthResult:
        """
        Liveness check - is the process alive?
        
        Returns healthy if the process is running.
        Used by Kubernetes liveness probe.
        """
        return HealthResult(
            status=HealthStatus.HEALTHY,
            components=[
                ComponentHealth(
                    name="process",
                    status=HealthStatus.HEALTHY,
                    message="Process is alive",
                )
            ],
        )
    
    async def check_readiness(self) -> HealthResult:
        """
        Readiness check - is the system ready to accept traffic?
        
        Runs all critical health checks.
        Used by Kubernetes readiness probe.
        """
        components = []
        
        # Only run critical checks
        critical_checks = [c for c in self._checks.values() if c.critical]
        
        tasks = [check.run() for check in critical_checks]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for check, result in zip(critical_checks, results):
                if isinstance(result, Exception):
                    components.append(ComponentHealth(
                        name=check.name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(result),
                    ))
                else:
                    components.append(result)
        
        status = self._aggregate_status(components)
        
        return HealthResult(
            status=status,
            components=components,
        )
    
    def _aggregate_status(self, components: list[ComponentHealth]) -> HealthStatus:
        """Aggregate component statuses into overall status."""
        if not components:
            return HealthStatus.HEALTHY
        
        statuses = [c.status for c in components]
        
        if HealthStatus.UNHEALTHY in statuses:
            # Check if any critical component is unhealthy
            for check_name, check in self._checks.items():
                if check.critical:
                    for comp in components:
                        if comp.name == check_name and comp.status == HealthStatus.UNHEALTHY:
                            return HealthStatus.UNHEALTHY
            return HealthStatus.DEGRADED
        
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY


# Built-in health check factories

def create_host_health_check(host: Any) -> Callable[[], Awaitable[ComponentHealth]]:
    """Create a health check for a Host."""
    async def check() -> ComponentHealth:
        from Engine.li.hosts.base import HostState
        
        if host.state == HostState.RUNNING:
            return ComponentHealth(
                name=f"host:{host.name}",
                status=HealthStatus.HEALTHY,
                message="Host is running",
                details={
                    "state": host.state.value,
                    "pool_size": host.pool_size,
                    "messages_received": host.metrics.messages_received,
                    "messages_failed": host.metrics.messages_failed,
                },
            )
        elif host.state == HostState.PAUSED:
            return ComponentHealth(
                name=f"host:{host.name}",
                status=HealthStatus.DEGRADED,
                message="Host is paused",
                details={"state": host.state.value},
            )
        else:
            return ComponentHealth(
                name=f"host:{host.name}",
                status=HealthStatus.UNHEALTHY,
                message=f"Host is in state: {host.state.value}",
                details={"state": host.state.value},
            )
    
    return check


def create_queue_health_check(
    queue: Any,
    queue_name: str,
    max_depth: int = 10000,
) -> Callable[[], Awaitable[ComponentHealth]]:
    """Create a health check for a message queue."""
    async def check() -> ComponentHealth:
        try:
            depth = await queue.get_queue_length(queue_name)
            processing = await queue.get_processing_count(queue_name)
            dlq = await queue.get_dlq_length(queue_name)
            
            if depth > max_depth:
                return ComponentHealth(
                    name=f"queue:{queue_name}",
                    status=HealthStatus.DEGRADED,
                    message=f"Queue depth ({depth}) exceeds threshold ({max_depth})",
                    details={
                        "depth": depth,
                        "processing": processing,
                        "dlq": dlq,
                    },
                )
            
            return ComponentHealth(
                name=f"queue:{queue_name}",
                status=HealthStatus.HEALTHY,
                message="Queue is healthy",
                details={
                    "depth": depth,
                    "processing": processing,
                    "dlq": dlq,
                },
            )
        except Exception as e:
            return ComponentHealth(
                name=f"queue:{queue_name}",
                status=HealthStatus.UNHEALTHY,
                message=f"Queue check failed: {e}",
            )
    
    return check


def create_wal_health_check(
    wal: Any,
    max_pending: int = 1000,
) -> Callable[[], Awaitable[ComponentHealth]]:
    """Create a health check for the WAL."""
    async def check() -> ComponentHealth:
        pending = wal.pending_count
        processing = wal.processing_count
        
        if pending > max_pending:
            return ComponentHealth(
                name="wal",
                status=HealthStatus.DEGRADED,
                message=f"WAL pending ({pending}) exceeds threshold ({max_pending})",
                details={
                    "pending": pending,
                    "processing": processing,
                },
            )
        
        return ComponentHealth(
            name="wal",
            status=HealthStatus.HEALTHY,
            message="WAL is healthy",
            details={
                "pending": pending,
                "processing": processing,
            },
        )
    
    return check


async def health_handler(request: Any) -> tuple[str, int, dict[str, str]]:
    """
    HTTP handler for health endpoint.
    
    Returns JSON health status.
    """
    import json
    
    registry = get_health_registry()
    result = await registry.check_all()
    
    status_code = 200 if result.is_healthy else 503
    body = json.dumps(result.to_dict())
    
    return body, status_code, {"Content-Type": "application/json"}


async def liveness_handler(request: Any) -> tuple[str, int, dict[str, str]]:
    """HTTP handler for liveness probe."""
    import json
    
    registry = get_health_registry()
    result = await registry.check_liveness()
    
    status_code = 200 if result.is_healthy else 503
    body = json.dumps(result.to_dict())
    
    return body, status_code, {"Content-Type": "application/json"}


async def readiness_handler(request: Any) -> tuple[str, int, dict[str, str]]:
    """HTTP handler for readiness probe."""
    import json
    
    registry = get_health_registry()
    result = await registry.check_readiness()
    
    status_code = 200 if result.is_ready else 503
    body = json.dumps(result.to_dict())
    
    return body, status_code, {"Content-Type": "application/json"}
