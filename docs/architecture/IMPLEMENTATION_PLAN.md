# LI Engine Implementation Plan

**Document Version:** 1.0  
**Created:** 2026-01-24  
**Status:** APPROVED - Ready for Implementation

---

## Executive Summary

This document outlines the phased implementation plan for the **LI (Lightweight Integration) Engine** - an enterprise-grade, IRIS-compatible workflow orchestrator for NHS hospital trust integration. The engine will be deployed as a Docker service capable of running hundreds of configuration items dynamically.

---

## Current Codebase Analysis

### Existing Foundation (HIE)

| Component | Location | Status | Reusability |
|-----------|----------|--------|-------------|
| **Item base class** | `hie/core/item.py` | ✅ Good | Extend to Host hierarchy |
| **Message model** | `hie/core/message.py` | ✅ Good | Already raw-first, enhance |
| **Production orchestrator** | `hie/core/production.py` | ✅ Good | Extend for dynamic management |
| **Route model** | `hie/core/route.py` | ✅ Good | Enhance for IRIS routing |
| **Config system** | `hie/core/config.py` | ⚠️ Partial | Add IRIS XML loader |
| **Schema definitions** | `hie/core/schema.py` | ⚠️ Partial | Add HL7 schema support |
| **Config loader** | `hie/core/config_loader.py` | ⚠️ Partial | Add IRIS XML parser |
| **Factory** | `hie/factory.py` | ✅ Good | Extend ClassRegistry |
| **HL7 parser** | `hie/parsers/hl7v2.py` | ✅ Good | Integrate with schema system |
| **Persistence** | `hie/persistence/` | ✅ Good | PostgreSQL + Redis ready |
| **HTTP Receiver** | `hie/items/receivers/` | ✅ Good | Add MLLP receiver |
| **MLLP Sender** | `hie/items/senders/` | ✅ Good | Enhance with ACK handling |
| **Docker setup** | `Dockerfile`, `docker-compose.yml` | ✅ Good | Enhance for scalability |

### Key Gaps to Fill

1. **IRIS XML Configuration Loader** - Parse production XML like `TEST.cls`
2. **Host Hierarchy** - BusinessService, BusinessProcess, BusinessOperation
3. **Schema System** - Lazy parsing with HL7 schema files (PKB.HL7)
4. **MLLP Inbound Adapter** - TCP listener with MLLP framing
5. **HL7 Routing Engine** - Rule-based message routing
6. **ReplyCodeActions** - IRIS-style error handling
7. **Hot Reload** - Dynamic item management without restart

---

## Implementation Phases

### Phase 1: Core Foundation (Week 1-2)

#### 1A: LI Branding & IRIS XML Config Loader

**Goal:** Load IRIS production XML and create runtime objects

**Files to Create/Modify:**

```
hie/
├── li/                              # NEW: LI Engine namespace
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── iris_xml_loader.py       # Parse IRIS production XML
│   │   ├── production_config.py     # ProductionConfig model
│   │   └── item_config.py           # ItemConfig with Host/Adapter settings
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── class_registry.py        # Dynamic class lookup
│   │   └── schema_registry.py       # Schema lookup
│   └── engine/
│       ├── __init__.py
│       └── production_engine.py     # Main engine orchestrator
```

**Key Implementation:**

```python
# li/config/iris_xml_loader.py
class IRISXMLLoader:
    """
    Loads IRIS Production XML configuration.
    
    Example input:
    <Production Name="BHRUH.Production.ADTProduction">
      <Item Name="from.BHR.ADT1" ClassName="EnsLib.HL7.Service.TCPService">
        <Setting Target="Adapter" Name="Port">35001</Setting>
        <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>
      </Item>
    </Production>
    """
    
    def load(self, xml_path: str) -> ProductionConfig:
        """Load production from XML file."""
        ...
    
    def load_from_string(self, xml_string: str) -> ProductionConfig:
        """Load production from XML string."""
        ...
```

**Deliverables:**
- [ ] `IRISXMLLoader` class that parses production XML
- [ ] `ProductionConfig` model matching IRIS structure
- [ ] `ItemConfig` with `adapter_settings` and `host_settings` separation
- [ ] Unit tests with actual BHRUH production XML

---

#### 1B: Host Hierarchy

**Goal:** Create IRIS-compatible Host classes

**Files to Create:**

