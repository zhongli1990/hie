"""
HIE Item Model

Items are independently configurable runtime units that process messages.
They are categorized as:
- Receivers: Accept messages from external systems
- Processors: Transform, validate, route, or enrich messages
- Senders: Deliver messages to external systems

Each item has a lifecycle and can run in various execution modes.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from hie.core.message import Message


class ItemType(str, Enum):
    """Category of item."""
    RECEIVER = "receiver"
    PROCESSOR = "processor"
    SENDER = "sender"


class ItemState(str, Enum):
    """Item lifecycle state."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ExecutionMode(str, Enum):
    """How the item executes."""
    SINGLE_PROCESS = "single_process"      # One process, one thread
    MULTI_PROCESS = "multi_process"        # Multiple processes
    ASYNC = "async"                        # Single process, async I/O
    THREAD_POOL = "thread_pool"            # Thread pool for blocking I/O


class ItemConfig(BaseModel):
    """Base configuration for all items."""
    model_config = ConfigDict(extra="allow")
    
    id: str = Field(description="Unique item identifier")
    name: str = Field(default="", description="Human-readable name")
    item_type: ItemType = Field(description="Category of item")
    enabled: bool = Field(default=True, description="Whether item is enabled")
    
    # Execution configuration
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.ASYNC,
        description="How the item executes"
    )
    concurrency: int = Field(
        default=1,
        ge=1,
        description="Number of concurrent workers/processes"
    )
    
    # Queue configuration
    queue_size: int = Field(
        default=1000,
        ge=1,
        description="Maximum pending messages"
    )
    batch_size: int = Field(
        default=1,
        ge=1,
        description="Messages to process per batch"
    )
    
    # Timeout configuration
    timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Processing timeout per message"
    )
    
    # Error handling
    max_errors: int = Field(
        default=10,
        ge=0,
        description="Max consecutive errors before error state"
    )
    error_delay_seconds: float = Field(
        default=5.0,
        ge=0,
        description="Delay after error before retry"
    )


@dataclass
class ItemMetrics:
    """Runtime metrics for an item."""
    messages_received: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    messages_in_queue: int = 0
    
    bytes_received: int = 0
    bytes_sent: int = 0
    
    processing_time_total_ms: float = 0.0
    processing_time_avg_ms: float = 0.0
    processing_time_max_ms: float = 0.0
    
    last_message_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None
    
    consecutive_errors: int = 0
    
    started_at: datetime | None = None
    uptime_seconds: float = 0.0
    
    def record_success(self, processing_time_ms: float, bytes_count: int = 0) -> None:
        """Record a successful message processing."""
        self.messages_processed += 1
        self.bytes_sent += bytes_count
        self.consecutive_errors = 0
        self.last_message_at = datetime.now(timezone.utc)
        
        self.processing_time_total_ms += processing_time_ms
        self.processing_time_avg_ms = (
            self.processing_time_total_ms / self.messages_processed
        )
        self.processing_time_max_ms = max(
            self.processing_time_max_ms, processing_time_ms
        )
    
    def record_failure(self, error_message: str) -> None:
        """Record a failed message processing."""
        self.messages_failed += 1
        self.consecutive_errors += 1
        self.last_error_at = datetime.now(timezone.utc)
        self.last_error_message = error_message
    
    def record_received(self, bytes_count: int = 0) -> None:
        """Record a received message."""
        self.messages_received += 1
        self.bytes_received += bytes_count
        self.last_message_at = datetime.now(timezone.utc)


MessageHandler = Callable[["Message"], Coroutine[Any, Any, "Message | list[Message] | None"]]


