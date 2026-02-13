# Message Model & Session ID - Architecture Analysis

**Date:** February 10, 2026
**Status:** 🔴 **CRITICAL GAPS IDENTIFIED**

---

## Executive Summary

Our session_id implementation **deviates from the core Message Model architecture**. We've added session tracking as ad-hoc attributes instead of properly integrating with the Envelope/Header structure.

### Critical Issues Found

1. ❌ **session_id NOT in Envelope/Header** - Added as standalone attribute to HL7Message
2. ❌ **correlation_id duplicated** - Envelope has it as UUID, we're passing as string
3. ❌ **HL7Message NOT using core Message model** - Separate ad-hoc class
4. ❌ **Message storage NOT preserving Envelope structure** - Flat table schema
5. ❌ **No message class type on connections** - Topology/sequence diagrams don't show schema

---

## Current Message Model Architecture

### Phase 3 (Production) - `Engine/core/message.py`

```python
Message (immutable dataclass)
├── Envelope (Pydantic BaseModel, frozen)
│   ├── Identity
│   │   ├── message_id: UUID               # ✅ Unique message ID
│   │   ├── correlation_id: UUID           # ✅ Groups related messages
│   │   └── causation_id: UUID | None      # ✅ ID of causing message
│   │
│   ├── Temporal
│   │   ├── created_at: datetime (UTC)
│   │   ├── expires_at: datetime | None
│   │   └── ttl: int | None
│   │
│   ├── Classification
│   │   ├── message_type: str              # ✅ Logical type (e.g., "ADT^A01")
│   │   ├── priority: Priority (low/normal/high/urgent)
│   │   └── tags: tuple[str, ...]
│   │
│   ├── Delivery
│   │   ├── retry_count: int
│   │   ├── max_retries: int
│   │   ├── retry_delay: int
│   │   └── delivery_mode: DeliveryMode
│   │
│   ├── Routing
│   │   └── RoutingInfo
│   │       ├── source: str                # ✅ Source item
│   │       ├── destination: str | None    # ✅ Target item
│   │       ├── route_id: str | None
│   │       └── hop_count: int
│   │
│   ├── Governance
│   │   └── GovernanceInfo
│   │       ├── audit_id: str | None
│   │       ├── tenant_id: str | None
│   │       └── sensitivity: Sensitivity
│   │
│   └── State
│       └── state: MessageState            # ✅ Lifecycle state
│
└── Payload (dataclass, frozen)
    ├── raw: bytes                         # ✅ AUTHORITATIVE CONTENT
    ├── content_type: str                  # ✅ MIME type
    ├── encoding: str                      # ✅ Character encoding
    └── _properties: dict[str, Property]   # ✅ Typed properties

# Key Principle: Raw-first, parse-on-demand
# Messages stored and transported in raw form
# Parsing occurs only when explicitly required
```

### Phase 4 (Future) - `Engine/core/message_envelope.py`

```python
MessageEnvelope
├── MessageHeader
│   ├── Core Identity
│   │   ├── message_id: str (UUID)
│   │   ├── correlation_id: str (UUID)    # ✅ Already exists!
│   │   └── timestamp: datetime
│   │
│   ├── Routing
│   │   ├── source: str
│   │   └── destination: str
│   │
│   ├── Schema Metadata (Phase 4 - enables runtime parsing)
│   │   ├── body_class_name: str          # ✅ Fully qualified class name
│   │   ├── content_type: str             # ✅ MIME type
│   │   ├── schema_version: str           # ✅ Protocol version
│   │   └── encoding: str                 # ✅ Character encoding
│   │
│   ├── Delivery & Priority
│   │   ├── priority: int (0-9)
│   │   ├── ttl: int | None
│   │   └── retry_count: int
│   │
│   └── Custom Properties
│       └── custom_properties: Dict[str, Any]  # ✅ Extensibility!
│
└── MessageBody
    ├── Schema
    │   ├── schema_name: str               # ✅ Logical name ("ADT_A01", "Patient")
    │   └── schema_namespace: str          # ✅ Namespace/URI
    │
    ├── Payload
    │   ├── raw_payload: bytes             # ✅ AUTHORITATIVE CONTENT
    │   └── _parsed_payload: Any           # Lazy-loaded, transient
    │
    ├── Validation State
    │   ├── validated: bool
    │   └── validation_errors: List[str]
    │
    └── Custom Properties
        └── custom_properties: Dict[str, Any]
```

---

