# LI Engine - Phase 1 Implementation Status

**Version:** 0.1.0  
**Release Date:** 2026-01-25  
**Status:** Phase 1 Complete ✅

## Overview

The LI (Lightweight Integration) Engine is a configurable, schema-driven healthcare integration engine designed to run IRIS production XML configurations. This document details the Phase 1 implementation status.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        LI Engine                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Config    │  │    Hosts    │  │        Schemas          │  │
│  │   Loader    │  │  Hierarchy  │  │    (Lazy Parsing)       │  │
│  ├─────────────┤  ├─────────────┤  ├─────────────────────────┤  │
│  │ IRIS XML    │  │ Host        │  │ Schema                  │  │
│  │ Production  │  │ Business    │  │ ParsedView              │  │
│  │ ItemConfig  │  │   Service   │  │ HL7Schema               │  │
│  │             │  │   Process   │  │ HL7ParsedView           │  │
│  │             │  │   Operation │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Adapters   │  │  Registry   │  │       Docker Dev        │  │
│  ├─────────────┤  ├─────────────┤  ├─────────────────────────┤  │
│  │ Inbound     │  │ Class       │  │ docker-compose.dev.yml  │  │
│  │ Outbound    │  │ Schema      │  │ Dockerfile.dev          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Phase 1 Components

### 1A: IRIS XML Config Loader ✅

**Location:** `hie/li/config/`

| File | Description | Lines |
|------|-------------|-------|
| `iris_xml_loader.py` | Parses IRIS .cls and XML production files | 302 |
| `item_config.py` | Pydantic model for Item configuration | 197 |
| `production_config.py` | Pydantic model for Production configuration | 117 |
| `__init__.py` | Module exports | 14 |

**Features:**
- Parse IRIS `.cls` files with embedded `XData ProductionDefinition`
- Parse standalone XML production files
- Map IRIS class names to LI equivalents (e.g., `EnsLib.HL7.Service.TCPService` → `li.hosts.hl7.HL7TCPService`)
- Extract settings by target (Adapter, Host, Item)
- Validate target references between items
- Compute dependency order for startup
- Round-trip XML serialization

**Key Classes:**
```python
from hie.li.config import (
    IRISXMLLoader,      # Main loader class
    ProductionConfig,   # Production configuration
    ItemConfig,         # Item configuration
    ItemSetting,        # Individual setting
    SettingTarget,      # Enum: ADAPTER, HOST, ITEM
)
```

**Usage Example:**
```python
loader = IRISXMLLoader()
production = loader.load_from_file("path/to/TEST.cls")

for item in production.items:
    print(f"{item.name}: {item.class_name}")
    print(f"  Adapter settings: {item.adapter_settings}")
    print(f"  Host settings: {item.host_settings}")
```

### 1B: Host Hierarchy ✅

**Location:** `hie/li/hosts/`

| File | Description | Lines |
|------|-------------|-------|
| `base.py` | Base Host, BusinessService, BusinessProcess, BusinessOperation | 376 |
| `__init__.py` | Module exports | 16 |

**Features:**
- Async lifecycle management (start, stop, pause, resume)
- Worker pool with configurable concurrency
- Message queue with backpressure
- Metrics collection (messages received/sent/failed, processing time)
- Configuration from ItemConfig or direct parameters
- Adapter integration

**Host Hierarchy:**
```
Host (ABC)
├── BusinessService    # Inbound - receives from external systems
├── BusinessProcess    # Processing - transforms and routes
└── BusinessOperation  # Outbound - sends to external systems
```

**Key Classes:**
```python
from hie.li.hosts import (
    Host,              # Abstract base class
    HostState,         # Enum: CREATED, STARTING, RUNNING, PAUSED, STOPPING, STOPPED, ERROR
    HostMetrics,       # Runtime metrics dataclass
    BusinessService,   # Inbound host with InboundAdapter
    BusinessProcess,   # Processing host with routing
    BusinessOperation, # Outbound host with OutboundAdapter
)
```

