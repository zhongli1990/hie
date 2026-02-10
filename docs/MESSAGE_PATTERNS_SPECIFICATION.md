# HIE Message Patterns Specification
**End-to-End Messaging Patterns for Enterprise Integration**

**Version:** 1.0.0
**Date:** February 10, 2026
**Status:** 🔴 **MANDATORY** - Core Integration Patterns
**Context:** Docker-first, containerized microservices architecture

---

## Executive Summary

This document defines the **mandatory messaging patterns** that each HIE service item MUST support. These patterns enable flexible, reliable, high-performance message processing across the distributed integration engine.

**Key Requirement:** All patterns MUST be **fully configurable** via production configuration without code changes.

---

## Architecture Context: Docker-First Design

### Container Deployment Model

```
┌─────────────────────────────────────────────────────────────────┐
│ Docker Compose Orchestration                                    │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │ hie-engine    │  │ hie-manager   │  │ hie-portal    │       │
│  │ Container     │  │ Container     │  │ Container     │       │
│  │               │  │               │  │               │       │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │       │
│  │ │HL7Service │ │  │ │   API     │ │  │ │  Next.js  │ │       │
│  │ │ Process 1 │ │  │ │  Server   │ │  │ │    App    │ │       │
│  │ │ Process 2 │ │  │ │           │ │  │ │           │ │       │
│  │ │ Process 3 │ │  │ └───────────┘ │  │ └───────────┘ │       │
│  │ │ Process 4 │ │  │               │  │               │       │
│  │ └───────────┘ │  └───────────────┘  └───────────────┘       │
│  │               │         ↕                    ↕                │
│  │ ┌───────────┐ │  ┌───────────────────────────────────┐      │
│  │ │  Router   │ │  │    PostgreSQL Container           │      │
│  │ │ Process 1 │ │  │    (Message Store, WAL)           │      │
│  │ │ Process 2 │ │  └───────────────────────────────────┘      │
│  │ └───────────┘ │         ↕                                    │
│  │               │  ┌───────────────────────────────────┐      │
│  │ ┌───────────┐ │  │    Redis Container                │      │
│  │ │HTTPSender │ │  │    (Queue, Cache)                 │      │
│  │ │ Process 1 │ │  └───────────────────────────────────┘      │
│  │ └───────────┘ │                                              │
│  └───────────────┘                                              │
│         ↕                                                        │
│  Docker Network Bridge                                          │
└─────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- ✅ Each container runs a **Production instance**
- ✅ Within each container, services can spawn **multiple processes**
- ✅ Multiprocessing is **WITHIN containers**, not across containers
- ✅ Inter-container communication via **Docker networking + Redis/PostgreSQL**
- ✅ Message persistence via **PostgreSQL + Redis** (shared containers)

---

## Mandatory Message Patterns

### Pattern 1: Async Reliable (Non-Blocking Event-Driven) ⭐ PRIMARY

**Description:**
Non-blocking, event-driven message processing with full persistence. Service receives message, processes asynchronously, calls other services via message events, receives responses asynchronously, returns transformed response/ACK to caller without blocking.

**Characteristics:**
- ✅ **Non-blocking**: Caller doesn't wait for processing completion
- ✅ **Event-driven**: All interactions via message events
- ✅ **Fully persistent**: All messages stored in WAL + MessageStore
- ✅ **High throughput**: Handles thousands of concurrent messages
- ✅ **No ordering guarantee**: Messages processed as soon as worker available

**Message Flow:**
```
Client/Service A                Service B (Async)              Service C
      │                              │                              │
      │──(1) Send Request──────────→│                              │
      │←─(2) ACK (immediate)─────────│                              │
      │                              │                              │
      │   [Client continues]         │                              │
      │                              │                              │
      │                              │──(3) Process + Store────→[WAL]
      │                              │                              │
      │                              │──(4) Call Service C────────→│
      │                              │                              │
      │                              │                              │
      │                              │←─(5) Response (async)────────│
      │                              │                              │
      │                              │──(6) Transform──────────→[Store]
      │                              │                              │
      │←─(7) Final Result (callback)─│                              │
      │                              │                              │

Timeline: Client waits ~1ms for ACK, total processing may take seconds
```

**Configuration:**
```yaml
items:
  - id: HL7_Router
    class: HL7RoutingEngine
    messaging_pattern: async_reliable     # ← Pattern selector
    execution_mode: multi_process         # ← Multiple processes
    concurrency: 8                        # ← 8 processes
    queue_type: unordered                 # ← No FIFO guarantee
    queue_size: 10000
    persistence:
      wal_enabled: true                   # ← Write-ahead log
      store_enabled: true                 # ← Message store
      ack_timeout: 5000                   # ← ACK timeout (ms)
