"""
Execution Strategies for Different Concurrency Modes

Provides pluggable execution strategies for running service workers:
- AsyncExecutionStrategy: Asyncio tasks (current default)
- MultiProcessExecutionStrategy: OS-level processes (NEW - bypasses GIL)
- ThreadPoolExecutionStrategy: Thread pool for blocking I/O (NEW)
- SingleProcessExecutionStrategy: Single process, single worker (debugging)

Usage:
    strategy = get_execution_strategy("multi_process")
    workers = await strategy.start_workers(worker_func, count=4)
    await strategy.stop_workers(workers, timeout=30.0)
"""
from __future__ import annotations

import asyncio
import multiprocessing as mp
import signal
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)


class ExecutionStrategy(ABC):
    """
    Base class for execution strategies.

    Each strategy encapsulates how workers are created, managed, and stopped
    based on the execution mode (async, multiprocess, threadpool).
    """

    @abstractmethod
    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[Any]:
        """
        Start workers based on execution strategy.

        Args:
            worker_func: The worker function to run
            worker_count: Number of workers to create
            **kwargs: Additional arguments passed to workers

        Returns:
            List of worker handles (tasks, processes, or futures)
        """
        pass

    @abstractmethod
    async def stop_workers(self, workers: list[Any], timeout: float) -> None:
        """
        Stop all workers gracefully.

        Args:
            workers: List of worker handles
            timeout: Maximum seconds to wait for graceful shutdown
        """
        pass


class AsyncExecutionStrategy(ExecutionStrategy):
    """
    Asyncio task-based execution (current default).

    Creates asyncio.Task instances that run in the same event loop.
    Best for I/O-bound operations with high concurrency.

    Pros:
    - Lightweight (no process/thread overhead)
    - Excellent for I/O-bound work
    - Easy to debug

    Cons:
    - Single Python process (GIL bottleneck)
    - Not suitable for CPU-bound operations
    """

    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[asyncio.Task]:
        """Create asyncio tasks."""
        logger.info(
            "starting_async_workers",
            count=worker_count,
            strategy="async"
        )

        workers = []
        for i in range(worker_count):
            task = asyncio.create_task(
                worker_func(i, **kwargs),
                name=f"worker-async-{i}"
            )
            workers.append(task)

        return workers

    async def stop_workers(
        self,
        workers: list[asyncio.Task],
        timeout: float
    ) -> None:
        """Cancel asyncio tasks."""
        logger.info(
            "stopping_async_workers",
            count=len(workers),
            timeout=timeout
        )

        for task in workers:
            task.cancel()

        # Wait for cancellation
        await asyncio.gather(*workers, return_exceptions=True)


class MultiProcessExecutionStrategy(ExecutionStrategy):
    """
    Multiprocessing-based execution (NEW).

    Creates separate OS processes using multiprocessing.Process.
    Each process has its own Python interpreter and memory space.

    Pros:
    - True parallelism (bypasses GIL)
    - Excellent for CPU-bound operations
    - Process isolation (crash doesn't affect others)

    Cons:
    - Higher memory overhead
    - Inter-process communication overhead
    - More complex debugging

    Use for:
    - High-volume message processing
    - CPU-intensive transformations
    - True multi-core utilization
    """

    def __init__(self):
        self._manager = mp.Manager()
        self._processes: list[mp.Process] = []
        self._shutdown_event = mp.Event()

    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[mp.Process]:
        """Create OS processes."""
        logger.info(
            "starting_multiprocess_workers",
            count=worker_count,
            strategy="multi_process"
        )

        processes = []

        # Create inter-process queue
        queue_size = kwargs.get('queue_size', 1000)
        mp_queue = self._manager.Queue(maxsize=queue_size)

        # Create shutdown event
        self._shutdown_event.clear()

        for i in range(worker_count):
            process = mp.Process(
                target=self._run_process_worker,
                args=(i, worker_func, mp_queue, self._shutdown_event),
                kwargs=kwargs,
                name=f"worker-process-{i}"
            )
            process.start()
            processes.append(process)

            logger.info(
                "process_started",
                worker_id=i,
                pid=process.pid
            )

        self._processes = processes
        return processes

    async def stop_workers(
        self,
        workers: list[mp.Process],
        timeout: float
    ) -> None:
        """Terminate processes gracefully."""
        logger.info(
            "stopping_multiprocess_workers",
            count=len(workers),
            timeout=timeout
        )

        # Signal shutdown to all processes
        self._shutdown_event.set()

        # Wait for graceful shutdown
        deadline = timeout / len(workers) if workers else 0

        for process in workers:
            if process.is_alive():
                process.join(timeout=deadline)

                # Force kill if still alive
                if process.is_alive():
                    logger.warning(
                        "process_force_killed",
                        pid=process.pid,
                        name=process.name
                    )
                    process.terminate()
                    process.join(timeout=1.0)

                    # Last resort: SIGKILL
                    if process.is_alive():
                        process.kill()
                        process.join()

    @staticmethod
    def _run_process_worker(
        worker_id: int,
        worker_func: Callable,
        queue: mp.Queue,
        shutdown_event: mp.Event,
        **kwargs
    ) -> None:
        """
        Entry point for process worker.

        Runs in separate process - must create its own asyncio event loop.
        """
        # Setup logging for this process
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
        )

        proc_logger = structlog.get_logger(__name__)
        proc_logger.info(
            "process_worker_started",
            worker_id=worker_id,
            pid=mp.current_process().pid
        )

        # Create new event loop for this process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Setup signal handlers
        def signal_handler(signum, frame):
            proc_logger.info("process_received_signal", signal=signum)
            shutdown_event.set()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            # Run worker function in this process's event loop
            loop.run_until_complete(
                worker_func(
                    worker_id,
                    queue=queue,
                    shutdown_event=shutdown_event,
                    **kwargs
                )
            )
        except Exception as e:
            proc_logger.error(
                "process_worker_error",
                worker_id=worker_id,
                error=str(e)
            )
            raise
        finally:
            loop.close()
            proc_logger.info(
                "process_worker_stopped",
                worker_id=worker_id
            )


