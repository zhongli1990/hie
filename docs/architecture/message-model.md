# HIE Message Model

**Version:** 2.0 (Phase 4 Design)
**Last Updated:** February 10, 2026
**Status:** Phase 3 (Simple Message) → Phase 4 (Message Envelope with Schema Metadata)

---

## Overview

The HIE message model is designed for **protocol-agnostic, schema-aware messaging** at enterprise scale. It consists of two parts:

1. **MessageHeader** — Routing, delivery, governance, and **schema metadata**
2. **MessageBody** — Raw payload + lazy-loaded parsed object + validation state

This design ensures:
- **Raw content preserved end-to-end** (audit trail)
- **Schema metadata enables runtime dynamic parsing** (HL7 v2.x, FHIR R4/R5, SOAP, JSON, custom)
- **No implicit transformations** (explicit parsing on demand)
- **Protocol-agnostic** (any message type to any service)
- **Unlimited extensibility** (custom_properties in header and body)

---

## Message Structure (Phase 4)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       MESSAGE ENVELOPE                               │
├─────────────────────────────────────────────────────────────────────┤
│  HEADER (MessageHeader)                                              │
│  ├── Core Identity                                                   │
│  │   ├── message_id (UUID)                                          │
│  │   ├── correlation_id (UUID)                                      │
│  │   └── timestamp (datetime UTC)                                   │
│  ├── Routing                                                         │
│  │   ├── source (item name)                                         │
│  │   └── destination (item name)                                    │
│  ├── Schema Metadata (NEW in Phase 4) 🔥                           │
│  │   ├── body_class_name (str) — e.g., "Engine.li.messages.hl7.HL7Message" │
│  │   ├── content_type (str) — e.g., "application/hl7-v2+er7"       │
│  │   ├── schema_version (str) — e.g., "2.4", "R4", "custom-v1.0"   │
│  │   └── encoding (str) — e.g., "utf-8", "ascii", "base64"         │
│  ├── Delivery & Priority                                             │
│  │   ├── priority (int, 0-9, default 5)                             │
│  │   ├── ttl (int, seconds, optional)                               │
│  │   └── retry_count (int, default 0)                               │
│  └── Custom Properties (unlimited extensibility)                     │
│      └── custom_properties (Dict[str, Any])                         │
├─────────────────────────────────────────────────────────────────────┤
│  BODY (MessageBody)                                                  │
│  ├── Schema Reference (NEW in Phase 4) 🔥                          │
│  │   ├── schema_name (str) — e.g., "ADT_A01", "Patient", "OrderRequest" │
│  │   └── schema_namespace (str) — e.g., "urn:hl7-org:v2", "http://hl7.org/fhir" │
│  ├── Payload                                                         │
│  │   ├── raw_payload (bytes) — THE AUTHORITATIVE CONTENT            │
│  │   └── _parsed_payload (Any, lazy-loaded, transient)             │
│  ├── Validation State (NEW in Phase 4) 🔥                          │
│  │   ├── validated (bool)                                           │
│  │   └── validation_errors (List[str])                              │
│  └── Custom Properties (unlimited extensibility)                     │
│      └── custom_properties (Dict[str, Any])                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 3 vs Phase 4 Comparison

| Aspect | Phase 3 (Current) | Phase 4 (Planned) |
|--------|------------------|-------------------|
| **Header** | Simple envelope (source, destination, priority) | **+ Schema metadata** (content_type, schema_version, body_class_name) |
| **Body** | Raw bytes only | **Raw bytes + lazy-loaded parsed object** |
| **Parsing** | Manual, item-specific | **Automatic based on content_type** |
| **Validation** | External | **Built-in validation state** |
| **Protocol Support** | HL7 v2.x only | **HL7 v2.x, FHIR R4/R5, SOAP, JSON, custom** |
| **Extensibility** | Limited | **Unlimited (custom_properties)** |
| **Schema Awareness** | No | **Yes (schema_name, schema_namespace)** |

---

## MessageHeader Details