```

**Use Cases:**
- ✅ High-volume HL7 message routing
- ✅ Real-time patient data synchronization
- ✅ Event notifications
- ✅ Audit logging

**Implementation Requirements:**
```python
class Host(ABC):
    async def process_async_reliable(self, message: Any) -> str:
        """
        Process message in async reliable mode.

        Returns:
            correlation_id: Immediate ACK with correlation ID
        """
        # 1. Generate correlation ID
        correlation_id = str(uuid4())

        # 2. Persist to WAL immediately
        await self._wal.write(message, correlation_id)

        # 3. Send immediate ACK
        self._send_ack(correlation_id, status="accepted")

        # 4. Enqueue for async processing (non-blocking)
        await self._queue.put({
            "message": message,
            "correlation_id": correlation_id,
            "pattern": "async_reliable"
        })

        # 5. Return correlation ID immediately
        return correlation_id
```

---

### Pattern 2: Sync Reliable (Blocking Request/Reply) ⭐ CRITICAL

**Description:**
Blocking request/reply pattern with FIFO ordering. Service blocks caller until complete processing (including calls to other services) finishes, then returns response. Caller also blocks until response received.

**Characteristics:**
- ✅ **Blocking**: Caller waits for complete processing
- ✅ **FIFO ordering**: Messages processed in strict order
- ✅ **Fully persistent**: All messages + responses stored
- ✅ **Guaranteed response**: Always returns response or timeout
- ✅ **Lower throughput**: Sequential processing per caller

**Message Flow:**
```
Client/Service A                Service B (Sync)               Service C
      │                              │                              │
      │──(1) Send Request──────────→│                              │
      │                              │                              │
      │   [Client BLOCKS]            │──(2) Store Request──────→[WAL]
      │                              │                              │
      │                              │──(3) Call Service C (sync)──→│
      │                              │                              │
      │                              │   [Service B BLOCKS]         │
      │                              │                              │
      │                              │←─(4) Response────────────────│
      │                              │                              │
      │                              │──(5) Transform + Store───→[Store]
      │                              │                              │
      │←─(6) Final Response──────────│                              │
      │                              │                              │
      │   [Client UNBLOCKS]          │                              │
      │                              │                              │
      │──(7) Next Request────────────→│                              │

Timeline: Client waits entire duration (could be seconds)
```

**Configuration:**
```yaml
items:
  - id: PDS_Lookup_Service
    class: PDSLookupService
    messaging_pattern: sync_reliable      # ← Sync blocking pattern
    execution_mode: async                 # ← Still async internally
    concurrency: 4                        # ← 4 workers (parallel)
    queue_type: fifo                      # ← STRICT ordering
    queue_size: 1000
    timeout: 30000                        # ← Request timeout (ms)
    persistence:
      wal_enabled: true
      store_enabled: true
    blocking:
      max_wait_time: 30000                # ← Max blocking time
      deadlock_detection: true            # ← Prevent deadlocks
```

**Use Cases:**
- ✅ PDS (Patient Demographics Service) lookups
- ✅ External API calls requiring immediate response
- ✅ Synchronous database queries
- ✅ Critical validation services

**Implementation Requirements:**
```python
class Host(ABC):
    async def process_sync_reliable(self, message: Any, timeout: float = 30.0) -> Any:
        """
        Process message in sync reliable mode.

        Blocks until processing complete or timeout.

        Returns:
            response: The processed response

        Raises:
            asyncio.TimeoutError: If processing exceeds timeout
        """
        # 1. Persist to WAL
        correlation_id = str(uuid4())
        await self._wal.write(message, correlation_id)

        # 2. Create future for response
        response_future = asyncio.Future()
        self._pending_sync_requests[correlation_id] = response_future

        # 3. Enqueue for processing
        await self._queue.put({
            "message": message,
            "correlation_id": correlation_id,
            "pattern": "sync_reliable",
            "response_future": response_future
        })

        # 4. BLOCK until response or timeout
        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._pending_sync_requests.pop(correlation_id, None)
            raise

    async def _complete_sync_request(self, correlation_id: str, response: Any):
        """Complete a sync request (called by worker after processing)."""
        future = self._pending_sync_requests.pop(correlation_id, None)
        if future and not future.done():
            future.set_result(response)
