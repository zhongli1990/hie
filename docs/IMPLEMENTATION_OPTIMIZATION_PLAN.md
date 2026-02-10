# HIE Implementation Optimization Plan
**Remediation Strategy for Critical Architectural Gaps**

**Version:** 1.0.0
**Date:** February 10, 2026
**Sprint:** Phase 1 - Critical Gaps Resolution
**Duration:** 2-3 weeks (14-21 days)
**Branch:** `feature/multiprocess-concurrency-implementation`

---

## Executive Summary

This plan provides **detailed implementation steps** to close the **11 critical gaps** identified in the Architecture QA Review, bringing HIE to **100% compliance** with mandatory technical requirements.

**Current State:** 59% compliant (16/27 mandatory requirements)
**Target State:** 100% compliant (27/27 mandatory requirements)
**Timeline:** 3 sprints (5 weeks total)

---

## Phase 1: Critical Gaps (P0) - 2 Weeks

### Gap #1: Multiprocessing Not Implemented 🔴 CRITICAL

**Requirement:** Support `ExecutionMode.MULTI_PROCESS` with true OS-level process isolation

#### Problem Analysis

**Current State:**
```python
# Engine/core/item.py - Defined but not used
class ExecutionMode(str, Enum):
    MULTI_PROCESS = "multi_process"  # ❌ NOT IMPLEMENTED

# Engine/li/hosts/base.py:225 - Only creates asyncio tasks
for i in range(self._pool_size):
    worker = asyncio.create_task(self._worker_loop(i))  # ❌ Not a process
```

**Impact:**
- All workers in single Python process (GIL bottleneck)
- Cannot utilize multiple CPU cores
- Limited throughput for CPU-bound transformations

#### Solution Design

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│ ProductionEngine (Main Process)                         │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ HL7Service   │  │ Router       │  │ HTTPSender   │  │
│  │              │  │              │  │              │  │
│  │ Process 1    │  │ Process 1    │  │ Process 1    │  │
│  │ Process 2    │  │ Process 2    │  │ Process 2    │  │
│  │ Process 3    │  │ Process 3    │  │ Process 3    │  │
│  │ Process 4    │  │ Process 4    │  │ Process 4    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ↓                  ↓                  ↓          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Inter-Process Message Queue (multiprocessing)     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

#### Implementation Steps

**Step 1.1: Create Process Executor Module**

**File:** `Engine/core/executors.py` (NEW)