```
hie/li/hosts/
├── __init__.py
├── base.py                          # Host, BusinessService, BusinessProcess, BusinessOperation
├── adapters/
│   ├── __init__.py
│   ├── base.py                      # InboundAdapter, OutboundAdapter
│   ├── tcp_adapter.py               # TCPInboundAdapter, TCPOutboundAdapter
│   └── mllp_adapter.py              # MLLP framing layer
└── settings.py                      # Common host settings (PoolSize, Enabled, etc.)
```

**Key Implementation:**

```python
# li/hosts/base.py
class Host(ABC):
    """Base class for all business hosts."""
    
    name: str
    pool_size: int
    enabled: bool
    adapter_settings: dict[str, Any]
    host_settings: dict[str, Any]
    
    # Lifecycle
    async def on_init(self) -> None: ...
    async def on_start(self) -> None: ...
    async def on_stop(self) -> None: ...
    async def on_teardown(self) -> None: ...
    
    # Extension points
    def get_setting(self, target: str, name: str, default: Any = None) -> Any: ...


class BusinessService(Host):
    """Inbound host - receives messages from external systems."""
    _adapter: InboundAdapter
    target_config_names: list[str]
    
    async def on_message_received(self, raw: bytes) -> Message: ...
    async def send_to_targets(self, message: Message) -> None: ...


class BusinessProcess(Host):
    """Processing host - transforms, routes, or enriches messages."""
    
    async def on_message(self, message: Message) -> Message | list[Message] | None: ...


class BusinessOperation(Host):
    """Outbound host - sends messages to external systems."""
    _adapter: OutboundAdapter
    
    async def on_message(self, message: Message) -> Message | None: ...
```

**Deliverables:**
- [ ] `Host` base class with lifecycle and settings
- [ ] `BusinessService`, `BusinessProcess`, `BusinessOperation`
- [ ] `InboundAdapter`, `OutboundAdapter` base classes
- [ ] Settings management (Target="Host" vs Target="Adapter")

---

#### 1C: Schema System with Lazy Parsing

**Goal:** Load HL7 schemas and parse on-demand

**Files to Create:**

```
hie/li/schemas/
├── __init__.py
├── base.py                          # Schema, ParsedView base classes
├── registry.py                      # SchemaRegistry
├── loader.py                        # SchemaLoader (XML schema files)
└── hl7/
    ├── __init__.py
    ├── schema.py                    # HL7Schema
    ├── parsed_view.py               # HL7ParsedView
    └── definitions.py               # MessageType, Segment, Field definitions
```

**Key Implementation:**

```python
# li/schemas/base.py
class Schema(ABC):
    """Base class for message schemas."""
    name: str
    version: str
    base_schema: str | None  # Inheritance
    
    @abstractmethod
    def parse(self, raw: bytes) -> ParsedView: ...
    
    @abstractmethod
    def validate(self, raw: bytes) -> list[ValidationError]: ...


class ParsedView(ABC):
    """Lazy parsed view of a message."""
    _raw: bytes
    _schema: Schema
    _cache: dict[str, Any]  # Cached parsed values
    
    @abstractmethod
    def get_field(self, path: str) -> Any: ...
    
    @abstractmethod
    def set_field(self, path: str, value: Any) -> bytes: ...


# li/schemas/registry.py
class SchemaRegistry:
    """Global registry for schemas."""
    _schemas: dict[str, Schema] = {}
    
    @classmethod
    def register(cls, schema: Schema) -> None: ...
    
    @classmethod
    def get(cls, name: str) -> Schema | None: ...
    
    @classmethod
    def load_from_directory(cls, path: str) -> int: ...
```

**Deliverables:**
- [ ] `Schema` and `ParsedView` base classes
- [ ] `HL7Schema` that loads from XML (like PKB.HL7)
- [ ] `HL7ParsedView` with field access (e.g., `get_field("PID-3.1")`)
- [ ] `SchemaRegistry` for global schema lookup
- [ ] `SchemaLoader` for loading schema XML files

---

### Phase 2: HL7 Stack (Week 3-4)

#### 2A: MLLP Adapters

**Files to Create:**

```
hie/li/adapters/
├── mllp/
│   ├── __init__.py
│   ├── inbound.py                   # MLLPInboundAdapter (TCP listener)
│   ├── outbound.py                  # MLLPOutboundAdapter (TCP client)
│   ├── framing.py                   # MLLP frame/unframe
│   └── connection_pool.py           # Connection pooling
```

