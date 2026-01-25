# HIE Enterprise Workflow Engine Architecture

## Executive Summary

This document describes the architecture for uplifting HIE to an enterprise-grade, dynamically scalable, and fully configurable workflow runtime engine. The design matches or exceeds the capabilities of IRIS HealthConnect/Ensemble, Rhapsody, and Mirth Connect.

## Design Principles

1. **Adapter Pattern** - Separate protocol handling (adapters) from business logic (hosts)
2. **Configuration-Driven** - Every aspect configurable via XML/JSON/YAML
3. **Process Isolation** - Each item runs in its own process(es) with configurable pool size
4. **Reliable Queuing** - Persistent queues per item with guaranteed delivery
5. **Dynamic Scaling** - Runtime adjustment of pool sizes and configurations
6. **Enterprise Observability** - Full tracing, metrics, and audit logging

---

## Class Hierarchy

### Core Abstract Classes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BUSINESS HOST HIERARCHY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BusinessHost (Abstract Base)                                                │
│  ├── adapter: InboundAdapter | OutboundAdapter | None                       │
│  ├── queue: ReliableQueue                                                   │
│  ├── pool_size: int                                                         │
│  ├── settings: HostSettings                                                 │
│  ├── schedule: Schedule                                                     │
│  └── targets: list[str]  # Next items to route to                          │
│      │                                                                       │
│      ├── BusinessService (Inbound)                                          │
│      │   ├── adapter: InboundAdapter                                        │
│      │   └── on_message_received() -> routes to targets                     │
│      │                                                                       │
│      ├── BusinessProcess (Processing/Routing)                               │
│      │   ├── on_request() -> Message | list[Message]                        │
│      │   └── Subclasses:                                                    │
│      │       ├── RoutingEngine (rule-based routing)                         │
│      │       ├── TransformProcess (DTL transformations)                     │
│      │       └── CustomProcess (user-defined logic)                         │
│      │                                                                       │
│      └── BusinessOperation (Outbound)                                       │
│          ├── adapter: OutboundAdapter                                       │
│          └── on_message() -> sends via adapter                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            ADAPTER HIERARCHY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Adapter (Abstract Base)                                                     │
│  ├── settings: AdapterSettings                                              │
│  ├── connected: bool                                                        │
│  └── health_check() -> HealthStatus                                         │
│      │                                                                       │
│      ├── InboundAdapter (for BusinessService)                               │
│      │   ├── on_data_received: Callback                                     │
│      │   └── Implementations:                                               │
│      │       ├── TCPInboundAdapter (raw TCP)                                │
│      │       ├── MLLPInboundAdapter (HL7 MLLP)                              │
│      │       ├── HTTPInboundAdapter (REST/SOAP)                             │
│      │       ├── FileInboundAdapter (directory watch)                       │
│      │       ├── FTPInboundAdapter (FTP/SFTP polling)                       │
│      │       ├── KafkaInboundAdapter (Kafka consumer)                       │
│      │       └── DatabaseInboundAdapter (SQL polling)                       │
│      │                                                                       │
│      └── OutboundAdapter (for BusinessOperation)                            │
│          ├── send(data) -> response                                         │
│          └── Implementations:                                               │
│              ├── TCPOutboundAdapter (raw TCP)                               │
│              ├── MLLPOutboundAdapter (HL7 MLLP with ACK)                    │
│              ├── HTTPOutboundAdapter (REST/SOAP client)                     │
│              ├── FileOutboundAdapter (file writer)                          │
│              ├── FTPOutboundAdapter (FTP/SFTP upload)                       │
│              ├── KafkaOutboundAdapter (Kafka producer)                      │
│              ├── DatabaseOutboundAdapter (SQL insert/update)                │
│              └── EmailOutboundAdapter (SMTP)                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           MESSAGE HIERARCHY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Message (Abstract Base)                                                     │
│  ├── id: UUID                                                               │
│  ├── correlation_id: UUID                                                   │
│  ├── raw: bytes                                                             │
│  └── metadata: MessageMetadata                                              │
│      │                                                                       │
│      ├── HL7Message                                                         │
│      │   ├── segments: list[Segment]                                        │
│      │   ├── get_segment(name) -> Segment                                   │
│      │   └── get_field(path) -> str                                         │
│      │                                                                       │
│      ├── FHIRMessage                                                        │
│      │   └── resource: FHIRResource                                         │
│      │                                                                       │
│      ├── XMLMessage                                                         │
│      │   └── document: XMLDocument                                          │
│      │                                                                       │
│      ├── JSONMessage                                                        │
│      │   └── data: dict                                                     │
│      │                                                                       │
│      └── StreamContainer (binary/file)                                      │
│          └── stream: BinaryIO                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Production Configuration Schema