```python
"""
Execution strategies for different concurrency modes.
"""
from __future__ import annotations

import asyncio
import multiprocessing as mp
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)


class ExecutionStrategy(ABC):
    """Base class for execution strategies."""

    @abstractmethod
    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[Any]:
        """Start workers based on execution strategy."""
        pass

    @abstractmethod
    async def stop_workers(self, workers: list[Any], timeout: float) -> None:
        """Stop all workers gracefully."""
        pass


class AsyncExecutionStrategy(ExecutionStrategy):
    """Asyncio task-based execution (current implementation)."""

    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[asyncio.Task]:
        """Create asyncio tasks."""
        workers = []
        for i in range(worker_count):
            task = asyncio.create_task(
                worker_func(i, **kwargs),
                name=f"worker-{i}"
            )
            workers.append(task)
        return workers

    async def stop_workers(
        self,
        workers: list[asyncio.Task],
        timeout: float
    ) -> None:
        """Cancel asyncio tasks."""
        for task in workers:
            task.cancel()

        await asyncio.gather(*workers, return_exceptions=True)


class MultiProcessExecutionStrategy(ExecutionStrategy):
    """Multiprocessing-based execution (NEW)."""

    def __init__(self):
        self._manager = mp.Manager()
        self._processes: list[mp.Process] = []

    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[mp.Process]:
        """Create OS processes."""
        processes = []

        # Create inter-process queue
        queue = self._manager.Queue(maxsize=kwargs.get('queue_size', 1000))

        for i in range(worker_count):
            process = mp.Process(
                target=self._run_process_worker,
                args=(i, worker_func, queue),
                kwargs=kwargs,
                name=f"worker-process-{i}"
            )
            process.start()
            processes.append(process)

        self._processes = processes
        return processes

    async def stop_workers(
        self,
        workers: list[mp.Process],
        timeout: float
    ) -> None:
        """Terminate processes gracefully."""
        # Send shutdown signal to each process
        for process in workers:
            if process.is_alive():
                process.terminate()

        # Wait for graceful shutdown
        for process in workers:
            process.join(timeout=timeout / len(workers))

            # Force kill if still alive
            if process.is_alive():
                logger.warning(
                    "process_force_killed",
                    pid=process.pid
                )
                process.kill()
                process.join()

    @staticmethod
    def _run_process_worker(
        worker_id: int,
        worker_func: Callable,
        queue: mp.Queue,
        **kwargs
    ) -> None:
        """
        Entry point for process worker.

        Runs in separate process - must handle asyncio event loop.
        """
        # Create new event loop for this process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run worker function in this process's event loop
            loop.run_until_complete(
                worker_func(worker_id, queue=queue, **kwargs)
            )
        finally:
            loop.close()


class ThreadPoolExecutionStrategy(ExecutionStrategy):
    """Thread pool-based execution (NEW)."""

    def __init__(self):
        self._executor: ThreadPoolExecutor | None = None

    async def start_workers(
        self,
        worker_func: Callable,
        worker_count: int,
        **kwargs
    ) -> list[Any]:
        """Create thread pool."""
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
                kwargs
            )
            futures.append(future)

        return futures

    async def stop_workers(
        self,
        workers: list[Any],
        timeout: float
    ) -> None:
        """Shutdown thread pool."""
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)

    @staticmethod
    def _run_thread_worker(
        worker_id: int,
        worker_func: Callable,
        kwargs: dict
    ) -> None:
        """
        Entry point for thread worker.

        Runs in thread - must handle asyncio event loop.
        """
        # Create event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                worker_func(worker_id, **kwargs)
            )
        finally:
            loop.close()


def get_execution_strategy(mode: str) -> ExecutionStrategy:
    """Factory for execution strategies."""
    strategies = {
        "async": AsyncExecutionStrategy,
        "multi_process": MultiProcessExecutionStrategy,
        "thread_pool": ThreadPoolExecutionStrategy,
        "single_process": AsyncExecutionStrategy,  # Same as async
    }

    strategy_class = strategies.get(mode)
    if not strategy_class:
        raise ValueError(f"Unknown execution mode: {mode}")

    return strategy_class()
```

**Step 1.2: Update Host Base Class**

**File:** `Engine/li/hosts/base.py` (MODIFY)

```python
from Engine.core.executors import get_execution_strategy, ExecutionStrategy

class Host(ABC):
    def __init__(self, ...):
        # Add execution strategy
        self._execution_strategy: ExecutionStrategy | None = None

    async def start(self) -> None:
        """Start with execution strategy pattern."""
        # ... existing code ...

        # Get execution strategy based on config
        execution_mode = self.get_setting("Host", "ExecutionMode", "async")
        self._execution_strategy = get_execution_strategy(execution_mode)

        # Start workers using strategy
        self._workers = await self._execution_strategy.start_workers(
            worker_func=self._worker_loop,
            worker_count=self._pool_size,
            queue_size=queue_size,
            shutdown_event=self._shutdown_event,
            pause_event=self._pause_event
        )

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop using execution strategy."""
        if self._execution_strategy and self._workers:
            await self._execution_strategy.stop_workers(
                self._workers,
                timeout
            )
```

**Step 1.3: Update ItemConfig**

**File:** `Engine/li/config/item_config.py` (MODIFY)

```python
class ItemConfig(BaseModel):
    # ... existing fields ...

    # Execution configuration
    execution_mode: str = Field(
        default="async",
        description="Execution mode: async, multi_process, thread_pool, single_process"
    )

    host_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Host-specific settings including ExecutionMode"
    )
```

**Step 1.4: Add Tests**

**File:** `tests/unit/test_executors.py` (NEW)