## Our Current Session ID Implementation

### What We Did (Deviates from Architecture)

**File:** `Engine/li/hosts/hl7.py`

```python
class HL7Message:
    def __init__(
        self,
        raw: bytes,
        parsed: HL7ParsedView | None = None,
        ack: bytes | None = None,
        received_at: datetime | None = None,
        source: str | None = None,
        validation_errors: list | None = None,
        error: str | None = None,
        session_id: str | None = None,        # ❌ Ad-hoc attribute
        correlation_id: str | None = None,    # ❌ Duplicate (Envelope has UUID)
    ):
        self.raw = raw
        self.parsed = parsed
        self.ack = ack
        self.received_at = received_at or datetime.now(timezone.utc)
        self.source = source
        self.validation_errors = validation_errors or []
        self.error = error
        self.session_id = session_id          # ❌ Not in Envelope
        self.correlation_id = correlation_id  # ❌ Not using Envelope.correlation_id
```

### Problems

1. **Not using Message/MessageEnvelope** - HL7Message is a separate, ad-hoc class
2. **session_id as standalone attribute** - Should be in Envelope/Header
3. **correlation_id duplicated** - Envelope already has it (as UUID)
4. **No schema metadata** - Missing body_class_name, schema_name
5. **Properties scattered** - Not using typed Property system

---

## Gap Analysis

### 🔴 Critical Gaps

| Gap | Current State | Should Be | Impact |
|-----|---------------|-----------|--------|
| **session_id location** | Ad-hoc attribute on HL7Message | In Envelope (Phase 3) or MessageHeader (Phase 4) | ❌ Not part of core architecture |
| **correlation_id type** | String attribute on HL7Message | UUID in Envelope.correlation_id | ❌ Type mismatch, duplicate field |
| **Message wrapping** | HL7Message is standalone | Should wrap/use core Message class | ❌ Not leveraging message model |
| **Envelope preservation** | Not stored in portal_messages | Should serialize full Envelope | ❌ Lost metadata |
| **Schema metadata** | Not tracked | body_class_name, schema_name | ❌ Can't display on diagrams |

### 🟡 Architectural Deviations

1. **HL7Message doesn't inherit from Message** - Should wrap or compose
2. **No use of Payload.properties** - Should use typed Property system
3. **No MessageState tracking** - Envelope has state machine
4. **No RoutingInfo.hop_count** - Can't track pipeline depth
5. **No causation_id** - Can't track derived messages

### 🟢 What We Got Right

1. ✅ session_id format (`SES-{UUID}`) is consistent
2. ✅ Propagation pattern (Service → Process → Operation) is correct
3. ✅ Storage in portal_messages works (flat schema)
4. ✅ Extraction pattern using getattr() is safe

---

## Recommended Fix Strategy

### Option 1: Quick Fix (Align with Phase 3) ⭐ **RECOMMENDED**

**Add session_id to Envelope, use existing correlation_id**

```python
# Engine/core/message.py - Update Envelope class
class Envelope(BaseModel):
    """Message envelope containing routing, delivery, and governance metadata."""
    model_config = ConfigDict(frozen=True)

    # Identity
    message_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)     # ✅ Already exists
    causation_id: UUID | None = Field(default=None)
    session_id: str | None = Field(default=None)            # ✅ ADD THIS

    # ... rest of fields ...
```

**Update HL7Message to wrap Message**

```python
# Engine/li/hosts/hl7.py
class HL7Message:
    def __init__(
        self,
        message: Message,                    # ✅ Wrap core Message
        parsed: HL7ParsedView | None = None,
        ack: bytes | None = None,
        validation_errors: list | None = None,
        error: str | None = None,
    ):
        self.message = message               # ✅ Store full Message
        self.parsed = parsed
        self.ack = ack
        self.validation_errors = validation_errors or []
        self.error = error

    @property
    def raw(self) -> bytes:
        return self.message.payload.raw

    @property
    def session_id(self) -> str | None:
        return self.message.envelope.session_id

    @property
    def correlation_id(self) -> UUID:
        return self.message.envelope.correlation_id

    @property
    def source(self) -> str:
        return self.message.envelope.routing.source
```

**Update message creation in HL7TCPService**