**Lifecycle Example:**
```python
class MyService(BusinessService):
    async def on_message_received(self, data: bytes) -> Any:
        return {"raw": data, "timestamp": datetime.now()}

service = MyService(name="my-service", pool_size=2)
await service.start()
# ... process messages ...
await service.stop()
```

### 1B: Adapter Base Classes ✅

**Location:** `hie/li/adapters/`

| File | Description | Lines |
|------|-------------|-------|
| `base.py` | Adapter, InboundAdapter, OutboundAdapter | 230 |
| `__init__.py` | Module exports | 20 |

**Features:**
- Protocol-agnostic adapter interface
- Lifecycle management (start, stop)
- Metrics (bytes sent/received, connections)
- Settings access

**Key Classes:**
```python
from hie.li.adapters import (
    Adapter,           # Abstract base class
    AdapterState,      # Enum: CREATED, STARTING, RUNNING, STOPPING, STOPPED, ERROR
    AdapterMetrics,    # Runtime metrics dataclass
    InboundAdapter,    # For receiving data
    OutboundAdapter,   # For sending data
)
```

### 1C: Schema System ✅

**Location:** `hie/li/schemas/`

| File | Description | Lines |
|------|-------------|-------|
| `base.py` | Schema, ParsedView, ValidationError | 200 |
| `hl7/__init__.py` | HL7 module exports | 21 |
| `hl7/schema.py` | HL7Schema implementation | 280 |
| `hl7/parsed_view.py` | HL7ParsedView with lazy parsing | 350 |
| `hl7/definitions.py` | HL7 segment/field definitions | 230 |

**Features:**
- **Lazy Parsing:** Fields parsed on-demand, cached for reuse
- **HL7 Path Notation:** Access fields via `MSH-9.1`, `PID-3(1).1`, etc.
- **Validation:** Check message structure against schema
- **ACK Generation:** Create HL7 acknowledgments
- **Immutable Raw:** Modifications return new bytes, original preserved
- **Custom Delimiters:** Auto-detect from MSH segment

**Key Classes:**
```python
from hie.li.schemas import (
    Schema,            # Abstract base class
    ParsedView,        # Abstract parsed view
    ValidationError,   # Validation error dataclass
)

from hie.li.schemas.hl7 import (
    HL7Schema,         # HL7v2 schema implementation
    HL7ParsedView,     # HL7v2 lazy parsed view
    SegmentDefinition, # Segment structure definition
    FieldDefinition,   # Field structure definition
    MessageTypeDefinition,  # Message type definition
)
```

**Usage Example:**
```python
schema = HL7Schema(name="2.4")
parsed = schema.parse(raw_hl7_bytes)

# Lazy field access
msg_type = parsed.get_field("MSH-9.1")      # "ADT"
patient_id = parsed.get_field("PID-3.1")    # "12345"
patient_name = parsed.get_field("PID-5.1")  # "DOE"

# Convenience methods
print(parsed.get_message_type())      # "ADT_A01"
print(parsed.get_message_control_id()) # "MSG00001"

# Validation
errors = schema.validate(raw_hl7_bytes)
if not errors:
    print("Message is valid")

# ACK generation
ack = schema.create_ack(parsed, "AA", "Message Accepted")
```

### Registry System ✅

**Location:** `hie/li/registry/`

| File | Description | Lines |
|------|-------------|-------|
| `class_registry.py` | Dynamic class lookup with aliases | 189 |
| `schema_registry.py` | Lazy schema loading and lookup | 179 |
| `__init__.py` | Module exports | 9 |

**Features:**
- Dynamic class registration and lookup
- IRIS class name aliasing
- Lazy schema loading
- Thread-safe singleton pattern

**Key Classes:**
```python
from hie.li.registry import (
    ClassRegistry,     # Dynamic class lookup
    SchemaRegistry,    # Schema lookup and caching
)
```

## Docker Development Environment

**Location:** Project root

| File | Description |
|------|-------------|
| `docker-compose.dev.yml` | Development stack configuration |
| `Dockerfile.dev` | Development container image |
| `Makefile` | Build and test commands |

### Port Mappings (9300-9350 range)