### Core Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | str (UUID) | Unique identifier for this message instance |
| `correlation_id` | str (UUID) | Groups related messages (e.g., request/response) |
| `timestamp` | datetime | When the message was created (UTC) |

**Example**: An ADT A01 message triggers a notification. The notification's `correlation_id` matches the ADT message's `correlation_id`, enabling trace correlation.

### Routing Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | str | Item name that created/received this message (e.g., "Cerner_PAS_Receiver") |
| `destination` | str | Target item name (e.g., "NHS_Validation_Process") |

### Schema Metadata Fields (Phase 4) 🔥

These fields enable **runtime dynamic parsing** without hardcoded type checks:

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `body_class_name` | str | Fully qualified Python class name for parsed object | `"Engine.li.messages.hl7.HL7Message"`, `"Engine.li.messages.fhir.FHIRResource"` |
| `content_type` | str | MIME type describing payload format | `"application/hl7-v2+er7"`, `"application/fhir+json"`, `"application/soap+xml"` |
| `schema_version` | str | Protocol/schema version | `"2.3"`, `"2.4"`, `"2.5"`, `"R4"`, `"R5"`, `"custom-v1.0"` |
| `encoding` | str | Character encoding of raw_payload | `"utf-8"`, `"ascii"`, `"iso-8859-1"`, `"base64"` |

**Why This Matters:**

Before (Phase 3):
```python
# Hard-coded type checks
if isinstance(message, HL7Message):
    parsed = message  # Already parsed
elif isinstance(message, bytes):
    parsed = HL7Message.parse(message)  # Manual parsing
else:
    raise TypeError("Unknown message type")
```

After (Phase 4):
```python
# Dynamic parsing based on content_type
envelope = MessageEnvelope(...)
parsed = envelope.parse()  # Automatically selects parser based on content_type

# Works for ANY protocol
if envelope.header.content_type == "application/hl7-v2+er7":
    # HL7Message instance
elif envelope.header.content_type == "application/fhir+json":
    # FHIRResource instance
elif envelope.header.content_type == "application/soap+xml":
    # SOAPMessage instance
```

### Delivery & Priority Fields

| Field | Type | Description |
|-------|------|-------------|
| `priority` | int (0-9) | Message priority (0 = lowest, 9 = highest, default 5) |
| `ttl` | int (optional) | Time-to-live in seconds (discard after this time) |
| `retry_count` | int | Current retry attempt (starts at 0) |

### Custom Properties

**Unlimited extensibility** for custom use cases:

```python
header.custom_properties = {
    "trace_id": "abc123",  # Distributed tracing
    "span_id": "def456",
    "patient_id": "NHS9434765870",  # Business context
    "facility_code": "ROYAL_HOSPITAL",
    "is_urgent": True,
    "custom_routing_key": "ward_a",
}
```

---

## MessageBody Details

### Schema Reference Fields (Phase 4) 🔥

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `schema_name` | str | Logical schema name | `"ADT_A01"`, `"Patient"`, `"OrderRequest"`, `"CustomOrder"` |
| `schema_namespace` | str | Schema namespace/URI | `"urn:hl7-org:v2"`, `"http://hl7.org/fhir"`, `"urn:company:custom"` |

**Purpose**: Enables schema validation, routing rules, and documentation lookup.

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `raw_payload` | bytes | **The authoritative message content** (always preserved) |
| `_parsed_payload` | Any (optional) | Lazy-loaded parsed object (transient, not serialized) |

**Key Principle**: `raw_payload` is **always** the source of truth. `_parsed_payload` is a convenience cache that can be discarded and regenerated at any time.

### Validation State Fields (Phase 4) 🔥

| Field | Type | Description |
|-------|------|-------------|
| `validated` | bool | True if message passed validation, False if failed |
| `validation_errors` | List[str] | List of validation error messages (empty if validated=True) |

**Example**:
```python
body.validated = False
body.validation_errors = [
    "PID-3 (Patient ID) is required but missing",
    "MSH-9 (Message Type) has invalid value 'ADT^A99' (unknown event type)",
]
```

### Custom Properties

**Unlimited extensibility** for enrichment data, caching, or custom metadata:

