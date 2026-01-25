# LI (Lightweight Integration) Engine - Class Hierarchy Design

## Overview

This document defines the Python class hierarchy for the **LI (Lightweight Integration) Engine**, an enterprise-grade, open-source healthcare integration platform. The design emphasizes **extensibility at every hierarchy level** so users can easily extend any class to create custom implementations.

**Design Principles:**
- Every class is designed for extension (not final)
- Clear extension points with hooks and callbacks
- Settings are schema-driven and extensible
- Class registry allows runtime registration of custom classes
- No hardcoded behavior - everything is configurable

---

## 1. Production & Host Base Classes

```
li.engine.Production
    │
    ├── name: str
    ├── testing_enabled: bool
    ├── log_general_trace_events: bool
    ├── actor_pool_size: int
    ├── items: dict[str, Host]
    │
    ├── Extension Points:
    │   ├── on_before_start()              # Hook before production starts
    │   ├── on_after_start()               # Hook after production starts
    │   ├── on_before_stop()               # Hook before production stops
    │   ├── on_after_stop()                # Hook after production stops
    │   └── on_error(host, error)          # Global error handler
    │
    └── Methods: start(), stop(), get_host(), route_message()


li.engine.Host (ABC)
    │
    ├── name: str                          # "from.BHR.ADT1"
    ├── class_name: str                    # "li.hosts.hl7.HL7TCPService"
    ├── category: str                      # "Oracle Health"
    ├── pool_size: int                     # Number of worker processes/threads
    ├── enabled: bool
    ├── foreground: bool
    ├── log_trace_events: bool
    ├── schedule: str                      # Cron-like schedule
    ├── comment: str
    │
    ├── adapter_settings: dict             # Target="Adapter" settings
    ├── host_settings: dict                # Target="Host" settings
    │
    ├── _adapter: Adapter | None
    ├── _queue: Queue
    ├── _state: HostState
    │
    ├── Extension Points (Override in subclasses):
    │   ├── on_init()                      # Called once at startup
    │   ├── on_teardown()                  # Called once at shutdown
    │   ├── on_process_input(message)      # Main processing logic
    │   ├── on_error(error, message)       # Error handling
    │   ├── on_before_process(message)     # Pre-processing hook
    │   ├── on_after_process(message)      # Post-processing hook
    │   └── get_settings_schema()          # Return Pydantic schema for settings
    │
    └── Abstract Methods: on_init(), on_teardown(), on_process_input()
```

**How to Extend:**
```python
# User creates custom host by extending any level
class MyCustomService(li.hosts.BusinessService):
    """Custom service with special logic."""
    
    def on_init(self):
        # Custom initialization
        pass
    
    def on_process_input(self, message):
        # Custom processing
        return self.transform_message(message)
```

---

## 2. Business Service Hierarchy (Inbound)

```
li.hosts.BusinessService (Host)
    │
    ├── target_config_names: list[str]     # Where to route messages
    ├── archive_io: bool
    ├── alert_on_error: bool
    ├── _adapter: InboundAdapter
    │
    ├── Extension Points:
    │   ├── on_message_received(raw)       # Raw data from adapter
    │   ├── on_message_parsed(message)     # After parsing
    │   ├── on_before_route(message)       # Before routing to targets
    │   ├── create_message(raw) -> Message # Override message creation
    │   └── generate_ack(message) -> bytes # Override ACK generation
    │
    └── li.hosts.hl7.HL7Service (BusinessService)
        │
        ├── message_schema_category: str   # "2.3", "2.4", "2.5"
        ├── ack_mode: str                  # "App", "Imm", "None"
        ├── use_ack_commit_codes: bool
        │
        ├── Extension Points:
        │   ├── parse_hl7(raw) -> HL7Message
        │   ├── validate_hl7(message)
        │   └── create_hl7_ack(message, code) -> bytes
        │
        ├── li.hosts.hl7.HL7TCPService
        │   └── Uses: MLLPInboundAdapter
        │   └── LI Class: li.hosts.hl7.HL7TCPService
        │
        ├── li.hosts.hl7.HL7HTTPService
        │   └── Uses: HTTPInboundAdapter
        │   └── LI Class: li.hosts.hl7.HL7HTTPService
        │
        └── li.hosts.hl7.HL7FileService
            └── Uses: FileInboundAdapter
            └── LI Class: li.hosts.hl7.HL7FileService


    li.hosts.fhir.FHIRService (BusinessService)
        │
        └── li.hosts.fhir.FHIRHTTPService
            └── Uses: HTTPInboundAdapter


    li.hosts.xml.XMLService (BusinessService)
        │
        └── li.hosts.xml.XMLFileService
            └── Uses: FileInboundAdapter


    li.hosts.json.JSONService (BusinessService)
        │
        └── li.hosts.json.JSONHTTPService
            └── Uses: HTTPInboundAdapter
```

**How to Extend:**
```python
# Extend at HL7Service level for all HL7 services
class MyHL7Service(li.hosts.hl7.HL7Service):
    def validate_hl7(self, message):
        # Custom validation logic
        super().validate_hl7(message)
        self.check_custom_rules(message)

# Or extend at specific service level
class MySpecialTCPService(li.hosts.hl7.HL7TCPService):
    def on_message_received(self, raw):
        # Custom pre-processing
        return super().on_message_received(raw)
```

---

## 3. Business Process Hierarchy (Routing/Processing)

```
li.hosts.BusinessProcess (Host)
    │
    ├── _adapter = None                    # Processes have no adapter
    │
    ├── Extension Points:
    │   ├── on_request(message) -> Response
    │   ├── send_request_sync(target, message, timeout) -> Message
    │   ├── send_request_async(target, message)
    │   ├── on_response(response)
    │   └── on_timeout(target, message)
    │
    ├── li.hosts.routing.RoutingEngine (BusinessProcess)
    │   │
    │   ├── business_rule_name: str
    │   ├── validation: str
    │   ├── rule_logging: str
    │   ├── act_on_transform_error: bool
    │   ├── act_on_validation_error: bool
    │   │
    │   ├── Extension Points:
    │   │   ├── load_rules(rule_name) -> BusinessRuleSet
    │   │   ├── evaluate_rules(message) -> list[RuleResult]
    │   │   ├── apply_transform(message, transform) -> Message
    │   │   └── on_rule_match(rule, message)
    │   │
    │   ├── li.hosts.hl7.HL7RoutingEngine (RoutingEngine)
    │   │   └── LI Class: li.hosts.hl7.HL7RoutingEngine
    │   │   └── HL7-aware validation (d=doc, m=msg, z=allow-z)
    │   │
    │   └── li.hosts.routing.GenericRoutingEngine (RoutingEngine)
    │       └── LI Class: li.hosts.routing.GenericRoutingEngine
    │
    ├── li.hosts.orchestration.Orchestrator (BusinessProcess)
    │   │
    │   ├── Long-running workflow orchestration
    │   ├── State persistence
    │   └── Compensation/rollback support
    │
    └── li.hosts.CustomProcess (BusinessProcess)
        │
        ├── Base for user-defined processes
        │
        └── Extension Points:
            ├── on_request(message) -> Response   # MUST override
            └── on_complete(message, response)
```

**How to Extend:**
```python
# Create custom routing engine with special rules
class MyRoutingEngine(li.hosts.hl7.HL7RoutingEngine):
    def evaluate_rules(self, message):
        # Add custom rule evaluation
        results = super().evaluate_rules(message)
        results.extend(self.evaluate_custom_rules(message))
        return results

# Create custom BPL-style process
class E3BabyRegProcess(li.hosts.CustomProcess):
    def on_request(self, message):
        # Custom business logic
        baby_data = self.extract_baby_info(message)
        transformed = self.create_registration(baby_data)
        return self.send_request_async("to.BHR.ADT", transformed)
```

---

## 4. Business Operation Hierarchy (Outbound)