**Key Implementation:**

```python
# li/adapters/mllp/inbound.py
class MLLPInboundAdapter(InboundAdapter):
    """
    MLLP TCP listener adapter.
    
    Settings:
    - Port: TCP port to listen on
    - SSLConfig: TLS configuration name
    - CallInterval: Polling interval
    """
    
    async def start(self) -> None:
        """Start TCP server."""
        self._server = await asyncio.start_server(
            self._handle_connection,
            host=self.settings.get("Host", "0.0.0.0"),
            port=self.settings["Port"],
        )
    
    async def _handle_connection(self, reader, writer) -> None:
        """Handle incoming MLLP connection."""
        while True:
            raw = await self._read_mllp_frame(reader)
            if not raw:
                break
            await self._host.on_message_received(raw)
```

**Deliverables:**
- [ ] `MLLPInboundAdapter` - TCP server with MLLP framing
- [ ] `MLLPOutboundAdapter` - TCP client with connection pooling
- [ ] MLLP frame/unframe utilities
- [ ] TLS support via SSLConfig

---

#### 2B: HL7 Business Hosts

**Files to Create:**

```
hie/li/hosts/hl7/
├── __init__.py
├── tcp_service.py                   # HL7TCPService (EnsLib.HL7.Service.TCPService)
├── tcp_operation.py                 # HL7TCPOperation (EnsLib.HL7.Operation.TCPOperation)
├── routing_engine.py                # HL7RoutingEngine (EnsLib.HL7.MsgRouter.RoutingEngine)
├── file_service.py                  # HL7FileService
└── ack.py                           # ACK generation utilities
```

**Key Implementation:**

```python
# li/hosts/hl7/tcp_service.py
class HL7TCPService(BusinessService):
    """
    HL7 TCP/MLLP inbound service.
    
    Equivalent to: EnsLib.HL7.Service.TCPService
    
    Host Settings:
    - MessageSchemaCategory: Schema for parsing/ACK generation
    - TargetConfigNames: Comma-separated list of targets
    - AckMode: App, Immediate, None
    """
    
    adapter_class = MLLPInboundAdapter
    
    def on_init(self):
        schema_name = self.get_setting("Host", "MessageSchemaCategory", "2.4")
        self._schema = SchemaRegistry.get(schema_name)
    
    async def on_message_received(self, raw: bytes) -> Message:
        message = Message(raw=raw, content_type="application/hl7-v2", source=self.name)
        await self.send_to_targets(message)
        return message
    
    def generate_ack(self, message: Message, code: str) -> bytes:
        parsed = self._schema.parse(message.raw)
        return self._schema.create_ack(parsed, code)


# li/hosts/hl7/routing_engine.py
class HL7RoutingEngine(BusinessProcess):
    """
    HL7 message router with business rules.
    
    Equivalent to: EnsLib.HL7.MsgRouter.RoutingEngine
    
    Host Settings:
    - BusinessRuleName: Name of rule set to use
    - ValidationSchema: Schema for validation
    """
    
    def on_init(self):
        rule_name = self.get_setting("Host", "BusinessRuleName")
        self._rules = RuleLoader.load(rule_name)
        
        schema_name = self.get_setting("Host", "ValidationSchema", "2.4")
        self._schema = SchemaRegistry.get(schema_name)
    
    async def on_message(self, message: Message) -> list[Message]:
        parsed = self._schema.parse(message.raw)
        
        results = []
        for rule in self._rules:
            if rule.evaluate(parsed):
                targets = rule.get_targets()
                for target in targets:
                    results.append((target, message))
        
        return results
```

**Deliverables:**
- [ ] `HL7TCPService` - MLLP inbound with ACK generation
- [ ] `HL7TCPOperation` - MLLP outbound with ReplyCodeActions
- [ ] `HL7RoutingEngine` - Rule-based routing
- [ ] ACK generation utilities
- [ ] Class registration in ClassRegistry

---

#### 2C: Business Rules Engine

**Files to Create:**

```
hie/li/rules/
├── __init__.py
├── base.py                          # Rule, RuleSet, Condition, Action
├── loader.py                        # Load rules from config/files
├── conditions/
│   ├── __init__.py
│   ├── field.py                     # Field-based conditions
│   ├── message_type.py              # Message type conditions
│   └── custom.py                    # Custom condition support
└── actions/
    ├── __init__.py
    ├── send.py                      # Send to target
    ├── transform.py                 # Apply transform
    └── delete.py                    # Delete/filter message
```

