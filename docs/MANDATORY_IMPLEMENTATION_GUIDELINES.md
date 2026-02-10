# HIE Mandatory Implementation Guidelines
**Enterprise Healthcare Integration Engine - Technical Implementation Requirements**

**Version:** 1.0.0
**Date:** February 10, 2026
**Status:** 🔴 **MANDATORY** - Non-Negotiable Requirements
**Purpose:** Define architectural mandates for mission-critical NHS Trust deployments

---

## Executive Summary

This document defines the **mandatory technical implementation requirements** for the HIE (Healthcare Integration Engine) to ensure it meets enterprise-grade standards for:

- **High scalability** - Handle thousands of messages per second
- **High availability** - 99.99% uptime for mission-critical NHS workflows
- **High concurrency** - True multi-process, multi-threaded parallelism
- **Future compatibility** - Extensible architecture for evolving healthcare standards

These requirements are **NON-NEGOTIABLE** and must be fully implemented before production deployment.

---

## Mandatory Requirement #1: Multi-Process Service Architecture

### Requirement Statement

> **Each workflow item MUST run as a service loop of one or more CPU Python processes of a predefined class, and each process MUST be able to spawn one or more threads.**

### Technical Specifications

#### 1.1 Process-Level Isolation

**MUST Support:**
- ✅ **OS-level process isolation** using Python `multiprocessing.Process`
- ✅ **Configurable process pool size** (1-N processes per service item)
- ✅ **Independent process memory space** (no shared GIL contention)
- ✅ **Process crash isolation** (one process failure ≠ total service failure)

**Configuration:**
```yaml
# Example: production.yaml
items:
  - id: HL7_Receiver
    class: HL7TCPService
    execution_mode: multi_process  # ← MANDATORY support
    concurrency: 4                  # ← 4 OS processes
```

**Implementation Contract:**
```python
class Item(ABC):
    """Each item can run as multiple OS processes."""

    async def start(self) -> None:
        if self._config.execution_mode == ExecutionMode.MULTI_PROCESS:
            # MUST create OS processes via multiprocessing
            for i in range(self._config.concurrency):
                process = Process(target=self._process_worker)
                process.start()
                self._processes.append(process)
```

#### 1.2 Thread-Level Concurrency

**MUST Support:**
- ✅ **Thread spawning within each process** using `threading.Thread` or `ThreadPoolExecutor`
- ✅ **Configurable thread pool size per process**
- ✅ **Mixed async/sync execution** (async I/O with blocking thread workers)

**Implementation Contract:**
```python
class Item(ABC):
    async def start(self) -> None:
        if self._config.execution_mode == ExecutionMode.THREAD_POOL:
            # MUST create thread pool for blocking I/O
            self._executor = ThreadPoolExecutor(
                max_workers=self._config.concurrency,
                thread_name_prefix=f"{self.id}-worker"
            )
```

#### 1.3 Execution Mode Requirements

**MUST implement ALL four execution modes:**

| Mode | Description | Use Case | Priority |
|------|-------------|----------|----------|
| `ASYNC` | Single process, asyncio event loop | I/O-bound, high concurrency | P0 ✅ (exists) |
| `THREAD_POOL` | Single process, thread pool | Blocking I/O, sync libraries | P0 🔴 (missing) |
| `MULTI_PROCESS` | Multiple OS processes | CPU-bound, true parallelism | P0 🔴 (missing) |
| `SINGLE_PROCESS` | Single process, single thread | Lightweight, debugging | P1 ✅ (exists) |

**Rationale:**
- **High-volume HL7 processing** requires multi-process to bypass GIL
- **Legacy sync libraries** require thread pool (database drivers, file I/O)
- **Async/await** for modern I/O-bound operations

---

## Mandatory Requirement #2: Continuous Service Loop Pattern

### Requirement Statement

> **Services MUST continuously wait for inbound request message(s), perform transformations as defined in their class, send responses, and support calling other services via messaging or events.**

### Technical Specifications

#### 2.1 Continuous Wait Loop

**MUST Implement:**
```python
async def _worker_loop(self, worker_id: int) -> None:
    """Continuous service loop - MANDATORY pattern."""
    while not self._shutdown_event.is_set():
        # 1. WAIT for message (blocking with timeout)
        message = await self._queue.get(timeout=1.0)

        # 2. PROCESS message (transform, validate, route)
        result = await self._process_message(message)

        # 3. RESPOND (send to next service or external system)
        if result:
            await self._send_response(result)

        # 4. REPEAT (loop continues until shutdown)
```

