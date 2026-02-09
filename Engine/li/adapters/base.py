"""
LI Adapter Base Classes

Defines the adapter hierarchy for protocol-specific communication:
- Adapter: Base class for all adapters
- InboundAdapter: Receives data from external systems (for BusinessService)
- OutboundAdapter: Sends data to external systems (for BusinessOperation)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from Engine.li.hosts.base import Host

logger = structlog.get_logger(__name__)


class AdapterState(str, Enum):
    """Adapter lifecycle state."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AdapterMetrics:
    """Runtime metrics for an adapter."""
    bytes_received: int = 0
    bytes_sent: int = 0
    connections_total: int = 0
    connections_active: int = 0
    errors_total: int = 0
    
    last_activity_at: datetime | None = None
    started_at: datetime | None = None


class Adapter(ABC):
    """
    Base class for all adapters.
    
    An Adapter handles protocol-specific communication for a Host.
    It abstracts the transport layer (TCP, HTTP, File, etc.) from
    the business logic in the Host.
    
    This matches IRIS Ens.Adapter architecture.
    """
    
    def __init__(
        self,
        host: Host,
        settings: dict[str, Any] | None = None,
    ):
        """
        Initialize an adapter.
        
        Args:
            host: The host this adapter belongs to
            settings: Adapter settings (Target="Adapter" from config)
        """
        self._host = host
        self._settings = settings or {}
        self._state = AdapterState.CREATED
        self._metrics = AdapterMetrics()
        
        self._log = logger.bind(
            adapter=self.__class__.__name__,
            host=host.name,
        )
    
    @property
    def host(self) -> Host:
        """The host this adapter belongs to."""
        return self._host
    
    @property
    def settings(self) -> dict[str, Any]:
        """Adapter settings."""
        return self._settings
    
    @property
    def state(self) -> AdapterState:
        """Current lifecycle state."""
        return self._state
    
    @property
    def metrics(self) -> AdapterMetrics:
        """Runtime metrics."""
        return self._metrics
    
    def get_setting(self, name: str, default: Any = None) -> Any:
        """
        Get a setting value (case-insensitive lookup).
        
        Args:
            name: Setting name
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        # Try exact match first
        if name in self._settings:
            return self._settings[name]
        
        # Try case-insensitive match
        name_lower = name.lower()
        for key, value in self._settings.items():
            if key.lower() == name_lower:
                return value
        
        return default
    
    async def start(self) -> None:
        """
        Start the adapter.
        
        Override to implement protocol-specific startup.
        """
        if self._state not in (AdapterState.CREATED, AdapterState.STOPPED):
            raise RuntimeError(f"Cannot start adapter in state: {self._state}")
        
        self._log.info("adapter_starting")
        self._state = AdapterState.STARTING
        
        try:
            await self.on_start()
            self._state = AdapterState.RUNNING
            self._metrics.started_at = datetime.now(timezone.utc)
            self._log.info("adapter_started")
        except Exception as e:
            self._state = AdapterState.ERROR
            self._log.error("adapter_start_failed", error=str(e))
            raise
    
    async def stop(self) -> None:
        """
        Stop the adapter.
        
        Override to implement protocol-specific shutdown.
        """
        if self._state not in (AdapterState.RUNNING, AdapterState.ERROR):
            return
        
        self._log.info("adapter_stopping")
        self._state = AdapterState.STOPPING
        
        try:
            await self.on_stop()
            self._state = AdapterState.STOPPED
            self._log.info("adapter_stopped")
        except Exception as e:
            self._state = AdapterState.ERROR
            self._log.error("adapter_stop_failed", error=str(e))
            raise
    
    async def on_start(self) -> None:
        """
        Called during adapter startup.
        
        Override to implement protocol-specific initialization.
        """
        pass
    
    async def on_stop(self) -> None:
        """
        Called during adapter shutdown.
        
        Override to implement protocol-specific cleanup.
        """
        pass


class InboundAdapter(Adapter):
    """
    Adapter for receiving data from external systems.
    
    Used by BusinessService hosts to receive messages via
    various protocols (TCP/MLLP, HTTP, File, etc.).
    
    The adapter receives raw data and passes it to the host
    via on_data_received().
    """
    
    async def on_data_received(self, data: bytes) -> Any:
        """
        Called when data is received from external system.
        
        Passes data to the host for processing.
        
        Args:
            data: Raw bytes received
            
        Returns:
            Response from host (e.g., ACK)
        """
        self._metrics.bytes_received += len(data)
        self._metrics.last_activity_at = datetime.now(timezone.utc)
        
        # Call host's on_message_received
        from Engine.li.hosts.base import BusinessService
        if isinstance(self._host, BusinessService):
            message = await self._host.on_message_received(data)
            # Submit to host's queue for processing
            await self._host.submit(message)
            return message
        
        return None
    
    @abstractmethod
    async def listen(self) -> None:
        """
        Start listening for incoming connections/data.
        
        Must be implemented by subclasses.
        """
        ...


class OutboundAdapter(Adapter):
    """
    Adapter for sending data to external systems.
    
    Used by BusinessOperation hosts to send messages via
    various protocols (TCP/MLLP, HTTP, File, etc.).
    
    The adapter receives a message from the host and sends
    it to the external system.
    """
    
    @abstractmethod
    async def send(self, message: Any) -> Any:
        """
        Send a message to the external system.
        
        Must be implemented by subclasses.
        
        Args:
            message: Message to send
            
        Returns:
            Response from external system (e.g., ACK)
        """
        ...
    
    async def on_send(self, data: bytes) -> None:
        """
        Called after data is sent.
        
        Updates metrics.
        
        Args:
            data: Raw bytes sent
        """
        self._metrics.bytes_sent += len(data)
        self._metrics.last_activity_at = datetime.now(timezone.utc)