```python
import pytest
import asyncio
from Engine.core.executors import (
    AsyncExecutionStrategy,
    MultiProcessExecutionStrategy,
    ThreadPoolExecutionStrategy
)


async def dummy_worker(worker_id: int, **kwargs):
    """Dummy worker for testing."""
    for i in range(5):
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_async_execution_strategy():
    strategy = AsyncExecutionStrategy()
    workers = await strategy.start_workers(dummy_worker, 4)

    assert len(workers) == 4
    assert all(isinstance(w, asyncio.Task) for w in workers)

    await strategy.stop_workers(workers, timeout=5.0)


@pytest.mark.asyncio
async def test_multiprocess_execution_strategy():
    strategy = MultiProcessExecutionStrategy()
    workers = await strategy.start_workers(dummy_worker, 2)

    assert len(workers) == 2

    await asyncio.sleep(1.0)  # Let workers run
    await strategy.stop_workers(workers, timeout=5.0)


@pytest.mark.asyncio
async def test_threadpool_execution_strategy():
    strategy = ThreadPoolExecutionStrategy()
    workers = await strategy.start_workers(dummy_worker, 3)

    assert len(workers) == 3

    await asyncio.sleep(1.0)
    await strategy.stop_workers(workers, timeout=5.0)
```

**Effort:** 5 days
**Files Changed:** 4 new, 2 modified
**Lines of Code:** ~500

---

### Gap #2: Thread Pool Not Implemented 🔴 CRITICAL

**Status:** ✅ Solved by Gap #1 implementation above

The `ThreadPoolExecutionStrategy` in `executors.py` provides full thread pool support.

**Additional work needed:**
- Documentation on when to use THREAD_POOL vs ASYNC
- Performance benchmarks

**Effort:** 1 day (documentation + benchmarks)

---

### Gap #3: Service-to-Service Messaging 🔴 CRITICAL

**Requirement:** Services must be able to call other services directly (like IRIS `SendRequestSync`)

#### Problem Analysis

**Current State:**
- Services can only emit to Production-level callback
- No direct service-to-service communication
- No request/reply correlation

**Desired State:**
```python
class HL7RoutingEngine(BusinessProcess):
    async def _process_message(self, message: HL7Message) -> HL7Message:
        # Call PDS lookup service synchronously
        patient_data = await self.send_request_sync(
            "PDS.Lookup.Service",
            {"nhs_number": message.PID.PatientID},
            timeout=5.0
        )

        # Enrich message with PDS data
        message.PID.PatientName = patient_data["name"]
        return message
```

#### Solution Design

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│ ProductionEngine                                    │
│  - Service Registry: {"ServiceA": ServiceA_instance}│
│  - Message Router                                    │
│                                                       │
│  ┌──────────────┐           ┌──────────────┐        │
│  │ Service A    │  request  │ Service B    │        │
│  │              │──────────>│              │        │
│  │              │<──────────│              │        │
│  │              │  response │              │        │
│  └──────────────┘           └──────────────┘        │
│         │                                             │
│         └─> service_registry.get("ServiceB")         │
└─────────────────────────────────────────────────────┘
```

#### Implementation Steps

**Step 3.1: Add Service Registry to ProductionEngine**

**File:** `Engine/li/engine/production.py` (MODIFY)

```python
class ProductionEngine:
    def __init__(self, config: EngineConfig | None = None):
        # ... existing ...
        self._service_registry: dict[str, Host] = {}
        self._pending_requests: dict[str, asyncio.Future] = {}

    async def _create_hosts(self) -> None:
        """Create and register all hosts."""
        # ... existing host creation ...

        # Register all hosts in service registry
        for name, host in self._all_hosts.items():
            self._service_registry[name] = host

    def get_service(self, name: str) -> Host | None:
        """Get service by name for inter-service calls."""
        return self._service_registry.get(name)

    async def route_request(
        self,
        source: str,
        target: str,
        message: Any,
        correlation_id: str
    ) -> asyncio.Future:
        """
        Route request from source service to target service.

        Returns Future that will be resolved when target responds.
        """
        target_host = self._service_registry.get(target)
        if not target_host:
            raise ValueError(f"Unknown target service: {target}")

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[correlation_id] = future

        # Enqueue message to target
        await target_host._queue.put({
            "message": message,
            "correlation_id": correlation_id,
            "source": source
        })

        return future

    async def send_response(
        self,
        correlation_id: str,
        response: Any
    ) -> None:
        """Send response back to waiting caller."""
        future = self._pending_requests.pop(correlation_id, None)
        if future and not future.done():
            future.set_result(response)
