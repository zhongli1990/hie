# HIE Architecture Overview

## Executive Summary

HIE (Healthcare Integration Engine) is an enterprise-grade integration platform designed for high-throughput, mission-critical healthcare messaging environments such as NHS acute trusts.

## Design Philosophy

### 1. Raw-First, Parse-on-Demand

Unlike traditional integration engines that eagerly parse and normalize messages, HIE:

- **Stores messages in raw form** — The original bytes are preserved end-to-end
- **Parses only when required** — Parsing is triggered explicitly by items that need structured access
- **Treats parsed forms as transient** — Parsed representations are disposable; raw content is authoritative

**Rationale**: This approach provides better performance (no unnecessary parsing), better auditability (original message preserved), and better reliability (no lossy transformations).

### 2. Explicit Over Implicit

Every behavior in HIE is explicitly configured:

- No automatic message transformations
- No implicit routing decisions
- No hidden schema applications
- No magic property bags

**Rationale**: Implicit behavior is the source of most integration bugs. Explicit configuration is auditable, testable, and debuggable.

### 3. Vendor Neutrality

HIE uses clean, domain-appropriate terminology:

| HIE Term | Purpose |
|----------|---------|
| Production | Runtime orchestrator |
| Item | Runtime component (receiver/processor/sender) |
| Route | Message flow path |
| Envelope | Message metadata |
| Payload | Message content |

Legacy engine concepts can be mapped via adapters, not core types.

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      ROUTE MANAGER                          ││
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                 ││
│  │  │ Route 1 │    │ Route 2 │    │ Route N │                 ││
│  │  └─────────┘    └─────────┘    └─────────┘                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      ITEM REGISTRY                          ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   ││
│  │  │ Receiver │  │ Receiver │  │Processor │  │  Sender  │   ││
│  │  │  (HTTP)  │  │  (File)  │  │(Transform│  │  (MLLP)  │   ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    MESSAGE STORE                            ││
│  │         (PostgreSQL / Redis / In-Memory)                    ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Message Model

### Envelope (Header)

The envelope carries operational metadata:

```python
@dataclass
class Envelope:
    message_id: str           # Unique identifier (UUID)
    correlation_id: str       # Links related messages
    causation_id: str         # ID of message that caused this one
    timestamp: datetime       # Creation time (UTC)
    source: str               # Originating item/system
    message_type: str         # Logical type (e.g., "ADT^A01")
    priority: Priority        # Processing priority
    ttl: Optional[int]        # Time-to-live in seconds
    retry_count: int          # Number of delivery attempts
    routing: RoutingInfo      # Target routes/items
    governance: GovernanceInfo # Audit, compliance metadata
```

### Payload (Body)

The payload carries the actual content:

```python
@dataclass
class Payload:
    raw: bytes                # Original message bytes (authoritative)
    content_type: str         # MIME type (e.g., "x-application/hl7-v2")
    encoding: str             # Character encoding (e.g., "utf-8")
    properties: Properties    # Typed, explicit properties
```

### Properties

Properties are **explicitly set, typed values** used for:

- Routing decisions
- Validation
- Enrichment
- Legacy compatibility

Properties are **not** a free-form property bag. Each property must be:
- Explicitly defined in configuration
- Typed (string, int, bool, datetime, etc.)
- Bounded (max size, allowed values)

## Item Model

### Item Categories

1. **Receivers** — Inbound items that accept messages from external systems
   - HTTP receiver (REST endpoints)
   - File receiver (directory watcher)
   - MLLP receiver (HL7 over TCP)

2. **Processors** — Items that transform, validate, route, or enrich messages
   - Transform processor (apply transformations)
   - Validation processor (schema validation)
   - Router processor (content-based routing)
   - Enrichment processor (add data from external sources)

3. **Senders** — Outbound items that deliver messages to external systems
   - MLLP sender (HL7 over TCP)
   - File sender (write to directory)
   - HTTP sender (REST calls)

### Item Lifecycle

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ CREATED │────▶│ STARTING│────▶│ RUNNING │────▶│ STOPPING│
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                     │               │               │
                     ▼               ▼               ▼
                ┌─────────┐     ┌─────────┐     ┌─────────┐
                │  ERROR  │     │  PAUSED │     │ STOPPED │
                └─────────┘     └─────────┘     └─────────┘
```

### Item Execution Modes

Each item can be configured to run as:

| Mode | Description | Use Case |
|------|-------------|----------|
| `single_process` | One process, one thread | Simple, low-volume |
| `multi_process` | Multiple processes | CPU-bound, high isolation |
| `async` | Single process, async I/O | I/O-bound, high concurrency |
| `thread_pool` | Thread pool for blocking I/O | Legacy integrations |

## Route Model

Routes define message flow paths:

```yaml
routes:
  - id: adt_inbound
    path: [http_receiver, adt_validator, adt_transformer, mllp_sender]
    error_handler: error_queue
    
  - id: lab_results
    path: [file_receiver, csv_parser, hl7_builder, mllp_sender]
    filters:
      - type: content_type
        match: "text/csv"
```

### Route Features

- **Linear paths** — Simple A → B → C flows
- **Branching** — Content-based routing to multiple paths
- **Joining** — Multiple sources converging
- **Error handling** — Configurable error routes
- **Filtering** — Route-level message filtering

## Concurrency Model

HIE is designed for high concurrency:

1. **Async-first** — Core runtime uses `asyncio` for non-blocking I/O
2. **Process isolation** — Items can run in separate processes for isolation
3. **Backpressure** — Built-in flow control prevents overwhelming downstream systems
4. **Ordered delivery** — Optional ordering guarantees per-route

## Persistence

### Message Store

Messages are persisted for:
- Reliability (survive restarts)
- Audit (compliance requirements)
- Replay (reprocess failed messages)

Storage backends:
- **PostgreSQL** — Primary durable store
- **Redis** — High-speed queue and cache
- **In-memory** — Development and ultra-low-latency scenarios

### State Management

Item state (offsets, checkpoints) is persisted separately from messages.

## Reliability Guarantees

| Guarantee | Description |
|-----------|-------------|
| At-least-once | Messages are delivered at least once (may duplicate) |
| Ordering | Optional per-route ordering |
| Durability | Messages survive process/node restarts |
| Idempotency | Items should be idempotent (duplicates are safe) |

## Scalability

### Horizontal Scaling

- Multiple Production instances can run concurrently
- Items can be distributed across nodes
- Message store provides coordination

### Vertical Scaling

- Async I/O maximizes single-node throughput
- Process pools for CPU-bound work
- Configurable buffer sizes and batch processing

## Security Considerations

- TLS for all network communication
- Authentication for management API
- Audit logging for all message operations
- Encryption at rest for sensitive payloads
- Role-based access control for configuration

## Monitoring & Observability

- **Metrics** — Prometheus-compatible metrics export
- **Logging** — Structured logging (JSON)
- **Tracing** — OpenTelemetry integration
- **Health checks** — Liveness and readiness probes