Based on IRIS Production XML, here's the equivalent JSON schema:

```json
{
  "$schema": "https://hie.nhs.uk/schemas/production/v2",
  "production": {
    "name": "BHRUH.Production.ADTProduction",
    "description": "ADT Integration Production",
    "enabled": true,
    "testing_enabled": true,
    "log_general_trace_events": true,
    "actor_pool_size": 1,
    
    "items": [
      {
        "name": "from.BHR.ADT1",
        "class_name": "hie.services.hl7.TCPService",
        "category": "Oracle Health",
        "pool_size": 1,
        "enabled": true,
        "foreground": false,
        "log_trace_events": true,
        "schedule": "",
        "comment": "Millennium ADT feed",
        
        "settings": {
          "adapter": {
            "port": 35001,
            "job_per_connection": false,
            "stay_connected": -1,
            "read_timeout": 30,
            "ssl_config": ""
          },
          "host": {
            "message_schema_category": "2.3.CER",
            "target_config_names": ["Main ADT Router"],
            "ack_mode": "App",
            "archive_io": true
          }
        }
      },
      
      {
        "name": "Main ADT Router",
        "class_name": "hie.processes.hl7.RoutingEngine",
        "category": "Oracle Health, C1",
        "pool_size": 1,
        "enabled": true,
        
        "settings": {
          "host": {
            "business_rule_name": "BHRUH.Router.ADTGeneral",
            "validation": "",
            "rule_logging": "a"
          }
        }
      },
      
      {
        "name": "to.Aqure.ADT",
        "class_name": "hie.operations.hl7.TCPOperation",
        "category": "Aqure",
        "pool_size": 1,
        "enabled": true,
        "log_trace_events": true,
        
        "settings": {
          "adapter": {
            "ip_address": "10.124.117.106",
            "port": 2005,
            "connect_timeout": 30,
            "reconnect_retry": 5,
            "stay_connected": -1,
            "local_interface": ""
          },
          "host": {
            "reply_code_actions": ":?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C",
            "archive_io": true,
            "failure_timeout": 15,
            "retry_interval": 5
          }
        }
      }
    ]
  }
}
```

---

## Core Components

### 1. Production Engine

The Production is the top-level orchestrator that:
- Loads configuration (XML/JSON/YAML)
- Creates and manages all BusinessHost instances
- Manages process pools for each item
- Handles graceful startup/shutdown
- Provides health monitoring and metrics

```python
class ProductionEngine:
    """Enterprise-grade production orchestrator."""
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.hosts: dict[str, BusinessHost] = {}
        self.process_manager = ProcessManager()
        self.queue_manager = QueueManager()
        self.scheduler = Scheduler()
        self.metrics = MetricsCollector()
    
    async def start(self):
        """Start all enabled hosts with their configured pool sizes."""
        for item_config in self.config.items:
            if not item_config.enabled:
                continue
            
            # Create host instance
            host = self.create_host(item_config)
            self.hosts[item_config.name] = host
            
            # Create reliable queue for this host
            queue = self.queue_manager.create_queue(
                name=item_config.name,
                persistent=True,
                max_size=item_config.queue_size
            )
            host.bind_queue(queue)
            
            # Start worker processes/threads
            await self.process_manager.start_pool(
                host=host,
                pool_size=item_config.pool_size,
                foreground=item_config.foreground
            )
            
            # Register schedule if configured
            if item_config.schedule:
                self.scheduler.register(host, item_config.schedule)
```

### 2. Business Host Base

```python
class BusinessHost(ABC):
    """
    Abstract base for all business hosts.
    
    A BusinessHost is a configurable runtime unit that processes messages.
    It can have an adapter for protocol handling and a queue for reliable delivery.
    """
    
    def __init__(self, config: HostConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        self.pool_size = config.pool_size
        
        # Settings are split between adapter and host
        self.adapter_settings = config.settings.get("adapter", {})
        self.host_settings = config.settings.get("host", {})
        
        # Runtime components (injected by Production)
        self._adapter: Adapter | None = None
        self._queue: ReliableQueue | None = None
        self._targets: list[str] = []
        
        # Metrics
        self._metrics = HostMetrics()
        self._state = HostState.CREATED
    
    @abstractmethod
    async def on_init(self) -> None:
        """Initialize the host. Called once at startup."""
        pass
    
    @abstractmethod
    async def on_teardown(self) -> None:
        """Cleanup the host. Called once at shutdown."""
        pass
    
    async def send_to_targets(self, message: Message) -> None:
        """Route message to configured target hosts."""
        for target_name in self._targets:
            target_queue = self._production.get_queue(target_name)
            await target_queue.put(message)
```

### 3. Business Service (Inbound)

