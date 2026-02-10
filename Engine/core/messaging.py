"""
Service-to-Service Messaging Module

Provides pattern-aware messaging between services within a production.
Supports all 4 mandatory messaging patterns:
- Async Reliable: Non-blocking, event-driven, persisted
- Sync Reliable: Blocking request/reply, FIFO
- Concurrent Async: Parallel non-blocking, max throughput
- Concurrent Sync: Parallel blocking workers

Usage:
    # Async reliable (non-blocking)
    correlation_id = await self.send_request_async("PDS.Lookup", message)

    # Sync reliable (blocking)
    response = await self.send_request_sync("PDS.Lookup", message, timeout=5.0)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

import structlog

if TYPE_CHECKING:
    from Engine.core.production import Production

logger = structlog.get_logger(__name__)


class MessagingPattern(str, Enum):
    """Message processing patterns."""
    ASYNC_RELIABLE = "async_reliable"
    SYNC_RELIABLE = "sync_reliable"
    CONCURRENT_ASYNC = "concurrent_async"
    CONCURRENT_SYNC = "concurrent_sync"


class MessagePriority(int, Enum):
    """Message priority levels for priority queues."""
    CRITICAL = 0    # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BULK = 4        # Lowest priority


@dataclass
class MessageEnvelope:
    """
    Message envelope wrapping actual message with metadata.

    Supports all messaging patterns with correlation tracking,
    persistence, and response handling.
    """
    # Message identity
    message_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None
    causation_id: str | None = None

    # Message content
    message: Any = None

    # Routing information
    source: str | None = None
    target: str | None = None

    # Pattern information
    pattern: MessagingPattern = MessagingPattern.ASYNC_RELIABLE
    priority: MessagePriority = MessagePriority.NORMAL

    # Timing
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout: float = 30.0

    # Response handling (for sync patterns)
    response_future: asyncio.Future | None = None
    is_response: bool = False

    # Persistence flags
    persist_wal: bool = True
    persist_store: bool = True

    # Metadata
    properties: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: MessageEnvelope) -> bool:
        """Support priority queue comparison."""
        return self.priority.value < other.priority.value


class ServiceRegistry:
    """
    Registry of all services in a production.

    Manages service lookup and message routing between services.
    Used by ProductionEngine to enable inter-service communication.
    """

    def __init__(self):
        self._services: dict[str, Any] = {}  # name -> Host instance
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._log = logger.bind(component="ServiceRegistry")

    def register(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service
        self._log.info("service_registered", name=name)

    def unregister(self, name: str) -> None:
        """Unregister a service."""
        self._services.pop(name, None)
        self._log.info("service_unregistered", name=name)

    def get(self, name: str) -> Any | None:
        """Get service by name."""
        return self._services.get(name)

    def list_services(self) -> list[str]:
        """List all registered service names."""
        return list(self._services.keys())

    async def route_message(
        self,
        envelope: MessageEnvelope
    ) -> str | Any:
        """
        Route message to target service.

        Returns:
            - For async patterns: correlation_id
            - For sync patterns: response (blocks until received)
        """
        if not envelope.target:
            raise ValueError("Message envelope missing target")

        target_service = self.get(envelope.target)
        if not target_service:
            raise ValueError(f"Unknown target service: {envelope.target}")

        # Handle based on pattern
        if envelope.pattern in (MessagingPattern.ASYNC_RELIABLE, MessagingPattern.CONCURRENT_ASYNC):
            # Async patterns: enqueue and return correlation ID
            await self._route_async(target_service, envelope)
            return envelope.correlation_id or envelope.message_id

        elif envelope.pattern in (MessagingPattern.SYNC_RELIABLE, MessagingPattern.CONCURRENT_SYNC):
            # Sync patterns: enqueue and wait for response
            return await self._route_sync(target_service, envelope)

        else:
            raise ValueError(f"Unknown messaging pattern: {envelope.pattern}")

    async def _route_async(self, target_service: Any, envelope: MessageEnvelope) -> None:
        """Route message asynchronously (non-blocking)."""
        self._log.debug(
            "routing_async",
            source=envelope.source,
            target=envelope.target,
            message_id=envelope.message_id
        )

        # Enqueue to target service
        if hasattr(target_service, '_queue'):
            await target_service._queue.put(envelope)
        else:
            raise RuntimeError(f"Service {envelope.target} has no message queue")

    async def _route_sync(
        self,
        target_service: Any,
        envelope: MessageEnvelope
    ) -> Any:
        """Route message synchronously (blocking until response)."""
        self._log.debug(
            "routing_sync",
            source=envelope.source,
            target=envelope.target,
            message_id=envelope.message_id,
            timeout=envelope.timeout
        )

        # Create future for response
        response_future = asyncio.Future()
        correlation_id = envelope.correlation_id or envelope.message_id

        self._pending_requests[correlation_id] = response_future
        envelope.response_future = response_future

        # Enqueue to target service
        if hasattr(target_service, '_queue'):
            await target_service._queue.put(envelope)
        else:
            raise RuntimeError(f"Service {envelope.target} has no message queue")

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(
                response_future,
                timeout=envelope.timeout
            )
            return response

        except asyncio.TimeoutError:
            self._pending_requests.pop(correlation_id, None)
            self._log.error(
                "sync_request_timeout",
                source=envelope.source,
                target=envelope.target,
                correlation_id=correlation_id
            )
            raise

        finally:
            # Cleanup
            self._pending_requests.pop(correlation_id, None)

    async def send_response(
        self,
        correlation_id: str,
        response: Any
    ) -> None:
        """
        Send response back to waiting caller (for sync patterns).

        Args:
            correlation_id: ID from original request
            response: Response data
        """
        future = self._pending_requests.get(correlation_id)
        if future and not future.done():
            future.set_result(response)
            self._log.debug(
                "response_sent",
                correlation_id=correlation_id
            )
        else:
            self._log.warning(
                "response_no_waiter",
                correlation_id=correlation_id
            )


class MessageBroker:
    """
    Message broker mixin for services.

    Provides send_request_sync() and send_request_async() methods
    that services can use to call other services.
    """

    def __init__(self):
        self._service_registry: ServiceRegistry | None = None
        self._service_name: str | None = None
        self._messaging_pattern: MessagingPattern = MessagingPattern.ASYNC_RELIABLE

    def set_service_registry(
        self,
        registry: ServiceRegistry,
        service_name: str,
        messaging_pattern: MessagingPattern = MessagingPattern.ASYNC_RELIABLE
    ) -> None:
        """Register with service registry for inter-service messaging."""
        self._service_registry = registry
        self._service_name = service_name
        self._messaging_pattern = messaging_pattern

    async def send_request_async(
        self,
        target: str,
        message: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        properties: dict[str, Any] | None = None
    ) -> str:
        """
        Send asynchronous request to another service (fire-and-forget).

        Like IRIS: Do ..SendRequestAsync("TargetService", request)

        Args:
            target: Target service name
            message: Request message
            priority: Message priority (for priority queues)
            properties: Optional message properties

        Returns:
            correlation_id: ID for tracking this request

        Raises:
            RuntimeError: If not registered with service registry
            ValueError: If target service not found
        """
        if not self._service_registry:
            raise RuntimeError(
                f"Service {self._service_name} not registered with ServiceRegistry. "
                "Call set_service_registry() during initialization."
            )

        # Create message envelope
        envelope = MessageEnvelope(
            message=message,
            source=self._service_name,
            target=target,
            pattern=MessagingPattern.ASYNC_RELIABLE,
            priority=priority,
            properties=properties or {},
            persist_wal=True,
            persist_store=True
        )

        # Route through registry (non-blocking)
        correlation_id = await self._service_registry.route_message(envelope)

        return correlation_id

    async def send_request_sync(
        self,
        target: str,
        message: Any,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL,
        properties: dict[str, Any] | None = None
    ) -> Any:
        """
        Send synchronous request to another service (wait for response).

        Like IRIS: Set response = ..SendRequestSync("TargetService", request)

        Args:
            target: Target service name
            message: Request message
            timeout: Response timeout in seconds
            priority: Message priority
            properties: Optional message properties

        Returns:
            response: The response from target service

        Raises:
            RuntimeError: If not registered with service registry
            ValueError: If target service not found
            asyncio.TimeoutError: If no response within timeout
        """
        if not self._service_registry:
            raise RuntimeError(
                f"Service {self._service_name} not registered with ServiceRegistry. "
                "Call set_service_registry() during initialization."
            )

        # Create message envelope
        envelope = MessageEnvelope(
            message=message,
            source=self._service_name,
            target=target,
            pattern=MessagingPattern.SYNC_RELIABLE,
            timeout=timeout,
            priority=priority,
            properties=properties or {},
            persist_wal=True,
            persist_store=True
        )

        # Route through registry (BLOCKS until response)
        response = await self._service_registry.route_message(envelope)

        return response

    async def send_response(
        self,
        correlation_id: str,
        response: Any
    ) -> None:
        """
        Send response back to caller (for sync requests).

        Use when receiving a sync request and need to reply.

        Args:
            correlation_id: ID from incoming request envelope
            response: Response data
        """
        if not self._service_registry:
            raise RuntimeError("Service not registered with ServiceRegistry")

        await self._service_registry.send_response(correlation_id, response)
