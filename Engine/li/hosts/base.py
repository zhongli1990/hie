"""
LI Host Base Classes

Defines the core Host hierarchy matching IRIS/Ensemble architecture:
- Host: Base class for all business hosts
- BusinessService: Inbound hosts (receive messages from external systems)
- BusinessProcess: Processing hosts (transform, route, enrich messages)
- BusinessOperation: Outbound hosts (send messages to external systems)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING
from uuid import UUID, uuid4

import structlog

from Engine.core.messaging import (
    MessageBroker,
    MessagingPattern,
    MessageEnvelope,
    MessagePriority,
    ServiceRegistry
)
from Engine.core.queues import (
    QueueType,
    OverflowStrategy,
    create_queue,
    ManagedQueue
)

if TYPE_CHECKING:
    from Engine.li.config import ItemConfig
    from Engine.li.adapters.base import InboundAdapter, OutboundAdapter

logger = structlog.get_logger(__name__)


class HostState(str, Enum):
    """Host lifecycle state."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class HostMetrics:
    """Runtime metrics for a host."""
    messages_received: int = 0
    messages_processed: int = 0
    messages_sent: int = 0
    messages_failed: int = 0

    last_message_at: datetime | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None

    total_processing_time_ms: float = 0.0
    restart_count: int = 0  # Track auto-restart count
    
    @property
    def avg_processing_time_ms(self) -> float:
        """Average processing time per message."""
        if self.messages_processed == 0:
            return 0.0
        return self.total_processing_time_ms / self.messages_processed