class Item(ABC):
    """
    Base class for all HIE items.
    
    Items are the building blocks of message processing. Each item:
    - Has a unique ID and configuration
    - Manages its own lifecycle (start, stop, pause)
    - Processes messages according to its type
    - Reports metrics and health status
    """
    
    def __init__(self, config: ItemConfig) -> None:
        self._config = config
        self._state = ItemState.CREATED
        self._metrics = ItemMetrics()
        self._queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=config.queue_size)
        self._tasks: list[asyncio.Task[Any]] = []
        self._shutdown_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        
        # Callbacks
        self._on_message: MessageHandler | None = None
        self._on_error: Callable[[Exception, Message | None], Coroutine[Any, Any, None]] | None = None
    
    @property
    def id(self) -> str:
        """Unique item identifier."""
        return self._config.id
    
    @property
    def name(self) -> str:
        """Human-readable name."""
        return self._config.name or self._config.id
    
    @property
    def item_type(self) -> ItemType:
        """Category of item."""
        return self._config.item_type
    
    @property
    def state(self) -> ItemState:
        """Current lifecycle state."""
        return self._state
    
    @property
    def config(self) -> ItemConfig:
        """Item configuration."""
        return self._config
    
    @property
    def metrics(self) -> ItemMetrics:
        """Runtime metrics."""
        return self._metrics
    
    @property
    def is_running(self) -> bool:
        """Check if item is running."""
        return self._state == ItemState.RUNNING
    
    @property
    def is_healthy(self) -> bool:
        """Check if item is healthy (running without excessive errors)."""
        return (
            self._state == ItemState.RUNNING
            and self._metrics.consecutive_errors < self._config.max_errors
        )
    
    def set_message_handler(self, handler: MessageHandler) -> None:
        """Set the handler for processed messages."""
        self._on_message = handler
    
    def set_error_handler(
        self,
        handler: Callable[[Exception, Message | None], Coroutine[Any, Any, None]]
    ) -> None:
        """Set the handler for errors."""
        self._on_error = handler
    
    async def start(self) -> None:
        """Start the item."""
        if self._state not in (ItemState.CREATED, ItemState.STOPPED):
            raise RuntimeError(f"Cannot start item in state: {self._state}")
        
        self._state = ItemState.STARTING
        self._shutdown_event.clear()
        self._metrics.started_at = datetime.now(timezone.utc)
        
        try:
            await self._on_start()
            
            # Start worker tasks
            for i in range(self._config.concurrency):
                task = asyncio.create_task(
                    self._worker_loop(i),
                    name=f"{self.id}-worker-{i}"
                )
                self._tasks.append(task)
            
            self._state = ItemState.RUNNING
        except Exception as e:
            self._state = ItemState.ERROR
            self._metrics.record_failure(str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the item gracefully."""
        if self._state not in (ItemState.RUNNING, ItemState.PAUSED, ItemState.ERROR):
            return
        
        self._state = ItemState.STOPPING
        self._shutdown_event.set()
        
        # Wait for workers to finish
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        
        await self._on_stop()
        self._state = ItemState.STOPPED
    
    async def pause(self) -> None:
        """Pause message processing."""
        if self._state != ItemState.RUNNING:
            raise RuntimeError(f"Cannot pause item in state: {self._state}")
        
        self._pause_event.clear()
        self._state = ItemState.PAUSED
    
    async def resume(self) -> None:
        """Resume message processing."""
        if self._state != ItemState.PAUSED:
            raise RuntimeError(f"Cannot resume item in state: {self._state}")
        
        self._pause_event.set()
        self._state = ItemState.RUNNING
    
    async def submit(self, message: Message) -> None:
        """Submit a message for processing."""
        if self._state not in (ItemState.RUNNING, ItemState.PAUSED):
            raise RuntimeError(f"Cannot submit to item in state: {self._state}")
        
        await self._queue.put(message)
        self._metrics.messages_in_queue = self._queue.qsize()
    
    def submit_nowait(self, message: Message) -> bool:
        """Submit a message without waiting. Returns False if queue is full."""
        if self._state not in (ItemState.RUNNING, ItemState.PAUSED):
            return False
        
        try:
            self._queue.put_nowait(message)
            self._metrics.messages_in_queue = self._queue.qsize()
            return True
        except asyncio.QueueFull:
            return False
    
    async def _worker_loop(self, worker_id: int) -> None:
        """Main worker loop for processing messages."""
        while not self._shutdown_event.is_set():
            # Wait if paused
            await self._pause_event.wait()
            
            try:
                # Get message with timeout to allow shutdown checks
                try:
                    message = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                self._metrics.messages_in_queue = self._queue.qsize()
                
                # Process message
                start_time = asyncio.get_event_loop().time()
                try:
                    result = await asyncio.wait_for(
                        self._process(message),
                        timeout=self._config.timeout_seconds
                    )
                    
                    elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    self._metrics.record_success(elapsed_ms, message.payload.size)
                    
                    # Forward result to handler
                    if result is not None and self._on_message is not None:
                        if isinstance(result, list):
                            for msg in result:
                                await self._on_message(msg)
                        else:
                            await self._on_message(result)
                    
                except asyncio.TimeoutError:
                    self._metrics.record_failure(f"Processing timeout after {self._config.timeout_seconds}s")
                    if self._on_error:
                        await self._on_error(
                            TimeoutError(f"Processing timeout"),
                            message
                        )
                
                except Exception as e:
                    self._metrics.record_failure(str(e))
                    if self._on_error:
                        await self._on_error(e, message)
                    
                    # Check if we should enter error state
                    if self._metrics.consecutive_errors >= self._config.max_errors:
                        self._state = ItemState.ERROR
                        break
                    
                    # Delay before next message
                    await asyncio.sleep(self._config.error_delay_seconds)
                
                finally:
                    self._queue.task_done()
            
            except asyncio.CancelledError:
                break
    
    @abstractmethod
    async def _process(self, message: Message) -> Message | list[Message] | None:
        """
        Process a single message.
        
        Override this in subclasses to implement specific processing logic.
        
        Returns:
            - A single Message to forward
            - A list of Messages to forward (fan-out)
            - None if no forwarding needed
        """
        ...
    
    async def _on_start(self) -> None:
        """Called when item is starting. Override for setup logic."""
        pass
    
    async def _on_stop(self) -> None:
        """Called when item is stopping. Override for cleanup logic."""
        pass
    
    def health_check(self) -> dict[str, Any]:
        """Return health status."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.item_type.value,
            "state": self._state.value,
            "healthy": self.is_healthy,
            "metrics": {
                "messages_received": self._metrics.messages_received,
                "messages_processed": self._metrics.messages_processed,
                "messages_failed": self._metrics.messages_failed,
                "messages_in_queue": self._metrics.messages_in_queue,
                "consecutive_errors": self._metrics.consecutive_errors,
                "processing_time_avg_ms": round(self._metrics.processing_time_avg_ms, 2),
            },
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, state={self._state.value})"


