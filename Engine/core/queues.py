"""
Configurable Queue Types for Message Processing

Provides different queue ordering strategies for different messaging patterns:
- FIFO: First-in-first-out (strict ordering)
- Priority: Priority-based ordering (high priority first)
- LIFO: Last-in-first-out (stack-based)
- Unordered: No ordering guarantees (maximum throughput)

Usage:
    queue = create_queue(QueueType.PRIORITY, maxsize=1000)
    await queue.put((priority, message))
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

import structlog

from Engine.core.messaging import MessagePriority, MessageEnvelope

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class QueueType(str, Enum):
    """Queue ordering strategies."""
    FIFO = "fifo"               # First-in-first-out (default)
    PRIORITY = "priority"       # Priority-based
    LIFO = "lifo"               # Last-in-first-out (stack)
    UNORDERED = "unordered"     # No ordering (fastest)


class OverflowStrategy(str, Enum):
    """Queue overflow handling strategies."""
    BLOCK = "block"             # Block until space available
    DROP_OLDEST = "drop_oldest" # Drop oldest message
    DROP_NEWEST = "drop_newest" # Drop incoming message
    REDIRECT = "redirect"       # Redirect to overflow queue


class UnorderedQueue(asyncio.Queue):
    """
    Queue with no ordering guarantees.

    Optimized for maximum throughput by allowing workers to grab
    messages in any order. Uses asyncio.Queue internally but
    explicitly documents that order is not guaranteed.

    Best for: High-volume concurrent async patterns
    """

    def __init__(self, maxsize: int = 0):
        super().__init__(maxsize=maxsize)
        self._type = QueueType.UNORDERED


@dataclass
class QueueMetrics:
    """Runtime metrics for a queue."""
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_dropped: int = 0
    peak_size: int = 0
    current_size: int = 0

    @property
    def messages_in_flight(self) -> int:
        """Messages currently in queue."""
        return self.total_enqueued - self.total_dequeued - self.total_dropped


class ManagedQueue(Generic[T]):
    """
    Wrapper around asyncio queues with metrics and overflow handling.

    Provides:
    - Configurable queue type (FIFO, Priority, LIFO, Unordered)
    - Overflow strategies (block, drop, redirect)
    - Runtime metrics
    - Pattern-aware queue selection
    """

    def __init__(
        self,
        queue_type: QueueType = QueueType.FIFO,
        maxsize: int = 1000,
        overflow_strategy: OverflowStrategy = OverflowStrategy.BLOCK,
        overflow_queue: ManagedQueue | None = None
    ):
        """
        Initialize managed queue.

        Args:
            queue_type: Queue ordering strategy
            maxsize: Maximum queue size (0 = unlimited)
            overflow_strategy: How to handle queue full
            overflow_queue: Redirect target for overflow
        """
        self._queue_type = queue_type
        self._maxsize = maxsize
        self._overflow_strategy = overflow_strategy
        self._overflow_queue = overflow_queue

        # Create underlying queue
        self._queue = self._create_queue(queue_type, maxsize)

        # Metrics
        self._metrics = QueueMetrics()

        # Logging
        self._log = logger.bind(queue_type=queue_type.value)

    def _create_queue(
        self,
        queue_type: QueueType,
        maxsize: int
    ) -> asyncio.Queue:
        """Create appropriate queue type."""
        if queue_type == QueueType.FIFO:
            return asyncio.Queue(maxsize=maxsize)

        elif queue_type == QueueType.PRIORITY:
            return asyncio.PriorityQueue(maxsize=maxsize)

        elif queue_type == QueueType.LIFO:
            return asyncio.LifoQueue(maxsize=maxsize)

        elif queue_type == QueueType.UNORDERED:
            return UnorderedQueue(maxsize=maxsize)

        else:
            raise ValueError(f"Unknown queue type: {queue_type}")

    async def put(self, item: T) -> bool:
        """
        Put item in queue with overflow handling.

        Args:
            item: Item to enqueue

        Returns:
            True if enqueued, False if dropped

        Raises:
            asyncio.QueueFull: If strategy is BLOCK and queue is full
        """
        # For priority queues, wrap item if needed
        if self._queue_type == QueueType.PRIORITY:
            item = self._wrap_for_priority(item)

        # Handle overflow
        if self._queue.full():
            return await self._handle_overflow(item)

        # Normal put
        try:
            await self._queue.put(item)
            self._metrics.total_enqueued += 1
            self._metrics.current_size = self._queue.qsize()
            self._metrics.peak_size = max(
                self._metrics.peak_size,
                self._metrics.current_size
            )
            return True

        except asyncio.QueueFull:
            return await self._handle_overflow(item)

    async def get(self, timeout: float | None = None) -> T:
        """
        Get item from queue.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            Item from queue

        Raises:
            asyncio.TimeoutError: If timeout expires
        """
        if timeout:
            item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        else:
            item = await self._queue.get()

        # Unwrap priority items
        if self._queue_type == QueueType.PRIORITY:
            item = self._unwrap_priority(item)

        self._metrics.total_dequeued += 1
        self._metrics.current_size = self._queue.qsize()

        return item

    async def _handle_overflow(self, item: T) -> bool:
        """Handle queue overflow based on strategy."""
        if self._overflow_strategy == OverflowStrategy.BLOCK:
            # Block until space (default asyncio behavior)
            await self._queue.put(item)
            self._metrics.total_enqueued += 1
            return True

        elif self._overflow_strategy == OverflowStrategy.DROP_NEWEST:
            # Drop incoming message
            self._metrics.total_dropped += 1
            self._log.warning(
                "queue_overflow_drop_newest",
                size=self._queue.qsize()
            )
            return False

        elif self._overflow_strategy == OverflowStrategy.DROP_OLDEST:
            # Drop oldest, add new
            try:
                await self._queue.get()  # Remove oldest
                await self._queue.put(item)  # Add new
                self._metrics.total_dropped += 1
                self._log.warning(
                    "queue_overflow_drop_oldest",
                    size=self._queue.qsize()
                )
                return True
            except:
                return False

        elif self._overflow_strategy == OverflowStrategy.REDIRECT:
            # Redirect to overflow queue
            if self._overflow_queue:
                result = await self._overflow_queue.put(item)
                if result:
                    self._log.info(
                        "queue_overflow_redirected",
                        target_queue=self._overflow_queue._queue_type
                    )
                return result
            else:
                self._log.error("queue_overflow_no_redirect_target")
                return False

        return False

    def _wrap_for_priority(self, item: T) -> tuple[int, T]:
        """Wrap item with priority for PriorityQueue."""
        # Extract priority if MessageEnvelope
        if isinstance(item, MessageEnvelope):
            priority = item.priority.value
            return (priority, item)

        # Default to normal priority
        return (MessagePriority.NORMAL.value, item)

    def _unwrap_priority(self, item: tuple[int, T]) -> T:
        """Unwrap priority item."""
        if isinstance(item, tuple) and len(item) == 2:
            return item[1]
        return item

    def qsize(self) -> int:
        """Current queue size."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def full(self) -> bool:
        """Check if queue is full."""
        return self._queue.full()

    def task_done(self) -> None:
        """Mark task as done."""
        self._queue.task_done()

    @property
    def metrics(self) -> QueueMetrics:
        """Queue metrics."""
        self._metrics.current_size = self._queue.qsize()
        return self._metrics

    @property
    def queue_type(self) -> QueueType:
        """Queue type."""
        return self._queue_type


def create_queue(
    queue_type: QueueType = QueueType.FIFO,
    maxsize: int = 1000,
    overflow_strategy: OverflowStrategy = OverflowStrategy.BLOCK,
    overflow_queue: ManagedQueue | None = None
) -> ManagedQueue:
    """
    Factory function to create managed queues.

    Args:
        queue_type: Queue ordering strategy
        maxsize: Maximum queue size
        overflow_strategy: Overflow handling
        overflow_queue: Redirect target

    Returns:
        ManagedQueue instance
    """
    return ManagedQueue(
        queue_type=queue_type,
        maxsize=maxsize,
        overflow_strategy=overflow_strategy,
        overflow_queue=overflow_queue
    )