```

---

### Pattern 3: Concurrent Async (Parallel Non-Blocking) ⭐ HIGH PERFORMANCE

**Description:**
Maximum parallelism without ordering guarantees. Multiple processes/threads process messages concurrently without FIFO blocking. Highest throughput pattern.

**Characteristics:**
- ✅ **Maximum concurrency**: All workers process in parallel
- ✅ **No ordering**: Messages processed in any order
- ✅ **Non-blocking**: Immediate ACK
- ✅ **Persistent**: Full WAL + store
- ✅ **Best throughput**: 10,000+ messages/second

**Configuration:**
```yaml
items:
  - id: HL7_Transformer
    class: HL7TransformService
    messaging_pattern: concurrent_async   # ← Parallel async
    execution_mode: multi_process         # ← Multiple processes
    concurrency: 16                       # ← 16 parallel workers
    queue_type: priority                  # ← Priority-based (not FIFO)
    queue_size: 50000                     # ← Large queue
    persistence:
      wal_enabled: true
      batch_size: 100                     # ← Batch writes for performance
```

**Use Cases:**
- ✅ High-volume message transformation
- ✅ Batch processing
- ✅ Log aggregation
- ✅ Real-time analytics

---

### Pattern 4: Concurrent Sync (Parallel Blocking Workers) ⭐ BALANCED

**Description:**
Multiple concurrent workers handling sync requests in parallel. Each worker blocks on its request, but multiple requests processed simultaneously.

**Characteristics:**
- ✅ **Parallel workers**: Multiple concurrent sync handlers
- ✅ **Per-worker blocking**: Each worker blocks on its request
- ✅ **No global FIFO**: Workers pick next available request
- ✅ **Balanced throughput**: Good throughput + response guarantees

**Message Flow:**
```
Multiple Clients          Service (4 Workers)           External Service
      │                   Worker1  Worker2  Worker3       │
      │                     │       │        │            │
Req1──┼────────────────────→│       │        │            │
Req2──┼────────────────────────────→│        │            │
Req3──┼────────────────────────────────────→│            │
Req4──┼─────────────────────→       │        │            │
      │                     │       │        │            │
      │                  [BLOCK]  [BLOCK]  [BLOCK]       │
      │                     │       │        │            │
      │                     │───────┼────────┼───────────→│
      │                     │       │───────→│            │
      │                     │       │        │←───────────│
      │                     │←──────────────────────────────
      │←────────────────────│       │        │            │
      │                     │       │←───────┼────────────│
      │←────────────────────────────│        │            │

All 4 requests processed in parallel, each worker blocks independently
```

**Configuration:**
```yaml
items:
  - id: External_API_Gateway
    class: RESTAPIGateway
    messaging_pattern: concurrent_sync    # ← Parallel sync
    execution_mode: thread_pool           # ← Threads for blocking I/O
    concurrency: 32                       # ← 32 thread workers
    queue_type: fifo                      # ← Fair ordering
    timeout: 10000                        # ← Per-request timeout
```

**Use Cases:**
- ✅ External REST API calls
- ✅ Database queries
- ✅ File I/O operations
- ✅ Third-party service integration

---

## Pattern Comparison Matrix

| Pattern | Blocking | Ordering | Throughput | Latency | Complexity | Use Case |
|---------|----------|----------|------------|---------|------------|----------|
| **Async Reliable** | No | None | ⭐⭐⭐⭐⭐ | Low | Medium | High-volume HL7 routing |
| **Sync Reliable** | Yes | FIFO | ⭐⭐ | High | Low | PDS lookups, critical queries |
| **Concurrent Async** | No | None | ⭐⭐⭐⭐⭐⭐ | Very Low | High | Batch processing, analytics |
| **Concurrent Sync** | Per-worker | Fair | ⭐⭐⭐⭐ | Medium | Medium | API gateways, file I/O |

---

## Configuration Schema

### Message Pattern Configuration

```python
class MessagingPattern(str, Enum):
    ASYNC_RELIABLE = "async_reliable"
    SYNC_RELIABLE = "sync_reliable"
    CONCURRENT_ASYNC = "concurrent_async"
    CONCURRENT_SYNC = "concurrent_sync"


class QueueType(str, Enum):
    FIFO = "fifo"               # Strict ordering
    PRIORITY = "priority"       # Priority-based
    UNORDERED = "unordered"     # No ordering (fastest)
    LIFO = "lifo"               # Stack-based