class ThreadPoolExecutionStrategy(ExecutionStrategy):
    """
    Thread pool-based execution (NEW).

    Creates a thread pool using concurrent.futures.ThreadPoolExecutor.
    Each thread runs in the same process but with separate execution context.

    Pros:
    - Good for blocking I/O (file, database)
    - Lower overhead than multiprocessing
    - Shared memory (easier communication)

    Cons:
    - Still affected by GIL for CPU-bound work
    - Not true parallelism for Python code

    Use for:
    - Blocking I/O operations
    - Legacy sync libraries
    - Mixed async/sync workloads
    """

    def __init__(self):
        self._executor: ThreadPoolExecutor | None = None
        self._shutdown_event = asyncio.Event()

    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[asyncio.Future]:
        """Create thread pool."""
        logger.info(
            "starting_threadpool_workers",
            count=worker_count,
            strategy="thread_pool"
        )

        self._executor = ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="worker-thread"
        )

        # Submit worker tasks to thread pool
        futures = []
        loop = asyncio.get_event_loop()

        for i in range(worker_count):
            future = loop.run_in_executor(
                self._executor,
                self._run_thread_worker,
                i,
                worker_func,
                self._shutdown_event,
                kwargs
            )
            futures.append(future)

        return futures

    async def stop_workers(
        self,
        workers: list[asyncio.Future],
        timeout: float
    ) -> None:
        """Shutdown thread pool."""
        logger.info(
            "stopping_threadpool_workers",
            count=len(workers),
            timeout=timeout
        )

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for threads with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*workers, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("thread_shutdown_timeout")

        # Shutdown executor
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)

    @staticmethod
    def _run_thread_worker(
        worker_id: int,
        worker_func: Callable,
        shutdown_event: asyncio.Event,
        kwargs: dict
    ) -> None:
        """
        Entry point for thread worker.

        Runs in thread - must create its own asyncio event loop.
        """
        thread_logger = structlog.get_logger(__name__)
        thread_logger.info(
            "thread_worker_started",
            worker_id=worker_id
        )

        # Create event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                worker_func(
                    worker_id,
                    shutdown_event=shutdown_event,
                    **kwargs
                )
            )
        except Exception as e:
            thread_logger.error(
                "thread_worker_error",
                worker_id=worker_id,
                error=str(e)
            )
            raise
        finally:
            loop.close()
            thread_logger.info(
                "thread_worker_stopped",
                worker_id=worker_id
            )


class SingleProcessExecutionStrategy(AsyncExecutionStrategy):
    """
    Single process, single worker execution.

    Same as AsyncExecutionStrategy but forces worker_count=1.
    Useful for debugging and simple use cases.
    """

    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[asyncio.Task]:
        """Create single worker."""
        logger.info(
            "starting_single_worker",
            strategy="single_process"
        )

        # Force count to 1
        return await super().start_workers(worker_func, 1, **kwargs)


def get_execution_strategy(mode: str) -> ExecutionStrategy:
    """
    Factory for execution strategies.

    Args:
        mode: Execution mode string: "async", "multi_process", "thread_pool", "single_process"

    Returns:
        ExecutionStrategy instance

    Raises:
        ValueError: If mode is unknown
    """
    strategies = {
        "async": AsyncExecutionStrategy,
        "multi_process": MultiProcessExecutionStrategy,
        "thread_pool": ThreadPoolExecutionStrategy,
        "single_process": SingleProcessExecutionStrategy,
    }

    strategy_class = strategies.get(mode)
    if not strategy_class:
        raise ValueError(
            f"Unknown execution mode: {mode}. "
            f"Valid modes: {', '.join(strategies.keys())}"
        )

    return strategy_class()