```

**Step 3.2: Add Messaging Methods to Host**

**File:** `Engine/li/hosts/base.py` (MODIFY)

```python
from uuid import uuid4

class Host(ABC):
    def __init__(self, ...):
        # ... existing ...
        self._production: ProductionEngine | None = None  # Set by ProductionEngine

    def set_production(self, production: ProductionEngine) -> None:
        """Register production engine for inter-service calls."""
        self._production = production

    async def send_request_sync(
        self,
        target: str,
        message: Any,
        timeout: float = 30.0
    ) -> Any:
        """
        Send synchronous request to another service.

        Like IRIS: Set response = ..SendRequestSync("TargetService", request)

        Args:
            target: Target service name
            message: Request message
            timeout: Response timeout in seconds

        Returns:
            Response from target service

        Raises:
            asyncio.TimeoutError: If no response within timeout
            ValueError: If target service not found
        """
        if not self._production:
            raise RuntimeError("Host not registered with production")

        # Generate correlation ID
        correlation_id = str(uuid4())

        # Route request through production
        response_future = await self._production.route_request(
            source=self._name,
            target=target,
            message=message,
            correlation_id=correlation_id
        )

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._log.error(
                "request_timeout",
                target=target,
                correlation_id=correlation_id
            )
            raise

    async def send_request_async(
        self,
        target: str,
        message: Any
    ) -> None:
        """
        Send asynchronous request to another service (fire-and-forget).

        Like IRIS: Do ..SendRequestAsync("TargetService", request)

        Args:
            target: Target service name
            message: Request message
        """
        if not self._production:
            raise RuntimeError("Host not registered with production")

        target_host = self._production.get_service(target)
        if not target_host:
            raise ValueError(f"Unknown target service: {target}")

        # Enqueue directly (no response expected)
        await target_host._queue.put({
            "message": message,
            "source": self._name,
            "async": True
        })

    async def send_response(
        self,
        correlation_id: str,
        response: Any
    ) -> None:
        """
        Send response back to caller.

        Use in service that receives SendRequestSync call.

        Args:
            correlation_id: ID from incoming request
            response: Response data
        """
        if not self._production:
            raise RuntimeError("Host not registered with production")

        await self._production.send_response(correlation_id, response)