```python
# Generate session_id
session_id = f"SES-{uuid4()}"

# Create proper Message
message = Message.create(
    raw=data,
    content_type="application/hl7-v2+er7",
    encoding="utf-8",
    source=self.name,
    message_type=message_type,
    priority=Priority.NORMAL,
)

# Update envelope with session_id
message = Message(
    envelope=message.envelope.with_updates(session_id=session_id),
    payload=message.payload,
)

# Wrap in HL7Message
hl7_message = HL7Message(
    message=message,
    parsed=parsed,
    ack=ack,
    validation_errors=validation_errors,
)
```

**Update message storage to preserve Envelope**

```python
# Engine/api/services/message_store.py
async def store_message(
    project_id: UUID,
    message: Message,                       # ✅ Accept full Message
    item_name: str,
    item_type: str,
    direction: str,
    status: str = "received",
    ack_content: bytes | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
) -> UUID | None:
    """Store a message preserving full Envelope structure."""

    # Extract from Envelope
    session_id = message.envelope.session_id
    correlation_id = str(message.envelope.correlation_id)
    message_type = message.envelope.message_type
    source_item = message.envelope.routing.source
    destination_item = message.envelope.routing.destination

    # Serialize full envelope for metadata
    envelope_json = message.envelope.model_dump(mode="json")

    query = """
        INSERT INTO portal_messages (
            project_id, item_name, item_type, direction, message_type,
            correlation_id, session_id, status, raw_content,
            source_item, destination_item,
            envelope_metadata, ...
        ) VALUES (...)
    """
```

### Option 2: Phase 4 Migration (Long-term)

**Use MessageEnvelope with schema metadata**

```python
# Create MessageEnvelope for HL7 message
envelope = MessageEnvelope.create_hl7(
    raw_payload=data,
    version="2.4",
    source="PAS-In",
    destination="ADT_Router"
)

# Add session_id to header.custom_properties
envelope.header.custom_properties['session_id'] = f"SES-{uuid4()}"

# Parse and get schema_name
parsed = envelope.parse()
envelope.body.schema_name = parsed.message_type  # "ADT_A01"
envelope.body.schema_namespace = "urn:hl7-org:v2"
```

**Display on diagrams**

```typescript
// Portal/src/components/ProductionDiagram/SequenceArrow.tsx
<text className="message-schema" x={arrowMidX} y={arrowY + 35}>
  {message.schema_name || message.body_class_name || message.message_type}
</text>
// Displays: "ADT_A01", "Patient", "ORU_R01", etc.
```

---

## Database Schema Update

### Add envelope_metadata column

```sql
-- Migration: Add envelope metadata preservation
ALTER TABLE portal_messages
ADD COLUMN envelope_metadata JSONB,
ADD COLUMN payload_metadata JSONB;

-- Index for querying envelope fields
CREATE INDEX idx_portal_messages_envelope_gin ON portal_messages USING GIN (envelope_metadata);

-- Example stored envelope:
{
  "message_id": "123e4567-e89b-12d3-a456-426614174000",
  "correlation_id": "123e4567-e89b-12d3-a456-426614174001",
  "session_id": "SES-123e4567-e89b-12d3-a456-426614174002",
  "message_type": "ADT^A01",
  "priority": "normal",
  "routing": {
    "source": "PAS-In",
    "destination": "ADT_Router",
    "hop_count": 1
  },
  "governance": {
    "tenant_id": "nhs-trust-001",
    "sensitivity": "confidential"
  },
  "state": "delivered"
}
```

---

## Display Message Class on Topology & Sequence Diagrams

### Key Concept: Meta Message Model

Similar to IRIS virtual document schema, each message is a **meta class instance** that dynamically processes payload types:

```
Message Flow = Message Class (processor) + Payload Schema (data type)
```

**Example:**
- **Message Class**: `Engine.li.messages.hl7.HL7Message` (processor intelligence)
- **Payload Schema**: `ADT_A01` (data type being processed)
- **Connection Label**: "HL7Message → ADT_A01" or "HL7Message (ADT_A01)"

### Architecture Clarity

```
MessageEnvelope/Message
├── Header/Envelope (ROUTING & META CLASS)
│   ├── session_id: "SES-{uuid}"           # Session tracking
│   ├── correlation_id: UUID               # Message correlation
│   ├── body_class_name: str               # ⭐ META CLASS (what to display!)
│   │   Examples:
│   │   - "Engine.li.messages.hl7.HL7Message"
│   │   - "Engine.li.messages.fhir.FHIRResource"
│   │   - "custom.nhs.NHSValidationMessage"
│   │   - "custom.acme.CustomTransform"
│   ├── content_type: "application/hl7-v2+er7"
│   └── routing: RoutingInfo(source, destination, hop_count)
│
└── Body/Payload (CONTENT & SCHEMA)
    ├── schema_name: str                   # ⭐ PAYLOAD TYPE
    │   Examples:
    │   - "ADT_A01" (HL7 message type)
    │   - "Patient" (FHIR resource type)
    │   - "Observation" (FHIR resource type)
    │   - "NHSNumber" (custom validation type)
    ├── schema_namespace: "urn:hl7-org:v2"
    ├── raw_payload: bytes                 # AUTHORITATIVE content
    └── _parsed_payload: Any               # Instance of body_class_name
```