**Deliverables:**
- [ ] `Rule`, `RuleSet`, `Condition`, `Action` base classes
- [ ] Field-based conditions (equals, contains, matches)
- [ ] Send action with target resolution
- [ ] Rule loader from configuration

---

### Phase 3: Enterprise Features (Week 5-6)

#### 3A: Message Persistence (WAL + Queue)

**Files to Modify/Create:**

```
hie/li/persistence/
├── __init__.py
├── wal.py                           # Write-Ahead Log
├── queue.py                         # Message queue abstraction
├── redis_queue.py                   # Redis-backed queue
└── archive.py                       # ArchiveIO implementation
```

**Key Implementation:**

```python
# li/persistence/wal.py
class WriteAheadLog:
    """
    Write-ahead log for message durability.
    
    Every message is written to WAL before processing.
    On crash recovery, uncommitted messages are replayed.
    """
    
    async def append(self, message: Message, host_name: str) -> int:
        """Append message to WAL, return sequence number."""
        ...
    
    async def commit(self, sequence: int) -> None:
        """Mark message as successfully processed."""
        ...
    
    async def recover(self) -> AsyncIterator[tuple[int, Message, str]]:
        """Yield uncommitted messages for replay."""
        ...


# li/persistence/queue.py
class MessageQueue(ABC):
    """Abstract message queue."""
    
    @abstractmethod
    async def enqueue(self, message: Message, priority: int = 0) -> None: ...
    
    @abstractmethod
    async def dequeue(self, timeout: float = None) -> Message | None: ...
    
    @abstractmethod
    async def ack(self, message_id: UUID) -> None: ...
    
    @abstractmethod
    async def nack(self, message_id: UUID, requeue: bool = True) -> None: ...
```

**Deliverables:**
- [ ] `WriteAheadLog` for message durability
- [ ] `MessageQueue` abstraction
- [ ] `RedisQueue` implementation
- [ ] `ArchiveIO` for message archival
- [ ] Crash recovery mechanism

---

#### 3B: Error Handling (ReplyCodeActions)

**Files to Create:**

```
hie/li/errors/
├── __init__.py
├── reply_code_actions.py            # Parse and execute ReplyCodeActions
├── retry.py                         # Retry policy
└── dead_letter.py                   # Dead letter queue
```

**Key Implementation:**

```python
# li/errors/reply_code_actions.py
class ReplyCodeActions:
    """
    IRIS-style reply code action parser.
    
    Format: ":?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C"
    
    Actions:
    - F = Fail (move to error queue, alert)
    - S = Suspend (retry with backoff)
    - C = Complete (success)
    - W = Warning (log, continue)
    - D = Disable (disable the host)
    """
    
    def __init__(self, actions_string: str):
        self._rules = self._parse(actions_string)
    
    def get_action(self, ack_code: str) -> Action:
        """Get action for ACK code (AA, AE, AR, etc.)."""
        ...
```

**Deliverables:**
- [ ] `ReplyCodeActions` parser
- [ ] `RetryPolicy` with exponential backoff
- [ ] `DeadLetterQueue` for failed messages
- [ ] Alert integration

---

#### 3C: Observability

**Files to Create:**

```
hie/li/monitoring/
├── __init__.py
├── metrics.py                       # Prometheus metrics
├── logging.py                       # Structured logging setup
├── health.py                        # Health check endpoints
└── tracing.py                       # OpenTelemetry integration
```

**Key Metrics:**

```python
# li/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

messages_received = Counter(
    "li_messages_received_total",
    "Total messages received",
    ["host", "status"]
)

messages_sent = Counter(
    "li_messages_sent_total", 
    "Total messages sent",
    ["host", "status"]
)

processing_time = Histogram(
    "li_message_processing_seconds",
    "Message processing time",
    ["host"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

queue_depth = Gauge(
    "li_queue_depth",
    "Current queue depth",
    ["queue"]
)

host_status = Gauge(
    "li_host_status",
    "Host status (1=running, 0=stopped, -1=error)",
    ["host"]
)
```

**Deliverables:**
- [ ] Prometheus metrics for all key operations
- [ ] Structured JSON logging with correlation IDs
- [ ] Health check endpoint (`/health`, `/ready`)
- [ ] OpenTelemetry trace propagation

---