```
li.hosts.BusinessOperation (Host)
    │
    ├── archive_io: bool
    ├── failure_timeout: int
    ├── retry_interval: int
    ├── alert_on_error: bool
    ├── _adapter: OutboundAdapter
    │
    ├── Extension Points:
    │   ├── on_message(message) -> Response
    │   ├── on_before_send(message)
    │   ├── on_after_send(message, response)
    │   ├── on_send_error(message, error)
    │   ├── should_retry(message, error) -> bool
    │   └── transform_outbound(message) -> bytes
    │
    ├── li.hosts.hl7.HL7Operation (BusinessOperation)
    │   │
    │   ├── reply_code_actions: str
    │   │
    │   ├── Extension Points:
    │   │   ├── parse_ack(response) -> AckResult
    │   │   ├── evaluate_ack(ack) -> Action
    │   │   └── on_nack(message, ack)
    │   │
    │   ├── li.hosts.hl7.HL7TCPOperation
    │   │   └── Uses: MLLPOutboundAdapter
    │   │   └── LI Class: li.hosts.hl7.HL7TCPOperation
    │   │
    │   ├── li.hosts.hl7.HL7HTTPOperation
    │   │   └── Uses: HTTPOutboundAdapter
    │   │   └── LI Class: li.hosts.hl7.HL7HTTPOperation
    │   │
    │   └── li.hosts.hl7.HL7FileOperation
    │       └── Uses: FileOutboundAdapter
    │       └── LI Class: li.hosts.hl7.HL7FileOperation
    │
    ├── li.hosts.email.EmailAlertOperation (BusinessOperation)
    │   └── Uses: EmailOutboundAdapter
    │   └── LI Class: li.hosts.email.EmailAlertOperation
    │
    ├── li.hosts.recordmap.RecordMapBatchFileOperation (BusinessOperation)
    │   │
    │   ├── record_map: str
    │   ├── default_batch_class: str
    │   ├── rollover_limit: int
    │   │
    │   └── Uses: FileOutboundAdapter
    │       └── LI Class: li.hosts.recordmap.RecordMapBatchFileOperation
    │
    ├── li.hosts.soap.SOAPOperation (BusinessOperation)
    │   └── Uses: SOAPOutboundAdapter
    │   └── LI Class: li.hosts.soap.SOAPOperation
    │
    ├── li.hosts.rest.RESTOperation (BusinessOperation)
    │   └── Uses: HTTPOutboundAdapter
    │   └── LI Class: li.hosts.rest.RESTOperation
    │
    ├── li.hosts.database.DatabaseOperation (BusinessOperation)
    │   └── Uses: DatabaseOutboundAdapter
    │   └── LI Class: li.hosts.database.DatabaseOperation
    │
    └── li.hosts.kafka.KafkaOperation (BusinessOperation)
        └── Uses: KafkaOutboundAdapter
        └── LI Class: li.hosts.kafka.KafkaOperation
```

**How to Extend:**
```python
# Custom operation with special ACK handling
class MyHL7Operation(li.hosts.hl7.HL7TCPOperation):
    def evaluate_ack(self, ack):
        # Custom ACK evaluation
        if ack.get_field("MSA-1") == "CR":
            return self.handle_commit_reject(ack)
        return super().evaluate_ack(ack)

# Custom SOAP operation for specific web service
class PKBAcceptMessageOperation(li.hosts.soap.SOAPOperation):
    def on_message(self, message):
        # Transform to SOAP request
        soap_request = self.build_pkb_request(message)
        return super().on_message(soap_request)
```

---

## 5. Adapter Hierarchy

```
li.adapters.Adapter (ABC)
    │
    ├── settings: AdapterSettings
    ├── _connected: bool
    │
    ├── Extension Points:
    │   ├── on_init()
    │   ├── on_teardown()
    │   ├── on_connect()
    │   ├── on_disconnect()
    │   └── get_settings_schema() -> type[BaseModel]
    │
    ├── li.adapters.InboundAdapter (Adapter)
    │   │
    │   ├── on_data_received: Callback
    │   │
    │   ├── Extension Points:
    │   │   ├── start()
    │   │   ├── stop()
    │   │   ├── on_connection_opened(conn)
    │   │   ├── on_connection_closed(conn)
    │   │   └── read_message(conn) -> bytes
    │   │
    │   ├── li.adapters.tcp.TCPInboundAdapter
    │   │   │ Settings: Port, StayConnected, ReadTimeout, QSize, LocalInterface
    │   │   │
    │   │   ├── Extension Points:
    │   │   │   ├── handle_connection(reader, writer)
    │   │   │   ├── read_frame(reader) -> bytes
    │   │   │   └── write_frame(writer, data)
    │   │   │
    │   │   └── li.adapters.mllp.MLLPInboundAdapter
    │   │       └── Adds MLLP framing (0x0B...0x1C0x0D)
    │   │
    │   ├── li.adapters.http.HTTPInboundAdapter
    │   │   │ Settings: Port, Path, Methods, SSLConfig, MaxBodySize
    │   │   │
    │   │   └── Extension Points:
    │   │       ├── handle_request(request) -> response
    │   │       └── validate_request(request)
    │   │
    │   ├── li.adapters.file.FileInboundAdapter
    │   │   │ Settings: FilePath, FileSpec, ArchivePath, PollInterval
    │   │   │
    │   │   └── Extension Points:
    │   │       ├── scan_directory() -> list[Path]
    │   │       ├── read_file(path) -> bytes
    │   │       └── archive_file(path)
    │   │
    │   ├── li.adapters.ftp.FTPInboundAdapter
    │   │   └── Settings: Host, Port, Username, Password, Path
    │   │
    │   ├── li.adapters.kafka.KafkaInboundAdapter
    │   │   └── Settings: Brokers, Topic, GroupId
    │   │
    │   └── li.adapters.database.DatabaseInboundAdapter
    │       └── Settings: ConnectionString, Query, PollInterval
    │
    └── li.adapters.OutboundAdapter (Adapter)
        │
        ├── Extension Points:
        │   ├── connect()
        │   ├── disconnect()
        │   ├── send(data) -> response
        │   ├── on_send_success(data, response)
        │   └── on_send_failure(data, error)
        │
        ├── li.adapters.tcp.TCPOutboundAdapter
        │   │ Settings: IPAddress, Port, ConnectTimeout, ResponseTimeout,
        │   │           ReconnectRetry, StayConnected, LocalInterface, SSLConfig
        │   │
        │   ├── Extension Points:
        │   │   ├── create_connection() -> Connection
        │   │   ├── send_frame(conn, data)
        │   │   └── receive_frame(conn) -> bytes
        │   │
        │   └── li.adapters.mllp.MLLPOutboundAdapter
        │       └── Adds MLLP framing
        │
        ├── li.adapters.http.HTTPOutboundAdapter
        │   │ Settings: URL, Method, Headers, SSLConfig, Credentials
        │   │
        │   └── Extension Points:
        │       ├── build_request(data) -> Request
        │       └── parse_response(response) -> bytes
        │
        ├── li.adapters.file.FileOutboundAdapter
        │   │ Settings: FilePath, Overwrite, CreateDirectory
        │   │
        │   └── Extension Points:
        │       ├── generate_filename(message) -> str
        │       └── write_file(path, data)
        │
        ├── li.adapters.email.EmailOutboundAdapter
        │   └── Settings: SMTPServer, SMTPPort, From, Recipient, Cc, SSLConfig
        │
        ├── li.adapters.soap.SOAPOutboundAdapter
        │   └── Settings: WebServiceURL, SOAPAction, SSLConfig, Credentials
        │
        ├── li.adapters.ftp.FTPOutboundAdapter
        │   └── Settings: Host, Port, Username, Password, Path
        │
        ├── li.adapters.kafka.KafkaOutboundAdapter
        │   └── Settings: Brokers, Topic
        │
        └── li.adapters.database.DatabaseOutboundAdapter
            └── Settings: ConnectionString, InsertQuery
```

**How to Extend:**
```python
# Custom adapter with special framing
class MyFramingAdapter(li.adapters.tcp.TCPInboundAdapter):
    def read_frame(self, reader):
        # Custom framing protocol
        length = await reader.read(4)
        return await reader.read(int.from_bytes(length))

# Custom FTP adapter with SFTP support
class SFTPInboundAdapter(li.adapters.ftp.FTPInboundAdapter):
    def connect(self):
        # Use paramiko for SFTP
        self._client = paramiko.SFTPClient.from_transport(self._transport)
```

---

## 6. Message Class (Unified Raw-First Design)

**IMPORTANT ARCHITECTURAL DECISION:**

The LI Engine uses a **single unified Message class** that:
1. **Always holds raw bytes** as the authoritative data
2. **Schema is NOT embedded** in the message - it's a configuration on the Host
3. **Parsing is lazy** and done via the Host's configured schema
4. **Messages flow through the workflow as raw containers**

This matches IRIS where messages are raw streams and the `MessageSchemaCategory` setting on each Host determines how to parse them.

```
li.messages.Message
    │
    ├── id: UUID                           # Unique message ID
    ├── correlation_id: UUID               # Groups related messages
    ├── causation_id: UUID | None          # Parent message ID
    ├── created_at: datetime
    ├── source: str                        # Originating host name
    │
    ├── raw: bytes                         # THE AUTHORITATIVE DATA (never parsed eagerly)
    ├── content_type: str                  # MIME hint: "application/hl7-v2", "application/json"
    ├── original_filename: str | None      # For file-based messages
    │
    ├── metadata: dict[str, Any]           # Extensible metadata
    │
    ├── Methods:
    │   ├── get_raw() -> bytes             # Always available
    │   ├── as_text(encoding="utf-8") -> str
    │   ├── with_raw(new_raw) -> Message   # Create derived message with new raw
    │   ├── with_metadata(key, value) -> Message
    │   ├── serialize() -> bytes           # For persistence/transport
    │   └── deserialize(data) -> Message
    │
    └── NO PARSING METHODS HERE - Parsing is done by Host using its configured Schema
```