### What to Display on Diagrams

**Primary Label**: **body_class_name** (from Header/Envelope)
- Shows the **meta class** processing the message
- This is the **processing intelligence** - what handles the message
- Examples: "HL7Message", "FHIRResource", "NHSValidationMessage"

**Secondary Label**: **schema_name** (from Body)
- Shows the **payload type** being processed
- This is the **data format** - what's inside the message
- Examples: "ADT_A01", "Patient", "Observation"

**Format Options:**
1. **Compact**: `HL7Message`
2. **With Schema**: `HL7Message (ADT_A01)`
3. **Full Class Path**: `Engine.li.messages.hl7.HL7Message`
4. **Two Lines**:
   ```
   HL7Message
   ADT_A01
   ```

### Update TypeScript Interfaces

```typescript
// Portal/src/lib/api-v2.ts
export interface PortalMessage {
  id: string;
  session_id?: string;
  correlation_id?: string;

  // Message Class (Header/Envelope) - WHAT PROCESSES THE MESSAGE
  body_class_name?: string;         // ⭐ PRIMARY: "Engine.li.messages.hl7.HL7Message"
  content_type?: string;            // "application/hl7-v2+er7"

  // Payload Schema (Body) - WHAT'S IN THE MESSAGE
  schema_name?: string;             // ⭐ SECONDARY: "ADT_A01"
  schema_namespace?: string;        // "urn:hl7-org:v2"
  message_type?: string;            // Fallback: "ADT^A01" (legacy field)

  // Routing
  source_item?: string;
  destination_item?: string;

  // ... rest
}

export interface SequenceMessage {
  messageId: string;

  // Display metadata
  body_class_name?: string;         // ⭐ Meta class (primary label)
  schema_name?: string;             // ⭐ Payload type (secondary label)
  message_type?: string;            // Fallback

  sourceItemId: string;
  targetItemId: string;
  duration_ms: number;
  status: string;
}
```

### Update Sequence Diagram Arrow Labels

```typescript
// Portal/src/components/ProductionDiagram/SequenceArrow.tsx
export function SequenceArrow({ message, sourceLane, targetLane, yPosition }: Props) {
  // Extract short class name from fully qualified name
  const getShortClassName = (fullName?: string): string | null => {
    if (!fullName) return null;
    const parts = fullName.split('.');
    return parts[parts.length - 1]; // "Engine.li.messages.hl7.HL7Message" → "HL7Message"
  };

  // Primary label: Message Class (meta class that processes the message)
  const messageClass = getShortClassName(message.body_class_name);

  // Secondary label: Payload Schema (data type being processed)
  const payloadSchema = message.schema_name || message.message_type;

  // Fallback if no class name
  const displayLabel = messageClass || payloadSchema || 'Message';

  return (
    <g className="sequence-arrow" onClick={onArrowClick}>
      {/* Arrow line with Bezier curve */}
      <path
        d={bezierPath}
        stroke={getStatusColor(message.status)}
        strokeWidth={3}
        fill="none"
        markerEnd="url(#arrowhead)"
      />

      {/* Timing label (above arrow) */}
      <text
        x={midX}
        y={yPosition - 12}
        textAnchor="middle"
        className="text-xs text-gray-600 font-mono"
      >
        +{message.duration_ms}ms
      </text>

      {/* PRIMARY: Message Class Name (meta class) */}
      <text
        x={midX}
        y={yPosition + 18}
        textAnchor="middle"
        className="text-sm font-semibold text-blue-700"
        title={message.body_class_name || 'Message class'}
      >
        {displayLabel}
      </text>

      {/* SECONDARY: Payload Schema (if different from class name) */}
      {payloadSchema && payloadSchema !== displayLabel && (
        <text
          x={midX}
          y={yPosition + 32}
          textAnchor="middle"
          className="text-xs text-gray-500 italic"
          title={`Schema: ${message.schema_namespace || 'unknown'}`}
        >
          ({payloadSchema})
        </text>
      )}

      {/* Full class path (on hover tooltip, optional) */}
      {message.body_class_name && (
        <title>{message.body_class_name}</title>
      )}
    </g>
  );
}
```