class ItemConfig(BaseModel):
    # Messaging configuration
    messaging_pattern: MessagingPattern = Field(
        default=MessagingPattern.ASYNC_RELIABLE,
        description="Message processing pattern"
    )

    queue_type: QueueType = Field(
        default=QueueType.FIFO,
        description="Queue ordering strategy"
    )

    # Blocking configuration
    blocking_enabled: bool = Field(
        default=False,
        description="Enable blocking for sync patterns"
    )

    blocking_timeout: float = Field(
        default=30000,  # milliseconds
        description="Max blocking time for sync requests"
    )

    # Persistence configuration
    persistence_mode: str = Field(
        default="wal_and_store",  # "wal_only", "store_only", "wal_and_store", "none"
        description="Message persistence strategy"
    )

    wal_enabled: bool = Field(default=True)
    store_enabled: bool = Field(default=True)
    batch_writes: bool = Field(default=False)
    batch_size: int = Field(default=100)
```

---

## Implementation Requirements

### Requirement 1: Pattern Selection at Runtime

Services MUST support pattern switching via configuration:

```python
class Host(ABC):
    async def _process_with_pattern(self, message: Any) -> Any:
        """Process message according to configured pattern."""
        pattern = self._config.messaging_pattern

        if pattern == MessagingPattern.ASYNC_RELIABLE:
            return await self._process_async_reliable(message)

        elif pattern == MessagingPattern.SYNC_RELIABLE:
            return await self._process_sync_reliable(message)

        elif pattern == MessagingPattern.CONCURRENT_ASYNC:
            return await self._process_concurrent_async(message)

        elif pattern == MessagingPattern.CONCURRENT_SYNC:
            return await self._process_concurrent_sync(message)
```

### Requirement 2: Queue Type Configuration

Queue selection based on pattern:

```python
def _create_queue(self, queue_type: QueueType, maxsize: int) -> Queue:
    """Create queue based on configuration."""
    if queue_type == QueueType.FIFO:
        return asyncio.Queue(maxsize=maxsize)

    elif queue_type == QueueType.PRIORITY:
        return asyncio.PriorityQueue(maxsize=maxsize)

    elif queue_type == QueueType.LIFO:
        return asyncio.LifoQueue(maxsize=maxsize)

    elif queue_type == QueueType.UNORDERED:
        # Custom unordered queue for maximum throughput
        return UnorderedQueue(maxsize=maxsize)
```

### Requirement 3: Persistence Strategy

All patterns MUST support full persistence:

```python
async def _persist_message(
    self,
    message: Any,
    correlation_id: str,
    direction: str  # "inbound", "outbound", "internal"
) -> None:
    """Persist message to WAL and/or store."""
    if self._config.wal_enabled:
        await self._wal.write(message, correlation_id, direction)

    if self._config.store_enabled:
        await self._store.save(message, correlation_id, direction)
```

---

## Docker Deployment Considerations

### Within-Container Multiprocessing

Each Docker container can spawn multiple processes:

```yaml
# docker-compose.yml
services:
  hie-engine:
    build: .
    environment:
      - EXECUTION_MODE=multi_process
      - CONCURRENCY=8              # 8 processes within container
      - MESSAGING_PATTERN=async_reliable
    deploy:
      resources:
        limits:
          cpus: '4.0'               # Allocate 4 CPUs to container
          memory: 4G
```

### Inter-Container Communication

Services in different containers communicate via:
- **Redis queues** for async messaging
- **HTTP/gRPC** for sync messaging
- **PostgreSQL** for persistence
- **Docker network** for connectivity

---

## Performance Targets

| Pattern | Messages/Second | Latency (p50) | Latency (p99) | CPU Usage |
|---------|-----------------|---------------|---------------|-----------|
| Async Reliable | 5,000+ | <10ms | <50ms | Medium |
| Sync Reliable | 1,000+ | <100ms | <500ms | Low |
| Concurrent Async | 10,000+ | <5ms | <20ms | High |
| Concurrent Sync | 3,000+ | <50ms | <200ms | Medium |

---

## Compliance Checklist

Services MUST implement:
- [ ] All 4 messaging patterns
- [ ] Configurable queue types (FIFO, Priority, Unordered, LIFO)
- [ ] Full message persistence (WAL + Store)
- [ ] Correlation ID tracking
- [ ] Timeout handling
- [ ] Dead letter queue routing
- [ ] Pattern-aware metrics
- [ ] Docker-compatible multiprocessing

---

**Document Owner:** HIE Architecture Team
**Approved By:** TBD
**Next Review:** After implementation