```python
class BusinessService(BusinessHost):
    """
    Inbound message handler with protocol adapter.
    
    Receives messages from external systems via its adapter
    and routes them to target BusinessProcesses or BusinessOperations.
    """
    
    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self._targets = config.settings.get("host", {}).get("target_config_names", [])
    
    async def on_init(self) -> None:
        """Initialize adapter and start listening."""
        # Create and configure adapter
        adapter_class = get_adapter_class(self.config.adapter_type)
        self._adapter = adapter_class(self.adapter_settings)
        self._adapter.on_data_received = self._handle_incoming
        await self._adapter.start()
    
    async def _handle_incoming(self, data: bytes, metadata: dict) -> bytes | None:
        """
        Handle incoming data from adapter.
        
        Returns acknowledgment bytes if applicable.
        """
        # Create message from raw data
        message = self.create_message(data, metadata)
        
        # Archive if configured
        if self.host_settings.get("archive_io"):
            await self._archive(message, direction="inbound")
        
        # Route to targets
        await self.send_to_targets(message)
        
        # Generate acknowledgment
        if self.host_settings.get("ack_mode") == "App":
            return self.generate_ack(message)
        return None


class HL7TCPService(BusinessService):
    """HL7v2 TCP/MLLP inbound service."""
    
    adapter_type = "mllp_inbound"
    
    def create_message(self, data: bytes, metadata: dict) -> HL7Message:
        schema = self.host_settings.get("message_schema_category", "2.5")
        return HL7Message.parse(data, schema=schema)
    
    def generate_ack(self, message: HL7Message) -> bytes:
        return message.generate_ack(ack_code="AA")
```

### 4. Business Process (Routing/Transformation)

```python
class BusinessProcess(BusinessHost):
    """
    Message processor for routing, transformation, and orchestration.
    
    Receives messages from its queue, processes them, and routes
    to target hosts based on business rules.
    """
    
    async def on_init(self) -> None:
        """Initialize process-specific resources."""
        pass
    
    @abstractmethod
    async def on_request(self, message: Message) -> ProcessResult:
        """
        Process a message.
        
        Returns:
            ProcessResult containing output messages and target routing
        """
        pass
    
    async def run(self) -> None:
        """Main processing loop."""
        while self._state == HostState.RUNNING:
            message = await self._queue.get()
            try:
                result = await self.on_request(message)
                for output_msg, target in result.outputs:
                    await self._production.route_to(target, output_msg)
                await self._queue.ack(message)
            except Exception as e:
                await self._handle_error(message, e)


class RoutingEngine(BusinessProcess):
    """
    Rule-based message router.
    
    Evaluates business rules to determine message routing.
    Equivalent to EnsLib.HL7.MsgRouter.RoutingEngine.
    """
    
    def __init__(self, config: ProcessConfig):
        super().__init__(config)
        self.rule_name = self.host_settings.get("business_rule_name")
        self.validation = self.host_settings.get("validation", "")
        self._rules: BusinessRuleSet | None = None
    
    async def on_init(self) -> None:
        # Load business rules
        self._rules = await load_business_rules(self.rule_name)
    
    async def on_request(self, message: Message) -> ProcessResult:
        # Validate if configured
        if self.validation:
            await self.validate(message, self.validation)
        
        # Evaluate rules to determine routing
        results = await self._rules.evaluate(message)
        
        outputs = []
        for rule_result in results:
            if rule_result.transform:
                message = await rule_result.transform.apply(message)
            outputs.append((message, rule_result.target))
        
        return ProcessResult(outputs=outputs)
```

### 5. Business Operation (Outbound)