### Update Topology Connection Labels

```typescript
// Portal/src/components/ProductionDiagram/ProductionDiagram.tsx

// Add metadata to connections showing message classes
interface ConnectionWithMetadata extends ProjectConnection {
  recent_message_classes?: string[];  // ["HL7Message", "FHIRResource"]
  recent_schema_types?: string[];     // ["ADT_A01", "Patient"]
}

<Edge
  id={connection.id}
  source={connection.source_item_id}
  target={connection.target_item_id}
  label={
    <div className="connection-label bg-white px-2 py-1 rounded shadow-sm border">
      {/* Connection name */}
      <div className="font-semibold text-sm">{connection.name}</div>

      {/* Message classes flowing through this connection */}
      {connection.recent_message_classes && connection.recent_message_classes.length > 0 && (
        <div className="text-xs text-blue-600 mt-1 font-mono">
          {connection.recent_message_classes.slice(0, 3).join(', ')}
        </div>
      )}

      {/* Payload schemas */}
      {connection.recent_schema_types && connection.recent_schema_types.length > 0 && (
        <div className="text-xs text-gray-500 mt-0.5 italic">
          ({connection.recent_schema_types.slice(0, 3).join(', ')})
        </div>
      )}
    </div>
  }
  style={{
    stroke: getConnectionColor(connection),
    strokeWidth: 2,
  }}
/>
```

### Update Topology Connection Labels

```typescript
// Portal/src/components/ProductionDiagram/ProductionDiagram.tsx
<Edge
  id={connection.id}
  source={connection.source_item_id}
  target={connection.target_item_id}
  label={
    <div className="connection-label">
      <div className="font-semibold">{connection.name}</div>
      {connection.recent_message_types && (
        <div className="text-xs text-gray-500 mt-1">
          {connection.recent_message_types.join(', ')}
        </div>
      )}
    </div>
  }
/>
```

---

## Implementation Priority

### Phase 1: Fix Critical Gaps ⭐ **IMMEDIATE**

1. **Add session_id to Envelope** (5 min)
   - Update `Engine/core/message.py`
   - Add `session_id: str | None = Field(default=None)`

2. **Update HL7Message to wrap Message** (30 min)
   - Refactor `Engine/li/hosts/hl7.py`
   - Use properties for session_id, correlation_id

3. **Update message storage** (20 min)
   - Extract session_id from envelope
   - Convert correlation_id UUID → string

4. **Test end-to-end** (15 min)
   - Send test message
   - Verify session propagation
   - Check sequence diagram

### Phase 2: Enhance Storage (1-2 hours)

1. **Add envelope_metadata column**
2. **Serialize full Envelope to JSONB**
3. **Update queries to extract from JSONB**

### Phase 3: Display Schema on Diagrams (2-3 hours)

1. **Add schema_name to API responses**
2. **Update TypeScript interfaces**
3. **Render schema on sequence arrows**
4. **Render message types on topology connections**

---

## Success Criteria

### Phase 1 Complete ✅

- [ ] session_id is a field on Envelope
- [ ] HL7Message wraps core Message
- [ ] correlation_id uses Envelope.correlation_id (UUID)
- [ ] All tests pass with new structure
- [ ] Sequence diagram shows full pipeline

### Phase 2 Complete ✅

- [ ] envelope_metadata stored in database
- [ ] Full Envelope can be reconstructed
- [ ] No metadata loss during storage
- [ ] Queries use JSONB extraction

### Phase 3 Complete ✅

- [ ] Sequence arrows show schema_name (e.g., "ADT_A01")
- [ ] Topology connections show recent message types
- [ ] Class names displayed when available
- [ ] User can see message flow types at a glance

---

## Conclusion

Our current session_id implementation works **functionally** but **architecturally deviates** from the core Message Model. The recommended fix is to:

