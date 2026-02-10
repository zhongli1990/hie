"""
Unit tests for configurable queue types and overflow strategies.
"""

import asyncio
import pytest
from Engine.core.queues import (
    QueueType,
    OverflowStrategy,
    ManagedQueue,
    QueueOverflowError,
)
from Engine.core.messaging import MessageEnvelope, MessagePriority


@pytest.mark.asyncio
class TestQueueTypes:
    """Test different queue type behaviors."""

    async def test_fifo_queue_ordering(self):
        """Test FIFO queue maintains order."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Put items in order
        for i in range(5):
            await queue.put(i)

        # Should come out in same order
        for i in range(5):
            item = await queue.get()
            assert item == i

    async def test_lifo_queue_ordering(self):
        """Test LIFO queue reverses order."""
        queue = ManagedQueue[int](
            queue_type=QueueType.LIFO,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Put items in order
        for i in range(5):
            await queue.put(i)

        # Should come out in reverse order
        for i in range(4, -1, -1):
            item = await queue.get()
            assert item == i

    async def test_priority_queue_ordering(self):
        """Test priority queue orders by priority."""
        queue = ManagedQueue[MessageEnvelope](
            queue_type=QueueType.PRIORITY,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Put items with different priorities
        high = MessageEnvelope(message="high", priority=MessagePriority.HIGH)
        normal = MessageEnvelope(message="normal", priority=MessagePriority.NORMAL)
        critical = MessageEnvelope(message="critical", priority=MessagePriority.CRITICAL)
        low = MessageEnvelope(message="low", priority=MessagePriority.LOW)

        # Add in random order
        await queue.put(normal)
        await queue.put(low)
        await queue.put(critical)
        await queue.put(high)

        # Should come out by priority
        assert (await queue.get()).message == "critical"
        assert (await queue.get()).message == "high"
        assert (await queue.get()).message == "normal"
        assert (await queue.get()).message == "low"

    async def test_unordered_queue_basic(self):
        """Test unordered queue basic functionality."""
        queue = ManagedQueue[int](
            queue_type=QueueType.UNORDERED,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Put items
        for i in range(5):
            await queue.put(i)

        # Should get all items back (order not guaranteed)
        results = []
        for _ in range(5):
            results.append(await queue.get())

        assert sorted(results) == [0, 1, 2, 3, 4]
        assert len(results) == 5


@pytest.mark.asyncio
class TestOverflowStrategies:
    """Test different overflow handling strategies."""

    async def test_block_strategy(self):
        """Test BLOCK strategy waits for space."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=2,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Fill queue
        await queue.put(1)
        await queue.put(2)
        assert queue.full()

        # Try to put with timeout should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.put(3), timeout=0.1)

        # Remove one item
        assert await queue.get() == 1

        # Now should be able to put
        await queue.put(3)
        assert queue.qsize() == 2

    async def test_drop_oldest_strategy(self):
        """Test DROP_OLDEST removes oldest item."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=2,
            overflow_strategy=OverflowStrategy.DROP_OLDEST
        )

        # Fill queue
        await queue.put(1)
        await queue.put(2)
        assert queue.full()

        # Put new item - should drop oldest (1)
        await queue.put(3)

        # Should have 2 and 3
        assert await queue.get() == 2
        assert await queue.get() == 3

    async def test_drop_newest_strategy(self):
        """Test DROP_NEWEST rejects new item."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=2,
            overflow_strategy=OverflowStrategy.DROP_NEWEST
        )

        # Fill queue
        await queue.put(1)
        await queue.put(2)
        assert queue.full()

        # Put new item - should be dropped
        await queue.put(3)

        # Should still have 1 and 2
        assert await queue.get() == 1
        assert await queue.get() == 2

    async def test_reject_strategy(self):
        """Test REJECT raises exception."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=2,
            overflow_strategy=OverflowStrategy.REJECT
        )

        # Fill queue
        await queue.put(1)
        await queue.put(2)
        assert queue.full()

        # Put new item - should raise exception
        with pytest.raises(QueueOverflowError):
            await queue.put(3)


@pytest.mark.asyncio
class TestQueueProperties:
    """Test queue property methods."""

    async def test_empty_property(self):
        """Test empty() property."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=5,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        assert queue.empty()

        await queue.put(1)
        assert not queue.empty()

        await queue.get()
        assert queue.empty()

    async def test_full_property(self):
        """Test full() property."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=2,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        assert not queue.full()

        await queue.put(1)
        assert not queue.full()

        await queue.put(2)
        assert queue.full()

        await queue.get()
        assert not queue.full()

    async def test_qsize_property(self):
        """Test qsize() property."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        assert queue.qsize() == 0

        for i in range(5):
            await queue.put(i)

        assert queue.qsize() == 5

        await queue.get()
        assert queue.qsize() == 4

    async def test_maxsize_property(self):
        """Test maxsize property."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        assert queue.maxsize == 10

    async def test_get_with_timeout(self):
        """Test get() with timeout."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Empty queue should timeout
        with pytest.raises(asyncio.TimeoutError):
            await queue.get(timeout=0.1)


@pytest.mark.asyncio
class TestQueueConcurrency:
    """Test queue behavior under concurrent access."""

    async def test_concurrent_producers(self):
        """Test multiple producers don't lose messages."""
        queue = ManagedQueue[int](
            queue_type=QueueType.UNORDERED,
            maxsize=1000,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        async def producer(start: int, count: int):
            for i in range(start, start + count):
                await queue.put(i)

        # Start 10 producers, each adding 10 items
        tasks = [producer(i * 10, 10) for i in range(10)]
        await asyncio.gather(*tasks)

        # Should have 100 items
        assert queue.qsize() == 100

        # Collect all items
        results = []
        while not queue.empty():
            results.append(await queue.get())

        assert len(results) == 100
        assert sorted(results) == list(range(100))

    async def test_concurrent_consumers(self):
        """Test multiple consumers process all messages."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=1000,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Fill queue
        for i in range(100):
            await queue.put(i)

        results = []
        lock = asyncio.Lock()

        async def consumer():
            while True:
                try:
                    item = await queue.get(timeout=0.5)
                    async with lock:
                        results.append(item)
                except asyncio.TimeoutError:
                    break

        # Start 5 consumers
        tasks = [consumer() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Should have processed all 100 items
        assert len(results) == 100
        assert sorted(results) == list(range(100))


@pytest.mark.asyncio
class TestQueueStatistics:
    """Test queue statistics tracking."""

    async def test_overflow_count(self):
        """Test overflow statistics."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=2,
            overflow_strategy=OverflowStrategy.DROP_NEWEST
        )

        # Fill queue
        await queue.put(1)
        await queue.put(2)

        # Cause overflows
        await queue.put(3)
        await queue.put(4)
        await queue.put(5)

        # Should have tracked 3 overflows
        stats = queue.get_stats()
        assert stats["overflow_count"] == 3
        assert stats["items_dropped"] == 3

    async def test_throughput_stats(self):
        """Test throughput statistics."""
        queue = ManagedQueue[int](
            queue_type=QueueType.FIFO,
            maxsize=10,
            overflow_strategy=OverflowStrategy.BLOCK
        )

        # Process some items
        for i in range(5):
            await queue.put(i)

        for _ in range(5):
            await queue.get()

        stats = queue.get_stats()
        assert stats["items_put"] == 5
        assert stats["items_get"] == 5
        assert stats["current_size"] == 0
