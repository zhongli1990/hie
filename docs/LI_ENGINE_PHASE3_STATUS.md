# LI Engine - Phase 3 Implementation Status

**Version:** 0.3.0  
**Release Date:** 2026-01-25  
**Status:** Phase 3 Complete ✅

## Overview

Phase 3 implements enterprise features for production-grade NHS acute hospital deployments:
- Write-Ahead Log (WAL) for crash recovery
- Redis-based message queuing for distributed processing
- Prometheus metrics export for monitoring
- Health checks for Kubernetes deployments
- Graceful shutdown with message draining

## Phase 3 Components

### 3A: Write-Ahead Log (WAL) ✅

**Location:** `hie/li/persistence/wal.py`

Provides crash-recovery durability for message processing. Messages are written to the WAL before processing and removed after successful completion.

**Features:**
- Append-only log file for durability
- Configurable sync modes (fsync, async, none)
- Automatic recovery on restart
- Periodic checkpointing
- Entry TTL and expiration

**Usage:**
```python
from hie.li.persistence import WAL, WALConfig, SyncMode

config = WALConfig(
    directory="./wal",
    sync_mode=SyncMode.ASYNC,
    max_retries=3,
)

wal = WAL(config)
await wal.start()

# Log message before processing
entry = await wal.append(
    host_name="HL7.In.TCP",
    message_id="MSG001",
    payload=raw_bytes,
)

try:
    await process(raw_bytes)
    await wal.complete(entry.id)
except Exception as e:
    should_retry = await wal.fail(entry.id, str(e))

await wal.stop()
```

**WALConfig Options:**
| Option | Default | Description |
|--------|---------|-------------|
| directory | ./wal | WAL file directory |
| max_file_size | 100MB | Max size before rotation |
| sync_mode | ASYNC | FSYNC, ASYNC, or NONE |
| sync_interval | 1.0s | Interval for async sync |
| checkpoint_interval | 60s | Interval for checkpointing |
| max_retries | 3 | Max retries before permanent failure |
| entry_ttl | 3600s | Entry time-to-live |

### 3B: Message Store ✅

**Location:** `hie/li/persistence/store.py`

Provides persistent message storage for audit, replay, and debugging.

**Features:**
- Pluggable storage backends
- File-based backend included
- Query by host, type, state, correlation ID
- Message state tracking

**Usage:**
```python
from hie.li.persistence import MessageStore, MessageQuery, MessageState

store = MessageStore()
await store.start()

# Store a message
record = await store.store(
    host_name="HL7.In.TCP",
    message_id="MSG001",
    payload=raw_bytes,
    message_type="ADT_A01",
    correlation_id="CORR001",
)

# Update state
await store.mark_processing(record.id)
await store.mark_completed(record.id)

# Query messages
failed = await store.get_failed(host_name="HL7.In.TCP")
```

### 3C: Redis Message Queue ✅

**Location:** `hie/li/persistence/queue.py`

Provides distributed message queuing using Redis for horizontal scaling.

**Features:**
- Reliable queue with acknowledgment
- Dead letter queue for failed messages
- Priority queues
- Message visibility timeout
- Automatic retry with backoff

**Usage:**
```python
from hie.li.persistence import MessageQueue, QueueConfig

config = QueueConfig(
    redis_url="redis://localhost:6379",
    visibility_timeout=30.0,
    max_retries=3,
)

queue = MessageQueue(config)
await queue.start()

# Producer
await queue.send("hl7-inbound", payload, priority=1)

# Consumer
msg = await queue.receive("hl7-inbound")
if msg:
    try:
        await process(msg.payload)
        await queue.ack(msg)
    except Exception:
        await queue.nack(msg, requeue=True)

await queue.stop()
```

**QueueConfig Options:**
| Option | Default | Description |
|--------|---------|-------------|
| redis_url | redis://localhost:6379 | Redis connection URL |
| queue_prefix | li:queue | Redis key prefix |
| visibility_timeout | 30s | Time before message returns to queue |
| max_retries | 3 | Max retries before DLQ |
| retry_delay | 5s | Delay between retries |
| dead_letter_enabled | true | Enable dead letter queue |

### 3D: Prometheus Metrics ✅

**Location:** `hie/li/metrics/prometheus.py`

Provides Prometheus-compatible metrics for monitoring.

**Built-in Metrics:**
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| li_messages_received_total | Counter | host, message_type | Total messages received |
| li_messages_sent_total | Counter | host, target | Total messages sent |
| li_messages_failed_total | Counter | host, error_type | Total messages failed |
| li_message_processing_seconds | Histogram | host | Processing latency |
| li_message_size_bytes | Histogram | host, direction | Message size |
| li_connections_active | Gauge | host, adapter | Active connections |
| li_queue_depth | Gauge | host | Current queue depth |
| li_host_status | Gauge | host, type | Host status (1=running) |
| li_wal_pending | Gauge | - | Pending WAL entries |