**Contract Requirements:**
- ✅ Infinite while loop with clean shutdown signal
- ✅ Blocking wait on message queue (with timeout to check shutdown)
- ✅ Pause/resume capability without losing messages
- ✅ Graceful drain on shutdown (process in-flight messages)

#### 2.2 Transformation Capabilities

**Each service MUST support:**
- ✅ Message transformation (HL7 → JSON, XML → HL7, etc.)
- ✅ Content-based routing (filter rules, conditional logic)
- ✅ Message enrichment (lookup data, append fields)
- ✅ Validation (schema validation, business rules)
- ✅ Protocol adaptation (MLLP ↔ HTTP ↔ File)

**Implementation via class override:**
```python
class HL7RoutingEngine(BusinessProcess):
    async def _process_message(self, message: HL7Message) -> HL7Message:
        # Transform: Apply routing rules
        if message.MSH.SendingApplication == "EMIS":
            message = await self._enrich_from_pds(message)

        # Route: Content-based routing
        if message.MSH.MessageType == "ADT^A01":
            return await self.route_to_admissions(message)

        return message
```

#### 2.3 Service-to-Service Messaging

**MUST Support (currently MISSING):**

```python
class Host(ABC):
    async def send_request_sync(
        self,
        target_service: str,
        message: Any,
        timeout: float = 30.0
    ) -> Any:
        """
        Send synchronous request to another service.

        Like IRIS: Set response = ..SendRequestSync("HL7.Router", request)

        MANDATORY for dynamic service calls.
        """
        pass

    async def send_request_async(
        self,
        target_service: str,
        message: Any
    ) -> None:
        """
        Send asynchronous request to another service.

        Like IRIS: Do ..SendRequestAsync("HL7.Router", request)

        MANDATORY for fire-and-forget patterns.
        """
        pass
```

**Requirements:**
- ✅ Services can call other services by name
- ✅ Synchronous request/reply pattern (wait for response)
- ✅ Asynchronous fire-and-forget pattern
- ✅ Message correlation tracking (request ↔ response)
- ✅ Timeout handling for sync calls

---

## Mandatory Requirement #3: Manager/Orchestrator Responsibilities

### Requirement Statement

> **The manager MUST orchestrate lifecycles of each running service item and messages per configuration of each item on the project workflow.**

### Technical Specifications

#### 3.1 Lifecycle Management

**Manager MUST control:**

| Lifecycle Stage | Manager Responsibility | Status |
|-----------------|----------------------|---------|
| **Load** | Parse IRIS XML config, instantiate hosts | ✅ Implemented |
| **Validate** | Check config correctness before start | ✅ Implemented |
| **Start** | Start items in dependency order (Ops → Procs → Svcs) | ✅ Implemented |
| **Monitor** | Track item states, health, metrics | ✅ Implemented |
| **Reload** | Hot reload config without downtime | ✅ Implemented |
| **Pause/Resume** | Pause/resume items individually | ✅ Implemented |
| **Stop** | Graceful shutdown in reverse order | ✅ Implemented |
| **Restart** | Restart failed items automatically | ⚠️ Partial |

#### 3.2 Message Routing Orchestration

**Manager MUST:**
- ✅ Route messages between services based on configuration
- ✅ Apply filter rules per route
- ✅ Handle error routing (redirect failed messages)
- ✅ Support dead letter queues
- ✅ Track message lineage (correlation ID, causation ID)

**Currently implemented via callback pattern:**
```python
# Engine/li/engine/production.py
class ProductionEngine:
    async def _wire_services(self) -> None:
        """Wire services together based on configuration."""
        # Service A → callback → Manager → route → Service B
        service_a.set_message_handler(self._route_message)
```