| Port | Service |
|------|---------|
| 9300 | HIE API |
| 9301 | HIE Portal |
| 9302 | HIE Engine |
| 9305 | Prometheus |
| 9310 | PostgreSQL |
| 9311 | Redis |
| 9320 | MLLP Echo Server |

### Make Commands

```bash
# Docker Stack Management
make li-up          # Start development stack
make li-down        # Stop development stack
make li-restart     # Restart development stack
make li-logs        # View container logs

# Testing
make li-test-li     # Run LI module tests in Docker
make li-test-all    # Run all tests in Docker

# Development
make li-shell       # Shell into engine container
make li-build       # Rebuild Docker images
```

## Test Coverage

**Total Tests:** 73 passing ✅

| Test File | Tests | Description |
|-----------|-------|-------------|
| `tests/li/test_iris_xml_loader.py` | 22 | Config loader and models |
| `tests/li/test_hosts.py` | 20 | Host hierarchy and adapters |
| `tests/li/test_schemas.py` | 31 | Schema system and HL7 parsing |

### Running Tests

```bash
# In Docker (recommended)
make li-test-li

# Output
============================== 73 passed in 3.39s ==============================
```

## File Structure

```
hie/li/
├── __init__.py                 # LI namespace exports
├── config/
│   ├── __init__.py
│   ├── iris_xml_loader.py      # IRIS XML parser
│   ├── item_config.py          # Item configuration model
│   └── production_config.py    # Production configuration model
├── hosts/
│   ├── __init__.py
│   └── base.py                 # Host hierarchy base classes
├── adapters/
│   ├── __init__.py
│   └── base.py                 # Adapter base classes
├── schemas/
│   ├── __init__.py
│   ├── base.py                 # Schema base classes
│   └── hl7/
│       ├── __init__.py
│       ├── schema.py           # HL7Schema implementation
│       ├── parsed_view.py      # HL7ParsedView implementation
│       └── definitions.py      # HL7 segment/field definitions
└── registry/
    ├── __init__.py
    ├── class_registry.py       # Dynamic class registry
    └── schema_registry.py      # Schema registry

tests/li/
├── __init__.py
├── test_iris_xml_loader.py     # Config loader tests
├── test_hosts.py               # Host hierarchy tests
└── test_schemas.py             # Schema system tests
```

## Design Decisions

1. **Raw-First Message Model:** Messages preserve raw bytes; parsing is lazy and on-demand
2. **Schema as Host Setting:** Schema is configuration, not embedded in message class
3. **IRIS Compatibility:** Class name mapping allows running IRIS production configs
4. **Async-First:** All hosts use asyncio for concurrent processing
5. **Docker Development:** All testing runs in containers for consistency
6. **Pydantic Models:** Configuration uses Pydantic for validation and serialization

## Known Limitations

1. **No MLLP Adapters Yet:** TCP/MLLP adapters are Phase 2
2. **No Routing Engine:** Business rule routing is Phase 2
3. **No Persistence:** WAL and Redis queues are Phase 3
4. **No Metrics Export:** Prometheus integration is Phase 3

## Next Phase: Phase 2 - HL7 Stack

The following components will be implemented in Phase 2:

- `HL7TCPService` - MLLP inbound with ACK generation
- `HL7TCPOperation` - MLLP outbound with ReplyCodeActions
- `HL7RoutingEngine` - Rule-based message routing
- `MLLPInboundAdapter` - TCP with MLLP framing (inbound)
- `MLLPOutboundAdapter` - TCP with MLLP framing (outbound)

## Changelog

### v0.1.0 (2026-01-25)

**Phase 1 Complete**

- ✅ IRIS XML config loader with .cls and XML support
- ✅ ProductionConfig and ItemConfig Pydantic models
- ✅ Host hierarchy (BusinessService, BusinessProcess, BusinessOperation)
- ✅ Adapter base classes (InboundAdapter, OutboundAdapter)
- ✅ Schema system with lazy parsing
- ✅ HL7Schema with HL7ParsedView
- ✅ ClassRegistry and SchemaRegistry
- ✅ Docker development environment
- ✅ 73 passing tests