**Usage:**
```python
from hie.li.metrics import (
    get_metrics_registry,
    record_message_received,
    record_processing_time,
    set_host_status,
)

# Record metrics
record_message_received("HL7.In.TCP", "ADT_A01")
record_processing_time("HL7.In.TCP", 0.025)
set_host_status("HL7.In.TCP", "service", running=True)

# Export for Prometheus
registry = get_metrics_registry()
prometheus_output = registry.export()
```

**HTTP Endpoint:**
```python
# Add to your HTTP server
from hie.li.metrics import metrics_handler

# GET /metrics -> Prometheus text format
```

### 3E: Health Checks ✅

**Location:** `hie/li/health/checks.py`

Provides health check infrastructure for Kubernetes liveness and readiness probes.

**Health Status:**
- `HEALTHY` - Component is functioning normally
- `DEGRADED` - Component has issues but is operational
- `UNHEALTHY` - Component has failed
- `UNKNOWN` - Status cannot be determined

**Usage:**
```python
from hie.li.health import (
    get_health_registry,
    HealthCheck,
    create_host_health_check,
    create_queue_health_check,
)

registry = get_health_registry()

# Register host health check
registry.add_check(
    "hl7-service",
    create_host_health_check(service),
    critical=True,
)

# Register queue health check
registry.add_check(
    "inbound-queue",
    create_queue_health_check(queue, "hl7-inbound", max_depth=10000),
    critical=True,
)

# Check health
result = await registry.check_all()
print(result.status)  # HEALTHY, DEGRADED, or UNHEALTHY

# Kubernetes probes
liveness = await registry.check_liveness()
readiness = await registry.check_readiness()
```

**HTTP Endpoints:**
```python
from hie.li.health.checks import health_handler, liveness_handler, readiness_handler

# GET /health -> Full health status
# GET /health/live -> Liveness probe
# GET /health/ready -> Readiness probe
```

### 3F: Graceful Shutdown ✅

**Location:** `hie/li/health/shutdown.py`

Provides graceful shutdown handling with message draining.

**Features:**
- Signal handling (SIGTERM, SIGINT)
- Configurable shutdown timeout
- Queue draining before shutdown
- Ordered component shutdown
- Custom shutdown handlers

**Usage:**
```python
from hie.li.health import GracefulShutdown, ShutdownConfig

shutdown = GracefulShutdown(ShutdownConfig(
    timeout=30.0,
    drain_timeout=10.0,
))

# Register components
shutdown.register_host(service)
shutdown.register_host(router)
shutdown.register_host(operation)

# Register cleanup handlers
shutdown.register_handler(cleanup_database)
shutdown.register_handler(flush_metrics)

# Install signal handlers
shutdown.install_signal_handlers()

# Wait for shutdown signal
await shutdown.wait()
await shutdown.wait_complete()
```

**Shutdown Phases:**
1. Stop accepting new connections
2. Drain message queues
3. Stop hosts (reverse order)
4. Run custom handlers

## Test Coverage

**Total Tests:** 148 passing ✅

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_iris_xml_loader.py` | 22 | Config loader and models |
| `test_hosts.py` | 20 | Host hierarchy and adapters |
| `test_schemas.py` | 31 | Schema system and HL7 parsing |
| `test_mllp.py` | 17 | MLLP framing and adapters |
| `test_hl7_hosts.py` | 30 | HL7 hosts and routing |
| `test_integration.py` | 10 | End-to-end integration |
| `test_persistence.py` | 18 | WAL, Store, and Metrics |

## File Structure (Phase 3 Additions)

```
hie/li/
├── persistence/
│   ├── __init__.py          # Module exports
│   ├── wal.py               # Write-Ahead Log
│   ├── store.py             # Message Store
│   └── queue.py             # Redis Queue
├── metrics/
│   ├── __init__.py          # Module exports
│   └── prometheus.py        # Prometheus metrics
└── health/
    ├── __init__.py          # Module exports
    ├── checks.py            # Health checks
    └── shutdown.py          # Graceful shutdown

tests/li/
└── test_persistence.py      # Persistence tests
```

## Kubernetes Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: li-engine
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: li-engine
        image: li-engine:0.3.0
        ports:
        - containerPort: 8080
        - containerPort: 9090  # Metrics
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10"]
```

## Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'li-engine'
    static_configs:
      - targets: ['li-engine:9090']
    metrics_path: /metrics
```

## Changelog

### v0.3.0 (2026-01-25)

**Phase 3 Complete - Enterprise Features**

- ✅ Write-Ahead Log (WAL) for crash recovery
- ✅ Message Store with file backend
- ✅ Redis Message Queue with DLQ
- ✅ Prometheus metrics export
- ✅ Health checks (liveness, readiness)
- ✅ Graceful shutdown with message draining
- ✅ 148 passing tests

## Next Phase: Phase 4 - Production Deployment

- Production Engine class orchestrating all components
- Docker service with horizontal scaling
- Load testing for 100s of items
- Performance optimization
- Production documentation