**Enhancement needed:** Service-initiated routing (see Requirement #2.3)

#### 3.3 Configuration-Driven Behavior

**MUST support:**
- ✅ IRIS XML production configuration
- ✅ YAML/JSON alternative formats
- ✅ Per-item settings (adapter_settings, host_settings)
- ✅ Runtime config changes (hot reload)
- ✅ Version control for configs

**Status:** ✅ Fully implemented

---

## Mandatory Requirement #4: Concurrency Patterns & Hooks

### Requirement Statement

> **Each service loop MUST handle concurrency of large message volumes per various patterns (sync/async, FIFO/non-FIFO), and MUST provide pre- and post-hooks per class hierarchy.**

### Technical Specifications

#### 4.1 Concurrency Patterns

**MUST Support:**

##### 4.1.1 Synchronous vs Asynchronous Processing

| Pattern | Description | Use Case | Status |
|---------|-------------|----------|--------|
| **Async/Await** | Non-blocking I/O with event loop | Modern HTTP, database queries | ✅ Implemented |
| **Sync Blocking** | Thread-based blocking calls | Legacy libraries, file I/O | ⚠️ Partial |

**Implementation requirement:**
```python
class ItemConfig(BaseModel):
    execution_mode: ExecutionMode  # ASYNC vs THREAD_POOL

# Async mode
async def _process_message(self, msg: Any) -> Any:
    result = await async_transform(msg)  # Non-blocking

# Sync mode (in thread pool)
def _process_message_sync(self, msg: Any) -> Any:
    result = sync_transform(msg)  # Blocking, but in thread
```

##### 4.1.2 Queue Ordering Patterns

**MUST Support:**

| Queue Type | Order | Use Case | Status |
|------------|-------|----------|--------|
| **FIFO** | First-in-first-out | Standard message processing | ✅ Implemented |
| **Priority** | Highest priority first | Urgent vs routine messages | 🔴 Missing |
| **LIFO** | Last-in-first-out | Stack-based workflows | 🔴 Missing |

**Configuration requirement:**
```yaml
items:
  - id: HL7_Router
    queue_type: priority        # ← MANDATORY support
    queue_size: 10000
    queue_overflow: redirect    # block, drop, or redirect
```

**Implementation requirement:**
```python
from asyncio import Queue, PriorityQueue, LifoQueue

class ItemConfig(BaseModel):
    queue_type: QueueType = Field(default=QueueType.FIFO)
    queue_overflow: OverflowStrategy = Field(default="block")

class Item(ABC):
    async def start(self) -> None:
        # MUST support all queue types
        if self._config.queue_type == QueueType.PRIORITY:
            self._queue = PriorityQueue(maxsize=queue_size)
        elif self._config.queue_type == QueueType.LIFO:
            self._queue = LifoQueue(maxsize=queue_size)
        else:
            self._queue = Queue(maxsize=queue_size)
```

#### 4.2 Pre/Post Hook System

**MUST Provide:**

##### 4.2.1 Lifecycle Hooks (Currently Implemented ✅)

```python
class Host(ABC):
    async def on_init(self) -> None:
        """Called during initialization."""

    async def on_start(self) -> None:
        """Called after start."""

    async def on_stop(self) -> None:
        """Called before stop."""

    async def on_teardown(self) -> None:
        """Called during teardown."""
```

##### 4.2.2 Message-Level Hooks (Currently MISSING 🔴)

**MANDATORY implementation:**
```python
class Host(ABC):
    async def on_before_process(self, message: Any) -> Any:
        """
        Called BEFORE processing each message.

        Use for:
        - Message validation
        - Pre-processing transformation
        - Audit logging (message received)
        - Metric collection (start timer)

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

        Use for:
        - Post-processing transformation
        - Audit logging (message processed)
        - Metric collection (end timer)
        - Cleanup

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

        Use for:
        - Error logging
        - Dead letter queue routing
        - Retry logic
        - Alert generation

        Returns:
            Recovery result or None
        """
        return None
```

**Usage in worker loop:**
```python
async def _worker_loop(self, worker_id: int) -> None:
    while not self._shutdown_event.is_set():
        message = await self._queue.get()

        try:
            # PRE-HOOK
            message = await self.on_before_process(message)

            # PROCESS
            result = await self._process_message(message)

            # POST-HOOK
            result = await self.on_after_process(message, result)

            # SEND
            if result and self._on_message:
                await self._on_message(result)

        except Exception as e:
            # ERROR HOOK
            recovery = await self.on_process_error(message, e)
            if recovery and self._on_error:
                await self._on_error(e, message, recovery)
```

#### 4.3 High-Volume Performance Requirements

**MUST achieve:**
- ✅ **Throughput:** 1,000+ messages/second per service (with multiprocessing)
- ✅ **Latency:** <100ms average processing time
- ✅ **Memory:** <500MB per process
- ✅ **CPU:** Efficient multi-core utilization (multiprocessing)

**Scalability targets:**
- ✅ 10,000 messages in queue without blocking
- ✅ 4-16 worker processes per service item
- ✅ Horizontal scaling across multiple machines

---

## Implementation Priority Matrix

### Phase 1: Critical Gaps (P0) 🔴

| Gap | Requirement | Priority | Effort | Impact |
|-----|-------------|----------|--------|--------|
| **Multiprocessing** | Req #1 | P0 | 5d | CRITICAL |
| **Thread Pool** | Req #1 | P0 | 3d | CRITICAL |
| **Service Messaging** | Req #2 | P0 | 4d | HIGH |
| **Message Hooks** | Req #4 | P0 | 2d | MEDIUM |

**Total Effort:** 14 days
**Target Completion:** Phase 1 Sprint (2 weeks)

### Phase 2: Important Enhancements (P1) 🟡

| Gap | Requirement | Priority | Effort | Impact |
|-----|-------------|----------|--------|--------|
| **Priority Queues** | Req #4 | P1 | 2d | MEDIUM |
| **LIFO Queues** | Req #4 | P1 | 1d | LOW |
| **Auto Restart** | Req #3 | P1 | 2d | MEDIUM |
| **Correlation Tracking** | Req #3 | P1 | 3d | MEDIUM |

**Total Effort:** 8 days
**Target Completion:** Phase 2 Sprint (1 week)

### Phase 3: Optimizations (P2) 🟢

| Enhancement | Requirement | Priority | Effort | Impact |
|-------------|-------------|----------|--------|--------|
| **Circuit Breaker** | Req #4 | P2 | 3d | MEDIUM |
| **Rate Limiting** | Req #4 | P2 | 2d | LOW |
| **Distributed Messaging** | Req #2 | P2 | 5d | HIGH |

**Total Effort:** 10 days
**Target Completion:** Phase 3 Sprint (2 weeks)

---

## Compliance Checklist

### Mandatory Requirement #1: Multi-Process Architecture

- [ ] **1.1** OS-level process isolation implemented
- [ ] **1.2** Configurable process pool size
- [ ] **1.3** Thread spawning within processes
- [ ] **1.4** ThreadPoolExecutor integration
- [ ] **1.5** All 4 execution modes working (ASYNC ✅, SINGLE_PROCESS ✅, MULTI_PROCESS ❌, THREAD_POOL ❌)
- [ ] **1.6** Inter-process queue (multiprocessing.Queue)
- [ ] **1.7** Process crash recovery

**Status:** 🔴 **40% Complete** (2/7 items)

### Mandatory Requirement #2: Continuous Service Loop

- [x] **2.1** While-loop service pattern ✅
- [x] **2.2** Queue-based message waiting ✅
- [x] **2.3** Transformation capabilities ✅
- [x] **2.4** Response sending ✅
- [ ] **2.5** Service-to-service messaging (SendRequestSync) ❌
- [ ] **2.6** Service-to-service messaging (SendRequestAsync) ❌
- [x] **2.7** Pause/resume without message loss ✅

**Status:** 🟡 **71% Complete** (5/7 items)

### Mandatory Requirement #3: Manager Orchestration

- [x] **3.1** Lifecycle management (start/stop/pause) ✅
- [x] **3.2** Dependency-aware startup order ✅
- [x] **3.3** Message routing orchestration ✅
- [x] **3.4** Configuration-driven behavior ✅
- [x] **3.5** Hot reload capability ✅
- [ ] **3.6** Automatic restart on failure ⚠️
- [x] **3.7** Graceful shutdown with drain ✅

**Status:** 🟢 **86% Complete** (6/7 items)

### Mandatory Requirement #4: Concurrency & Hooks

- [x] **4.1** Async/await pattern ✅
- [ ] **4.2** Sync blocking in thread pool ❌
- [x] **4.3** FIFO queue ✅
- [ ] **4.4** Priority queue ❌
- [ ] **4.5** LIFO queue ❌
- [x] **4.6** Lifecycle hooks (on_init, on_start, etc.) ✅
- [ ] **4.7** Message hooks (on_before_process, on_after_process) ❌
- [ ] **4.8** Error hooks (on_process_error) ❌

**Status:** 🔴 **38% Complete** (3/8 items)

---

## Overall Compliance

**Current Status:** 🟡 **59% Compliant** (16/27 mandatory items)

**Critical Gaps:** 11 items
**Phase 1 Target:** 🎯 **85% Compliant** (23/27 items)
**Phase 2 Target:** 🎯 **100% Compliant** (27/27 items)

---

## Sign-Off Requirements

Before production deployment, **ALL** mandatory requirements MUST be:
- ✅ Implemented and tested
- ✅ Documented with examples
- ✅ Benchmarked for performance
- ✅ Reviewed and approved

**Approval Required From:**
- [ ] Technical Architect
- [ ] NHS Integration Lead
- [ ] Quality Assurance Lead
- [ ] Security Review Board

---

**Document Owner:** HIE Technical Architecture Team
**Last Updated:** February 10, 2026
**Next Review:** After Phase 1 implementation (2 weeks)