1. **Add session_id to Envelope** (aligns with Phase 3)
2. **Use existing correlation_id from Envelope** (don't duplicate)
3. **Wrap Message in HL7Message** (composition over duplication)
4. **Preserve full Envelope in storage** (JSONB metadata)
5. **Display schema on diagrams** (schema_name, body_class_name)

This ensures:
- ✅ Architectural consistency
- ✅ Future-proof for Phase 4 migration
- ✅ Better metadata preservation
- ✅ Richer UI visualization
- ✅ IRIS HealthConnect-style experience

---

## 📊 Visual Mockup - Sequence Diagram with Message Classes

### Display Strategy: Show Meta Class + Payload Schema

**Each arrow displays:**
1. **Timing** (above arrow): `+450ms`
2. **Message Class** (primary label): `HL7Message` ← **body_class_name** from header
3. **Payload Schema** (secondary label): `(ADT_A01)` ← **schema_name** from body

```
┌──────────┬──────────┬──────────┬──────────┐
│ SERVICE  │ PROCESS  │OPERATION │OPERATION │
│ PAS-In   │ADT_Router│ EPR_Out  │ RIS_Out  │
├──────────┼──────────┼──────────┼──────────┤
│    ●──────────────>●          │          │
│  +450ms  │          │          │          │
│HL7Message│          │          │          │  ← Message Class (processor)
│ (ADT_A01)│          │          │          │  ← Payload Schema (data type)
│          │          │          │          │
│          │    ●───────────────────────>●  │
│          │ +1200ms  │          │          │
│          │HL7Message│          │          │
│          │ (ADT_A01)│          │          │
│          │          │          │          │
│          │          │     ●──────────────>●
│          │          │  +800ms  │          │
│          │          │FHIRResource         │  ← Different class!
│          │          │ (Patient)│          │  ← Transformed schema!
└──────────┴──────────┴──────────┴──────────┘
```

### Real-World Example - Multi-Protocol Pipeline

This shows how **message classes change** as messages flow through transforms:

```
NHS PAS System (HL7 v2.4)
    ↓ raw HL7 message
┌──────────────────────────────────────────┐
│ PAS-In (HL7TCPService)                   │
│                                          │
│ Receives → Instantiates:                │
│   body_class_name: "HL7Message"         │
│   schema_name: "ADT_A01"                │
│   raw_payload: MSH|^~\&|PAS|...         │
└───────────────┬──────────────────────────┘
                │
                ↓ HL7Message(ADT_A01) instance
┌──────────────────────────────────────────┐
│ NHSValidation (NHSValidationProcess)    │
│                                          │
│ Validates → Same message class:         │
│   body_class_name: "HL7Message"         │
│   schema_name: "ADT_A01"                │
│   + validation_errors: []               │
└───────────────┬──────────────────────────┘
                │
                ↓ HL7Message(ADT_A01) instance
┌──────────────────────────────────────────┐
│ ADT_Router (HL7RoutingEngine)           │
│                                          │
│ Routes → Same message class:            │
│   body_class_name: "HL7Message"         │
│   schema_name: "ADT_A01"                │
│   routing.hop_count: 2                  │
└───────────────┬──────────────────────────┘
                │
                ├────→ EPR_Out: HL7Message(ADT_A01)
                │      (sends to EPR via MLLP - no transform)
                │
                ├────→ HL7ToFHIR (TransformProcess)
                │          ↓ transform()
                │      FHIRResource(Patient)  ← CLASS CHANGED!
                │      body_class_name: "FHIRResource"
                │      schema_name: "Patient"
                │      schema_namespace: "http://hl7.org/fhir"
                │          ↓
                │      FHIR_Out: FHIRResource(Patient)
                │      (sends to FHIR R4 server)
                │
                └────→ DataWarehouse: HL7Message(ADT_A01)
                       (archives to analytics DB - no transform)
```

### Topology View - Connection Labels

Show message classes flowing through connections:

```
┌────────────┐
│  PAS-In    │
│  (service) │
└──────┬─────┘
       │ HL7Message, FHIRResource
       │ (ADT_A01, Patient)
       ↓
┌────────────┐
│ADT_Router  │
│ (process)  │
└──────┬─────┘
       │ HL7Message
       │ (ADT_A01, ADT_A04)
       ↓
┌────────────┐
│  EPR_Out   │
│(operation) │
└────────────┘
```

**Key Insights:**
- **body_class_name** = Processing intelligence (HL7Message, FHIRResource, CustomTransform)
- **schema_name** = Data type (ADT_A01, Patient, Observation)
- **Classes transform** at process boundaries (HL7Message → FHIRResource)
- **Schema shows payload** content type at each stage
- **Dynamic instantiation** like IRIS virtual documents and meta-instantiation

---

**Next Steps:** Implement Phase 1 fixes before proceeding with new features.