```python
class BusinessOperation(BusinessHost):
    """
    Outbound message sender with protocol adapter.
    
    Receives messages from its queue and sends them to external
    systems via its adapter, handling acknowledgments and retries.
    """
    
    def __init__(self, config: OperationConfig):
        super().__init__(config)
        self.reply_code_actions = self._parse_reply_codes(
            self.host_settings.get("reply_code_actions", "")
        )
        self.failure_timeout = self.host_settings.get("failure_timeout", 15)
        self.retry_interval = self.host_settings.get("retry_interval", 5)
    
    async def on_init(self) -> None:
        """Initialize outbound adapter."""
        adapter_class = get_adapter_class(self.config.adapter_type)
        self._adapter = adapter_class(self.adapter_settings)
        await self._adapter.connect()
    
    async def on_message(self, message: Message) -> OperationResult:
        """
        Send message via adapter and handle response.
        """
        try:
            response = await self._adapter.send(message.raw)
            
            # Archive if configured
            if self.host_settings.get("archive_io"):
                await self._archive(message, direction="outbound")
                await self._archive_response(response)
            
            # Evaluate response based on reply code actions
            action = self._evaluate_reply(response)
            return OperationResult(success=action.success, action=action)
            
        except ConnectionError as e:
            return OperationResult(success=False, error=e, retry=True)
    
    def _parse_reply_codes(self, codes: str) -> dict:
        """
        Parse IRIS-style reply code actions.
        
        Format: ":?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C"
        - ?R = Reject -> F (Fail)
        - ?E = Error -> S (Suspend)
        - ?A = Accept -> C (Complete)
        - etc.
        """
        actions = {}
        for part in codes.split(","):
            if "=" in part:
                code, action = part.split("=")
                actions[code.strip(":")] = action
        return actions


class HL7TCPOperation(BusinessOperation):
    """HL7v2 TCP/MLLP outbound operation."""
    
    adapter_type = "mllp_outbound"
    
    def _evaluate_reply(self, response: bytes) -> ReplyAction:
        """Evaluate HL7 ACK/NAK response."""
        ack = HL7Message.parse(response)
        msa = ack.get_segment("MSA")
        ack_code = msa.get_field(1) if msa else "AA"
        
        # Map ACK code to action based on reply_code_actions
        for pattern, action in self.reply_code_actions.items():
            if self._matches_pattern(ack_code, pattern):
                return ReplyAction(
                    code=ack_code,
                    action=action,
                    success=action in ("C", "W")  # Complete or Warning
                )
        
        return ReplyAction(code=ack_code, action="C", success=True)
```

### 6. Adapter System

```python
class Adapter(ABC):
    """
    Abstract base for protocol adapters.
    
    Adapters handle the protocol-specific details of communication,
    separate from the business logic in hosts.
    """
    
    def __init__(self, settings: dict):
        self.settings = AdapterSettings.parse(settings)
        self._connected = False
        self._metrics = AdapterMetrics()
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass
    
    @property
    def is_connected(self) -> bool:
        return self._connected


class InboundAdapter(Adapter):
    """Adapter for receiving data from external systems."""
    
    def __init__(self, settings: dict):
        super().__init__(settings)
        self.on_data_received: Callable[[bytes, dict], Awaitable[bytes | None]] = None
    
    @abstractmethod
    async def start(self) -> None:
        """Start listening for incoming data."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop listening."""
        pass


class OutboundAdapter(Adapter):
    """Adapter for sending data to external systems."""
    
    @abstractmethod
    async def send(self, data: bytes) -> bytes:
        """
        Send data and return response.
        
        Args:
            data: Raw bytes to send
            
        Returns:
            Response bytes from remote system
        """
        pass


class MLLPInboundAdapter(InboundAdapter):
    """MLLP TCP server adapter."""
    
    def __init__(self, settings: dict):
        super().__init__(settings)
        self.port = settings.get("port", 2575)
        self.job_per_connection = settings.get("job_per_connection", False)
        self.stay_connected = settings.get("stay_connected", -1)
        self.read_timeout = settings.get("read_timeout", 30)
        self._server: asyncio.Server | None = None
    
    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_connection,
            host="0.0.0.0",
            port=self.port
        )
        self._connected = True
    
    async def _handle_connection(self, reader, writer):
        """Handle a single MLLP connection."""
        while True:
            try:
                # Read MLLP-framed message
                data = await self._read_mllp_frame(reader)
                if not data:
                    break
                
                # Callback to host
                ack = await self.on_data_received(data, {
                    "remote_addr": writer.get_extra_info("peername")
                })
                
                # Send acknowledgment
                if ack:
                    await self._write_mllp_frame(writer, ack)
                
                # Check stay_connected
                if self.stay_connected == 0:
                    break
                    
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error("mllp_connection_error", error=str(e))
                break
        
        writer.close()
        await writer.wait_closed()


class MLLPOutboundAdapter(OutboundAdapter):
    """MLLP TCP client adapter with connection pooling."""
    
    def __init__(self, settings: dict):
        super().__init__(settings)
        self.ip_address = settings.get("ip_address")
        self.port = settings.get("port")
        self.connect_timeout = settings.get("connect_timeout", 30)
        self.reconnect_retry = settings.get("reconnect_retry", 5)
        self.stay_connected = settings.get("stay_connected", -1)
        self.local_interface = settings.get("local_interface")
        self._pool: ConnectionPool | None = None
    
    async def connect(self) -> None:
        self._pool = ConnectionPool(
            host=self.ip_address,
            port=self.port,
            max_connections=5,
            timeout=self.connect_timeout,
            local_addr=self._parse_local_interface()
        )
        self._connected = True
    
    async def send(self, data: bytes) -> bytes:
        conn = await self._pool.acquire()
        try:
            # Send MLLP-framed message
            await conn.write(MLLP_START + data + MLLP_END + MLLP_CR)
            
            # Read MLLP-framed response
            response = await conn.read_mllp_frame(timeout=self.settings.response_timeout)
            return response
        finally:
            if self.stay_connected == -1:
                await self._pool.release(conn)
            else:
                await conn.close()
```