```python
body.custom_properties = {
    "pds_verified": True,  # NHS PDS lookup result
    "pds_data": {...},
    "duplicate_check_result": "PASS",
    "parsed_patient_name": "JONES, ALICE MARY",
    "cached_hl7_segments": {...},  # Avoid re-parsing
}
```

---

## MessageEnvelope Class

The complete message envelope combines header and body:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

@dataclass
class MessageHeader:
    """Message envelope header containing metadata."""

    # Core properties
    message_id: str
    correlation_id: str
    timestamp: datetime
    source: str
    destination: str

    # Schema metadata (Phase 4)
    body_class_name: str
    content_type: str
    schema_version: str
    encoding: str

    # Routing/processing
    priority: int = 5
    ttl: Optional[int] = None
    retry_count: int = 0

    # Custom properties
    custom_properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MessageBody:
    """Message envelope body containing payload."""

    # Schema reference (Phase 4)
    schema_name: str
    schema_namespace: str

    # Payload
    raw_payload: bytes
    _parsed_payload: Any = None

    # Validation (Phase 4)
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)

    # Custom properties
    custom_properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MessageEnvelope:
    """Complete message envelope (header + body)."""
    header: MessageHeader
    body: MessageBody

    def parse(self) -> Any:
        """Parse raw_payload into typed object based on content_type."""
        if self.body._parsed_payload is not None:
            return self.body._parsed_payload

        # Dynamic parsing based on content_type
        if self.header.content_type == "application/hl7-v2+er7":
            from Engine.li.messages.hl7 import HL7Message
            self.body._parsed_payload = HL7Message.parse(
                self.body.raw_payload,
                version=self.header.schema_version
            )
        elif self.header.content_type == "application/fhir+json":
            from Engine.li.messages.fhir import FHIRResource
            self.body._parsed_payload = FHIRResource.parse_json(
                self.body.raw_payload,
                version=self.header.schema_version
            )
        elif self.header.content_type == "application/soap+xml":
            from Engine.li.messages.soap import SOAPMessage
            self.body._parsed_payload = SOAPMessage.parse_xml(
                self.body.raw_payload
            )
        else:
            # Generic/custom message type
            self.body._parsed_payload = self.body.raw_payload

        return self.body._parsed_payload

    def validate(self) -> bool:
        """Validate message against schema."""
        try:
            parsed = self.parse()

            # Call type-specific validation
            if hasattr(parsed, 'validate'):
                is_valid, errors = parsed.validate()
                self.body.validated = is_valid
                self.body.validation_errors = errors
                return is_valid
            else:
                # No validation available
                self.body.validated = True
                return True
        except Exception as e:
            self.body.validated = False
            self.body.validation_errors = [str(e)]
            return False
```

---

## Factory Methods

Convenience methods for creating envelopes:

```python
class MessageEnvelope:
    @classmethod
    def create_hl7(
        cls,
        raw_payload: bytes,
        version: str,
        source: str,
        destination: str,
        priority: int = 5
    ) -> "MessageEnvelope":
        """Create HL7 v2.x message envelope."""
        header = MessageHeader(
            message_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source=source,
            destination=destination,
            body_class_name="Engine.li.messages.hl7.HL7Message",
            content_type="application/hl7-v2+er7",
            schema_version=version,
            encoding="utf-8",
            priority=priority
        )

        body = MessageBody(
            schema_name="ADT",  # Will be refined after parsing
            schema_namespace="urn:hl7-org:v2",
            raw_payload=raw_payload
        )

        return cls(header=header, body=body)

    @classmethod
    def create_fhir(
        cls,
        resource: Any,  # FHIR Resource (Patient, Observation, etc.)
        source: str,
        destination: str,
        fhir_version: str = "R4"
    ) -> "MessageEnvelope":
        """Create FHIR message envelope."""
        header = MessageHeader(
            message_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source=source,
            destination=destination,
            body_class_name="Engine.li.messages.fhir.FHIRResource",
            content_type="application/fhir+json",
            schema_version=fhir_version,
            encoding="utf-8",
            priority=5
        )

        body = MessageBody(
            schema_name=resource.resource_type,  # "Patient", "Observation", etc.
            schema_namespace="http://hl7.org/fhir",
            raw_payload=resource.json().encode("utf-8"),
            _parsed_payload=resource  # Cache parsed object
        )

        return cls(header=header, body=body)

    @classmethod
    def create_custom(
        cls,
        raw_payload: bytes,
        schema_name: str,
        schema_namespace: str,
        content_type: str,
        source: str,
        destination: str
    ) -> "MessageEnvelope":
        """Create custom message envelope."""
        header = MessageHeader(
            message_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source=source,
            destination=destination,
            body_class_name="Engine.core.message.GenericMessage",
            content_type=content_type,
            schema_version="1.0",
            encoding="utf-8",
            priority=5
        )

        body = MessageBody(
            schema_name=schema_name,
            schema_namespace=schema_namespace,
            raw_payload=raw_payload
        )

        return cls(header=header, body=body)