**Why no HL7Message, FHIRMessage, etc. subclasses?**

Because the **same raw bytes** might be parsed differently by different Hosts:
- Service A uses schema "PKB" 
- Router B uses schema "2.4" for validation
- Operation C doesn't parse at all, just forwards raw

The message itself doesn't know or care about schemas. **Schemas are Host configuration.**

---

## 7. Production = Configuration, Not Compiled Code

**CRITICAL ARCHITECTURAL PRINCIPLE:**

The LI Engine Production is **pure configuration** that is interpreted at runtime. There is NO compilation step. Items are created, started, stopped, and updated dynamically.

### 7.1 Production is Configuration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION = CONFIGURATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   production.xml / production.yaml / production.json                        │
│   ─────────────────────────────────────────────────────                     │
│   │                                                                          │
│   │  This is DATA, not CODE. It describes:                                  │
│   │  • What items exist (Services, Processes, Operations)                   │
│   │  • What class each item uses                                            │
│   │  • What settings each item has (including Schema)                       │
│   │  • How items connect (TargetConfigNames)                                │
│   │                                                                          │
│   │  The engine INTERPRETS this at runtime.                                 │
│   │  NO COMPILATION. NO CODE GENERATION.                                    │
│   │                                                                          │
│   ▼                                                                          │
│   ┌─────────────────┐                                                       │
│   │  ConfigLoader   │  ← Reads XML/YAML/JSON                                │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────┐                                                       │
│   │ ProductionConfig│  ← In-memory configuration object                     │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────┐                                                       │
│   │ProductionFactory│  ← Creates Host instances from config                 │
│   └────────┬────────┘    (looks up class in ClassRegistry)                  │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────┐                                                       │
│   │   Production    │  ← Running production with live Hosts                 │
│   │   (Runtime)     │                                                       │
│   └─────────────────┘                                                       │
│                                                                              │
│   At ANY time, you can:                                                     │
│   • Add new items (hot deploy)                                              │
│   • Remove items                                                            │
│   • Update item settings (including Schema)                                 │
│   • Enable/disable items                                                    │
│   • Change pool sizes                                                       │
│   WITHOUT restarting the engine or recompiling anything.                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Schema is Just a Host Setting

**Schema is NOT a special architectural concept.** It's simply a setting on the Host, just like Port or IPAddress:

```xml
<Item Name="from.BHR.ADT1" ClassName="li.hosts.hl7.HL7TCPService" PoolSize="1" Enabled="true">
  <!-- Adapter settings (protocol) -->
  <Setting Target="Adapter" Name="Port">35001</Setting>
  
  <!-- Host settings (business logic) -->
  <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>      <!-- Schema is just a setting! -->
  <Setting Target="Host" Name="TargetConfigNames">Main ADT Router</Setting>
  <Setting Target="Host" Name="AckMode">App</Setting>
</Item>

<Item Name="Main ADT Router" ClassName="li.hosts.hl7.HL7RoutingEngine" PoolSize="1" Enabled="true">
  <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.ADTGeneral</Setting>
  <Setting Target="Host" Name="ValidationSchema">PKB</Setting>           <!-- Router can use different schema -->
</Item>

<Item Name="to.ICNet.ADT" ClassName="li.hosts.hl7.HL7TCPOperation" PoolSize="1" Enabled="true">
  <Setting Target="Adapter" Name="IPAddress">10.124.117.13</Setting>
  <Setting Target="Adapter" Name="Port">24580</Setting>
  <!-- No schema needed - just forwards raw bytes -->
</Item>
```

### 7.3 How Hosts Use Schema (Internally)

The Host class uses its configured schema when it needs to parse:

```python
class HL7TCPService(BusinessService):
    """
    The schema is a HOST SETTING, accessed via self.host_settings.
    """
    
    def on_init(self):
        # Load schema from settings (lazy - only if configured)
        schema_name = self.host_settings.get("MessageSchemaCategory", "2.4")
        self._schema = SchemaRegistry.get(schema_name)
    
    def on_message_received(self, raw: bytes) -> Message:
        # Create raw message (NO PARSING)
        message = Message(raw=raw, content_type="application/hl7-v2", source=self.name)
        return message
    
    def generate_ack(self, message: Message, code: str) -> bytes:
        # NOW we parse - using our configured schema
        parsed = self._schema.parse(message.raw)
        return self._schema.create_ack(parsed, code)


class HL7RoutingEngine(RoutingEngine):
    """
    Router uses schema for validation and field access in rules.
    """
    
    def on_init(self):
        schema_name = self.host_settings.get("ValidationSchema", "2.4")
        self._schema = SchemaRegistry.get(schema_name)
    
    def evaluate_rules(self, message: Message) -> list[RuleResult]:
        # Parse with our schema for rule evaluation
        parsed = self._schema.parse(message.raw)
        
        # Rules access fields via parsed view
        for rule in self._rules:
            if rule.evaluate(parsed):  # Rule uses parsed.get_field("MSH-9.1")
                yield rule.execute(parsed)
```

### 7.4 Dynamic Item Management (No Compilation)

```python
# Runtime API - all dynamic, no compilation

# Start production from config
engine = ProductionEngine()
engine.load_config("production.xml")  # Just reads config, creates objects
engine.start()

# Hot-add new item at runtime
new_item_config = ItemConfig(
    name="to.NewSystem.ADT",
    class_name="li.hosts.hl7.HL7TCPOperation",
    pool_size=1,
    enabled=True,
    adapter_settings={"IPAddress": "10.0.0.1", "Port": 5000},
    host_settings={"ReplyCodeActions": ":?A=C,:*=S"}
)
engine.add_item(new_item_config)  # Instantly available, no restart

# Update existing item settings
engine.update_item_setting("from.BHR.ADT1", "Host", "MessageSchemaCategory", "CERNER2.3")

# Change pool size dynamically
engine.scale_item("Main ADT Router", pool_size=4)

# Enable/disable without restart
engine.disable_item("to.OldSystem.ADT")
engine.enable_item("to.NewSystem.ADT")
```

### 7.5 Class Registry Enables Dynamic Instantiation

The ClassRegistry is what makes this work - classes are looked up by name at runtime:

```python
class ProductionFactory:
    def create_host(self, item_config: ItemConfig) -> Host:
        # Look up class by name (string from config)
        host_class = ClassRegistry.get_host_class(item_config.class_name)
        
        # Instantiate with config
        host = host_class(
            name=item_config.name,
            adapter_settings=item_config.adapter_settings,
            host_settings=item_config.host_settings,
            pool_size=item_config.pool_size,
            # ... other settings
        )
        
        # Create adapter if host has one
        if host_class.adapter_class:
            adapter_class = ClassRegistry.get_adapter_class(host_class.adapter_class)
            host._adapter = adapter_class(settings=item_config.adapter_settings)
        
        return host
```

### 7.6 Summary: Configuration vs Code

| Aspect | Configuration (Data) | Code (Classes) |
|--------|---------------------|----------------|
| **Production XML/YAML** | ✅ What items exist, their settings | |
| **Item settings** | ✅ Schema, Port, IP, TargetConfigNames | |
| **Business Rules** | ✅ Routing rules, conditions, actions | |
| **Transforms** | ✅ DTL mappings | |
| **Host classes** | | ✅ `HL7TCPService`, `HL7RoutingEngine` |
| **Adapter classes** | | ✅ `MLLPInboundAdapter` |
| **Schema definitions** | ✅ PKB.HL7 XML files | |
| **Custom processes** | | ✅ User extends `CustomProcess` |

**The engine never compiles configuration.** It interprets it at runtime and creates/manages objects dynamically.

---

## 8. Rules & Transform Hierarchy