### 7. Reliable Queue System

```python
class ReliableQueue:
    """
    Persistent message queue with guaranteed delivery.
    
    Features:
    - Persistent storage (survives restarts)
    - At-least-once delivery
    - Message acknowledgment
    - Dead letter queue
    - Priority support
    """
    
    def __init__(
        self,
        name: str,
        storage: QueueStorage,
        max_size: int = 10000,
        max_retries: int = 3
    ):
        self.name = name
        self.storage = storage
        self.max_size = max_size
        self.max_retries = max_retries
        self._pending: dict[str, QueuedMessage] = {}
    
    async def put(self, message: Message, priority: int = 0) -> None:
        """Add message to queue."""
        queued = QueuedMessage(
            id=str(uuid4()),
            message=message,
            priority=priority,
            enqueued_at=datetime.now(timezone.utc),
            retry_count=0
        )
        await self.storage.store(self.name, queued)
    
    async def get(self, timeout: float | None = None) -> Message:
        """Get next message from queue (blocks until available)."""
        queued = await self.storage.fetch_next(self.name, timeout=timeout)
        self._pending[queued.id] = queued
        return queued.message
    
    async def ack(self, message: Message) -> None:
        """Acknowledge successful processing."""
        queued_id = self._find_queued_id(message)
        if queued_id:
            await self.storage.delete(self.name, queued_id)
            del self._pending[queued_id]
    
    async def nack(self, message: Message, requeue: bool = True) -> None:
        """Negative acknowledgment - message processing failed."""
        queued_id = self._find_queued_id(message)
        if queued_id:
            queued = self._pending[queued_id]
            if requeue and queued.retry_count < self.max_retries:
                queued.retry_count += 1
                await self.storage.requeue(self.name, queued)
            else:
                await self.storage.move_to_dead_letter(self.name, queued)
            del self._pending[queued_id]


class QueueStorage(ABC):
    """Abstract storage backend for queues."""
    
    @abstractmethod
    async def store(self, queue_name: str, message: QueuedMessage) -> None:
        pass
    
    @abstractmethod
    async def fetch_next(self, queue_name: str, timeout: float | None) -> QueuedMessage:
        pass
    
    @abstractmethod
    async def delete(self, queue_name: str, message_id: str) -> None:
        pass


class PostgresQueueStorage(QueueStorage):
    """PostgreSQL-backed queue storage for durability."""
    pass


class RedisQueueStorage(QueueStorage):
    """Redis-backed queue storage for high performance."""
    pass
```

### 8. Process Manager

```python
class ProcessManager:
    """
    Manages process/thread pools for business hosts.
    
    Each host can have multiple worker processes, each potentially
    with multiple threads for concurrent connection handling.
    """
    
    def __init__(self):
        self._pools: dict[str, ProcessPool] = {}
    
    async def start_pool(
        self,
        host: BusinessHost,
        pool_size: int,
        foreground: bool = False
    ) -> ProcessPool:
        """
        Start a process pool for a host.
        
        Args:
            host: The business host to run
            pool_size: Number of worker processes
            foreground: If True, run in main process (for debugging)
        """
        if foreground or pool_size == 1:
            # Run in current process with async workers
            pool = AsyncWorkerPool(host, pool_size)
        else:
            # Run in separate processes
            pool = MultiProcessPool(host, pool_size)
        
        await pool.start()
        self._pools[host.name] = pool
        return pool
    
    async def scale_pool(self, host_name: str, new_size: int) -> None:
        """Dynamically scale a host's pool size."""
        pool = self._pools.get(host_name)
        if pool:
            await pool.scale(new_size)
    
    async def stop_all(self, timeout: float = 30.0) -> None:
        """Gracefully stop all pools."""
        tasks = [pool.stop(timeout) for pool in self._pools.values()]
        await asyncio.gather(*tasks, return_exceptions=True)


class ProcessPool(ABC):
    """Abstract process pool."""
    
    @abstractmethod
    async def start(self) -> None:
        pass
    
    @abstractmethod
    async def stop(self, timeout: float) -> None:
        pass
    
    @abstractmethod
    async def scale(self, new_size: int) -> None:
        pass


class AsyncWorkerPool(ProcessPool):
    """Pool of async workers in a single process."""
    
    def __init__(self, host: BusinessHost, size: int):
        self.host = host
        self.size = size
        self._workers: list[asyncio.Task] = []
    
    async def start(self) -> None:
        for i in range(self.size):
            task = asyncio.create_task(
                self._worker_loop(i),
                name=f"{self.host.name}-worker-{i}"
            )
            self._workers.append(task)
    
    async def _worker_loop(self, worker_id: int) -> None:
        """Main worker loop."""
        await self.host.on_init()
        try:
            await self.host.run()
        finally:
            await self.host.on_teardown()
```