### Phase 4: Docker Service & Scalability (Week 7-8)

#### 4A: Production Engine Service

**Files to Create:**

```
hie/li/service/
├── __init__.py
├── main.py                          # Service entry point
├── api.py                           # Management API (FastAPI)
└── cli.py                           # CLI commands
```

**Key Implementation:**

```python
# li/service/main.py
class LIEngineService:
    """
    Main LI Engine service.
    
    Runs as a Docker container with:
    - Production engine (workflow orchestrator)
    - Management API (REST)
    - Metrics endpoint (Prometheus)
    - Health checks
    """
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.engine: ProductionEngine | None = None
        self.api: FastAPI | None = None
    
    async def start(self) -> None:
        # Load configuration
        if config_path.endswith(".xml"):
            config = IRISXMLLoader().load(config_path)
        else:
            config = YAMLLoader().load(config_path)
        
        # Create and start engine
        self.engine = ProductionEngine(config)
        await self.engine.start()
        
        # Start management API
        self.api = create_management_api(self.engine)
        
        # Start metrics server
        start_metrics_server(port=9090)
    
    async def reload(self) -> None:
        """Hot reload configuration."""
        new_config = self._load_config()
        await self.engine.apply_config_changes(new_config)
```

**Deliverables:**
- [ ] `LIEngineService` main service class
- [ ] Management API with CRUD for items
- [ ] Hot reload support
- [ ] Graceful shutdown

---

#### 4B: Docker Configuration

**Files to Modify:**

```
Dockerfile                           # Update for LI Engine
Dockerfile.li                        # NEW: Dedicated LI Engine image
docker-compose.li.yml                # NEW: LI Engine compose
```

**Key Configuration:**

```dockerfile
# Dockerfile.li
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY hie/ /app/hie/

# Environment
ENV PYTHONPATH=/app
ENV LI_CONFIG=/config/production.xml
ENV LI_LOG_LEVEL=INFO
ENV LI_METRICS_PORT=9090

# Ports
EXPOSE 8080 8081 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8081/health || exit 1

# Entry point
ENTRYPOINT ["python", "-m", "hie.li.service.main"]
CMD ["--config", "/config/production.xml"]
```

```yaml
# docker-compose.li.yml
version: '3.8'

services:
  li-engine:
    build:
      context: .
      dockerfile: Dockerfile.li
    container_name: li-engine
    ports:
      - "8080:8080"      # MLLP/HTTP receivers (configurable)
      - "8081:8081"      # Management API
      - "9090:9090"      # Prometheus metrics
    volumes:
      - ./config:/config:ro
      - ./schemas:/schemas:ro
      - ./data:/data
    environment:
      - LI_CONFIG=/config/production.xml
      - LI_SCHEMA_DIR=/schemas
      - DATABASE_URL=postgresql://li:li_password@postgres:5432/li
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 1G
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: li
      POSTGRES_PASSWORD: li_password
      POSTGRES_DB: li
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro

volumes:
  postgres_data:
  redis_data:
```

**Deliverables:**
- [ ] `Dockerfile.li` optimized for production
- [ ] `docker-compose.li.yml` with all services
- [ ] Prometheus configuration
- [ ] Resource limits for scalability

---

#### 4C: Scalability for 100s of Items