```
li.rules.BusinessRuleSet
    │
    ├── name: str
    ├── rules: list[BusinessRule]
    │
    ├── Extension Points:
    │   ├── load(name) -> BusinessRuleSet
    │   ├── evaluate(message) -> list[RuleResult]
    │   └── add_rule(rule)
    │
    └── li.rules.BusinessRule
        │
        ├── name: str
        ├── conditions: list[RuleCondition]
        ├── actions: list[RuleAction]
        ├── enabled: bool
        │
        └── Extension Points:
            ├── evaluate(message) -> bool
            └── execute(message) -> RuleResult


li.rules.conditions.RuleCondition (ABC)
    │
    ├── Extension Points:
    │   └── evaluate(context) -> bool
    │
    ├── li.rules.conditions.FieldCondition
    │   └── field, operator, value
    │
    ├── li.rules.conditions.ExpressionCondition
    │   └── expression (Python expression)
    │
    ├── li.rules.conditions.RegexCondition
    │   └── field, pattern
    │
    ├── li.rules.conditions.LookupCondition
    │   └── field, lookup_table, key_field
    │
    └── li.rules.conditions.CompositeCondition
        └── conditions, logic (AND/OR/NOT)


li.rules.actions.RuleAction (ABC)
    │
    ├── Extension Points:
    │   └── execute(context, result)
    │
    ├── li.rules.actions.SendAction
    │   └── target, transform
    │
    ├── li.rules.actions.TransformAction
    │   └── transform_name
    │
    ├── li.rules.actions.AssignAction
    │   └── property, value
    │
    ├── li.rules.actions.DeleteAction
    │
    ├── li.rules.actions.AlertAction
    │   └── alert_text, severity
    │
    └── li.rules.actions.CodeAction
        └── code (Python code block)


li.transforms.Transform (ABC)
    │
    ├── Extension Points:
    │   ├── apply(source) -> Message
    │   └── validate(source)
    │
    ├── li.transforms.DTLTransform
    │   │
    │   ├── source_class: str
    │   ├── target_class: str
    │   ├── mappings: list[FieldMapping]
    │   │
    │   └── Extension Points:
    │       ├── map_field(source, target, mapping)
    │       └── evaluate_expression(expr, source)
    │
    ├── li.transforms.XSLTTransform
    │   └── stylesheet: str
    │
    ├── li.transforms.PythonTransform
    │   └── script_path, function_name
    │
    └── li.transforms.TemplateTransform
        └── template: str (Jinja2)
```

**How to Extend:**
```python
# Custom condition type
class DateRangeCondition(li.rules.conditions.RuleCondition):
    def __init__(self, field, start_date, end_date):
        self.field = field
        self.start_date = start_date
        self.end_date = end_date
    
    def evaluate(self, context):
        value = context.message.get_field(self.field)
        date = parse_date(value)
        return self.start_date <= date <= self.end_date

# Custom action type
class WebhookAction(li.rules.actions.RuleAction):
    def __init__(self, url, method="POST"):
        self.url = url
        self.method = method
    
    def execute(self, context, result):
        requests.request(self.method, self.url, json=context.message.to_dict())
```

---

## 8. Utility Classes

```
li.utils.Credentials
    │
    ├── id: str
    ├── username: str
    ├── password: str (encrypted)
    │
    └── Methods: get(name), encrypt(), decrypt()


li.utils.SSLConfig
    │
    ├── name: str
    ├── certificate_file: str
    ├── private_key_file: str
    ├── ca_file: str
    ├── verify_peer: bool
    │
    └── Methods: get(name), get_ssl_context()


li.utils.Lookup
    │
    ├── name: str
    ├── data: dict[str, str]
    │
    └── Methods: get(key), reverse_get(value), reload()


li.utils.Schedule
    │
    ├── spec: str
    │
    └── Methods: is_active(at), next_start(after), next_stop(after)


li.utils.SequenceManager
    │
    ├── Handles message sequencing and deduplication
    │
    └── Methods: get_next(), check_duplicate(), resequence()


li.utils.Archive
    │
    ├── Handles message archiving
    │
    └── Methods: archive(message, direction), retrieve(id)
```

---

## 9. Class Registry & Factory

```
li.registry.ClassRegistry
    │
    ├── _hosts: dict[str, type[Host]]
    ├── _adapters: dict[str, type[Adapter]]
    ├── _messages: dict[str, type[Message]]
    ├── _transforms: dict[str, type[Transform]]
    ├── _rules: dict[str, type[BusinessRuleSet]]
    ├── _conditions: dict[str, type[RuleCondition]]
    ├── _actions: dict[str, type[RuleAction]]
    │
    ├── Methods:
    │   ├── register_host(class_name, host_class)
    │   ├── register_adapter(class_name, adapter_class)
    │   ├── register_message(class_name, message_class)
    │   ├── register_transform(class_name, transform_class)
    │   ├── register_condition(name, condition_class)
    │   ├── register_action(name, action_class)
    │   │
    │   ├── get_host_class(class_name) -> type[Host]
    │   ├── get_adapter_class(class_name) -> type[Adapter]
    │   └── list_registered() -> dict
    │
    └── Built-in Registrations:
        # Services
        "li.hosts.hl7.HL7TCPService"
        "li.hosts.hl7.HL7HTTPService"
        "li.hosts.hl7.HL7FileService"
        "li.hosts.fhir.FHIRHTTPService"
        
        # Processes
        "li.hosts.hl7.HL7RoutingEngine"
        "li.hosts.routing.GenericRoutingEngine"
        "li.hosts.CustomProcess"
        
        # Operations
        "li.hosts.hl7.HL7TCPOperation"
        "li.hosts.hl7.HL7FileOperation"
        "li.hosts.email.EmailAlertOperation"
        "li.hosts.recordmap.RecordMapBatchFileOperation"
        "li.hosts.soap.SOAPOperation"
        "li.hosts.rest.RESTOperation"
        "li.hosts.database.DatabaseOperation"
        
        # Adapters
        "li.adapters.mllp.MLLPInboundAdapter"
        "li.adapters.mllp.MLLPOutboundAdapter"
        "li.adapters.http.HTTPInboundAdapter"
        "li.adapters.http.HTTPOutboundAdapter"
        "li.adapters.file.FileInboundAdapter"
        "li.adapters.file.FileOutboundAdapter"
        "li.adapters.email.EmailOutboundAdapter"


li.factory.ProductionFactory
    │
    ├── Methods:
    │   ├── create_production(config) -> Production
    │   ├── create_host(item_config) -> Host
    │   ├── create_adapter(host) -> Adapter
    │   └── create_from_xml(xml_path) -> Production  # Import legacy configs
    │
    └── Extension Points:
        ├── on_before_create_host(config)
        ├── on_after_create_host(host)
        └── resolve_class_name(name) -> str  # Alias resolution
```

**How to Register Custom Classes:**
```python
from li.registry import ClassRegistry

# Register custom host
ClassRegistry.register_host(
    "mycompany.hosts.MyCustomService",
    MyCustomService
)

# Register custom adapter
ClassRegistry.register_adapter(
    "mycompany.adapters.MyProtocolAdapter",
    MyProtocolAdapter
)

# Register custom condition
ClassRegistry.register_condition(
    "DateRange",
    DateRangeCondition
)

# Now usable in configuration:
# <Item ClassName="mycompany.hosts.MyCustomService" ...>
```

---

## 10. Runtime Engine

```
li.engine.ProductionEngine
    │
    ├── production: Production
    ├── process_manager: ProcessManager
    ├── queue_manager: QueueManager
    ├── scheduler: Scheduler
    ├── metrics: MetricsCollector
    │
    ├── Extension Points:
    │   ├── on_start()
    │   ├── on_stop()
    │   ├── on_host_error(host, error)
    │   └── on_message_routed(message, from_host, to_host)
    │
    └── Methods: start(), stop(), scale_host(), get_metrics(), health_check()


li.engine.ProcessManager
    │
    ├── pools: dict[str, ProcessPool]
    │
    ├── Extension Points:
    │   ├── create_pool(host, size) -> ProcessPool
    │   └── on_worker_error(worker, error)
    │
    └── Methods: start_pool(), stop_pool(), scale_pool(), get_pool_status()


li.engine.ProcessPool (ABC)
    │
    ├── host: Host
    ├── pool_size: int
    ├── workers: list[Worker]
    │
    ├── Implementations:
    │   ├── li.engine.AsyncWorkerPool      # asyncio tasks
    │   ├── li.engine.ThreadPool           # threading
    │   └── li.engine.MultiProcessPool     # multiprocessing
    │
    └── Extension Points:
        ├── create_worker() -> Worker
        ├── on_worker_started(worker)
        └── on_worker_stopped(worker)


li.engine.QueueManager
    │
    ├── queues: dict[str, Queue]
    │
    ├── Extension Points:
    │   ├── create_queue(name, config) -> Queue
    │   └── on_message_queued(queue, message)
    │
    └── Methods: create_queue(), get_queue(), route_message()


li.engine.Queue (ABC)
    │
    ├── name: str
    ├── persistent: bool
    ├── max_size: int
    │
    ├── Implementations:
    │   ├── li.engine.MemoryQueue          # In-memory (fast, non-persistent)
    │   ├── li.engine.RedisQueue           # Redis-backed
    │   ├── li.engine.PostgresQueue        # PostgreSQL-backed
    │   └── li.engine.KafkaQueue           # Kafka-backed
    │
    └── Methods: put(), get(), ack(), nack(), peek(), size()


li.engine.Scheduler
    │
    ├── schedules: dict[str, ScheduleEntry]
    │
    └── Methods: register(), unregister(), is_active(), next_run()
```

