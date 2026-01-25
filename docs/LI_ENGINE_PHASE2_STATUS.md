# LI Engine - Phase 2 Implementation Status

**Version:** 0.2.0  
**Release Date:** 2026-01-25  
**Status:** Phase 2 Complete ✅

## Overview

Phase 2 implements the complete HL7v2 stack for the LI Engine, enabling NHS acute hospital trusts to receive, route, and send HL7v2 messages via MLLP/TCP protocol.

## Phase 2 Components

### 2A: MLLP Adapters ✅

**Location:** `hie/li/adapters/mllp.py`

| Component | Description |
|-----------|-------------|
| `MLLPInboundAdapter` | TCP server for receiving HL7 messages via MLLP |
| `MLLPOutboundAdapter` | TCP client for sending HL7 messages via MLLP |
| `mllp_wrap()` | Wrap message in MLLP framing |
| `mllp_unwrap()` | Unwrap message from MLLP framing |
| `read_mllp_message()` | Async read MLLP message from stream |
| `write_mllp_message()` | Async write MLLP message to stream |

**MLLP Frame Format:**
```
<SB>message<EB><CR>

SB = Start Block (0x0B)
EB = End Block (0x1C)
CR = Carriage Return (0x0D)
```

**MLLPInboundAdapter Settings:**
| Setting | Default | Description |
|---------|---------|-------------|
| Port | 2575 | TCP port to listen on |
| Host | 0.0.0.0 | IP address to bind to |
| MaxConnections | 100 | Maximum concurrent connections |
| ReadTimeout | 30 | Read timeout in seconds |
| AckTimeout | 30 | ACK generation timeout |
| MaxMessageSize | 10MB | Maximum message size |

**MLLPOutboundAdapter Settings:**
| Setting | Default | Description |
|---------|---------|-------------|
| IPAddress | localhost | Remote host |
| Port | 2575 | Remote TCP port |
| ConnectTimeout | 10 | Connection timeout |
| WriteTimeout | 30 | Write timeout |
| AckTimeout | 30 | ACK wait timeout |
| MaxRetries | 3 | Maximum send retries |
| ReconnectDelay | 5 | Delay before reconnection |

### 2B: HL7 Hosts ✅

**Location:** `hie/li/hosts/hl7.py`

#### HL7TCPService

Receives HL7v2 messages via MLLP/TCP, validates them, generates ACKs, and routes to targets.

**Equivalent to:** IRIS `EnsLib.HL7.Service.TCPService`

**Settings:**
| Setting | Target | Description |
|---------|--------|-------------|
| Port | Adapter | TCP port to listen on |
| MessageSchemaCategory | Host | Schema for validation (e.g., "2.4", "PKB") |
| TargetConfigNames | Host | Comma-separated list of targets |
| AckMode | Host | ACK mode: "Immediate", "Application", "Never" |
| BadMessageHandler | Host | Target for invalid messages |

**Example IRIS Config:**
```xml
<Item Name="HL7.In.TCP" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true">
  <Setting Target="Adapter" Name="Port">2575</Setting>
  <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>
  <Setting Target="Host" Name="TargetConfigNames">HL7.Router</Setting>
</Item>
```

#### HL7TCPOperation

Sends HL7v2 messages via MLLP/TCP and processes ACK responses.

**Equivalent to:** IRIS `EnsLib.HL7.Operation.TCPOperation`

**Settings:**
| Setting | Target | Description |
|---------|--------|-------------|
| IPAddress | Adapter | Remote host |
| Port | Adapter | Remote TCP port |
| ReplyCodeActions | Host | ACK code handling rules |
| ArchiveIO | Host | Archive messages for debugging |
| RetryInterval | Host | Interval between retries |

**ReplyCodeActions Format:**
```
Pattern=Action pairs separated by commas

Patterns: :AA, :AE, :AR, :?E (any error), :?R (any reject), :* (any)
Actions: S (success), F (fail), R (retry), W (warning)

Example: ":?R=F,:?E=S,:*=S"
  - Any reject (AR) = Fail
  - Any error (AE) = Success (log and continue)
  - Any other = Success
```

#### HL7Message

Container for HL7 messages with raw bytes, parsed view, ACK, and metadata.

```python
from hie.li.hosts import HL7Message

message = HL7Message(
    raw=raw_bytes,
    parsed=parsed_view,
    ack=ack_bytes,
    source="HL7.In.TCP",
)

# Properties
message.message_type      # "ADT_A01"
message.message_control_id  # "MSG00001"
message.is_valid          # True/False
message.get_field("PID-3.1")  # Patient ID
```

### 2C: HL7 Routing Engine ✅

**Location:** `hie/li/hosts/routing.py`

Routes messages to different targets based on configurable rules.

**Equivalent to:** IRIS `EnsLib.HL7.MsgRouter.RoutingEngine`

#### Condition Syntax

```
Field Access: {MSH-9.1}, {PID-3.1}, {OBX(1)-5}
Comparisons: =, !=, <, >, <=, >=, Contains, StartsWith, EndsWith
Logical: AND, OR, NOT
Grouping: ( )
Set: IN ("value1", "value2")
```

**Examples:**
```
{MSH-9.1} = "ADT"
{MSH-9.1} = "ADT" AND {MSH-9.2} = "A01"
{PID-3.1} StartsWith "NHS"
{MSH-9.1} IN ("ADT", "ORM", "ORU")
NOT ({MSH-9.1} = "ACK")
({MSH-9.1} = "ADT" AND {MSH-9.2} = "A01") OR {MSH-9.1} = "ORU"
```

