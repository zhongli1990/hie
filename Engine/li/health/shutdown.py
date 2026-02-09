"""
LI Graceful Shutdown

Provides graceful shutdown handling for LI Engine.
Ensures in-flight messages are processed before shutdown.

Features:
- Signal handling (SIGTERM, SIGINT)
- Configurable shutdown timeout
- Message draining
- Component shutdown ordering
"""

from __future__ import annotations

import asyncio
import signal
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from Engine.li.hosts.base import Host

logger = structlog.get_logger(__name__)


class ShutdownState(str, Enum):
    """Shutdown state."""
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


@dataclass
class ShutdownConfig:
    """Shutdown configuration."""
    timeout: float = 30.0  # Maximum shutdown time
    drain_timeout: float = 10.0  # Time to drain queues
    force_after: float = 60.0  # Force exit after this time


ShutdownHandler = Callable[[], Awaitable[None]]


class GracefulShutdown:
    """
    Manages graceful shutdown of LI Engine.
    
    Handles signals and coordinates shutdown of all components.
    
    Usage:
        shutdown = GracefulShutdown()
        
        # Register components
        shutdown.register_host(service)
        shutdown.register_host(router)
        shutdown.register_handler(cleanup_function)
        
        # Install signal handlers
        shutdown.install_signal_handlers()
        
        # Wait for shutdown
        await shutdown.wait()
    """
    
    def __init__(self, config: ShutdownConfig | None = None):
        self._config = config or ShutdownConfig()
        self._state = ShutdownState.RUNNING
        self._shutdown_event = asyncio.Event()
        self._shutdown_complete = asyncio.Event()
        
        # Components to shutdown
        self._hosts: list[Host] = []
        self._handlers: list[ShutdownHandler] = []
        
        # Shutdown timing
        self._shutdown_started_at: datetime | None = None
        
        self._log = logger.bind(component="GracefulShutdown")
    
    @property
    def state(self) -> ShutdownState:
        """Current shutdown state."""
        return self._state
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._state == ShutdownState.SHUTTING_DOWN
    
    def register_host(self, host: "Host") -> None:
        """Register a host for shutdown."""
        self._hosts.append(host)
        self._log.debug("host_registered_for_shutdown", host=host.name)
    
    def register_handler(self, handler: ShutdownHandler) -> None:
        """Register a shutdown handler."""
        self._handlers.append(handler)
    
    def install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s)),
                )
                self._log.debug("signal_handler_installed", signal=sig.name)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda s, f: asyncio.create_task(self._handle_signal(s)))
    
    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signal."""
        self._log.info("shutdown_signal_received", signal=sig.name if hasattr(sig, 'name') else sig)
        await self.shutdown()
    
    async def shutdown(self) -> None:
        """
        Initiate graceful shutdown.
        
        Stops accepting new messages, drains queues, and shuts down components.
        """
        if self._state != ShutdownState.RUNNING:
            return
        
        self._state = ShutdownState.SHUTTING_DOWN
        self._shutdown_started_at = datetime.now(timezone.utc)
        self._shutdown_event.set()
        
        self._log.info(
            "shutdown_started",
            hosts=len(self._hosts),
            handlers=len(self._handlers),
            timeout=self._config.timeout,
        )
        
        try:
            # Phase 1: Stop accepting new connections
            await self._stop_accepting()
            
            # Phase 2: Drain queues
            await self._drain_queues()
            
            # Phase 3: Stop hosts
            await self._stop_hosts()
            
            # Phase 4: Run custom handlers
            await self._run_handlers()
            
            self._state = ShutdownState.STOPPED
            self._shutdown_complete.set()
            
            self._log.info("shutdown_complete")
            
        except asyncio.TimeoutError:
            self._log.error("shutdown_timeout", timeout=self._config.timeout)
            self._state = ShutdownState.STOPPED
            self._shutdown_complete.set()
        
        except Exception as e:
            self._log.error("shutdown_error", error=str(e))
            self._state = ShutdownState.STOPPED
            self._shutdown_complete.set()
    
    async def _stop_accepting(self) -> None:
        """Stop accepting new connections on all hosts."""
        self._log.debug("stopping_accepting_connections")
        
        for host in self._hosts:
            try:
                # Pause the host to stop accepting new messages
                if hasattr(host, 'pause'):
                    await host.pause()
            except Exception as e:
                self._log.warning("pause_host_error", host=host.name, error=str(e))
    
    async def _drain_queues(self) -> None:
        """Wait for queues to drain."""
        self._log.debug("draining_queues", timeout=self._config.drain_timeout)
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < self._config.drain_timeout:
            # Check if all hosts have empty queues
            all_empty = True
            
            for host in self._hosts:
                if hasattr(host, '_queue') and host._queue:
                    if not host._queue.empty():
                        all_empty = False
                        break
            
            if all_empty:
                self._log.debug("queues_drained")
                return
            
            await asyncio.sleep(0.1)
        
        self._log.warning("drain_timeout", remaining_messages=self._count_pending())
    
    def _count_pending(self) -> int:
        """Count pending messages across all hosts."""
        count = 0
        for host in self._hosts:
            if hasattr(host, '_queue') and host._queue:
                count += host._queue.qsize()
        return count
    
    async def _stop_hosts(self) -> None:
        """Stop all registered hosts."""
        self._log.debug("stopping_hosts", count=len(self._hosts))
        
        # Stop hosts in reverse order (operations first, then processes, then services)
        for host in reversed(self._hosts):
            try:
                await asyncio.wait_for(
                    host.stop(),
                    timeout=self._config.timeout / len(self._hosts) if self._hosts else self._config.timeout,
                )
                self._log.debug("host_stopped", host=host.name)
            except asyncio.TimeoutError:
                self._log.warning("host_stop_timeout", host=host.name)
            except Exception as e:
                self._log.error("host_stop_error", host=host.name, error=str(e))
    
    async def _run_handlers(self) -> None:
        """Run custom shutdown handlers."""
        self._log.debug("running_shutdown_handlers", count=len(self._handlers))
        
        for handler in self._handlers:
            try:
                await asyncio.wait_for(handler(), timeout=5.0)
            except asyncio.TimeoutError:
                self._log.warning("handler_timeout")
            except Exception as e:
                self._log.error("handler_error", error=str(e))
    
    async def wait(self) -> None:
        """Wait for shutdown to be triggered."""
        await self._shutdown_event.wait()
    
    async def wait_complete(self) -> None:
        """Wait for shutdown to complete."""
        await self._shutdown_complete.wait()
    
    def trigger(self) -> None:
        """Trigger shutdown programmatically."""
        asyncio.create_task(self.shutdown())


# Convenience function for simple shutdown
async def shutdown_on_signal(
    hosts: list["Host"],
    handlers: list[ShutdownHandler] | None = None,
    timeout: float = 30.0,
) -> None:
    """
    Set up graceful shutdown for a list of hosts.
    
    Args:
        hosts: List of hosts to shutdown
        handlers: Optional list of cleanup handlers
        timeout: Shutdown timeout
    """
    shutdown = GracefulShutdown(ShutdownConfig(timeout=timeout))
    
    for host in hosts:
        shutdown.register_host(host)
    
    for handler in (handlers or []):
        shutdown.register_handler(handler)
    
    shutdown.install_signal_handlers()
    
    await shutdown.wait()
    await shutdown.wait_complete()