```

---

## Usage Examples

### Example 1: HL7 v2.4 ADT A01

```python
# Create HL7 v2.4 ADT A01 message
hl7_raw = b"MSH|^~\\&|CERNER|ROYAL_HOSPITAL|..."

envelope = MessageEnvelope.create_hl7(
    raw_payload=hl7_raw,
    version="2.4",
    source="Cerner_PAS_Receiver",
    destination="NHS_Validation_Process",
    priority=7
)

# Parse on demand
hl7_msg = envelope.parse()
patient_id = hl7_msg.get_field("PID", 3, 1)

# Validate
is_valid = envelope.validate()
if not is_valid:
    print(f"Validation errors: {envelope.body.validation_errors}")
```

### Example 2: FHIR R4 Patient

```python
from fhir.resources.patient import Patient

# Create FHIR Patient
patient = Patient(
    id="NHS9434765870",
    name=[{"family": "Jones", "given": ["Alice", "Mary"]}],
    birthDate="1985-03-15",
    gender="female"
)

# Create envelope
envelope = MessageEnvelope.create_fhir(
    resource=patient,
    source="FHIR_API_Service",
    destination="PDS_Lookup_Operation",
    fhir_version="R4"
)

# Parse (returns cached Patient object)
patient_obj = envelope.parse()
print(patient_obj.name[0].family)  # "Jones"
```

### Example 3: Custom JSON Message

```python
import json

# Custom order message
order_data = {
    "order_id": "ORD123456",
    "patient_id": "NHS9434765870",
    "items": [{"code": "LAB001", "description": "Blood Test"}]
}

envelope = MessageEnvelope.create_custom(
    raw_payload=json.dumps(order_data).encode("utf-8"),
    schema_name="OrderRequest",
    schema_namespace="urn:hospital:custom",
    content_type="application/json",
    source="Order_Entry_System",
    destination="Lab_Order_Router"
)

# Parse
order = envelope.parse()
```

---

## Raw-First Philosophy

### Why Raw-First?

Traditional integration engines parse messages eagerly:

```
Receive → Parse → Normalize → Store → Transform → Serialize → Send
```

Problems with this approach:
1. **Lossy** — Parsing may lose edge-case formatting
2. **Slow** — Parsing is expensive, even when not needed
3. **Fragile** — Parser bugs corrupt data silently
4. **Inflexible** — Hard to handle non-standard messages

HIE's approach:

```
Receive → Store Raw → [Parse on Demand] → Transform → Store Raw → Send
```

Benefits:
1. **Lossless** — Original bytes preserved
2. **Fast** — No parsing unless needed
3. **Auditable** — Can always see exactly what was received
4. **Flexible** — Non-standard messages pass through safely

### Parse-on-Demand (Phase 4)

With the message envelope pattern:

```python
# Raw payload - always available
raw_bytes = envelope.body.raw_payload

# Parsed view - created on demand, cached in _parsed_payload
parsed = envelope.parse()  # Automatic based on content_type
patient_id = parsed.get_field("PID", 3, 1)

# Modifications create new raw content
parsed.set_field("PID", 3, 1, "NEW_ID")
new_raw = parsed.serialize()

