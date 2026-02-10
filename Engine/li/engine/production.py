"""
LI Production Engine

The main orchestrator for LI Engine that manages the complete lifecycle
of a production configuration. Loads IRIS XML configs and instantiates
all hosts, adapters, and supporting infrastructure.

This is the entry point for running LI Engine in production.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, TYPE_CHECKING

import structlog

from Engine.li.config import IRISXMLLoader, ProductionConfig, ItemConfig
from Engine.li.hosts import (
    Host,
    HostState,
    BusinessService,
    BusinessProcess,
    BusinessOperation,
    HL7TCPService,
    HL7TCPOperation,
    HL7RoutingEngine,
)
from Engine.li.registry import ClassRegistry
from Engine.li.persistence import WAL, WALConfig, MessageStore
from Engine.li.metrics import get_metrics_registry, set_host_status
from Engine.li.health import (
    get_health_registry,
    GracefulShutdown,
    ShutdownConfig,
    create_host_health_check,
)
from Engine.core.messaging import ServiceRegistry, MessagingPattern

logger = structlog.get_logger(__name__)


class ProductionState(str, Enum):
    """Production lifecycle state."""
    CREATED = "created"
    LOADING = "loading"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class EngineConfig:
    """Production engine configuration."""
    # WAL settings
    wal_enabled: bool = True
    wal_directory: str = "./wal"
    
    # Message store settings
    store_enabled: bool = True
    store_directory: str = "./message_store"
    
    # Metrics settings
    metrics_enabled: bool = True
    metrics_port: int = 9090
    
    # Health check settings
    health_enabled: bool = True
    health_port: int = 8080
    
    # Shutdown settings
    shutdown_timeout: float = 30.0
    drain_timeout: float = 10.0
    
    # Startup settings
    start_disabled_items: bool = False
    parallel_start: bool = True
    startup_delay: float = 0.5  # Delay between starting items


@dataclass
class ProductionMetrics:
    """Runtime metrics for the production."""
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    items_started: int = 0
    items_failed: int = 0
    total_messages_received: int = 0
    total_messages_sent: int = 0
    total_messages_failed: int = 0


class ProductionEngine:
    """
    Main orchestrator for LI Engine.
    
    Manages the complete lifecycle of a production:
    1. Load configuration from IRIS XML
    2. Instantiate hosts based on config
    3. Start all enabled hosts
    4. Monitor health and metrics
    5. Graceful shutdown
    
    Usage:
        engine = ProductionEngine()
        await engine.load("path/to/production.cls")
        await engine.start()
        
        # Run until shutdown signal
        await engine.wait_for_shutdown()
        
        # Or manually stop
        await engine.stop()
    """
    
    def __init__(self, config: EngineConfig | None = None):
        self._config = config or EngineConfig()
        self._state = ProductionState.CREATED
        self._production_config: ProductionConfig | None = None
        
        # Hosts by category
        self._services: dict[str, BusinessService] = {}
        self._processes: dict[str, BusinessProcess] = {}
        self._operations: dict[str, BusinessOperation] = {}
        self._all_hosts: dict[str, Host] = {}
        
        # Infrastructure
        self._wal: WAL | None = None
        self._store: MessageStore | None = None
        self._shutdown: GracefulShutdown | None = None

        # Service messaging
        self._service_registry = ServiceRegistry()

        # Metrics
        self._metrics = ProductionMetrics()

        self._log = logger.bind(component="ProductionEngine")
    
    @property
    def state(self) -> ProductionState:
        """Current production state."""
        return self._state
    
    @property
    def production_name(self) -> str | None:
        """Name of the loaded production."""
        return self._production_config.name if self._production_config else None
    
    @property
    def hosts(self) -> dict[str, Host]:
        """All hosts by name."""
        return self._all_hosts
    
    @property
    def services(self) -> dict[str, BusinessService]:
        """All services by name."""
        return self._services
    
    @property
    def processes(self) -> dict[str, BusinessProcess]:
        """All processes by name."""
        return self._processes
    
    @property
    def operations(self) -> dict[str, BusinessOperation]:
        """All operations by name."""
        return self._operations
    
    def get_host(self, name: str) -> Host | None:
        """Get a host by name."""
        return self._all_hosts.get(name)
    
    async def load(self, path: str | Path) -> None:
        """
        Load production configuration from file.
        
        Args:
            path: Path to IRIS .cls or XML file
        """
        if self._state != ProductionState.CREATED:
            raise RuntimeError(f"Cannot load in state: {self._state}")
        
        self._state = ProductionState.LOADING
        self._log.info("loading_production", path=str(path))
        
        try:
            # Load configuration
            loader = IRISXMLLoader()
            self._production_config = loader.load(path)
            
            # Create hosts from config
            await self._create_hosts()
            
            self._log.info(
                "production_loaded",
                name=self._production_config.name,
                services=len(self._services),
                processes=len(self._processes),
                operations=len(self._operations),
            )
            
            self._state = ProductionState.CREATED
            
        except Exception as e:
            self._state = ProductionState.ERROR
            self._log.error("load_failed", error=str(e))
            raise
    
    async def load_from_config(self, config: ProductionConfig) -> None:
        """
        Load production from an existing ProductionConfig.
        
        Args:
            config: ProductionConfig object
        """
        if self._state != ProductionState.CREATED:
            raise RuntimeError(f"Cannot load in state: {self._state}")
        
        self._state = ProductionState.LOADING
        self._production_config = config
        
        try:
            await self._create_hosts()
            self._state = ProductionState.CREATED
        except Exception as e:
            self._state = ProductionState.ERROR
            raise
    
    async def _create_hosts(self) -> None:
        """Create host instances from production config."""
        if not self._production_config:
            return
        
        for item_config in self._production_config.items:
            try:
                host = self._create_host_from_config(item_config)
                if host:
                    self._register_host(host, item_config)
            except Exception as e:
                self._log.error(
                    "host_creation_failed",
                    name=item_config.name,
                    class_name=item_config.class_name,
                    error=str(e),
                )
    
    def _create_host_from_config(self, config: ItemConfig) -> Host | None:
        """Create a host instance from ItemConfig."""
        class_name = config.class_name
        
        # Try to get class from registry
        host_class = ClassRegistry.get_host_class(class_name)
        
        if not host_class:
            # Map known class names
            if "HL7TCPService" in class_name or "Service.TCPService" in class_name:
                host_class = HL7TCPService
            elif "HL7TCPOperation" in class_name or "Operation.TCPOperation" in class_name:
                host_class = HL7TCPOperation
            elif "RoutingEngine" in class_name:
                host_class = HL7RoutingEngine
            else:
                self._log.warning("unknown_host_class", class_name=class_name)
                return None
        
        # Create host instance
        return host_class(name=config.name, config=config)
    
    def _register_host(self, host: Host, config: ItemConfig) -> None:
        """Register a host in the appropriate category and service registry."""
        self._all_hosts[host.name] = host

        if isinstance(host, BusinessService):
            self._services[host.name] = host
        elif isinstance(host, BusinessOperation):
            self._operations[host.name] = host
        elif isinstance(host, BusinessProcess):
            self._processes[host.name] = host

        # Register with service registry for inter-service messaging
        self._service_registry.register(host.name, host)

        # Set up messaging for this host
        messaging_pattern = MessagingPattern.ASYNC_RELIABLE  # Default
        if hasattr(config, 'messaging_pattern'):
            messaging_pattern = config.messaging_pattern

        host.set_service_registry(
            self._service_registry,
            host.name,
            messaging_pattern
        )

        self._log.debug(
            "host_registered",
            name=host.name,
            type=type(host).__name__,
            enabled=config.enabled,
            messaging_pattern=messaging_pattern.value
        )
    
    async def start(self) -> None:
        """
        Start the production.
        
        Starts all enabled hosts in dependency order:
        1. Operations (outbound)
        2. Processes (routing/transformation)
        3. Services (inbound)
        """
        if self._state not in (ProductionState.CREATED, ProductionState.STOPPED):
            raise RuntimeError(f"Cannot start in state: {self._state}")
        
        self._state = ProductionState.STARTING
        self._log.info("starting_production", name=self.production_name)
        
        try:
            # Initialize infrastructure
            await self._init_infrastructure()
            
            # Start hosts in order
            await self._start_operations()
            await self._start_processes()
            await self._start_services()
            
            # Set up shutdown handler
            self._setup_shutdown()
            
            self._state = ProductionState.RUNNING
            self._metrics.started_at = datetime.now(timezone.utc)
            
            self._log.info(
                "production_started",
                name=self.production_name,
                items_started=self._metrics.items_started,
            )
            
        except Exception as e:
            self._state = ProductionState.ERROR
            self._log.error("start_failed", error=str(e))
            raise
    
    async def _init_infrastructure(self) -> None:
        """Initialize supporting infrastructure."""
        # WAL
        if self._config.wal_enabled:
            self._wal = WAL(WALConfig(directory=self._config.wal_directory))
            await self._wal.start()
            self._log.debug("wal_initialized")
        
        # Message Store
        if self._config.store_enabled:
            from Engine.li.persistence import FileStorageBackend
            backend = FileStorageBackend(self._config.store_directory)
            self._store = MessageStore(backend)
            await self._store.start()
            self._log.debug("message_store_initialized")
    
    async def _start_operations(self) -> None:
        """Start all enabled operations."""
        for name, host in self._operations.items():
            await self._start_host(host)
    
    async def _start_processes(self) -> None:
        """Start all enabled processes."""
        for name, host in self._processes.items():
            await self._start_host(host)
    
    async def _start_services(self) -> None:
        """Start all enabled services."""
        for name, host in self._services.items():
            await self._start_host(host)
    
    async def _start_host(self, host: Host) -> None:
        """Start a single host."""
        if not host.enabled and not self._config.start_disabled_items:
            self._log.debug("skipping_disabled_host", name=host.name)
            return
        
        try:
            await host.start()
            self._metrics.items_started += 1
            
            # Register health check
            if self._config.health_enabled:
                health_registry = get_health_registry()
                health_registry.add_check(
                    f"host:{host.name}",
                    create_host_health_check(host),
                    critical=True,
                )
            
            # Update metrics
            if self._config.metrics_enabled:
                set_host_status(host.name, type(host).__name__, running=True)
            
            self._log.debug("host_started", name=host.name)
            
            # Delay between starts
            if self._config.startup_delay > 0:
                await asyncio.sleep(self._config.startup_delay)
                
        except Exception as e:
            self._metrics.items_failed += 1
            self._log.error("host_start_failed", name=host.name, error=str(e))
    
    def _setup_shutdown(self) -> None:
        """Set up graceful shutdown handler."""
        self._shutdown = GracefulShutdown(ShutdownConfig(
            timeout=self._config.shutdown_timeout,
            drain_timeout=self._config.drain_timeout,
        ))
        
        # Register all hosts
        for host in self._all_hosts.values():
            if host.state == HostState.RUNNING:
                self._shutdown.register_host(host)
        
        # Register cleanup handlers
        self._shutdown.register_handler(self._cleanup_infrastructure)
        
        # Install signal handlers
        self._shutdown.install_signal_handlers()
    
    async def _cleanup_infrastructure(self) -> None:
        """Clean up infrastructure on shutdown."""
        if self._wal:
            await self._wal.stop()
        if self._store:
            await self._store.stop()
    
    async def stop(self) -> None:
        """Stop the production gracefully."""
        if self._state != ProductionState.RUNNING:
            return
        
        self._state = ProductionState.STOPPING
        self._log.info("stopping_production", name=self.production_name)
        
        try:
            # Stop hosts in reverse order
            for host in reversed(list(self._services.values())):
                await self._stop_host(host)
            
            for host in reversed(list(self._processes.values())):
                await self._stop_host(host)
            
            for host in reversed(list(self._operations.values())):
                await self._stop_host(host)
            
            # Cleanup infrastructure
            await self._cleanup_infrastructure()
            
            self._state = ProductionState.STOPPED
            self._metrics.stopped_at = datetime.now(timezone.utc)
            
            self._log.info("production_stopped", name=self.production_name)
            
        except Exception as e:
            self._state = ProductionState.ERROR
            self._log.error("stop_failed", error=str(e))
            raise
    
    async def _stop_host(self, host: Host) -> None:
        """Stop a single host."""
        if host.state not in (HostState.RUNNING, HostState.PAUSED):
            return
        
        try:
            await host.stop()
            
            if self._config.metrics_enabled:
                set_host_status(host.name, type(host).__name__, running=False)
            
            self._log.debug("host_stopped", name=host.name)
            
        except Exception as e:
            self._log.error("host_stop_failed", name=host.name, error=str(e))
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        if self._shutdown:
            await self._shutdown.wait()
            await self._shutdown.wait_complete()
    
    async def restart_host(self, name: str) -> None:
        """Restart a specific host."""
        host = self._all_hosts.get(name)
        if not host:
            raise KeyError(f"Host not found: {name}")
        
        self._log.info("restarting_host", name=name)
        
        await self._stop_host(host)
        await asyncio.sleep(1.0)
        await self._start_host(host)
    
    async def enable_host(self, name: str) -> None:
        """Enable and start a disabled host."""
        host = self._all_hosts.get(name)
        if not host:
            raise KeyError(f"Host not found: {name}")
        
        host._enabled = True
        await self._start_host(host)
    
    async def disable_host(self, name: str) -> None:
        """Disable and stop a host."""
        host = self._all_hosts.get(name)
        if not host:
            raise KeyError(f"Host not found: {name}")
        
        host._enabled = False
        await self._stop_host(host)
    
    async def reload_host_config(
        self,
        name: str,
        pool_size: int | None = None,
        enabled: bool | None = None,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Hot reload configuration for a specific host.
        
        This allows updating host settings without stopping the entire production.
        Messages in the queue are preserved during reload.
        
        Args:
            name: Host name to reload
            pool_size: New pool size (None = keep current)
            enabled: New enabled state (None = keep current)
            adapter_settings: New adapter settings (None = keep current)
            host_settings: New host settings (None = keep current)
            
        Returns:
            Updated host status
        """
        host = self._all_hosts.get(name)
        if not host:
            raise KeyError(f"Host not found: {name}")
        
        self._log.info(
            "reload_host_config",
            name=name,
            pool_size=pool_size,
            enabled=enabled,
        )
        
        await host.reload_config(
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )
        
        # Update metrics
        if self._config.metrics_enabled:
            set_host_status(host.name, type(host).__name__, running=host.state == HostState.RUNNING)
        
        return {
            "name": host.name,
            "state": host.state.value,
            "enabled": host.enabled,
            "pool_size": host.pool_size,
        }
    
    def get_status(self) -> dict[str, Any]:
        """Get production status summary."""
        return {
            "name": self.production_name,
            "state": self._state.value,
            "started_at": self._metrics.started_at.isoformat() if self._metrics.started_at else None,
            "items": {
                "total": len(self._all_hosts),
                "services": len(self._services),
                "processes": len(self._processes),
                "operations": len(self._operations),
                "started": self._metrics.items_started,
                "failed": self._metrics.items_failed,
            },
            "hosts": {
                name: {
                    "type": type(host).__name__,
                    "state": host.state.value,
                    "enabled": host.enabled,
                    "messages_received": host.metrics.messages_received,
                    "messages_failed": host.metrics.messages_failed,
                }
                for name, host in self._all_hosts.items()
            },
        }


async def run_production(
    config_path: str | Path,
    engine_config: EngineConfig | None = None,
) -> None:
    """
    Convenience function to run a production.
    
    Loads config, starts production, and waits for shutdown.
    
    Args:
        config_path: Path to IRIS .cls or XML file
        engine_config: Optional engine configuration
    """
    engine = ProductionEngine(engine_config)
    
    await engine.load(config_path)
    await engine.start()
    
    logger.info("production_running", name=engine.production_name)
    
    await engine.wait_for_shutdown()
