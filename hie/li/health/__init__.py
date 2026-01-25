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
    create_host_health_check,
    create_queue_health_check,
    create_wal_health_check,
    health_handler,
    liveness_handler,
    readiness_handler,
)
from hie.li.health.shutdown import (
    GracefulShutdown,
    ShutdownHandler,
    ShutdownConfig,
    ShutdownState,
    shutdown_on_signal,
)

__all__ = [
    # Health checks
    "HealthCheck",
    "HealthStatus",
    "HealthResult",
    "ComponentHealth",
    "HealthRegistry",
    "get_health_registry",
    "create_host_health_check",
    "create_queue_health_check",
    "create_wal_health_check",
    "health_handler",
    "liveness_handler",
    "readiness_handler",
    # Shutdown
    "GracefulShutdown",
    "ShutdownHandler",
    "ShutdownConfig",
    "ShutdownState",
    "shutdown_on_signal",
]
