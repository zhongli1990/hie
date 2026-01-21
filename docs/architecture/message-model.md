# HIE Message Model

## Overview

The HIE message model is deliberately simple and strict. It consists of two parts:

1. **Envelope** — Routing, delivery, governance, and operational metadata
2. **Payload** — The raw message content

This design ensures:
- Raw content is preserved end-to-end
- Metadata is structured and indexable
- No implicit transformations occur

## Message Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        MESSAGE                               │
├─────────────────────────────────────────────────────────────┤
│  ENVELOPE                                                    │
│  ├── Identity                                                │
│  │   ├── message_id (UUID)                                  │
│  │   ├── correlation_id (UUID)                              │
│  │   └── causation_id (UUID)                                │
│  ├── Temporal                                                │
│  │   ├── created_at (datetime)                              │
│  │   ├── expires_at (datetime, optional)                    │
│  │   └── ttl (seconds, optional)                            │
│  ├── Routing                                                 │
│  │   ├── source (item_id)                                   │
│  │   ├── destination (item_id, optional)                    │
│  │   ├── route_id (current route)                           │
│  │   └── hop_count (int)                                    │
│  ├── Classification                                          │
│  │   ├── message_type (string)                              │
│  │   ├── priority (enum)                                    │
│  │   └── tags (list)                                        │
│  ├── Delivery                                                │
│  │   ├── retry_count (int)                                  │
│  │   ├── max_retries (int)                                  │
│  │   ├── retry_delay (seconds)                              │
│  │   └── delivery_mode (at_least_once, at_most_once)        │
│  └── Governance                                              │
│      ├── audit_id (string)                                  │
│      ├── tenant_id (string, optional)                       │
│      └── sensitivity (enum)                                 │
├─────────────────────────────────────────────────────────────┤
│  PAYLOAD                                                     │
│  ├── raw (bytes) — THE AUTHORITATIVE CONTENT                │
│  ├── content_type (MIME type)                               │
│  ├── encoding (character encoding)                          │
│  ├── size (bytes)                                           │
│  └── properties (typed key-value pairs)                     │
└─────────────────────────────────────────────────────────────┘
```

## Envelope Details

### Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | UUID | Unique identifier for this message instance |
| `correlation_id` | UUID | Groups related messages (e.g., request/response) |
| `causation_id` | UUID | ID of the message that caused this one to be created |

**Example**: An ADT message triggers a notification. The notification's `causation_id` points to the ADT message's `message_id`. Both share the same `correlation_id`.

### Temporal Fields

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | datetime | When the message was created (UTC) |
| `expires_at` | datetime | When the message should be discarded (optional) |
| `ttl` | int | Time-to-live in seconds (alternative to expires_at) |

### Routing Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Item ID that created/received this message |
| `destination` | string | Target item ID (optional, for direct routing) |
| `route_id` | string | Current route being traversed |
| `hop_count` | int | Number of items this message has passed through |

### Classification Fields

| Field | Type | Description |
|-------|------|-------------|
| `message_type` | string | Logical type (e.g., "ADT^A01", "ORU^R01") |
| `priority` | enum | LOW, NORMAL, HIGH, URGENT |
| `tags` | list | Arbitrary tags for filtering/routing |

### Delivery Fields

| Field | Type | Description |
|-------|------|-------------|
| `retry_count` | int | Current retry attempt (starts at 0) |
| `max_retries` | int | Maximum retry attempts before dead-letter |
| `retry_delay` | int | Seconds between retries (may use backoff) |
| `delivery_mode` | enum | AT_LEAST_ONCE, AT_MOST_ONCE |

### Governance Fields

| Field | Type | Description |
|-------|------|-------------|
| `audit_id` | string | External audit/trace identifier |
| `tenant_id` | string | Multi-tenant isolation (optional) |
| `sensitivity` | enum | PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED |

## Payload Details

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `raw` | bytes | **The authoritative message content** |
| `content_type` | string | MIME type (e.g., "x-application/hl7-v2+er7") |
| `encoding` | string | Character encoding (e.g., "utf-8", "iso-8859-1") |
| `size` | int | Size of raw content in bytes |

### Properties

Properties are **typed, explicit key-value pairs** that can be attached to a payload.

**Key principles**:
1. Properties are **explicitly set** by items — never auto-populated
2. Properties are **typed** — string, int, float, bool, datetime, list, dict
3. Properties are **bounded** — max size, allowed values defined in schema
4. Properties are **optional** — the raw payload is always authoritative

**Use cases**:
- Routing decisions based on extracted values
- Caching parsed field values to avoid re-parsing
- Legacy system compatibility (property bags)
- Enrichment data from external lookups

**Example**:
```python
payload.properties = {
    "patient_id": Property(value="NHS1234567890", type="string"),
    "event_type": Property(value="A01", type="string"),
    "is_urgent": Property(value=True, type="bool"),
}
```

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

### Parse-on-Demand

When an item needs structured access:

```python
# Raw payload - always available
raw_bytes = message.payload.raw

# Parsed view - created on demand, transient
parsed = hl7v2.parse(message.payload)
patient_id = parsed.PID[3][1]  # Access structured data

# Modifications create new raw content
parsed.PID[3][1] = "NEW_ID"
new_raw = hl7v2.serialize(parsed)

# New message with new raw content
new_message = message.with_payload(raw=new_raw)
```

The parsed representation is:
- Created only when needed
- Local to the item that requested it
- Discarded after use
- Never stored or transmitted

## Message Lifecycle

```
┌──────────┐
│ CREATED  │  Message instantiated with envelope + payload
└────┬─────┘
     │
     ▼
┌──────────┐
│ RECEIVED │  Accepted by a receiver item
└────┬─────┘
     │
     ▼
┌──────────┐
│ QUEUED   │  Placed in route queue for processing
└────┬─────┘
     │
     ▼
┌──────────┐
│PROCESSING│  Being handled by an item
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

## Immutability

Messages are **immutable**. Operations that "modify" a message actually create a new message:

```python
# Original message
msg1 = Message(envelope=env1, payload=pay1)

# "Modified" message - actually a new instance
msg2 = msg1.with_envelope(priority=Priority.URGENT)
msg3 = msg1.with_payload(raw=new_bytes)

# msg1 is unchanged
assert msg1.envelope.priority == Priority.NORMAL
```

Benefits:
- Thread-safe by design
- Easy to track message lineage
- No accidental mutations
- Supports event sourcing patterns

## Serialization

Messages can be serialized for:
- Persistence (database storage)
- Transport (between processes/nodes)
- Export (to external systems)

Supported formats:
- **MessagePack** — Default, compact binary
- **JSON** — Human-readable, debugging
- **Protocol Buffers** — Cross-language compatibility

```python
# Serialize
bytes_data = message.serialize(format="msgpack")

# Deserialize
message = Message.deserialize(bytes_data, format="msgpack")
```

## Legacy Compatibility

Messages from legacy engines can be imported:

```python
# Import from Mirth-style message
legacy_msg = {
    "messageId": "123",
    "rawData": b"MSH|^~\\&|...",
    "channelMap": {"patientId": "NHS123"},
}

hie_message = LegacyAdapter.from_mirth(legacy_msg)
# - messageId → envelope.message_id
# - rawData → payload.raw
# - channelMap → payload.properties
```

Export is also supported:
```python
legacy_msg = LegacyAdapter.to_mirth(hie_message)
```

This allows HIE to interoperate with existing systems without polluting the core model.