### 9. Business Rules Engine

```python
class BusinessRule:
    """
    A single business rule for routing decisions.
    
    Rules consist of:
    - Conditions: When to apply the rule
    - Actions: What to do (transform, route, etc.)
    """
    
    def __init__(
        self,
        name: str,
        conditions: list[Condition],
        actions: list[Action],
        enabled: bool = True
    ):
        self.name = name
        self.conditions = conditions
        self.actions = actions
        self.enabled = enabled
    
    async def evaluate(self, message: Message) -> RuleResult | None:
        """Evaluate rule against message."""
        if not self.enabled:
            return None
        
        # Check all conditions
        if not all(c.evaluate(message) for c in self.conditions):
            return None
        
        # Execute actions
        result = RuleResult(rule=self.name)
        for action in self.actions:
            await action.execute(message, result)
        
        return result


class BusinessRuleSet:
    """Collection of business rules for a routing engine."""
    
    def __init__(self, name: str, rules: list[BusinessRule]):
        self.name = name
        self.rules = rules
    
    async def evaluate(self, message: Message) -> list[RuleResult]:
        """Evaluate all rules and return matching results."""
        results = []
        for rule in self.rules:
            result = await rule.evaluate(message)
            if result:
                results.append(result)
                if result.stop_processing:
                    break
        return results


class Condition(ABC):
    """Abstract condition for rule evaluation."""
    
    @abstractmethod
    def evaluate(self, message: Message) -> bool:
        pass


class FieldCondition(Condition):
    """Condition based on message field value."""
    
    def __init__(self, field_path: str, operator: str, value: Any):
        self.field_path = field_path
        self.operator = operator
        self.value = value
    
    def evaluate(self, message: Message) -> bool:
        actual = message.get_field(self.field_path)
        
        match self.operator:
            case "=": return actual == self.value
            case "!=": return actual != self.value
            case "contains": return self.value in actual
            case "starts_with": return actual.startswith(self.value)
            case "matches": return re.match(self.value, actual)
            case "in": return actual in self.value
            case _: return False


class Action(ABC):
    """Abstract action for rule execution."""
    
    @abstractmethod
    async def execute(self, message: Message, result: RuleResult) -> None:
        pass


class SendAction(Action):
    """Route message to a target."""
    
    def __init__(self, target: str, transform: str | None = None):
        self.target = target
        self.transform = transform
    
    async def execute(self, message: Message, result: RuleResult) -> None:
        if self.transform:
            transformer = await load_transform(self.transform)
            message = await transformer.apply(message)
        result.add_output(message, self.target)
```

---

## Configuration Import from IRIS

```python
class IRISConfigImporter:
    """Import IRIS/Ensemble production XML configuration."""
    
    def import_production(self, xml_content: str) -> ProductionConfig:
        """Parse IRIS production XML and convert to HIE config."""
        root = ET.fromstring(xml_content)
        production = root.find(".//Production")
        
        config = ProductionConfig(
            name=production.get("Name"),
            testing_enabled=production.get("TestingEnabled") == "true",
            log_general_trace_events=production.get("LogGeneralTraceEvents") == "true",
            actor_pool_size=int(production.get("ActorPoolSize", 1)),
            items=[]
        )
        
        for item in production.findall("Item"):
            item_config = self._parse_item(item)
            config.items.append(item_config)
        
        return config
    
    def _parse_item(self, item: ET.Element) -> ItemConfig:
        """Parse a single IRIS item configuration."""
        settings = {"adapter": {}, "host": {}}
        
        for setting in item.findall("Setting"):
            target = setting.get("Target", "Host").lower()
            name = self._convert_setting_name(setting.get("Name"))
            value = setting.text
            settings[target][name] = self._parse_value(value)
        
        return ItemConfig(
            name=item.get("Name"),
            class_name=self._map_class_name(item.get("ClassName")),
            category=item.get("Category", ""),
            pool_size=int(item.get("PoolSize", 1)),
            enabled=item.get("Enabled") == "true",
            foreground=item.get("Foreground") == "true",
            log_trace_events=item.get("LogTraceEvents") == "true",
            schedule=item.get("Schedule", ""),
            comment=item.get("Comment", ""),
            settings=settings
        )
    
    def _map_class_name(self, iris_class: str) -> str:
        """Map IRIS class names to HIE equivalents."""
        mapping = {
            "EnsLib.HL7.Service.TCPService": "hie.services.hl7.TCPService",
            "EnsLib.HL7.Operation.TCPOperation": "hie.operations.hl7.TCPOperation",
            "EnsLib.HL7.MsgRouter.RoutingEngine": "hie.processes.hl7.RoutingEngine",
            "EnsLib.HL7.Operation.FileOperation": "hie.operations.hl7.FileOperation",
            "EnsLib.EMail.AlertOperation": "hie.operations.email.AlertOperation",
            # Add more mappings...
        }
        return mapping.get(iris_class, iris_class)
```