**How to Extend:**
```python
# Custom queue implementation
class RabbitMQQueue(li.engine.Queue):
    def __init__(self, name, connection_url):
        super().__init__(name)
        self._connection = pika.connect(connection_url)
    
    def put(self, message):
        self._channel.basic_publish(exchange='', routing_key=self.name, body=message.serialize())

# Custom process pool
class KubernetesPool(li.engine.ProcessPool):
    def create_worker(self):
        # Spawn Kubernetes pod
        return KubernetesWorker(self.host)
```

---

## 11. Configuration Schema

```
li.config.ProductionConfig
    │
    ├── name: str
    ├── testing_enabled: bool
    ├── log_general_trace_events: bool
    ├── actor_pool_size: int
    ├── items: list[ItemConfig]
    │
    └── Formats: XML, JSON, YAML


li.config.ItemConfig
    │
    ├── name: str
    ├── class_name: str
    ├── category: str
    ├── pool_size: int
    ├── enabled: bool
    ├── foreground: bool
    ├── log_trace_events: bool
    ├── schedule: str
    ├── comment: str
    ├── settings: list[SettingConfig]
    │
    └── li.config.SettingConfig
        ├── target: str ("Adapter" | "Host")
        ├── name: str
        └── value: str


li.config.ConfigLoader
    │
    ├── Methods:
    │   ├── load_xml(path) -> ProductionConfig
    │   ├── load_json(path) -> ProductionConfig
    │   ├── load_yaml(path) -> ProductionConfig
    │   └── validate(config) -> list[Error]
    │
    └── Extension Points:
        └── parse_custom_format(data) -> ProductionConfig
```

---

## 12. Validation: Can This Design Run the Production?

**Mapping for BHRUH.Production.ADTProdudction:**

| Production Item | LI Class | Extensible At |
|-----------------|----------|---------------|
| `EnsLib.HL7.Service.TCPService` | `li.hosts.hl7.HL7TCPService` | Service, HL7Service, Host |
| `EnsLib.HL7.Operation.TCPOperation` | `li.hosts.hl7.HL7TCPOperation` | Operation, HL7Operation, Host |
| `EnsLib.HL7.Operation.FileOperation` | `li.hosts.hl7.HL7FileOperation` | Operation, HL7Operation, Host |
| `EnsLib.HL7.MsgRouter.RoutingEngine` | `li.hosts.hl7.HL7RoutingEngine` | RoutingEngine, Process, Host |
| `EnsLib.MsgRouter.RoutingEngine` | `li.hosts.routing.GenericRoutingEngine` | RoutingEngine, Process, Host |
| `EnsLib.EMail.AlertOperation` | `li.hosts.email.EmailAlertOperation` | Operation, Host |
| `EnsLib.RecordMap.Operation.BatchFileOperation` | `li.hosts.recordmap.RecordMapBatchFileOperation` | Operation, Host |
| `BHRUH.Process.*` (Custom) | Extend `li.hosts.CustomProcess` | CustomProcess, Process, Host |
| `BHRUH.PKB.Operation.*` (SOAP) | Extend `li.hosts.soap.SOAPOperation` | SOAPOperation, Operation, Host |

**All 100+ items can be mapped. Users can extend at ANY hierarchy level.**

---

## Summary

The LI (Lightweight Integration) Engine class hierarchy provides:

1. **Complete Host Hierarchy**: Services, Processes, Operations with clear extension points
2. **Adapter Separation**: Protocol handling isolated, fully extensible
3. **Message Classes**: HL7, FHIR, XML, JSON, custom - all extensible
4. **Rules Engine**: Conditions, Actions, Transforms - all extensible
5. **Class Registry**: Dynamic registration of custom classes at runtime
6. **Runtime Engine**: Configurable pools, queues, schedulers - all extensible
7. **No Hardcoding**: Everything configurable via XML/JSON/YAML

**Every class is designed for extension. Users can:**
- Extend at any hierarchy level (Host → BusinessService → HL7Service → HL7TCPService)
- Register custom classes in the registry
- Override any hook/extension point
- Add custom adapters, messages, conditions, actions, transforms

---

## 13. Schema-Driven Lazy Parsing System

### Design Philosophy: Raw-First, Parse-on-Demand

The LI Engine follows a **lazy parsing** approach where:
1. **Messages are always stored and transported as raw bytes/streams**
2. **Parsing only occurs when explicitly requested**
3. **Schemas are decoupled from messages** - any schema can be applied to any raw data
4. **Multiple schemas can parse the same raw data** differently
5. **Schemas are configurable and extensible** - users can define custom schemas

This matches the IRIS approach where HL7 messages flow through the system as raw MLLP streams and are only parsed when a routing rule or transform needs to access a specific field.

### 13.1 Stream/Container Hierarchy

```
li.streams.Stream (ABC)
    │
    ├── raw: bytes                         # The authoritative raw data
    ├── content_type: str                  # MIME type hint
    ├── encoding: str                      # Character encoding (utf-8, etc.)
    ├── size: int                          # Size in bytes
    │
    ├── Extension Points:
    │   ├── read() -> bytes
    │   ├── read_chunk(size) -> bytes
    │   ├── seek(position)
    │   └── as_text() -> str
    │
    ├── li.streams.ByteStream
    │   └── In-memory bytes
    │
    ├── li.streams.FileStream
    │   └── File-backed stream (for large messages)
    │
    └── li.streams.ChunkedStream
        └── Streaming/chunked data


li.messages.MessageContainer
    │
    ├── id: UUID
    ├── correlation_id: UUID
    ├── causation_id: UUID | None
    ├── created_at: datetime
    ├── source: str
    │
    ├── stream: Stream                     # RAW DATA - always preserved
    ├── content_type: str                  # "application/hl7-v2", "application/fhir+json", etc.
    │
    ├── _parsed_cache: dict[str, ParsedView]  # Lazy-loaded parsed views
    │
    ├── Methods:
    │   ├── get_raw() -> bytes             # Always returns raw data
    │   ├── as_text() -> str               # Decode as text
    │   │
    │   ├── parse(schema: Schema) -> ParsedView      # Parse with specific schema
    │   ├── parse_as(schema_name: str) -> ParsedView # Parse by schema name
    │   │
    │   ├── get_field(path: str, schema: Schema = None) -> Any  # Lazy field access
    │   └── set_field(path: str, value: Any, schema: Schema) -> MessageContainer
    │
    └── Extension Points:
        ├── on_parse(schema)               # Hook before parsing
        └── on_field_access(path, schema)  # Hook on field access
```

### 13.2 Schema Hierarchy

```
li.schemas.Schema (ABC)
    │
    ├── name: str                          # "PKB", "2.4", "FHIR_R4"
    ├── base: str | None                   # Parent schema (inheritance)
    ├── version: str
    │
    ├── Extension Points:
    │   ├── parse(raw: bytes) -> ParsedView
    │   ├── validate(parsed: ParsedView) -> list[ValidationError]
    │   ├── serialize(parsed: ParsedView) -> bytes
    │   └── get_field(parsed: ParsedView, path: str) -> Any
    │
    ├── li.schemas.hl7.HL7Schema (Schema)
    │   │
    │   ├── category: str                  # "PKB", "2.4", "CERNER2.3"
    │   ├── base_category: str             # "CANCERREG2.4", "2.4"
    │   ├── message_types: dict[str, MessageTypeDefinition]
    │   ├── message_structures: dict[str, MessageStructureDefinition]
    │   ├── segment_structures: dict[str, SegmentStructureDefinition]
    │   ├── data_types: dict[str, DataTypeDefinition]
    │   ├── code_tables: dict[str, CodeTableDefinition]
    │   │
    │   ├── Methods:
    │   │   ├── get_message_type(name) -> MessageTypeDefinition
    │   │   ├── get_structure(name) -> MessageStructureDefinition
    │   │   ├── get_segment(name) -> SegmentStructureDefinition
    │   │   ├── parse_segment(raw, segment_name) -> HL7Segment
    │   │   └── create_ack(message, code) -> bytes
    │   │
    │   └── Built-in schemas:
    │       ├── li.schemas.hl7.HL7v2_3
    │       ├── li.schemas.hl7.HL7v2_4
    │       ├── li.schemas.hl7.HL7v2_5
    │       └── (User-defined: PKB, CERNER2.3, etc.)
    │
    ├── li.schemas.fhir.FHIRSchema (Schema)
    │   │
    │   ├── version: str                   # "R4", "STU3"
    │   ├── profiles: dict[str, ProfileDefinition]
    │   ├── resource_types: dict[str, ResourceDefinition]
    │   │
    │   └── Built-in schemas:
    │       ├── li.schemas.fhir.FHIR_R4
    │       └── li.schemas.fhir.FHIR_STU3
    │
    ├── li.schemas.xml.XMLSchema (Schema)
    │   │
    │   ├── xsd_path: str                  # XSD file path
    │   ├── namespaces: dict[str, str]
    │   │
    │   └── Methods:
    │       ├── xpath(parsed, path) -> Any
    │       └── validate_xsd(parsed) -> list[Error]
    │
    ├── li.schemas.json.JSONSchema (Schema)
    │   │
    │   ├── json_schema: dict              # JSON Schema definition
    │   │
    │   └── Methods:
    │       ├── json_path(parsed, path) -> Any
    │       └── validate_schema(parsed) -> list[Error]
    │
    ├── li.schemas.csv.CSVSchema (Schema)
    │   │
    │   ├── delimiter: str
    │   ├── headers: list[str]
    │   ├── column_types: dict[str, type]
    │   │
    │   └── RecordMap equivalent
    │
    ├── li.schemas.binary.BinarySchema (Schema)
    │   │
    │   ├── Fixed-format binary parsing
    │   ├── field_definitions: list[BinaryFieldDef]
    │   │
    │   └── Methods:
    │       ├── unpack(raw) -> dict
    │       └── pack(data) -> bytes
    │
    └── li.schemas.custom.CustomSchema (Schema)
        │
        └── User-defined schema with custom parser
```