# New envelope with new raw content
new_envelope = MessageEnvelope.create_hl7(
    raw_payload=new_raw,
    version=envelope.header.schema_version,
    source=envelope.header.destination,  # Reverse source/dest
    destination="Next_Item",
    priority=envelope.header.priority
)
```

The parsed representation is:
- Created only when needed (lazy-loaded)
- Cached in `_parsed_payload` (avoid re-parsing)
- Local to the envelope instance
- **Not serialized** (only raw_payload is serialized)

---

## Message Lifecycle

```
┌──────────┐
│ CREATED  │  MessageEnvelope instantiated with header + body
└────┬─────┘
     │
     ▼
┌──────────┐
│ RECEIVED │  Accepted by a receiver item (Service)
└────┬─────┘
     │
     ▼
┌──────────┐
│ QUEUED   │  Placed in item's queue for processing
└────┬─────┘
     │
     ▼
┌──────────┐
│PROCESSING│  Being handled by an item (Process/Operation)
└────┬─────┘
     │
     ├─────────────────┐
     ▼                 ▼
┌──────────┐     ┌──────────┐
│DELIVERED │     │  FAILED  │
└──────────┘     └────┬─────┘
                      │
                      ▼
                ┌──────────┐
                │DEAD_LETTER│  After max retries
                └──────────┘
```

---

## Immutability

Messages are **immutable**. Operations that "modify" a message actually create a new message:

```python
# Original envelope
env1 = MessageEnvelope.create_hl7(...)

# "Modified" envelope - actually a new instance
env2 = env1.with_priority(9)  # New header.priority
env3 = env1.with_payload(new_raw_payload)  # New body.raw_payload

# env1 is unchanged
assert env1.header.priority == 5
```

Benefits:
- Thread-safe by design
- Easy to track message lineage
- No accidental mutations
- Supports event sourcing patterns

---

## Serialization

Messages can be serialized for:
- Persistence (database storage)
- Transport (Redis Streams, Kafka, RabbitMQ)
- Export (to external systems)

**Important**: Only `raw_payload` is serialized. `_parsed_payload` is transient and regenerated on demand.

Supported formats:
- **MessagePack** — Default, compact binary
- **JSON** — Human-readable, debugging
- **Protocol Buffers** — Cross-language compatibility (Phase 5)

```python
# Serialize
bytes_data = envelope.serialize(format="msgpack")

# Deserialize
envelope = MessageEnvelope.deserialize(bytes_data, format="msgpack")

# After deserialization, _parsed_payload is None
assert envelope.body._parsed_payload is None

# Parse recreates it
parsed = envelope.parse()
```

---

## Comparison to Industry Standards

| Envelope Pattern | HIE MessageEnvelope | Kafka | AMQP | HTTP |
|------------------|---------------------|-------|------|------|
| **Header/Metadata** | MessageHeader | Headers | Properties | HTTP Headers |
| **Payload/Body** | MessageBody | Value | Body | HTTP Body |
| **Schema Metadata** | ✅ content_type, schema_version | ✅ Headers | ✅ content-type | ✅ Content-Type |
| **Raw Preservation** | ✅ raw_payload | ✅ Value (bytes) | ✅ Body (bytes) | ✅ Body |
| **Lazy Parsing** | ✅ _parsed_payload | ❌ No | ❌ No | ❌ No |
| **Custom Properties** | ✅ header/body.custom_properties | ✅ Headers | ✅ Properties | ✅ Custom Headers |

**HIE's envelope pattern is based on proven industry standards** (Kafka, AMQP, HTTP) with enhancements for healthcare (schema metadata, validation state, lazy parsing).

---

## Integration with Host Base Class

All Host subclasses receive MessageEnvelope:

```python
class Host:
    async def on_message_envelope(self, envelope: MessageEnvelope):
        """Process message envelope."""
        # Log
        logger.info(
            "message_received",
            message_id=envelope.header.message_id,
            source=envelope.header.source,
            content_type=envelope.header.content_type,
            schema_version=envelope.header.schema_version
        )

        # Parse if needed
        if self.settings.get("ParseMessages", False):
            parsed = envelope.parse()
            # Process parsed object

        # Forward to target
        for target in self.target_config_names:
            await self.send_message_envelope(target, envelope)