class Host(MessageBroker, ABC):
    """
    Base class for all business hosts.

    A Host is a configurable runtime component that processes messages.
    It has a lifecycle (start/stop/pause/resume) and can be configured
    via adapter_settings and host_settings.

    Inherits from MessageBroker to support inter-service messaging:
    - send_request_async(): Non-blocking fire-and-forget
    - send_request_sync(): Blocking request/reply
    - send_response(): Reply to sync requests

    This matches IRIS Ens.Host architecture with SendRequestSync/Async.
    """

    # Class-level adapter class (set by subclasses)
    adapter_class: type | None = None
    
    def __init__(
        self,
        name: str,
        config: ItemConfig | None = None,
        *,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        """
        Initialize a host.
        
        Args:
            name: Unique name for this host instance
            config: Full ItemConfig (if provided, overrides other params)
            pool_size: Number of worker instances
            enabled: Whether host is enabled
            adapter_settings: Settings for the adapter (Target="Adapter")
            host_settings: Settings for the host (Target="Host")
        """
        # Initialize MessageBroker parent
        MessageBroker.__init__(self)

        self._id = uuid4()
        self._name = name
        self._state = HostState.CREATED
        self._metrics = HostMetrics()

        # Configuration
        if config:
            self._pool_size = config.pool_size
            self._enabled = config.enabled
            self._adapter_settings = config.adapter_settings
            self._host_settings = config.host_settings
            self._config = config
        else:
            self._pool_size = pool_size
            self._enabled = enabled
            self._adapter_settings = adapter_settings or {}
            self._host_settings = host_settings or {}
            self._config = None
        
        # Runtime state
        self._workers: list[asyncio.Task] = []
        self._queue: asyncio.Queue | None = None
        self._shutdown_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        
        # Callbacks
        self._on_message: Callable | None = None
        self._on_error: Callable | None = None
        
        # Adapter (created during start)
        self._adapter: Any = None
        
        # Logger with context
        self._log = logger.bind(host=self._name, host_type=self.__class__.__name__)
    
    @property
    def id(self) -> UUID:
        """Unique host ID."""
        return self._id
    
    @property
    def name(self) -> str:
        """Host name (from configuration)."""
        return self._name
    
    @property
    def state(self) -> HostState:
        """Current lifecycle state."""
        return self._state
    
    @property
    def metrics(self) -> HostMetrics:
        """Runtime metrics."""
        return self._metrics
    
    @property
    def pool_size(self) -> int:
        """Number of worker instances."""
        return self._pool_size
    
    @property
    def enabled(self) -> bool:
        """Whether host is enabled."""
        return self._enabled
    
    @property
    def adapter_settings(self) -> dict[str, Any]:
        """Adapter settings (Target="Adapter")."""
        return self._adapter_settings
    
    @property
    def host_settings(self) -> dict[str, Any]:
        """Host settings (Target="Host")."""
        return self._host_settings
    
    def get_setting(self, target: str, name: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            target: "Host" or "Adapter"
            name: Setting name
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        if target.lower() == "host":
            return self._host_settings.get(name, default)
        elif target.lower() == "adapter":
            return self._adapter_settings.get(name, default)
        return default
    
    # =========================================================================
    # Lifecycle Methods
    # =========================================================================
    
    async def start(self) -> None:
        """
        Start the host.
        
        Creates workers and begins processing messages.
        """
        if self._state not in (HostState.CREATED, HostState.STOPPED):
            raise RuntimeError(f"Cannot start host in state: {self._state}")
        
        self._log.info("host_starting", pool_size=self._pool_size)
        self._state = HostState.STARTING
        
        try:
            # Initialize
            await self.on_init()
            
            # Create adapter if needed
            if self.adapter_class:
                self._adapter = self.adapter_class(
                    host=self,
                    settings=self._adapter_settings,
                )
                await self._adapter.start()
            
            # Create queue with configurable type
            queue_size = self.get_setting("Host", "QueueSize", 1000)
            queue_type_str = self.get_setting("Host", "QueueType", "fifo")
            overflow_strategy_str = self.get_setting("Host", "OverflowStrategy", "block")

            # Parse queue type
            try:
                queue_type = QueueType(queue_type_str)
            except ValueError:
                self._log.warning(
                    "invalid_queue_type",
                    queue_type=queue_type_str,
                    using_default="fifo"
                )
                queue_type = QueueType.FIFO

            # Parse overflow strategy
            try:
                overflow_strategy = OverflowStrategy(overflow_strategy_str)
            except ValueError:
                overflow_strategy = OverflowStrategy.BLOCK

            # Create managed queue
            self._queue = create_queue(
                queue_type=queue_type,
                maxsize=queue_size,
                overflow_strategy=overflow_strategy
            )

            self._log.info(
                "queue_created",
                queue_type=queue_type.value,
                size=queue_size,
                overflow=overflow_strategy.value
            )

            self._shutdown_event.clear()
            
            for i in range(self._pool_size):
                worker = asyncio.create_task(
                    self._worker_loop(i),
                    name=f"{self._name}-worker-{i}"
                )
                self._workers.append(worker)
            
            # Call on_start hook
            await self.on_start()
            
            self._state = HostState.RUNNING
            self._metrics.started_at = datetime.now(timezone.utc)
            self._log.info("host_started")
            
        except Exception as e:
            self._state = HostState.ERROR
            self._log.error("host_start_failed", error=str(e))
            raise
    
    async def stop(self, timeout: float = 30.0) -> None:
        """
        Stop the host gracefully.
        
        Args:
            timeout: Maximum seconds to wait for graceful shutdown
        """
        if self._state not in (HostState.RUNNING, HostState.PAUSED, HostState.ERROR):
            return
        
        self._log.info("host_stopping")
        self._state = HostState.STOPPING
        
        try:
            # Signal shutdown
            self._shutdown_event.set()
            self._pause_event.set()  # Unpause if paused
            
            # Wait for workers to finish
            if self._workers:
                done, pending = await asyncio.wait(
                    self._workers,
                    timeout=timeout,
                )
                
                # Cancel any remaining workers
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Stop adapter
            if self._adapter:
                await self._adapter.stop()
            
            # Call on_stop hook
            await self.on_stop()
            
            # Cleanup
            await self.on_teardown()
            
            self._state = HostState.STOPPED
            self._metrics.stopped_at = datetime.now(timezone.utc)
            self._workers.clear()
            self._log.info("host_stopped")
            
        except Exception as e:
            self._state = HostState.ERROR
            self._log.error("host_stop_failed", error=str(e))
            raise
    
    async def pause(self) -> None:
        """Pause message processing."""
        if self._state != HostState.RUNNING:
            return
        
        self._pause_event.clear()
        self._state = HostState.PAUSED
        self._log.info("host_paused")
    
    async def resume(self) -> None:
        """Resume message processing."""
        if self._state != HostState.PAUSED:
            return
        
        self._pause_event.set()
        self._state = HostState.RUNNING
        self._log.info("host_resumed")
    
    async def reload_config(
        self,
        pool_size: int | None = None,
        enabled: bool | None = None,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ) -> None:
        """
        Hot reload configuration without losing messages.
        
        This performs a graceful restart:
        1. Pause to stop accepting new messages
        2. Wait for in-flight messages to complete
        3. Stop adapter
        4. Apply new configuration
        5. Restart adapter with new settings
        6. Resume processing
        
        Args:
            pool_size: New pool size (None = keep current)
            enabled: New enabled state (None = keep current)
            adapter_settings: New adapter settings (None = keep current)
            host_settings: New host settings (None = keep current)
        """
        was_running = self._state == HostState.RUNNING
        
        self._log.info(
            "config_reload_starting",
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings_keys=list(adapter_settings.keys()) if adapter_settings else None,
            host_settings_keys=list(host_settings.keys()) if host_settings else None,
        )
        
        try:
            # 1. Pause if running
            if was_running:
                await self.pause()
            
            # 2. Wait for queue to drain (with timeout)
            if self._queue and not self._queue.empty():
                self._log.info("waiting_for_queue_drain", queue_size=self._queue.qsize())
                try:
                    await asyncio.wait_for(self._queue.join(), timeout=30.0)
                except asyncio.TimeoutError:
                    self._log.warning("queue_drain_timeout", remaining=self._queue.qsize())
            
            # 3. Stop adapter if exists
            if self._adapter:
                await self._adapter.stop()
                self._adapter = None
            
            # 4. Apply new configuration
            if pool_size is not None:
                self._pool_size = pool_size
            if enabled is not None:
                self._enabled = enabled
            if adapter_settings is not None:
                self._adapter_settings = adapter_settings
            if host_settings is not None:
                self._host_settings = host_settings
            
            # 5. Recreate adapter with new settings
            if self.adapter_class and self._enabled:
                self._adapter = self.adapter_class(
                    host=self,
                    settings=self._adapter_settings,
                )
                await self._adapter.start()
            
            # 6. Resume if was running and still enabled
            if was_running and self._enabled:
                await self.resume()
            elif not self._enabled:
                self._state = HostState.STOPPED
            
            self._log.info("config_reload_complete")
            
        except Exception as e:
            self._state = HostState.ERROR
            self._log.error("config_reload_failed", error=str(e))
            raise
    
    # =========================================================================
    # Worker Loop
    # =========================================================================
    
    async def _worker_loop(self, worker_id: int) -> None:
        """
        Main worker loop for processing messages with pattern support.

        Handles both MessageEnvelope (from inter-service calls) and
        raw messages (from external adapters).

        Args:
            worker_id: Worker instance ID
        """
        self._log.debug("worker_started", worker_id=worker_id)

        while not self._shutdown_event.is_set():
            # Wait if paused
            await self._pause_event.wait()

            try:
                # Get message from queue with timeout
                item = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            # Process message with pattern awareness
            start_time = datetime.now(timezone.utc)
            try:
                # Extract envelope if present
                if isinstance(item, MessageEnvelope):
                    envelope = item
                    message = envelope.message
                    correlation_id = envelope.correlation_id
                    is_sync = envelope.pattern in (
                        MessagingPattern.SYNC_RELIABLE,
                        MessagingPattern.CONCURRENT_SYNC
                    )
                else:
                    # Raw message (from adapter)
                    envelope = None
                    message = item
                    correlation_id = None
                    is_sync = False

                # PRE-PROCESSING HOOK
                message = await self.on_before_process(message)

                # Process message
                timeout = self.get_setting("Host", "Timeout", 30.0)
                result = await asyncio.wait_for(
                    self._process_message(message),
                    timeout=timeout
                )

                # POST-PROCESSING HOOK
                result = await self.on_after_process(message, result)

                # Update metrics
                elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                self._metrics.messages_processed += 1
                self._metrics.total_processing_time_ms += elapsed_ms
                self._metrics.last_message_at = datetime.now(timezone.utc)

                # Handle response based on pattern
                if envelope and is_sync:
                    # Sync pattern: send response back to caller
                    if correlation_id:
                        await self.send_response(correlation_id, result)
                elif result is not None:
                    # Async pattern or no envelope: use callback
                    if self._on_message:
                        await self._on_message(result)

            except asyncio.TimeoutError as timeout_error:
                # ERROR HOOK for timeout
                recovery_result = await self.on_process_error(message, timeout_error)

                self._metrics.messages_failed += 1
                self._log.error("message_timeout", worker_id=worker_id)

                if self._on_error:
                    await self._on_error(timeout_error, message)

            except Exception as e:
                # ERROR HOOK for general exceptions
                recovery_result = await self.on_process_error(message, e)

                self._metrics.messages_failed += 1
                self._log.error("message_processing_failed", worker_id=worker_id, error=str(e))

                if self._on_error:
                    await self._on_error(e, message)

            finally:
                self._queue.task_done()

        self._log.debug("worker_stopped", worker_id=worker_id)
    
    async def submit(self, message: Any) -> bool:
        """
        Submit a message for processing.
        
        Args:
            message: Message to process
            
        Returns:
            True if message was queued, False if queue is full
        """
        if self._state != HostState.RUNNING:
            self._log.warning("submit_rejected", state=self._state)
            return False
        
        try:
            self._queue.put_nowait(message)
            self._metrics.messages_received += 1
            return True
        except asyncio.QueueFull:
            self._log.warning("queue_full")
            return False
    
    # =========================================================================
    # Extension Points (Override in subclasses)
    # =========================================================================
    
    async def on_init(self) -> None:
        """
        Called during host initialization.
        
        Override to perform setup like loading schemas, rules, etc.
        """
        pass
    
    async def on_start(self) -> None:
        """
        Called after host has started.
        
        Override to perform post-start actions.
        """
        pass
    
    async def on_stop(self) -> None:
        """
        Called before host stops.
        
        Override to perform cleanup before shutdown.
        """
        pass
    
    async def on_teardown(self) -> None:
        """
        Called during host teardown.

        Override to release resources.
        """
        pass

    # Message-Level Hooks (NEW)

    async def on_before_process(self, message: Any) -> Any:
        """
        Called BEFORE processing each message.

        Override to add:
        - Message validation
        - Pre-processing transformation
        - Audit logging (message received)
        - Metric collection (start timer)
        - Authentication/authorization checks

        Args:
            message: Incoming message

        Returns:
            Modified message (or original if no changes)

        Raises:
            Exception: To reject message and trigger error handling
        """
        return message

    async def on_after_process(
        self,
        message: Any,
        result: Any
    ) -> Any:
        """
        Called AFTER processing each message successfully.

        Override to add:
        - Post-processing transformation
        - Audit logging (message processed)
        - Metric collection (end timer)
        - Response enrichment
        - Cleanup actions

        Args:
            message: Original incoming message
            result: Processing result

        Returns:
            Modified result (or original if no changes)
        """
        return result

    async def on_process_error(
        self,
        message: Any,
        exception: Exception
    ) -> Any:
        """
        Called when message processing fails.

        Override to add:
        - Error logging
        - Dead letter queue routing
        - Retry logic
        - Alert generation
        - Recovery actions

        Args:
            message: Message that caused error
            exception: The exception raised

        Returns:
            Recovery result (if recovery successful) or None

        Raises:
            Exception: To propagate error up (if no recovery)
        """
        self._log.error(
            "message_processing_error",
            error=str(exception),
            error_type=type(exception).__name__
        )
        return None

    # =========================================================================
    # Phase 4: MessageEnvelope Support (Optional)
    # =========================================================================

    async def on_message_envelope(self, envelope: Any) -> Any:
        """
        Process Phase 4 message envelope (OPTIONAL).

        This is the Phase 4 preferred method for protocol-agnostic messaging.
        Override this in subclasses to use the new envelope pattern with
        schema metadata and dynamic parsing.

        Default implementation parses the envelope and delegates to
        on_process_message_content.

        Args:
            envelope: Phase 4 MessageEnvelope with header and body

        Returns:
            Processing result (or new envelope to forward)

        Example:
            async def on_message_envelope(self, envelope: MessageEnvelope):
                # Automatic parsing based on content_type
                parsed = envelope.parse()

                # Process with full envelope context
                result = await self.on_process_message_content(parsed, envelope)

                return result
        """
        from Engine.core.message_envelope import MessageEnvelope

        if not hasattr(envelope, 'parse'):
            # Not a Phase 4 envelope, fall back to legacy
            return await self._process_message(envelope)

        logger.debug(
            "processing_envelope",
            message_id=envelope.header.message_id,
            source=envelope.header.source,
            content_type=envelope.header.content_type
        )

        # Parse if needed
        parse_messages = self.get_setting("Host", "ParseMessages", False)
        if parse_messages or parse_messages == "True":
            parsed = envelope.parse()
        else:
            parsed = envelope.body.raw_payload

        # Process
        result = await self.on_process_message_content(parsed, envelope)

        return result

    async def on_process_message_content(
        self,
        content: Any,
        envelope: Any
    ) -> Any:
        """
        Process parsed message content with envelope context (Phase 4).

        Override this to process Phase 4 messages. Default implementation
        delegates to _process_message for backward compatibility.

        Args:
            content: Parsed message object (or raw bytes if parsing disabled)
            envelope: Full Phase 4 message envelope (access to header/body/metadata)

        Returns:
            Processing result (or new envelope to forward)

        Example:
            async def on_process_message_content(self, content, envelope):
                # Access envelope metadata
                priority = envelope.header.priority
                schema_version = envelope.header.schema_version

                # Process content
                if isinstance(content, HL7Message):
                    # Process HL7 message
                    return await self.process_hl7(content)

                return content
        """
        # Default: delegate to legacy _process_message
        return await self._process_message(content)

    @abstractmethod
    async def _process_message(self, message: Any) -> Any:
        """
        Process a single message.

        Must be implemented by subclasses.

        Args:
            message: Message to process

        Returns:
            Processed message or None
        """
        ...


class BusinessService(Host):
    """
    Inbound host that receives messages from external systems.
    
    BusinessServices typically have an InboundAdapter that handles
    protocol-specific communication (TCP, HTTP, File, etc.).
    
    Equivalent to IRIS Ens.BusinessService.
    
    Key settings:
    - TargetConfigNames: Comma-separated list of targets to send messages to
    - MessageSchemaCategory: Schema for parsing/validating messages
    """
    
    @property
    def target_config_names(self) -> list[str]:
        """Get list of target config names."""
        targets = self.get_setting("Host", "TargetConfigNames", "")
        if not targets:
            return []
        return [t.strip() for t in targets.split(",") if t.strip()]
    
    async def on_message_received(self, raw: bytes) -> Any:
        """
        Called when a message is received from the adapter.
        
        Override to customize message creation.
        
        Args:
            raw: Raw message bytes
            
        Returns:
            Message object to process
        """
        from Engine.core.message import Message
        return Message.create(
            raw=raw,
            content_type="application/octet-stream",
            source=self.name,
        )
    
    async def send_to_targets(self, message: Any) -> None:
        """
        Send message to configured targets.
        
        Args:
            message: Message to send
        """
        # This will be implemented when we have the production engine
        # For now, just log
        targets = self.target_config_names
        self._log.debug("send_to_targets", targets=targets, message_id=getattr(message, 'id', None))
    
    async def _process_message(self, message: Any) -> Any:
        """Process received message and send to targets."""
        await self.send_to_targets(message)
        return message


class BusinessProcess(Host):
    """
    Processing host that transforms, routes, or enriches messages.
    
    BusinessProcesses receive messages from other hosts and can:
    - Transform messages (DTL)
    - Route messages based on rules
    - Aggregate or split messages
    - Call external services
    
    Equivalent to IRIS Ens.BusinessProcess.
    
    Key settings:
    - BusinessRuleName: Name of routing rule set
    - ValidationSchema: Schema for validation
    - TargetConfigNames: Default targets if no rule matches
    """
    
    @property
    def business_rule_name(self) -> str | None:
        """Get business rule name."""
        return self.get_setting("Host", "BusinessRuleName")
    
    @property
    def target_config_names(self) -> list[str]:
        """Get list of default target config names."""
        targets = self.get_setting("Host", "TargetConfigNames", "")
        if not targets:
            return []
        return [t.strip() for t in str(targets).split(",") if t.strip()]
    
    async def on_message(self, message: Any) -> Any | list[Any] | None:
        """
        Process a message.
        
        Override to implement custom processing logic.
        
        Args:
            message: Message to process
            
        Returns:
            Processed message, list of messages, or None
        """
        return message
    
    async def _process_message(self, message: Any) -> Any:
        """Process message using on_message hook."""
        return await self.on_message(message)


class BusinessOperation(Host):
    """
    Outbound host that sends messages to external systems.
    
    BusinessOperations typically have an OutboundAdapter that handles
    protocol-specific communication (TCP, HTTP, File, etc.).
    
    Equivalent to IRIS Ens.BusinessOperation.
    
    Key settings:
    - ReplyCodeActions: How to handle different response codes
    - FailureTimeout: Timeout for failure handling
    - ArchiveIO: Whether to archive messages
    """
    
    @property
    def reply_code_actions(self) -> str:
        """Get reply code actions string."""
        return self.get_setting("Host", "ReplyCodeActions", "")
    
    @property
    def archive_io(self) -> bool:
        """Whether to archive I/O."""
        return bool(self.get_setting("Host", "ArchiveIO", 0))
    
    async def on_message(self, message: Any) -> Any | None:
        """
        Process a message before sending.
        
        Override to customize message handling.
        
        Args:
            message: Message to send
            
        Returns:
            Response message or None
        """
        # Default: send via adapter
        if self._adapter:
            return await self._adapter.send(message)
        return None
    
    async def _process_message(self, message: Any) -> Any:
        """Process message using on_message hook."""
        result = await self.on_message(message)
        self._metrics.messages_sent += 1
        return result