### 13.3 HL7 Schema Definition (from your PKB example)

```
li.schemas.hl7.definitions.MessageTypeDefinition
    │
    ├── name: str                          # "ADT_A01"
    ├── structure: str                     # "ADT_A01" (reference to MessageStructure)
    ├── return_type: str                   # "base:ACK_A01"
    ├── description: str
    │
    └── Example from PKB schema:
        MessageTypeDefinition(
            name="ADT_A01",
            structure="ADT_A01",
            return_type="base:ACK_A01",
            description="ADT message - Admit / visit notification"
        )


li.schemas.hl7.definitions.MessageStructureDefinition
    │
    ├── name: str                          # "ADT_A01"
    ├── definition: str                    # "MSH~base:EVN~PID~PV1"
    ├── description: str
    │
    ├── Syntax:
    │   ├── ~     = Segment separator
    │   ├── [~X~] = Optional segment
    │   ├── {~X~} = Repeating segment
    │   ├── base: = Reference to base schema
    │
    └── Example from PKB schema:
        MessageStructureDefinition(
            name="SIU_S12",
            definition="MSH~PID~SCH~[~NTE~]~[~PV1~]~[~[~RGS~]~[~{~AIP~}~]~]~[~ZAP~]",
            description="Schedule information unsolicited"
        )


li.schemas.hl7.definitions.SegmentStructureDefinition
    │
    ├── name: str                          # "PID", "MSH", "ZAP"
    ├── description: str
    ├── fields: list[SegmentFieldDefinition]
    │
    └── li.schemas.hl7.definitions.SegmentFieldDefinition
        │
        ├── piece: int                     # Field position (1-based)
        ├── description: str
        ├── datatype: str | None           # "base:CX", "base:XPN"
        ├── max_length: int
        ├── required: str                  # "R", "O", "X", "C", "B"
        ├── repeating: bool
        ├── repeat_count: int | None
        ├── code_table: str | None         # "base:1", "base:4"
        ├── symbol: str | None             # "!", "+", "*", "?", "&"
        │
        └── Example from PKB schema (PID-3):
            SegmentFieldDefinition(
                piece=3,
                description="Patient Identifier List",
                datatype="base:CX",
                symbol="+",
                max_length=250,
                required="R",
                repeating=True
            )


li.schemas.hl7.definitions.DataTypeDefinition
    │
    ├── name: str                          # "CX", "XPN", "TS"
    ├── components: list[ComponentDefinition]
    │
    └── Example: CX (Extended Composite ID)
        DataTypeDefinition(
            name="CX",
            components=[
                ComponentDefinition(1, "ID Number"),
                ComponentDefinition(2, "Check Digit"),
                ComponentDefinition(3, "Check Digit Scheme"),
                ComponentDefinition(4, "Assigning Authority"),
                ComponentDefinition(5, "Identifier Type Code"),
                ...
            ]
        )
```

### 13.4 Parsed View Hierarchy

```
li.schemas.ParsedView (ABC)
    │
    ├── schema: Schema                     # Schema used for parsing
    ├── raw: bytes                         # Original raw data (reference)
    ├── _cache: dict                       # Cached parsed elements
    │
    ├── Extension Points:
    │   ├── get_field(path: str) -> Any
    │   ├── set_field(path: str, value: Any) -> ParsedView
    │   ├── validate() -> list[ValidationError]
    │   └── serialize() -> bytes
    │
    ├── li.schemas.hl7.HL7ParsedView (ParsedView)
    │   │
    │   ├── message_type: str              # "ADT_A01"
    │   ├── _segments: dict[str, list[HL7SegmentView]]  # Lazy-loaded
    │   │
    │   ├── Methods:
    │   │   ├── get_segment(name, index=0) -> HL7SegmentView
    │   │   ├── get_segments(name) -> list[HL7SegmentView]
    │   │   ├── get_field(path) -> str     # "PID-3.1", "MSH-9.1"
    │   │   ├── set_field(path, value) -> HL7ParsedView
    │   │   └── create_ack(code) -> bytes
    │   │
    │   └── li.schemas.hl7.HL7SegmentView
    │       │
    │       ├── name: str                  # "PID", "MSH"
    │       ├── raw: str                   # Raw segment string
    │       ├── _fields: list[str]         # Lazy-parsed fields
    │       │
    │       └── Methods:
    │           ├── get_field(index) -> str
    │           ├── get_component(field, component) -> str
    │           ├── get_subcomponent(field, component, sub) -> str
    │           └── get_repetition(field, rep) -> str
    │
    ├── li.schemas.fhir.FHIRParsedView (ParsedView)
    │   │
    │   ├── resource_type: str
    │   ├── resource: dict                 # Parsed JSON
    │   │
    │   └── Methods:
    │       ├── get_path(fhir_path) -> Any
    │       └── set_path(fhir_path, value) -> FHIRParsedView
    │
    ├── li.schemas.xml.XMLParsedView (ParsedView)
    │   │
    │   ├── document: ElementTree
    │   │
    │   └── Methods:
    │       ├── xpath(path) -> Any
    │       └── set_xpath(path, value) -> XMLParsedView
    │
    └── li.schemas.json.JSONParsedView (ParsedView)
        │
        ├── data: dict
        │
        └── Methods:
            ├── json_path(path) -> Any
            └── set_json_path(path, value) -> JSONParsedView
```

### 13.5 Schema Registry & Loader

```
li.schemas.SchemaRegistry
    │
    ├── _schemas: dict[str, Schema]
    ├── _schema_paths: dict[str, Path]     # For lazy loading
    │
    ├── Methods:
    │   ├── register(name, schema)
    │   ├── register_from_file(name, path)
    │   ├── get(name) -> Schema
    │   ├── load(name) -> Schema           # Lazy load from file
    │   ├── list_schemas() -> list[str]
    │   └── resolve_base(schema) -> Schema # Resolve inheritance
    │
    └── Built-in registrations:
        "2.3"           → HL7v2_3
        "2.4"           → HL7v2_4
        "2.5"           → HL7v2_5
        "FHIR_R4"       → FHIR_R4
        "FHIR_STU3"     → FHIR_STU3
        # User registers custom:
        "PKB"           → PKB schema (extends CANCERREG2.4)
        "CERNER2.3"     → Cerner custom schema


li.schemas.SchemaLoader
    │
    ├── Methods:
    │   ├── load_hl7_schema(xml_path) -> HL7Schema
    │   ├── load_fhir_schema(json_path) -> FHIRSchema
    │   ├── load_json_schema(path) -> JSONSchema
    │   ├── load_xsd_schema(path) -> XMLSchema
    │   └── load_custom_schema(path, parser_class) -> CustomSchema
    │
    └── Extension Points:
        └── parse_schema_definition(data) -> Schema
```

### 13.6 Lazy Parsing in Action

```python
# Example: Message flows through system as raw bytes

# 1. Adapter receives raw MLLP data
raw_data = adapter.receive()  # bytes: b'\x0bMSH|^~\\&|...\x1c\x0d'

# 2. Create MessageContainer (NO PARSING YET)
message = MessageContainer(
    stream=ByteStream(raw_data),
    content_type="application/hl7-v2"
)

# 3. Message routes through workflow as raw container
await router.route(message)  # Still raw bytes

# 4. Only parse when needed (e.g., in routing rule)
class MyRoutingRule(RuleCondition):
    def evaluate(self, context):
        # NOW we parse - lazily, on demand
        parsed = context.message.parse_as("PKB")  # or "2.4", "CERNER2.3"
        
        # Access field - segment parsed on demand
        msg_type = parsed.get_field("MSH-9.1")  # "ADT"
        trigger = parsed.get_field("MSH-9.2")   # "A01"
        
        return msg_type == "ADT" and trigger == "A01"

# 5. Different schemas can parse same raw data
parsed_pkb = message.parse_as("PKB")           # PKB schema view
parsed_std = message.parse_as("2.4")           # Standard 2.4 view
# Both work on same raw bytes!

# 6. Transform can use schema to modify
class MyTransform(Transform):
    def apply(self, message):
        parsed = message.parse_as("PKB")
        
        # Modify field
        new_parsed = parsed.set_field("PID-5.1", "SMITH")
        
        # Serialize back to raw bytes
        new_raw = new_parsed.serialize()
        
        return message.with_raw(new_raw)
```