```

---

## Migration Path (Phase 3 → Phase 4)

### Phase 3 (Current)

```python
message = Message(content=b"MSH|...", headers={})
host.on_message(message)
```

### Phase 4 (Planned)

```python
envelope = MessageEnvelope.create_hl7(
    raw_payload=b"MSH|...",
    version="2.4",
    source="Cerner_PAS_Receiver",
    destination="NHS_Validation_Process"
)
host.on_message_envelope(envelope)
```

### Backward Compatibility

Phase 4 maintains backward compatibility with Phase 3 code:

```python
class Host:
    def on_message(self, message: Message):
        """Legacy method - auto-wrap in envelope."""
        envelope = MessageEnvelope.from_legacy_message(message)
        return self.on_message_envelope(envelope)

    def on_message_envelope(self, envelope: MessageEnvelope):
        """New method - process envelope."""
        # Subclasses override this
        pass
```

---

## Advanced Features (Phase 5-6)

### Distributed Tracing Integration

```python
# Propagate trace context in header
from opentelemetry import trace

ctx = trace.get_current_span().get_span_context()
envelope.header.custom_properties["trace_id"] = format(ctx.trace_id, "032x")
envelope.header.custom_properties["span_id"] = format(ctx.span_id, "016x")
```

### Message Replay (Event Sourcing)

```python
# All messages stored in Kafka
await kafka_event_store.publish_event("nhs-trust-messages", envelope)

# Replay from timestamp
async for envelope in kafka_event_store.replay_from(
    "nhs-trust-messages",
    timestamp=datetime(2026, 2, 10, 10, 0, 0)
):
    # Re-process message
    await production_engine.process_message(envelope)
```

---

## Best Practices

### 1. Always Preserve Raw Payload
```python
# ✅ Good
new_envelope = MessageEnvelope.create_hl7(
    raw_payload=original_envelope.body.raw_payload,  # Preserve raw
    ...
)

# ❌ Bad
new_envelope = MessageEnvelope.create_hl7(
    raw_payload=parsed_object.serialize(),  # May lose original formatting
    ...
)
```

### 2. Parse Only When Needed
```python
# ✅ Good - parse only if validation required
if self.settings.get("ValidateMessages", False):
    parsed = envelope.parse()
    envelope.validate()

# ❌ Bad - unnecessary parsing
parsed = envelope.parse()  # Always parse (slow)
```

### 3. Use Factory Methods
```python
# ✅ Good
envelope = MessageEnvelope.create_hl7(raw_payload=..., version="2.4", ...)

# ❌ Bad - manual construction (error-prone)
header = MessageHeader(...)
body = MessageBody(...)
envelope = MessageEnvelope(header=header, body=body)
```

### 4. Validate Before Forwarding
```python
# ✅ Good
if envelope.validate():
    await self.send_message_envelope(target, envelope)
else:
    logger.error("validation_failed", errors=envelope.body.validation_errors)
    await self.send_message_envelope("Exception_Handler", envelope)
```

---

## Summary

The HIE message envelope pattern (Phase 4) provides:

✅ **Protocol-agnostic messaging** (HL7, FHIR, SOAP, JSON, custom)
✅ **Schema-aware parsing** (content_type → automatic parser selection)
✅ **Raw-first design** (original bytes always preserved)
✅ **Lazy-loaded parsing** (parse on demand, cache result)
✅ **Built-in validation** (validated flag + validation_errors)
✅ **Unlimited extensibility** (custom_properties in header and body)
✅ **Industry-standard pattern** (Kafka, AMQP, HTTP headers+body)
✅ **Backward compatible** (Phase 3 code works unchanged)

This design enables HIE to handle **1 billion messages/day** with **any message type** to **any service** at **enterprise scale**.

---

*This document describes the Phase 4 message model. For implementation details, see [MESSAGE_ENVELOPE_DESIGN.md](MESSAGE_ENVELOPE_DESIGN.md).*