#### RoutingRule

```python
from hie.li.hosts import RoutingRule, RuleAction

rule = RoutingRule(
    name="ADT_A01_Route",
    condition='{MSH-9.1} = "ADT" AND {MSH-9.2} = "A01"',
    action=RuleAction.SEND,
    target="HL7.Out.PAS",
)
```

#### Helper Functions

```python
from hie.li.hosts import create_message_type_rule, create_facility_rule

# Route by message type
rule = create_message_type_rule(
    name="ADT_Route",
    message_type="ADT",
    target="HL7.Out.PAS",
    trigger_event="A01",  # Optional
)

# Route by facility
rule = create_facility_rule(
    name="Hospital_Route",
    sending_facility="HOSPITAL",
    target="HL7.Out.External",
)
```

### 2D: Integration Tests ✅

**Location:** `tests/li/test_integration.py`

| Test Class | Description |
|------------|-------------|
| `TestMLLPEchoServer` | Mock MLLP server for testing |
| `TestHL7TCPServiceIntegration` | Service receives and ACKs messages |
| `TestHL7TCPOperationIntegration` | Operation sends and handles ACKs |
| `TestRoutingEngineIntegration` | Routing by message type and conditions |
| `TestEndToEndFlow` | Complete message flow through components |
| `TestIRISConfigIntegration` | Load and use IRIS production configs |

## Test Coverage

**Total Tests:** 130 passing ✅

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_iris_xml_loader.py` | 22 | Config loader and models |
| `test_hosts.py` | 20 | Host hierarchy and adapters |
| `test_schemas.py` | 31 | Schema system and HL7 parsing |
| `test_mllp.py` | 17 | MLLP framing and adapters |
| `test_hl7_hosts.py` | 30 | HL7 hosts and routing |
| `test_integration.py` | 10 | End-to-end integration |

## File Structure (Phase 2 Additions)

```
hie/li/
├── adapters/
│   ├── __init__.py          # Updated with MLLP exports
│   ├── base.py
│   └── mllp.py               # NEW: MLLP adapters
├── hosts/
│   ├── __init__.py          # Updated with HL7 exports
│   ├── base.py              # Updated: BusinessProcess.target_config_names
│   ├── hl7.py               # NEW: HL7TCPService, HL7TCPOperation
│   └── routing.py           # NEW: HL7RoutingEngine
└── config/
    └── iris_xml_loader.py   # Updated: load_from_string, class mappings

tests/li/
├── test_mllp.py             # NEW: MLLP adapter tests
├── test_hl7_hosts.py        # NEW: HL7 host tests
└── test_integration.py      # NEW: Integration tests
```

## Usage Examples

### Receive HL7 Messages

```python
from hie.li.hosts import HL7TCPService

service = HL7TCPService(
    name="HL7.In.TCP",
    adapter_settings={"Port": 2575},
    host_settings={
        "MessageSchemaCategory": "2.4",
        "TargetConfigNames": "HL7.Router",
    },
)

await service.start()
# Service now listening on port 2575
# Messages are automatically ACKed and routed
```

### Send HL7 Messages

```python
from hie.li.hosts import HL7TCPOperation

operation = HL7TCPOperation(
    name="HL7.Out.TCP",
    adapter_settings={
        "IPAddress": "192.168.1.100",
        "Port": 2575,
    },
    host_settings={
        "ReplyCodeActions": ":?R=F,:?E=S,:*=S",
    },
)

await operation.start()
await operation.submit(hl7_message)
```

### Route Messages

```python
from hie.li.hosts import HL7RoutingEngine, create_message_type_rule

router = HL7RoutingEngine(name="HL7.Router")

router.add_rule(create_message_type_rule("ADT_Route", "ADT", "HL7.Out.PAS"))
router.add_rule(create_message_type_rule("ORU_Route", "ORU", "HL7.Out.LAB"))

await router.start()
```

### Load from IRIS Config

```python
from hie.li.config import IRISXMLLoader
from hie.li.hosts import HL7TCPService

loader = IRISXMLLoader()
production = loader.load("path/to/production.cls")

for item in production.services:
    if "HL7TCPService" in item.class_name:
        service = HL7TCPService(name=item.name, config=item)
        await service.start()
```

## IRIS Class Mappings

| IRIS Class | LI Class |
|------------|----------|
| `EnsLib.HL7.Service.TCPService` | `li.hosts.hl7.HL7TCPService` |
| `EnsLib.HL7.Operation.TCPOperation` | `li.hosts.hl7.HL7TCPOperation` |
| `EnsLib.HL7.MsgRouter.RoutingEngine` | `li.hosts.routing.HL7RoutingEngine` |

## Changelog

### v0.2.0 (2026-01-25)

**Phase 2 Complete - HL7 Stack**

- ✅ MLLPInboundAdapter for receiving HL7 via TCP
- ✅ MLLPOutboundAdapter for sending HL7 via TCP
- ✅ MLLP framing utilities (wrap, unwrap, read, write)
- ✅ HL7TCPService with ACK generation
- ✅ HL7TCPOperation with ReplyCodeActions
- ✅ HL7RoutingEngine with rule-based routing
- ✅ ConditionEvaluator with AND/OR/NOT/IN support
- ✅ HL7Message container class
- ✅ Integration tests with MLLP echo server
- ✅ 130 passing tests

## Next Phase: Phase 3 - Enterprise Features

- Write-Ahead Log (WAL) for message durability
- Redis queues for distributed processing
- Prometheus metrics export
- Health checks and monitoring
- Graceful shutdown with message draining