```

**Step 3.3: Update Worker Loop to Handle Requests**

**File:** `Engine/li/hosts/base.py` (MODIFY)

```python
async def _worker_loop(self, worker_id: int) -> None:
    """Worker loop with request/response support."""
    while not self._shutdown_event.is_set():
        await self._pause_event.wait()

        try:
            message_envelope = await asyncio.wait_for(
                self._queue.get(),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            continue

        # Extract message and metadata
        if isinstance(message_envelope, dict):
            message = message_envelope.get("message")
            correlation_id = message_envelope.get("correlation_id")
            source = message_envelope.get("source")
            is_async = message_envelope.get("async", False)
        else:
            # Legacy: just a message
            message = message_envelope
            correlation_id = None
            source = None
            is_async = False

        # Process message
        try:
            result = await self._process_message(message)

            # Send response if this was a sync request
            if correlation_id and not is_async:
                await self.send_response(correlation_id, result)

            # Otherwise, route to next service
            elif result and self._on_message:
                await self._on_message(result)

        except Exception as e:
            self._log.error("message_processing_failed", error=str(e))
            if self._on_error:
                await self._on_error(e, message)
```

**Step 3.4: Add Tests**

**File:** `tests/unit/test_service_messaging.py` (NEW)

```python
import pytest
import asyncio
from Engine.li.hosts import BusinessService, BusinessOperation
from Engine.li.engine.production import ProductionEngine


class LookupService(BusinessService):
    """Mock lookup service."""

    async def _process_message(self, message: dict) -> dict:
        # Simulate PDS lookup
        return {
            "nhs_number": message["nhs_number"],
            "name": "John Smith",
            "dob": "1980-01-01"
        }


class RoutingService(BusinessService):
    """Mock routing service that calls lookup."""

    async def _process_message(self, message: dict) -> dict:
        # Call lookup service synchronously
        patient_data = await self.send_request_sync(
            "LookupService",
            {"nhs_number": message["nhs_number"]},
            timeout=5.0
        )

        return {
            **message,
            "patient": patient_data
        }


@pytest.mark.asyncio
async def test_service_to_service_sync_call():
    """Test synchronous service call."""
    engine = ProductionEngine()

    # Create services
    lookup = LookupService("LookupService")
    router = RoutingService("RouterService")

    # Register with production
    lookup.set_production(engine)
    router.set_production(engine)

    engine._service_registry["LookupService"] = lookup
    engine._service_registry["RouterService"] = router

    # Start services
    await lookup.start()
    await router.start()

    # Send message to router (which will call lookup)
    result = await router._process_message({"nhs_number": "123456"})

    assert result["patient"]["name"] == "John Smith"

    await lookup.stop()
    await router.stop()
```

**Effort:** 4 days
**Files Changed:** 2 modified, 1 new test
**Lines of Code:** ~300

---

### Gap #4: Message-Level Hooks Missing 🔴 CRITICAL

**Requirement:** Provide `on_before_process`, `on_after_process`, `on_process_error` hooks

#### Implementation Steps

**Step 4.1: Add Hook Methods to Host**

**File:** `Engine/li/hosts/base.py` (MODIFY)

```python
class Host(ABC):
    # ... existing ...

    async def on_before_process(self, message: Any) -> Any:
        """
        Called BEFORE processing each message.

        Override to add:
        - Message validation
        - Pre-processing transformation
        - Audit logging
        - Metric collection

        Args:
            message: Incoming message

        Returns:
            Modified message (or original)
        """
        return message

    async def on_after_process(
        self,
        message: Any,
        result: Any
    ) -> Any:
        """
        Called AFTER processing each message.

        Override to add:
        - Post-processing transformation
        - Audit logging
        - Metric collection
        - Cleanup

        Args:
            message: Original message
            result: Processing result

        Returns:
            Modified result (or original)
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

        Args:
            message: Message that caused error
            exception: The exception raised

        Returns:
            Recovery result or None
        """
        self._log.error(
            "message_processing_error",
            error=str(exception),
            error_type=type(exception).__name__
        )
        return None
```

**Step 4.2: Update Worker Loop to Call Hooks**

**File:** `Engine/li/hosts/base.py` (MODIFY)

```python
async def _worker_loop(self, worker_id: int) -> None:
    """Worker loop with hook support."""
    while not self._shutdown_event.is_set():
        # ... get message ...

        try:
            # PRE-PROCESSING HOOK
            message = await self.on_before_process(message)

            # PROCESS
            result = await self._process_message(message)

            # POST-PROCESSING HOOK
            result = await self.on_after_process(message, result)

            # Send response or route
            # ... existing code ...

        except Exception as e:
            # ERROR HOOK
            recovery_result = await self.on_process_error(message, e)

            if recovery_result and self._on_error:
                await self._on_error(e, message, recovery_result)
```

**Step 4.3: Add Example Implementation**

**File:** `Engine/li/hosts/hl7.py` (MODIFY)

```python
class HL7TCPService(BusinessService):
    """HL7 TCP Service with hooks example."""

    async def on_before_process(self, message: bytes) -> bytes:
        """Validate HL7 message before processing."""
        # Log incoming message
        self._log.debug(
            "hl7_message_received",
            size=len(message)
        )

        # Validate minimum HL7 structure
        if not message.startswith(b'MSH'):
            raise ValueError("Invalid HL7 message: must start with MSH")

        return message

    async def on_after_process(
        self,
        message: bytes,
        result: Any
    ) -> Any:
        """Log successful processing."""
        self._log.info(
            "hl7_message_processed",
            message_type=result.MSH.MessageType if result else "unknown"
        )
        return result

    async def on_process_error(
        self,
        message: bytes,
        exception: Exception
    ) -> Any:
        """Send NACK on error."""
        self._log.error(
            "hl7_processing_error",
            error=str(exception)
        )

        # Generate HL7 NACK
        nack = self._generate_nack(message, str(exception))
        return nack
```

**Effort:** 2 days
**Files Changed:** 2 modified
**Lines of Code:** ~150

---

## Phase 2: Important Enhancements (P1) - 1 Week

### Gap #5: Priority Queue Not Supported 🟡 HIGH

**Implementation:**

**File:** `Engine/core/executors.py` (MODIFY)

```python
from asyncio import Queue, PriorityQueue, LifoQueue
from enum import Enum

class QueueType(str, Enum):
    FIFO = "fifo"
    PRIORITY = "priority"
    LIFO = "lifo"

class ExecutionStrategy(ABC):
    def _create_queue(
        self,
        queue_type: str,
        maxsize: int
    ) -> Queue | PriorityQueue | LifoQueue:
        """Create appropriate queue type."""
        if queue_type == "priority":
            return PriorityQueue(maxsize=maxsize)
        elif queue_type == "lifo":
            return LifoQueue(maxsize=maxsize)
        else:
            return Queue(maxsize=maxsize)
```

**Effort:** 2 days

### Gap #6: Auto-Restart Not Implemented 🟡 MEDIUM

**Implementation:**

**File:** `Engine/li/engine/production.py` (MODIFY)

```python
class ProductionEngine:
    async def _monitor_hosts(self) -> None:
        """Background task to monitor and restart failed hosts."""
        while self._state == ProductionState.RUNNING:
            await asyncio.sleep(5.0)  # Check every 5 seconds

            for name, host in self._all_hosts.items():
                if host.state == HostState.ERROR:
                    restart_policy = host.get_setting("Host", "RestartPolicy", "never")

                    if restart_policy == "always":
                        self._log.warning(
                            "auto_restarting_host",
                            host=name
                        )
                        await host.stop()
                        await asyncio.sleep(1.0)
                        await host.start()
```

**Effort:** 2 days

---

## Implementation Timeline

### Sprint 1: Week 1-2 (Phase 1)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Gap #1.1: Create executors.py | Execution strategies |
| 3-4 | Gap #1.2: Multiprocessing tests | Working multiprocess mode |
| 5 | Gap #2: Thread pool docs | Documentation |
| 6-8 | Gap #3: Service messaging | SendRequestSync/Async |
| 9-10 | Gap #4: Message hooks | Hook system |

**Deliverable:** ✅ All P0 gaps closed

### Sprint 2: Week 3 (Phase 2)

| Day | Task | Deliverable |
|-----|------|-------------|
| 11-12 | Gap #5: Priority queues | Configurable queue types |
| 13-14 | Gap #6: Auto-restart | Automatic host recovery |
| 15 | Integration testing | End-to-end tests |

**Deliverable:** ✅ All P1 gaps closed

### Sprint 3: Week 4-5 (Phase 3)

| Day | Task | Deliverable |
|-----|------|-------------|
| 16-18 | Performance benchmarking | Benchmark report |
| 19-20 | Documentation updates | Complete docs |
| 21 | Final review and sign-off | Production ready |

**Deliverable:** ✅ 100% compliance

---

## Success Criteria

### Phase 1 Complete When:

- [ ] Multiprocessing mode works (pass `test_multiprocess_execution_strategy`)
- [ ] Thread pool mode works (pass `test_threadpool_execution_strategy`)
- [ ] Service-to-service messaging works (pass `test_service_to_service_sync_call`)
- [ ] Message hooks work (pass `test_message_hooks`)
- [ ] All existing tests still pass
- [ ] Performance benchmarks show improvement

### Final Success When:

- [ ] 100% compliance with mandatory requirements (27/27 items)
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Performance targets met (1000+ msg/sec)
- [ ] Approved by technical architecture team

---

**Plan Owner:** HIE Development Team
**Reviewers:** Technical Architect, QA Lead
**Approval Date:** TBD after Phase 1 completion