### 13.7 Schema Inheritance

```
# PKB schema extends CANCERREG2.4 which extends 2.4

li.schemas.hl7.HL7Schema
    │
    ├── name: "2.4"
    ├── base: None
    ├── (Standard HL7 2.4 definitions)
    │
    └── li.schemas.hl7.HL7Schema
        │
        ├── name: "CANCERREG2.4"
        ├── base: "2.4"                    # Inherits from 2.4
        ├── (Cancer registry extensions)
        │
        └── li.schemas.hl7.HL7Schema
            │
            ├── name: "PKB"
            ├── base: "CANCERREG2.4"       # Inherits from CANCERREG2.4
            ├── (PKB-specific segments: ZAP, ZRX, ZSC, ZTM)
            ├── (PKB-specific message types)
            └── (PKB-specific structures)


# Resolution: When parsing with "PKB" schema:
# 1. Look for segment in PKB → found? use it
# 2. Not found? Look in CANCERREG2.4 → found? use it
# 3. Not found? Look in 2.4 (base) → found? use it
# 4. Not found? Unknown segment
```

### 13.8 How to Define Custom Schema

```python
# Option 1: Load from XML (like IRIS)
schema = SchemaLoader.load_hl7_schema("path/to/PKB.HL7")
SchemaRegistry.register("PKB", schema)

# Option 2: Define programmatically
from li.schemas.hl7 import HL7Schema, MessageTypeDefinition, SegmentStructureDefinition

pkb_schema = HL7Schema(
    name="PKB",
    base="CANCERREG2.4",
    message_types={
        "ADT_A01": MessageTypeDefinition(
            name="ADT_A01",
            structure="ADT_A01",
            return_type="base:ACK_A01",
            description="ADT message - Admit / visit notification"
        ),
        # ... more message types
    },
    segment_structures={
        "ZAP": SegmentStructureDefinition(
            name="ZAP",
            description="Partner Management URL",
            fields=[
                SegmentFieldDefinition(piece=1, description="External Management URL", max_length=1000)
            ]
        ),
        # ... more segments
    }
)

SchemaRegistry.register("PKB", pkb_schema)

# Option 3: Extend existing schema
class MyCustomSchema(HL7Schema):
    def __init__(self):
        super().__init__(name="MyCustom", base="2.4")
        self.add_segment("ZMY", my_segment_def)
        self.add_message_type("ADT_ZMY", my_message_type)
```

### 13.9 Integration with Host Settings

```xml
<!-- In production config, specify schema per service -->
<Item Name="from.BHR.ADT1" ClassName="li.hosts.hl7.HL7TCPService">
  <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>
  <Setting Target="Host" Name="TargetConfigNames">Main ADT Router</Setting>
</Item>

<!-- Router can use different schema for validation -->
<Item Name="Main ADT Router" ClassName="li.hosts.hl7.HL7RoutingEngine">
  <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.ADTGeneral</Setting>
  <Setting Target="Host" Name="ValidationSchema">PKB</Setting>
</Item>
```

### 13.10 Summary: Raw-First Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LI RAW-FIRST ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   INBOUND                    WORKFLOW                      OUTBOUND          │
│   ────────                   ────────                      ────────          │
│                                                                              │
│   ┌─────────┐               ┌─────────┐                   ┌─────────┐       │
│   │ Adapter │──raw bytes──▶│ Service │──MessageContainer─▶│ Router  │       │
│   │ (MLLP)  │               │         │   (still raw)     │         │       │
│   └─────────┘               └─────────┘                   └────┬────┘       │
│                                                                 │            │
│                                                                 │            │
│                                    ┌────────────────────────────┘            │
│                                    │                                         │
│                                    ▼                                         │
│                              ┌───────────┐                                   │
│                              │  Rule     │◀── parse_as("PKB")               │
│                              │ Evaluate  │    (LAZY PARSE)                   │
│                              └─────┬─────┘                                   │
│                                    │                                         │
│                                    ▼                                         │
│                              ┌───────────┐                                   │
│                              │ Transform │◀── modify fields                  │
│                              │           │    serialize back                 │
│                              └─────┬─────┘                                   │
│                                    │                                         │
│                                    ▼                                         │
│   ┌─────────┐               ┌───────────┐                                   │
│   │ Adapter │◀──raw bytes──│ Operation │◀── MessageContainer                │
│   │ (MLLP)  │               │           │    (raw or modified)              │
│   └─────────┘               └───────────┘                                   │
│                                                                              │
│   KEY: Messages flow as RAW BYTES. Parsing is LAZY and ON-DEMAND.           │
│        Schemas are DECOUPLED - any schema can parse any raw data.           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Enterprise Production Decisions (Pre-Implementation Checklist)

Before implementing, the following architectural decisions must be finalized for a **production-grade NHS Acute Hospital Trust integration engine**:

### 14.1 Message Persistence & Recovery

**Decision Required:** How do we ensure no message loss?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MESSAGE PERSISTENCE OPTIONS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Option A: Write-Ahead Log (WAL) - RECOMMENDED                             │
│   ─────────────────────────────────────────────                             │
│   • Every message written to persistent log BEFORE processing               │
│   • On crash recovery, replay uncommitted messages                          │
│   • Similar to Kafka's approach                                             │
│   • Storage: PostgreSQL, SQLite, or dedicated log files                     │
│                                                                              │
│   Option B: Queue-Based Persistence                                         │
│   ─────────────────────────────────────────                                 │
│   • Use persistent queue (Redis with AOF, PostgreSQL, RabbitMQ)             │
│   • Messages stay in queue until ACKed by downstream                        │
│                                                                              │
│   Option C: Hybrid (WAL + Queue)                                            │
│   ─────────────────────────────────────                                     │
│   • WAL for audit/replay                                                    │
│   • Queue for routing                                                       │
│                                                                              │
│   DECISION: _______________                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Recommendation:** Option C (Hybrid) - WAL for compliance/audit, Queue for routing.

### 14.2 Queue Implementation

**Decision Required:** What backs the message queues?

| Option | Pros | Cons | Use Case |
|--------|------|------|----------|
| **In-Memory (asyncio.Queue)** | Fast, simple | Lost on crash | Dev/test only |
| **Redis** | Fast, persistent (AOF), pub/sub | External dependency | Good default |
| **PostgreSQL** | ACID, already have it | Slower than Redis | Compliance-heavy |
| **Kafka** | Massive scale, replay | Complex, overkill? | Very high volume |
| **SQLite** | Simple, embedded | Single-writer | Small deployments |

**Recommendation:** Redis as default, PostgreSQL for audit trail, configurable per-queue.

### 14.3 Process/Thread Model

**Decision Required:** How do we achieve PoolSize concurrency?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONCURRENCY MODEL OPTIONS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Option A: Pure Asyncio (Single Process, Async Workers)                    │
│   ─────────────────────────────────────────────────────                     │
│   • PoolSize = number of concurrent asyncio tasks                           │
│   • Best for I/O-bound work (network, file)                                 │
│   • Simple, no IPC overhead                                                 │
│   • GIL not an issue for I/O                                                │
│                                                                              │
│   Option B: Thread Pool                                                     │
│   ─────────────────────────────────────────                                 │
│   • PoolSize = number of threads                                            │
│   • Good for blocking I/O libraries                                         │
│   • GIL limits CPU parallelism                                              │
│                                                                              │
│   Option C: Multi-Process                                                   │
│   ─────────────────────────────────────                                     │
│   • PoolSize = number of OS processes                                       │
│   • True parallelism, no GIL                                                │
│   • IPC overhead, more memory                                               │
│                                                                              │
│   Option D: Hybrid (Recommended)                                            │
│   ─────────────────────────────────                                         │
│   • Default: Asyncio for I/O-bound hosts (most HL7 work)                   │
│   • Configurable: ThreadPool for blocking adapters                          │
│   • Configurable: MultiProcess for CPU-heavy transforms                     │
│                                                                              │
│   DECISION: _______________                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Recommendation:** Option D (Hybrid) - Asyncio default, configurable per-host.

### 14.4 Error Handling & Retry Strategy

**Decision Required:** How do we handle failures?

