"""
Tests for execution strategies.

Tests all four execution modes:
- AsyncExecutionStrategy
- MultiProcessExecutionStrategy
- ThreadPoolExecutionStrategy
- SingleProcessExecutionStrategy
"""
import pytest
import asyncio
import time
from Engine.core.executors import (
    AsyncExecutionStrategy,
    MultiProcessExecutionStrategy,
    ThreadPoolExecutionStrategy,
    SingleProcessExecutionStrategy,
    get_execution_strategy
)


# Dummy worker functions for testing


async def dummy_async_worker(worker_id: int, **kwargs):
    """Dummy async worker that runs for a few iterations."""
    shutdown_event = kwargs.get('shutdown_event')
    queue = kwargs.get('queue')

    for i in range(5):
        if shutdown_event and shutdown_event.is_set():
            break

        await asyncio.sleep(0.1)

        # For multiprocess: queue is mp.Queue
        # For async: queue is asyncio.Queue or None
        if queue and hasattr(queue, 'put'):
            try:
                if asyncio.iscoroutinefunction(queue.put):
                    await queue.put(f"worker-{worker_id}-msg-{i}")
                else:
                    queue.put(f"worker-{worker_id}-msg-{i}")
            except:
                pass


def blocking_worker(worker_id: int, **kwargs):
    """Blocking worker for thread pool testing."""
    for i in range(3):
        time.sleep(0.1)  # Blocking sleep


# Tests


@pytest.mark.asyncio
async def test_async_execution_strategy():
    """Test AsyncExecutionStrategy creates asyncio tasks."""
    strategy = AsyncExecutionStrategy()

    workers = await strategy.start_workers(
        dummy_async_worker,
        worker_count=4
    )

    assert len(workers) == 4
    assert all(isinstance(w, asyncio.Task) for w in workers)

    # Let workers run briefly
    await asyncio.sleep(0.3)

    # Stop workers
    await strategy.stop_workers(workers, timeout=2.0)


@pytest.mark.asyncio
async def test_multiprocess_execution_strategy():
    """Test MultiProcessExecutionStrategy creates OS processes."""
    strategy = MultiProcessExecutionStrategy()

    workers = await strategy.start_workers(
        dummy_async_worker,
        worker_count=2,
        queue_size=100
    )

    assert len(workers) == 2

    # Let workers run
    await asyncio.sleep(1.0)

    # Stop workers
    await strategy.stop_workers(workers, timeout=5.0)

    # Verify all processes stopped
    assert all(not w.is_alive() for w in workers)


@pytest.mark.asyncio
async def test_threadpool_execution_strategy():
    """Test ThreadPoolExecutionStrategy creates thread pool."""
    strategy = ThreadPoolExecutionStrategy()

    workers = await strategy.start_workers(
        dummy_async_worker,
        worker_count=3
    )

    assert len(workers) == 3

    # Let workers run
    await asyncio.sleep(1.0)

    # Stop workers
    await strategy.stop_workers(workers, timeout=5.0)


@pytest.mark.asyncio
async def test_single_process_execution_strategy():
    """Test SingleProcessExecutionStrategy forces count=1."""
    strategy = SingleProcessExecutionStrategy()

    # Request 4 workers, should get 1
    workers = await strategy.start_workers(
        dummy_async_worker,
        worker_count=4  # Requested 4
    )

    assert len(workers) == 1  # But got 1

    await asyncio.sleep(0.3)
    await strategy.stop_workers(workers, timeout=2.0)


def test_get_execution_strategy_factory():
    """Test get_execution_strategy factory function."""
    # Test all valid modes
    async_strat = get_execution_strategy("async")
    assert isinstance(async_strat, AsyncExecutionStrategy)

    mp_strat = get_execution_strategy("multi_process")
    assert isinstance(mp_strat, MultiProcessExecutionStrategy)

    tp_strat = get_execution_strategy("thread_pool")
    assert isinstance(tp_strat, ThreadPoolExecutionStrategy)

    sp_strat = get_execution_strategy("single_process")
    assert isinstance(sp_strat, SingleProcessExecutionStrategy)

    # Test invalid mode
    with pytest.raises(ValueError, match="Unknown execution mode"):
        get_execution_strategy("invalid_mode")


@pytest.mark.asyncio
async def test_multiprocess_with_shutdown_signal():
    """Test multiprocess workers respond to shutdown signal."""
    strategy = MultiProcessExecutionStrategy()

    workers = await strategy.start_workers(
        dummy_async_worker,
        worker_count=2
    )

    # Let workers start
    await asyncio.sleep(0.5)

    # Stop immediately
    await strategy.stop_workers(workers, timeout=3.0)

    # All should be dead
    assert all(not w.is_alive() for w in workers)