class Receiver(Item):
    """
    Base class for receiver items.
    
    Receivers accept messages from external systems and inject them
    into the HIE message flow.
    """
    
    def __init__(self, config: ItemConfig) -> None:
        config = config.model_copy(update={"item_type": ItemType.RECEIVER})
        super().__init__(config)
    
    async def _process(self, message: Message) -> Message | None:
        """Receivers typically just forward received messages."""
        return message
    
    @abstractmethod
    async def _receive_loop(self) -> None:
        """
        Main receive loop. Override to implement protocol-specific receiving.
        
        This method should:
        1. Listen for incoming data
        2. Create Message objects
        3. Call self.submit(message) to queue for processing
        """
        ...
    
    async def _on_start(self) -> None:
        """Start the receive loop."""
        task = asyncio.create_task(
            self._receive_loop(),
            name=f"{self.id}-receiver"
        )
        self._tasks.append(task)


class Processor(Item):
    """
    Base class for processor items.
    
    Processors transform, validate, route, or enrich messages.
    """
    
    def __init__(self, config: ItemConfig) -> None:
        config = config.model_copy(update={"item_type": ItemType.PROCESSOR})
        super().__init__(config)


class Sender(Item):
    """
    Base class for sender items.
    
    Senders deliver messages to external systems.
    """
    
    def __init__(self, config: ItemConfig) -> None:
        config = config.model_copy(update={"item_type": ItemType.SENDER})
        super().__init__(config)
    
    @abstractmethod
    async def _send(self, message: Message) -> bool:
        """
        Send a message to the external system.
        
        Returns True if successful, False otherwise.
        """
        ...
    
    async def _process(self, message: Message) -> Message | None:
        """Process by sending to external system."""
        success = await self._send(message)
        if success:
            return message  # Return for acknowledgment/logging
        return None