---

## Directory Structure

```
hie/
├── engine/
│   ├── __init__.py
│   ├── production.py          # ProductionEngine
│   ├── process_manager.py     # ProcessManager, ProcessPool
│   ├── queue_manager.py       # QueueManager, ReliableQueue
│   ├── scheduler.py           # Schedule management
│   └── metrics.py             # MetricsCollector
│
├── hosts/
│   ├── __init__.py
│   ├── base.py                # BusinessHost base class
│   ├── service.py             # BusinessService base
│   ├── process.py             # BusinessProcess base
│   ├── operation.py           # BusinessOperation base
│   │
│   ├── services/              # Inbound services
│   │   ├── __init__.py
│   │   ├── hl7_tcp_service.py
│   │   ├── http_service.py
│   │   ├── file_service.py
│   │   └── ftp_service.py
│   │
│   ├── processes/             # Business processes
│   │   ├── __init__.py
│   │   ├── routing_engine.py
│   │   ├── transform_process.py
│   │   └── custom_process.py
│   │
│   └── operations/            # Outbound operations
│       ├── __init__.py
│       ├── hl7_tcp_operation.py
│       ├── http_operation.py
│       ├── file_operation.py
│       ├── ftp_operation.py
│       ├── database_operation.py
│       └── email_operation.py
│
├── adapters/
│   ├── __init__.py
│   ├── base.py                # Adapter base classes
│   │
│   ├── inbound/               # Inbound adapters
│   │   ├── __init__.py
│   │   ├── tcp_adapter.py
│   │   ├── mllp_adapter.py
│   │   ├── http_adapter.py
│   │   ├── file_adapter.py
│   │   ├── ftp_adapter.py
│   │   ├── kafka_adapter.py
│   │   └── database_adapter.py
│   │
│   └── outbound/              # Outbound adapters
│       ├── __init__.py
│       ├── tcp_adapter.py
│       ├── mllp_adapter.py
│       ├── http_adapter.py
│       ├── file_adapter.py
│       ├── ftp_adapter.py
│       ├── kafka_adapter.py
│       ├── database_adapter.py
│       └── email_adapter.py
│
├── messages/
│   ├── __init__.py
│   ├── base.py                # Message base class
│   ├── hl7_message.py         # HL7v2 message
│   ├── fhir_message.py        # FHIR message
│   ├── xml_message.py         # XML message
│   ├── json_message.py        # JSON message
│   └── stream_container.py    # Binary/file container
│
├── rules/
│   ├── __init__.py
│   ├── engine.py              # BusinessRuleSet, BusinessRule
│   ├── conditions.py          # Condition classes
│   ├── actions.py             # Action classes
│   └── loader.py              # Rule loading from config
│
├── transforms/
│   ├── __init__.py
│   ├── base.py                # Transform base class
│   ├── hl7_transform.py       # HL7 DTL-style transforms
│   ├── xslt_transform.py      # XSLT transforms
│   └── python_transform.py    # Python script transforms
│
├── storage/
│   ├── __init__.py
│   ├── queue_storage.py       # Queue storage backends
│   ├── message_store.py       # Message persistence
│   └── state_store.py         # Host state persistence
│
├── config/
│   ├── __init__.py
│   ├── schema.py              # Configuration schemas
│   ├── loader.py              # Config loading (JSON/YAML/XML)
│   ├── importer.py            # IRIS/Rhapsody config import
│   └── validator.py           # Configuration validation
│
└── monitoring/
    ├── __init__.py
    ├── metrics.py             # Prometheus metrics
    ├── tracing.py             # OpenTelemetry tracing
    ├── logging.py             # Structured logging
    └── health.py              # Health checks
```

---

## Runtime Architecture (Implementation Details)

This section documents the actual implementation of the LI Engine runtime model.

### Item → Python Class Mapping

Each configured item runs as an instance of a Python class that inherits from the base Host hierarchy:

```
Host (ABC) - hie/li/hosts/base.py
├── BusinessService (inbound - receives messages from external systems)
│   └── HL7TCPService, FileService, HTTPService, etc.
├── BusinessProcess (routing/transformation)
│   └── HL7RoutingEngine, MessageRouter, TransformProcess, etc.
└── BusinessOperation (outbound - sends messages to external systems)
    └── HL7TCPOperation, FileOperation, HTTPOperation, etc.
```

### Concurrency Model: Async Workers (Not Threads)

