"""
LI Health Module

Provides health checks and graceful shutdown for production deployments.
"""

from hie.li.health.checks import (
    HealthCheck,
    HealthStatus,
    HealthResult,
    ComponentHealth,
    HealthRegistry,
    get_health_registry,
)
from hie.li.health.shutdown import (
    GracefulShutdown,
    ShutdownHandler,
)

__all__ = [
    # Health checks
    "HealthCheck",
    "HealthStatus",
    "HealthResult",
    "ComponentHealth",
    "HealthRegistry",
    "get_health_registry",
    # Shutdown
    "GracefulShutdown",
    "ShutdownHandler",
]