**Design Considerations:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SCALABILITY ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Single Container (Phase 1)                                                │
│   ──────────────────────────                                                │
│   • Asyncio event loop handles 100s of concurrent connections              │
│   • Each Host runs as async task(s) based on PoolSize                      │
│   • Redis for inter-host queuing                                           │
│   • Target: 100+ items, 1000+ msg/sec                                      │
│                                                                              │
│   Multi-Container (Phase 2 - Future)                                        │
│   ─────────────────────────────────                                         │
│   • Kubernetes deployment                                                   │
│   • Horizontal pod autoscaling                                              │
│   • Distributed queue (Redis Cluster)                                       │
│   • Target: 1000+ items, 10000+ msg/sec                                    │
│                                                                              │
│   Memory Management                                                         │
│   ─────────────────                                                         │
│   • Lazy schema loading (load on first use)                                │
│   • Message streaming (don't hold entire message in memory)                │
│   • Connection pooling with limits                                         │
│   • Queue depth limits with backpressure                                   │
│                                                                              │
│   CPU Management                                                            │
│   ──────────────                                                            │
│   • Asyncio for I/O-bound work (most HL7)                                  │
│   • ThreadPool for blocking operations                                      │
│   • ProcessPool for CPU-heavy transforms (optional)                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Deliverables:**
- [ ] Lazy schema loading
- [ ] Connection pool management
- [ ] Queue backpressure handling
- [ ] Memory profiling and optimization
- [ ] Performance benchmarks

---

## Testing Strategy

### Unit Tests

```
tests/
├── li/
│   ├── config/
│   │   └── test_iris_xml_loader.py
│   ├── hosts/
│   │   ├── test_business_service.py
│   │   └── test_hl7_tcp_service.py
│   ├── schemas/
│   │   ├── test_hl7_schema.py
│   │   └── test_schema_registry.py
│   ├── rules/
│   │   └── test_routing_rules.py
│   └── persistence/
│       ├── test_wal.py
│       └── test_redis_queue.py
```

### Integration Tests

```
tests/integration/
├── test_mllp_flow.py                # End-to-end MLLP message flow
├── test_routing.py                  # Message routing through rules
├── test_persistence.py              # WAL and queue durability
└── test_hot_reload.py               # Configuration hot reload
```

### Production Simulation

```
tests/simulation/
├── test_bhruh_production.py         # Load actual BHRUH production config
├── fixtures/
│   ├── BHRUH.Production.ADTProduction.xml
│   ├── PKB.HL7
│   └── sample_messages/
│       ├── ADT_A01.hl7
│       ├── ADT_A08.hl7
│       └── ...
└── mocks/
    ├── mock_mllp_server.py          # Mock external MLLP endpoints
    └── mock_responses.py
```

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Can load IRIS production XML
- [ ] Host hierarchy implemented (Service, Process, Operation)
- [ ] Schema system loads PKB.HL7 and parses messages
- [ ] Unit tests pass

### Phase 2 Complete When:
- [ ] MLLP inbound/outbound working
- [ ] HL7TCPService receives messages and generates ACKs
- [ ] HL7RoutingEngine routes based on rules
- [ ] Integration tests pass

### Phase 3 Complete When:
- [ ] Messages persisted to WAL before processing
- [ ] Redis queue working for inter-host messaging
- [ ] Prometheus metrics exposed
- [ ] Structured logging with correlation IDs
- [ ] Error handling with ReplyCodeActions

### Phase 4 Complete When:
- [ ] Docker service running
- [ ] Management API functional
- [ ] Hot reload working
- [ ] Can run BHRUH production config
- [ ] Performance: 100+ items, 1000+ msg/sec

---

## File Structure (Final)

```
hie/
├── li/                              # LI Engine
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── iris_xml_loader.py
│   │   ├── yaml_loader.py
│   │   ├── production_config.py
│   │   └── item_config.py
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── class_registry.py
│   │   └── schema_registry.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── production_engine.py
│   │   └── host_manager.py
│   ├── hosts/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── settings.py
│   │   └── hl7/
│   │       ├── __init__.py
│   │       ├── tcp_service.py
│   │       ├── tcp_operation.py
│   │       ├── routing_engine.py
│   │       └── ack.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── mllp/
│   │       ├── __init__.py
│   │       ├── inbound.py
│   │       ├── outbound.py
│   │       └── framing.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── loader.py
│   │   └── hl7/
│   │       ├── __init__.py
│   │       ├── schema.py
│   │       ├── parsed_view.py
│   │       └── definitions.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── loader.py
│   │   ├── conditions/
│   │   └── actions/
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── wal.py
│   │   ├── queue.py
│   │   ├── redis_queue.py
│   │   └── archive.py
│   ├── errors/
│   │   ├── __init__.py
│   │   ├── reply_code_actions.py
│   │   ├── retry.py
│   │   └── dead_letter.py
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── logging.py
│   │   ├── health.py
│   │   └── tracing.py
│   └── service/
│       ├── __init__.py
│       ├── main.py
│       ├── api.py
│       └── cli.py
├── core/                            # Existing HIE core (reused)
├── items/                           # Existing items (reused)
├── persistence/                     # Existing persistence (reused)
└── parsers/                         # Existing parsers (reused)
```

---

## Next Steps

1. **Approve this plan** - Confirm scope and priorities
2. **Begin Phase 1A** - IRIS XML Config Loader
3. **Set up test fixtures** - Copy BHRUH production XML and PKB.HL7 schema

**Ready to proceed with implementation.**