The LI Engine uses **Python asyncio** for non-blocking I/O, not traditional threads:

| Concept | Implementation | Notes |
|---------|----------------|-------|
| **Pool Size** | `asyncio.Task` workers | Each item spawns N async tasks |
| **Message Queue** | `asyncio.Queue` | Per-host queue with configurable size |
| **Timeout Handling** | `asyncio.wait_for` | Configurable per-message timeout |
| **Pause/Resume** | `asyncio.Event` | Non-blocking pause mechanism |
| **Graceful Shutdown** | `asyncio.Event` + `asyncio.wait` | Wait for workers, then cancel |

**Why asyncio over threads?**
- Healthcare integration is I/O-bound (network, file, database)
- asyncio provides better performance for I/O-bound workloads
- No GIL contention issues
- Simpler debugging and error handling
- Native Python 3.11+ support

### Worker Loop (from `hie/li/hosts/base.py`)

```python
async def _worker_loop(self, worker_id: int):
    """Main worker loop for processing messages."""
    while not self._shutdown_event.is_set():
        # Wait if paused
        await self._pause_event.wait()
        
        # Get message from queue with timeout
        message = await asyncio.wait_for(self._queue.get(), timeout=1.0)
        
        # Process with configurable timeout
        result = await asyncio.wait_for(
            self._process_message(message),
            timeout=self.get_setting("Host", "Timeout", 30.0)
        )
```

### Hot Reload Architecture

Hot reload allows updating item configuration while the production is running:

```
┌─────────────────────────────────────────────────────────────────┐
│                     HOT RELOAD FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. API receives PUT /api/projects/{id}/items/{item_id}         │
│     └── Updates database with new settings                       │
│                                                                  │
│  2. API calls POST /api/projects/{id}/items/{item_id}/reload    │
│     └── Signals engine to reload specific item                   │
│                                                                  │
│  3. Engine performs graceful item restart:                       │
│     a. Pause item (stop accepting new messages)                  │
│     b. Wait for in-flight messages to complete                   │
│     c. Stop adapter                                              │
│     d. Load new configuration from database                      │
│     e. Recreate adapter with new settings                        │
│     f. Resume item (start accepting messages)                    │
│                                                                  │
│  4. No messages lost - queue persists during reload              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Database   │────▶│   API/UI     │────▶│   Engine     │
│  (source of  │     │  (edit &     │     │  (runtime    │
│   truth)     │◀────│   save)      │◀────│   state)     │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                         │
       │         ┌──────────────┐               │
       └────────▶│  Hot Reload  │◀──────────────┘
                 │  (sync DB →  │
                 │   Engine)    │
                 └──────────────┘
```

---

## Migration Path

### Phase 1: Core Infrastructure
1. Implement new `BusinessHost` hierarchy
2. Implement `Adapter` system
3. Implement `ReliableQueue` with PostgreSQL storage
4. Implement `ProcessManager`

### Phase 2: Protocol Adapters
1. MLLP inbound/outbound adapters
2. HTTP inbound/outbound adapters
3. File inbound/outbound adapters
4. FTP/SFTP adapters

### Phase 3: Business Hosts
1. HL7 TCP Service
2. HL7 TCP Operation
3. Routing Engine with business rules
4. File operations

### Phase 4: Advanced Features
1. IRIS configuration import
2. Business rules editor
3. Visual production designer
4. Dynamic scaling API

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Throughput | 50,000+ msg/sec | Per production instance |
| Latency (p50) | <5ms | Local processing |
| Latency (p99) | <50ms | Including network |
| Concurrent connections | 10,000+ | Per adapter |
| Message size | Up to 100MB | Stream support |
| Queue depth | 1M+ messages | Persistent |

---

## Comparison with Competitors

| Feature | HIE v2 | IRIS | Rhapsody | Mirth |
|---------|--------|------|----------|-------|
| Open Source | ✅ | ❌ | ❌ | ✅ (limited) |
| Python-based | ✅ | ❌ | ❌ | ❌ |
| Adapter/Host separation | ✅ | ✅ | ✅ | Partial |
| Configurable pool size | ✅ | ✅ | ✅ | ✅ |
| Persistent queues | ✅ | ✅ | ✅ | ✅ |
| Business rules engine | ✅ | ✅ | ✅ | ✅ |
| IRIS config import | ✅ | N/A | ❌ | ❌ |
| Cloud-native | ✅ | Partial | Partial | Partial |
| Kubernetes-ready | ✅ | Partial | Partial | Partial |
| Hot reload | ✅ | ✅ | ✅ | ✅ |
| Visual designer | 🔄 | ✅ | ✅ | ✅ |

---

*This architecture document serves as the blueprint for the HIE enterprise workflow engine uplift.*