```python
# IRIS-style ReplyCodeActions: ":?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C"
# 
# Actions:
#   F = Fail (move to error queue, alert)
#   S = Suspend (retry with backoff)
#   C = Complete (success)
#   W = Warning (log, continue)
#   D = Disable (disable the host)

class RetryPolicy:
    max_retries: int = 3
    initial_delay: float = 1.0        # seconds
    max_delay: float = 300.0          # 5 minutes max
    backoff_multiplier: float = 2.0   # exponential backoff
    retry_on: list[type] = [ConnectionError, TimeoutError]
    fail_on: list[type] = [ValidationError, PermanentError]

class ErrorQueue:
    """Dead letter queue for failed messages."""
    name: str
    max_age: timedelta = timedelta(days=30)
    
    # Methods
    def add(self, message, error, host_name): ...
    def retry(self, message_id): ...
    def purge(self, older_than): ...
```

### 14.5 Monitoring & Observability

**Decision Required:** What metrics/logging/tracing do we need?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY STACK                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   METRICS (Prometheus-compatible)                                           │
│   ─────────────────────────────────                                         │
│   • messages_received_total{host, status}                                   │
│   • messages_sent_total{host, status}                                       │
│   • message_processing_seconds{host, quantile}                              │
│   • queue_depth{queue}                                                      │
│   • host_status{host} (1=running, 0=stopped, -1=error)                     │
│   • connection_pool_size{host}                                              │
│   • error_total{host, error_type}                                           │
│                                                                              │
│   LOGGING (Structured JSON)                                                 │
│   ─────────────────────────────                                             │
│   • Every message: id, correlation_id, host, action, timestamp              │
│   • Configurable per-host: LogTraceEvents setting                           │
│   • Log levels: DEBUG, INFO, WARN, ERROR                                    │
│                                                                              │
│   TRACING (OpenTelemetry)                                                   │
│   ───────────────────────                                                   │
│   • Trace ID propagated through message flow                                │
│   • Spans for each host processing                                          │
│   • Integration with Jaeger/Zipkin                                          │
│                                                                              │
│   ALERTING                                                                  │
│   ────────                                                                  │
│   • Ens.Alert equivalent - route to EmailAlertOperation                     │
│   • AlertOnError setting per host                                           │
│   • Configurable thresholds                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 14.6 Message Archive (ArchiveIO)

**Decision Required:** How do we implement ArchiveIO setting?

```xml
<Setting Target="Host" Name="ArchiveIO">1</Setting>
```

```
Options:
├── File-based archive (like IRIS)
│   └── /archive/{date}/{host}/{message_id}.hl7
│
├── Database archive
│   └── PostgreSQL with partitioning by date
│
├── Object storage
│   └── S3/MinIO for long-term retention
│
└── Hybrid
    └── Hot: Database (7 days)
    └── Cold: Object storage (7+ years for NHS compliance)
```

**Recommendation:** Database for hot, Object storage for cold, configurable retention.

### 14.7 Security

**Decision Required:** Authentication, authorization, encryption?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY MODEL                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   TRANSPORT SECURITY                                                        │
│   ──────────────────                                                        │
│   • TLS for all external connections (SSLConfig setting)                    │
│   • Mutual TLS (mTLS) option for high-security endpoints                    │
│   • Certificate management via SSLConfig registry                           │
│                                                                              │
│   CREDENTIAL MANAGEMENT                                                     │
│   ──────────────────────                                                    │
│   • Credentials stored encrypted (like IRIS Ens.Config.Credentials)         │
│   • Support for external secret stores (Vault, AWS Secrets Manager)         │
│   • Never log credentials                                                   │
│                                                                              │
│   API SECURITY (Management Portal)                                          │
│   ─────────────────────────────────                                         │
│   • JWT/OAuth2 for portal authentication                                    │
│   • Role-based access control (RBAC)                                        │
│   • Audit logging of all admin actions                                      │
│                                                                              │
│   DATA SECURITY                                                             │
│   ─────────────                                                             │
│   • PII detection and masking in logs                                       │
│   • Encryption at rest for message archive                                  │
│   • NHS Data Security and Protection Toolkit compliance                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 14.8 High Availability & Clustering

**Decision Required:** Single instance or clustered?

```
Phase 1 (MVP): Single Instance
─────────────────────────────
• Single LI Engine process
• PostgreSQL for persistence
• Redis for queues
• Sufficient for most hospital trusts

Phase 2 (HA): Active-Passive
────────────────────────────
• Primary + standby instance
• Shared PostgreSQL (with replication)
• Shared Redis (with Sentinel)
• Automatic failover

Phase 3 (Scale-Out): Clustered
──────────────────────────────
• Multiple LI Engine instances
• Distributed queue (Redis Cluster or Kafka)
• Load balancing for inbound
• Consistent hashing for routing
```

**Recommendation:** Start with Phase 1, design for Phase 2 from day one.

### 14.9 Configuration Hot-Reload

**Decision Required:** How do we handle config changes?

```python
# Option A: Full restart required
engine.stop()
engine.load_config("production.xml")
engine.start()

# Option B: Hot reload (RECOMMENDED - matches IRIS)
engine.reload_config()  # Detects changes, updates only affected items

# Option C: Granular API
engine.update_item_setting("from.BHR.ADT1", "Host", "MessageSchemaCategory", "2.5")
engine.add_item(new_config)
engine.remove_item("old.item")
```

**Recommendation:** Option B + C - Hot reload plus granular API.

### 14.10 Testing Strategy

**Decision Required:** How do we test the engine?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TESTING STRATEGY                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   UNIT TESTS                                                                │
│   ──────────                                                                │
│   • Schema parsing (HL7, FHIR, etc.)                                        │
│   • Rule evaluation                                                         │
│   • Transform application                                                   │
│   • Message serialization                                                   │
│                                                                              │
│   INTEGRATION TESTS                                                         │
│   ─────────────────                                                         │
│   • Adapter connectivity (mock servers)                                     │
│   • End-to-end message flow                                                 │
│   • Queue persistence and recovery                                          │
│                                                                              │
│   PRODUCTION SIMULATION                                                     │
│   ──────────────────────                                                    │
│   • Load the actual BHRUH production config                                 │
│   • Mock external endpoints                                                 │
│   • Replay real message samples                                             │
│   • Verify routing matches IRIS behavior                                    │
│                                                                              │
│   PERFORMANCE TESTS                                                         │
│   ─────────────────                                                         │
│   • Target: 1000+ messages/second sustained                                 │
│   • Latency: <100ms p99 for routing                                         │
│   • Memory: Stable under load (no leaks)                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Implementation Roadmap

### Phase 1: Core Engine (MVP)
```
Week 1-2: Foundation
├── li.messages.Message (raw-first)
├── li.engine.Host base class
├── li.engine.Production
├── li.config.ConfigLoader (XML)
├── li.registry.ClassRegistry

Week 3-4: HL7 Stack
├── li.hosts.hl7.HL7TCPService
├── li.hosts.hl7.HL7TCPOperation
├── li.hosts.hl7.HL7RoutingEngine
├── li.adapters.mllp.MLLPInboundAdapter
├── li.adapters.mllp.MLLPOutboundAdapter
├── li.schemas.hl7.HL7Schema + SchemaLoader

Week 5-6: Rules & Routing
├── li.rules.BusinessRuleSet
├── li.rules.conditions.*
├── li.rules.actions.*
├── li.transforms.DTLTransform
```

### Phase 2: Enterprise Features
```
Week 7-8: Persistence & Reliability
├── Message persistence (WAL)
├── Queue implementation (Redis)
├── Error handling & retry
├── ArchiveIO implementation

Week 9-10: Observability
├── Metrics (Prometheus)
├── Structured logging
├── Alerting (EmailAlertOperation)
├── Health checks
```

### Phase 3: Production Validation
```
Week 11-12: BHRUH Production Test
├── Load full BHRUH.Production.ADTProdudction config
├── Mock all external endpoints
├── Replay real HL7 messages
├── Verify routing matches IRIS
├── Performance testing
```

---

## 16. Final Checklist Before Implementation

| # | Decision | Status | Choice |
|---|----------|--------|--------|
| 1 | Message persistence | ✅ | WAL + Queue hybrid |
| 2 | Queue backend | ✅ | Redis (configurable) |
| 3 | Concurrency model | ✅ | Asyncio default, configurable |
| 4 | Error handling | ✅ | IRIS-style ReplyCodeActions |
| 5 | Metrics format | ✅ | Prometheus |
| 6 | Logging format | ✅ | Structured JSON |
| 7 | Archive storage | ✅ | Database + Object storage |
| 8 | Security model | ✅ | TLS, encrypted credentials |
| 9 | HA approach | ✅ | Design for HA, implement single |
| 10 | Config reload | ✅ | Hot reload + granular API |
| 11 | Deployment | ✅ | Docker service, scalable to 100s of items |

**All decisions confirmed. Proceeding to implementation.**
