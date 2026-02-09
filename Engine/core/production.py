"""
HIE Production Model

The Production is the runtime orchestrator that contains all items and routes.
It manages the lifecycle of the entire integration engine instance.
"""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from Engine.core.item import Item, ItemConfig, ItemState
from Engine.core.message import Message
from Engine.core.route import Route, RouteConfig, RouteState

logger = structlog.get_logger(__name__)


class ProductionState(str, Enum):
    """Production lifecycle state."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ProductionConfig(BaseModel):
    """Configuration for a production."""
    model_config = ConfigDict(extra="allow")
    
    name: str = Field(description="Production name")
    description: str = Field(default="", description="Production description")
    enabled: bool = Field(default=True, description="Whether production is enabled")
    
    # Startup behavior
    auto_start_items: bool = Field(
        default=True,
        description="Automatically start items when production starts"
    )
    auto_start_routes: bool = Field(
        default=True,
        description="Automatically start routes when production starts"
    )
    
    # Shutdown behavior
    graceful_shutdown_timeout: float = Field(
        default=30.0,
        gt=0,
        description="Seconds to wait for graceful shutdown"
    )
    
    # Health check
    health_check_interval: float = Field(
        default=10.0,
        gt=0,
        description="Seconds between health checks"
    )


@dataclass
class ProductionMetrics:
    """Runtime metrics for the production."""
    total_messages_received: int = 0
    total_messages_processed: int = 0
    total_messages_failed: int = 0
    
    items_running: int = 0
    items_error: int = 0
    routes_running: int = 0
    routes_error: int = 0
    
    started_at: datetime | None = None
    uptime_seconds: float = 0.0
    
    last_health_check_at: datetime | None = None
    health_check_failures: int = 0


class Production:
    """
    The runtime orchestrator for HIE.
    
    A Production contains:
    - Items: Runtime components (receivers, processors, senders)
    - Routes: Message flow paths linking items
    
    The Production manages the lifecycle of all components and provides
    centralized monitoring and control.
    """
    
    def __init__(self, config: ProductionConfig) -> None:
        self._config = config
        self._state = ProductionState.CREATED
        self._metrics = ProductionMetrics()
        
        self._items: dict[str, Item] = {}
        self._routes: dict[str, Route] = {}
        
        self._health_check_task: asyncio.Task[Any] | None = None
        self._shutdown_event = asyncio.Event()
        
        self._logger = logger.bind(production=config.name)
    
    @property
    def name(self) -> str:
        """Production name."""
        return self._config.name
    
    @property
    def state(self) -> ProductionState:
        """Current lifecycle state."""
        return self._state
    
    @property
    def config(self) -> ProductionConfig:
        """Production configuration."""
        return self._config
    
    @property
    def metrics(self) -> ProductionMetrics:
        """Runtime metrics."""
        return self._metrics
    
    @property
    def items(self) -> dict[str, Item]:
        """Registered items."""
        return self._items.copy()
    
    @property
    def routes(self) -> dict[str, Route]:
        """Registered routes."""
        return self._routes.copy()
    
    @property
    def is_running(self) -> bool:
        """Check if production is running."""
        return self._state == ProductionState.RUNNING
    
    def register_item(self, item: Item) -> None:
        """Register an item with the production."""
        if item.id in self._items:
            raise ValueError(f"Item already registered: {item.id}")
        
        self._items[item.id] = item
        self._logger.info("item_registered", item_id=item.id, item_type=item.item_type.value)
    
    def unregister_item(self, item_id: str) -> Item | None:
        """Unregister an item from the production."""
        item = self._items.pop(item_id, None)
        if item:
            self._logger.info("item_unregistered", item_id=item_id)
        return item
    
    def get_item(self, item_id: str) -> Item | None:
        """Get an item by ID."""
        return self._items.get(item_id)
    
    def register_route(self, route: Route) -> None:
        """Register a route with the production."""
        if route.id in self._routes:
            raise ValueError(f"Route already registered: {route.id}")
        
        # Bind items to route
        route.bind_items(
            self._items,
            error_handler=self._items.get(route.config.error_handler) if route.config.error_handler else None,
            dead_letter=self._items.get(route.config.dead_letter) if route.config.dead_letter else None,
        )
        
        self._routes[route.id] = route
        self._logger.info("route_registered", route_id=route.id, path=route.config.path)
    
    def unregister_route(self, route_id: str) -> Route | None:
        """Unregister a route from the production."""
        route = self._routes.pop(route_id, None)
        if route:
            self._logger.info("route_unregistered", route_id=route_id)
        return route
    
    def get_route(self, route_id: str) -> Route | None:
        """Get a route by ID."""
        return self._routes.get(route_id)
    
    async def start(self) -> None:
        """Start the production and all enabled components."""
        if self._state not in (ProductionState.CREATED, ProductionState.STOPPED):
            raise RuntimeError(f"Cannot start production in state: {self._state}")
        
        self._state = ProductionState.STARTING
        self._metrics.started_at = datetime.now(timezone.utc)
        self._shutdown_event.clear()
        
        self._logger.info("production_starting")
        
        try:
            # Start items
            if self._config.auto_start_items:
                await self._start_all_items()
            
            # Start routes
            if self._config.auto_start_routes:
                await self._start_all_routes()
            
            # Start health check
            self._health_check_task = asyncio.create_task(
                self._health_check_loop(),
                name=f"{self.name}-health-check"
            )
            
            self._state = ProductionState.RUNNING
            self._logger.info(
                "production_started",
                items=len(self._items),
                routes=len(self._routes)
            )
        
        except Exception as e:
            self._state = ProductionState.ERROR
            self._logger.error("production_start_failed", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the production gracefully."""
        if self._state not in (ProductionState.RUNNING, ProductionState.PAUSED, ProductionState.ERROR):
            return
        
        self._state = ProductionState.STOPPING
        self._shutdown_event.set()
        
        self._logger.info("production_stopping")
        
        # Stop health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop routes first
        await self._stop_all_routes()
        
        # Then stop items
        await self._stop_all_items()
        
        self._state = ProductionState.STOPPED
        self._logger.info("production_stopped")
    
    async def pause(self) -> None:
        """Pause all routes (items continue running but don't process)."""
        if self._state != ProductionState.RUNNING:
            raise RuntimeError(f"Cannot pause production in state: {self._state}")
        
        for route in self._routes.values():
            if route.state == RouteState.RUNNING:
                await route.pause()
        
        self._state = ProductionState.PAUSED
        self._logger.info("production_paused")
    
    async def resume(self) -> None:
        """Resume all paused routes."""
        if self._state != ProductionState.PAUSED:
            raise RuntimeError(f"Cannot resume production in state: {self._state}")
        
        for route in self._routes.values():
            if route.state == RouteState.PAUSED:
                await route.resume()
        
        self._state = ProductionState.RUNNING
        self._logger.info("production_resumed")
    
    async def _start_all_items(self) -> None:
        """Start all enabled items."""
        tasks = []
        for item in self._items.values():
            if item.config.enabled:
                tasks.append(self._start_item(item))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _start_item(self, item: Item) -> None:
        """Start a single item."""
        try:
            await item.start()
            self._metrics.items_running += 1
            self._logger.info("item_started", item_id=item.id)
        except Exception as e:
            self._metrics.items_error += 1
            self._logger.error("item_start_failed", item_id=item.id, error=str(e))
            raise
    
    async def _stop_all_items(self) -> None:
        """Stop all running items."""
        tasks = []
        for item in self._items.values():
            if item.state in (ItemState.RUNNING, ItemState.PAUSED):
                tasks.append(self._stop_item(item))
        
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self._config.graceful_shutdown_timeout
                )
            except asyncio.TimeoutError:
                self._logger.warning("item_stop_timeout")
    
    async def _stop_item(self, item: Item) -> None:
        """Stop a single item."""
        try:
            await item.stop()
            self._metrics.items_running -= 1
            self._logger.info("item_stopped", item_id=item.id)
        except Exception as e:
            self._logger.error("item_stop_failed", item_id=item.id, error=str(e))
    
    async def _start_all_routes(self) -> None:
        """Start all enabled routes."""
        for route in self._routes.values():
            if route.config.enabled:
                await self._start_route(route)
    
    async def _start_route(self, route: Route) -> None:
        """Start a single route."""
        try:
            await route.start()
            self._metrics.routes_running += 1
            self._logger.info("route_started", route_id=route.id)
        except Exception as e:
            self._metrics.routes_error += 1
            self._logger.error("route_start_failed", route_id=route.id, error=str(e))
            raise
    
    async def _stop_all_routes(self) -> None:
        """Stop all running routes."""
        for route in self._routes.values():
            if route.state in (RouteState.RUNNING, RouteState.PAUSED):
                await self._stop_route(route)
    
    async def _stop_route(self, route: Route) -> None:
        """Stop a single route."""
        try:
            await route.stop()
            self._metrics.routes_running -= 1
            self._logger.info("route_stopped", route_id=route.id)
        except Exception as e:
            self._logger.error("route_stop_failed", route_id=route.id, error=str(e))
    
    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._config.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._metrics.health_check_failures += 1
                self._logger.error("health_check_failed", error=str(e))
    
    async def _perform_health_check(self) -> None:
        """Perform a health check on all components."""
        self._metrics.last_health_check_at = datetime.now(timezone.utc)
        
        # Update uptime
        if self._metrics.started_at:
            delta = datetime.now(timezone.utc) - self._metrics.started_at
            self._metrics.uptime_seconds = delta.total_seconds()
        
        # Count running/error items
        items_running = sum(1 for i in self._items.values() if i.state == ItemState.RUNNING)
        items_error = sum(1 for i in self._items.values() if i.state == ItemState.ERROR)
        
        self._metrics.items_running = items_running
        self._metrics.items_error = items_error
        
        # Count running/error routes
        routes_running = sum(1 for r in self._routes.values() if r.state == RouteState.RUNNING)
        routes_error = sum(1 for r in self._routes.values() if r.state == RouteState.ERROR)
        
        self._metrics.routes_running = routes_running
        self._metrics.routes_error = routes_error
        
        # Aggregate message counts
        total_received = sum(i.metrics.messages_received for i in self._items.values())
        total_processed = sum(i.metrics.messages_processed for i in self._items.values())
        total_failed = sum(i.metrics.messages_failed for i in self._items.values())
        
        self._metrics.total_messages_received = total_received
        self._metrics.total_messages_processed = total_processed
        self._metrics.total_messages_failed = total_failed
    
    def health_check(self) -> dict[str, Any]:
        """Return comprehensive health status."""
        items_health = {item_id: item.health_check() for item_id, item in self._items.items()}
        routes_health = {route_id: route.health_check() for route_id, route in self._routes.items()}
        
        overall_healthy = (
            self._state == ProductionState.RUNNING
            and self._metrics.items_error == 0
            and self._metrics.routes_error == 0
        )
        
        return {
            "name": self.name,
            "state": self._state.value,
            "healthy": overall_healthy,
            "uptime_seconds": round(self._metrics.uptime_seconds, 2),
            "metrics": {
                "total_messages_received": self._metrics.total_messages_received,
                "total_messages_processed": self._metrics.total_messages_processed,
                "total_messages_failed": self._metrics.total_messages_failed,
                "items_running": self._metrics.items_running,
                "items_error": self._metrics.items_error,
                "routes_running": self._metrics.routes_running,
                "routes_error": self._metrics.routes_error,
            },
            "items": items_health,
            "routes": routes_health,
        }
    
    async def run_forever(self) -> None:
        """Run the production until shutdown signal."""
        await self.start()
        
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
        
        # Wait for shutdown
        await self._shutdown_event.wait()
    
    def __repr__(self) -> str:
        return (
            f"Production(name={self.name!r}, state={self._state.value}, "
            f"items={len(self._items)}, routes={len(self._routes)})"
        )
