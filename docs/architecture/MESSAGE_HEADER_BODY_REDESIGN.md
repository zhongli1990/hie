# MessageHeader & MessageBody — Architecture Review & Revised Design

**Version:** 2.1  
**Date:** February 13, 2026  
**Status:** ✅ Implemented (Phase 1–3 complete)  
**Author:** Architecture Team  
**Scope:** Core message model, DB schema, visual trace, cross-platform compatibility  
**Implementation Branch:** `feature/enterprise-topology-viewer`  

> **Architecture Decision: Option C (Hybrid) for MessageBody storage.**  
> In IRIS, each body class has its own SQL table (`EnsLib_HL7.Message`, `Ens.StreamContainer`, etc.).  
> PostgreSQL doesn't have IRIS's class-per-table inheritance, so we use a **single `message_bodies` table**  
> with a `body_class_name` discriminator column and **protocol-specific nullable columns** with partial indexes.  
> A future **SearchTable** (EAV pattern, equivalent to `EnsLib.HL7.SearchTable`) will provide configurable  
> per-field indexing. See migration `004_message_headers_bodies.sql` for the actual schema.  

> **This is the master consolidated design document.** All related docs are updated to reflect implementation:
> - [MESSAGE_MODEL.md](MESSAGE_MODEL.md) — v3.1 ✅ Implemented: Two-layer architecture (in-memory + persisted trace)
> - [SESSION_ID_DESIGN.md](SESSION_ID_DESIGN.md) — v2.1 ✅ Resolved: One-row-per-leg model with session_id propagation
> - [MESSAGE_MODEL_SESSION_ANALYSIS.md](MESSAGE_MODEL_SESSION_ANALYSIS.md) — ✅ Resolved: All critical gaps closed
> - [MESSAGE_ENVELOPE_DESIGN.md](MESSAGE_ENVELOPE_DESIGN.md) — v2.2: Layer 1 in-memory transport (unchanged by this work)
>
> **Host lifecycle is completely unchanged by design.** The trace layer is purely a storage concern.
> Each host still runs as a standalone async worker loop with queue-based message reception,
> configurable pool_size, and full callback support. See [MESSAGE_MODEL.md](MESSAGE_MODEL.md) §Host Lifecycle.

---

## 1. Problem Statement

### 1.1 Broken Sequence Diagram — Root Cause Analysis

The current Message Sequence Diagram (screenshot evidence) shows three critical defects:

**Defect 1 — Ghost swimlane "EPR_Out,RIS_Out" appears as a PROCESS**

The routing engine stores `destination_item = "EPR_Out,RIS_Out"` (comma-joined string) in `portal_messages`. The `buildSequenceDiagram()` function in the frontend then creates a swimlane for this composite string as if it were a single item. IRIS never does this — each leg is a separate `Ens.MessageHeader` row.

**Defect 2 — No arrow from ADT_Router → EPR_Out or ADT_Router → RIS_Out**

The routing engine stores ONE message record for itself with `destination_item = "EPR_Out,RIS_Out"`, but the outbound operations (EPR_Out, RIS_Out) store their own records with `source_item = NULL`. There is no parent-child linkage between the router's record and the operation records. The frontend cannot draw arrows because `source_item` on the operation records is empty.

**Defect 3 — All messages appear at the same timestamp (0ms offset)**

All `store_and_complete_message()` calls happen near-simultaneously in an async pipeline. Without a sequential ordering field (like IRIS's `MessageId` auto-increment), the diagram cannot determine message ordering.

### 1.2 Root Cause Summary

| Issue | Root Cause |
|-------|-----------|
| Ghost swimlane | `destination_item` stores comma-joined target list instead of one row per leg |
| Missing arrows | No `source_item`/`destination_item` linkage between router record and operation records |
| No ordering | No sequence number; all records share same `session_id` but no parent→child chain |
| Wrong item types | `source_item`/`destination_item` extracted from messages don't carry `item_type`; defaults to "process" |

### 1.3 Why This Is a Design Problem, Not Just a Bug

The current `portal_messages` table is a **flat log** — it records that something happened at an item, but it does not model the **message journey** (who sent what to whom, in what order, as part of what session). This is fundamentally different from how IRIS, Rhapsody, and Mirth model messages.

---

## 2. Cross-Platform Message Model Comparison

### 2.1 InterSystems IRIS — Ens.MessageHeader + Ens.MessageBody

IRIS's model is the gold standard for integration engine message tracking. Key design:

```
Ens.MessageHeader (persisted, one row per message leg)
├── MessageId           — Auto-increment integer (global ordering)
├── SessionId           — Groups all legs of one inbound message
├── CorrespondingMessageId — Links request→response pairs
├── SourceConfigName    — Item that SENT this message (e.g., "CaMIS-ADT-IN-FileBS")
├── TargetConfigName    — Item that RECEIVED this message (e.g., "HIEMsgRouterConsolidated")
├── SourceBusinessType  — "BusinessService" | "BusinessProcess" | "BusinessOperation"
├── TargetBusinessType  — "BusinessService" | "BusinessProcess" | "BusinessOperation"
├── MessageBodyClassName — "EnsLib.HL7.Message" (polymorphic body reference)
├── MessageBodyId       — Foreign key to the body object
├── Type                — "Request" | "Response"
├── Invocation          — "Queue" | "InProc"
├── Status              — "Completed" | "Error" | "Discarded"
├── Priority            — "Async" | "Sync"
├── TimeCreated         — Timestamp with sub-second precision
├── TimeProcessed       — Completion timestamp
├── IsError             — Boolean
├── ErrorStatus         — Error text
├── ReturnQueueName     — Queue for response routing
├── BusinessProcessId   — Links to BPL process instance
├── Description         — Human-readable description
├── Resent              — Boolean (was this a resend?)
├── SuperSession        — Groups multiple sessions (e.g., batch)
└── Banked              — Archival flag

Ens.MessageBody (abstract base — polymorphic)
├── %Id()               — Unique body ID
└── (subclass-specific content)

EnsLib.HL7.Message extends Ens.MessageBody
├── RawContent          — Raw HL7 bytes
├── DocType             — Schema category:name (e.g., "2.4:ADT_A01")
├── Name                — Message type string
├── Identifier          — Control ID
├── Source              — Origin system
├── IsMutable           — Whether content can be modified
└── (segment access API)
```

**Critical IRIS design principles:**

1. **One row per message leg** — When a router sends to 3 targets, IRIS creates 3 separate `Ens.MessageHeader` rows, each with its own `SourceConfigName` → `TargetConfigName` pair. The Visual Trace draws one arrow per row.

2. **SessionId groups the entire journey** — All headers in one end-to-end flow share the same `SessionId`. The first inbound message creates the session; all downstream legs inherit it.

3. **CorrespondingMessageId links request↔response** — When an operation sends a message and gets an ACK, the ACK's header has `CorrespondingMessageId` pointing to the request's `MessageId`.

4. **MessageBodyClassName enables polymorphism** — The header stores the fully-qualified class name of the body. The body can be `EnsLib.HL7.Message`, `EnsLib.DICOM.Document`, `Ens.StreamContainer`, or any custom class. The viewer uses this to render the correct body tab.

5. **Auto-increment MessageId provides global ordering** — No timestamp collisions. The Visual Trace sorts by `MessageId` to show the exact sequence.

### 2.2 Orion Health Rhapsody — MessageObject

```
MessageObject
├── messageId           — UUID
├── messageControlId    — HL7 MSH-10
├── messageType         — "ADT^A01"
├── sourceRoute         — Route that received the message
├── destinationRoute    — Route that will process the message
├── inputConnector      — Connector that received (= IRIS SourceConfigName)
├── outputConnector     — Connector that sent (= IRIS TargetConfigName)
├── messageBody         — Raw content (stored in message store)
├── messageProperties   — Key-value metadata map
├── processingState     — "RECEIVED" | "PROCESSING" | "SENT" | "ERROR"
├── timestamp           — Receive time
├── completedTimestamp  — Completion time
├── correlationId       — Groups related messages
├── parentMessageId     — Links to parent (= IRIS CorrespondingMessageId)
└── errorDetails        — Error information
```

**Rhapsody key differences from IRIS:**
- Uses `parentMessageId` instead of `CorrespondingMessageId` (tree structure vs. flat pairs)
- `messageProperties` is a free-form map (more flexible, less structured)
- No separate body class hierarchy — body is always raw bytes in the message store

### 2.3 NextGen Mirth Connect — ConnectorMessage

```
ConnectorMessage
├── messageId           — Long auto-increment
├── metaDataId          — Channel-specific sequence
├── channelId           — Which channel processed this
├── channelName         — Human-readable channel name
├── connectorName       — Source or destination connector name
├── serverId            — Cluster node ID
├── status              — "RECEIVED" | "FILTERED" | "TRANSFORMED" | "SENT" | "ERROR"
├── rawData             — Original inbound content
├── transformedData     — Content after transformation
├── encodedData         — Content after encoding for destination
├── responseData        — ACK/response content
├── responseError       — Response error text
├── processingError     — Processing error text
├── sendAttempts        — Retry count
├── sendDate            — When sent to destination
├── responseDate        — When response received
├── orderId             — Ordering within a batch
└── connectorMap        — Key-value metadata (like Rhapsody properties)

Message (parent container)
├── messageId           — Groups all ConnectorMessages for one inbound
├── serverId            — Cluster node
└── connectorMessages   — Map<metaDataId, ConnectorMessage>
```

**Mirth key differences:**
- **One ConnectorMessage per connector** — Similar to IRIS's one-header-per-leg
- **Stores raw + transformed + encoded** — Three versions of the content at different pipeline stages
- **connectorMap** — Free-form metadata (like Rhapsody's messageProperties)
- **No polymorphic body class** — Always stores raw/transformed/encoded as strings

### 2.4 Comparison Matrix

| Feature | IRIS | Rhapsody | Mirth | **HIE Current** | **HIE Proposed** |
|---------|------|----------|-------|-----------------|------------------|
| One record per leg | ✅ | ✅ | ✅ | ❌ (one per item) | ✅ |
| Session grouping | ✅ SessionId | ✅ correlationId | ✅ messageId | ⚠️ session_id (broken) | ✅ |
| Parent→child chain | ✅ CorrespondingMessageId | ✅ parentMessageId | ✅ metaDataId ordering | ❌ | ✅ |
| Global ordering | ✅ auto-increment | ⚠️ timestamp | ✅ auto-increment | ❌ | ✅ |
| Polymorphic body | ✅ MessageBodyClassName | ❌ raw bytes | ❌ raw strings | ⚠️ body_class_name (unused) | ✅ |
| Source→Target per record | ✅ | ✅ | ✅ | ❌ | ✅ |
| Request/Response linking | ✅ | ✅ | ✅ | ❌ | ✅ |
| Body class hierarchy | ✅ deep | ❌ | ❌ | ⚠️ exists but disconnected | ✅ |
| Transform audit trail | ⚠️ via DTL | ⚠️ via route | ✅ raw/transformed/encoded | ❌ | ✅ |
| Batch/SuperSession | ✅ SuperSession | ❌ | ✅ orderId | ❌ | ✅ |

---

## 3. Revised Design

### 3.1 Design Principles

1. **One row per message leg** — Every time a message crosses from one item to another, a new `message_header` row is created. This is the fundamental unit of the visual trace.

2. **Session = complete journey** — All headers in one end-to-end flow share the same `session_id`. Created by the first inbound service, propagated through every downstream leg.

3. **Parent→child chain** — Every header (except the first) has a `parent_header_id` pointing to the header that caused it. This forms a tree: inbound → router → [operation1, operation2].

4. **Polymorphic body** — The header's `body_class_name` identifies the body type. Bodies are stored separately and can be any class: HL7Message, FHIRResource, CSVBatch, GenericMessage, or any custom class.

5. **Global sequence** — An auto-increment `sequence_num` provides unambiguous ordering even when timestamps collide.

6. **Request/Response pairing** — When an operation gets an ACK, the ACK header's `corresponding_header_id` points to the request header.

7. **Backwards-compatible** — The design can import IRIS `Ens.MessageHeader` rows, Rhapsody `MessageObject` records, and Mirth `ConnectorMessage` records with minimal transformation.

### 3.2 MessageHeader — Revised Class

```python
@dataclass
class MessageHeader:
    """
    Tracks one leg of a message's journey through the production.
    
    One row per message leg. When a router sends to 3 targets,
    3 MessageHeader rows are created — one per leg.
    
    IRIS equivalent: Ens.MessageHeader
    Rhapsody equivalent: MessageObject (partial)
    Mirth equivalent: ConnectorMessage (partial)
    """
    
    # ─── Identity ───────────────────────────────────────────────
    id: UUID                          # Primary key (= IRIS %Id)
    sequence_num: int                 # Auto-increment global ordering (= IRIS MessageId)
    
    # ─── Session & Lineage ──────────────────────────────────────
    session_id: str                   # Groups entire journey (= IRIS SessionId)
    parent_header_id: UUID | None     # Header that caused this leg (tree structure)
    corresponding_header_id: UUID | None  # Links request↔response (= IRIS CorrespondingMessageId)
    super_session_id: str | None      # Groups multiple sessions, e.g. batch (= IRIS SuperSession)
    
    # ─── Routing ────────────────────────────────────────────────
    source_config_name: str           # Item that SENT (= IRIS SourceConfigName)
    target_config_name: str           # Item that RECEIVED (= IRIS TargetConfigName)
    source_business_type: str         # "service" | "process" | "operation" (= IRIS SourceBusinessType)
    target_business_type: str         # "service" | "process" | "operation" (= IRIS TargetBusinessType)
    
    # ─── Message Classification ─────────────────────────────────
    message_type: str | None          # "ADT^A01", "ORM^O01", "Patient" (= IRIS Name on body)
    body_class_name: str              # FQ class name (= IRIS MessageBodyClassName)
    message_body_id: UUID | None      # FK to message_bodies table (= IRIS MessageBodyId)
    
    # ─── Invocation ─────────────────────────────────────────────
    type: str = "Request"             # "Request" | "Response" (= IRIS Type)
    invocation: str = "Queue"         # "Queue" | "InProc" (= IRIS Invocation)
    priority: str = "Async"           # "Async" | "Sync" (= IRIS Priority)
    
    # ─── Status & Timing ────────────────────────────────────────
    status: str = "created"           # "created"|"queued"|"delivered"|"completed"|"error"|"discarded"
    is_error: bool = False            # (= IRIS IsError)
    error_status: str | None = None   # Error text (= IRIS ErrorStatus)
    time_created: datetime            # When this header was created (= IRIS TimeCreated)
    time_processed: datetime | None   # When processing completed (= IRIS TimeProcessed)
    
    # ─── Delivery ───────────────────────────────────────────────
    return_queue_name: str | None = None  # Queue for response routing (= IRIS ReturnQueueName)
    target_queue_name: str | None = None  # Target's queue name (= IRIS TargetQueueName)
    business_process_id: str | None = None  # BPL process instance (= IRIS BusinessProcessId)
    resent: bool = False              # Was this a resend? (= IRIS Resent)
    banked: bool = False              # Archived? (= IRIS Banked)
    
    # ─── Extensibility ──────────────────────────────────────────
    description: str | None = None    # Human-readable (= IRIS Description)
    metadata: dict = field(default_factory=dict)  # Free-form (= Rhapsody messageProperties, Mirth connectorMap)
    
    # ─── Project Scoping ────────────────────────────────────────
    project_id: UUID                  # HIE-specific: which project this belongs to
```

### 3.3 MessageBody — Revised Class Hierarchy

```
MessageBody (abstract base)
│   id: UUID
│   body_class_name: str          # Self-describing (= IRIS %ClassName)
│   content_type: str             # MIME type
│   raw_content: bytes            # Authoritative raw bytes
│   content_size: int             # Size in bytes
│   checksum: str                 # SHA-256 for dedup/integrity
│   created_at: datetime
│
├── HL7MessageBody(MessageBody)
│   │   schema_category: str      # "2.3", "2.4", "2.5.1" (= IRIS DocType category)
│   │   schema_name: str          # "ADT_A01" (= IRIS DocType name)
│   │   message_control_id: str   # MSH-10
│   │   sending_application: str  # MSH-3
│   │   sending_facility: str     # MSH-4
│   │   receiving_application: str # MSH-5
│   │   receiving_facility: str   # MSH-6
│   │   message_type: str         # "ADT" (MSH-9.1)
│   │   trigger_event: str        # "A01" (MSH-9.2)
│   │   message_structure: str    # "ADT_A01" (MSH-9.3)
│   │   _parsed: HL7ParsedView   # Transient, lazy-loaded
│   │
│   ├── HL7v2MessageBody(HL7MessageBody)    # HL7 v2.x ER7/XML
│   └── HL7v3MessageBody(HL7MessageBody)    # HL7 v3 CDA (future)
│
├── FHIRMessageBody(MessageBody)
│   │   fhir_version: str         # "R4", "R5"
│   │   resource_type: str        # "Patient", "Bundle", "Observation"
│   │   resource_id: str          # FHIR resource ID
│   │   profile_url: str          # FHIR profile URL
│   │   _parsed: dict             # Transient, lazy-loaded JSON
│   │
│   ├── FHIRResourceBody(FHIRMessageBody)   # Single resource
│   └── FHIRBundleBody(FHIRMessageBody)     # Bundle of resources
│
├── CSVMessageBody(MessageBody)
│       delimiter: str            # "," or "|" or "\t"
│       has_header: bool
│       row_count: int
│       column_names: list[str]
│
├── XMLMessageBody(MessageBody)
│       root_element: str
│       namespace: str
│       schema_url: str
│
├── JSONMessageBody(MessageBody)
│       root_type: str            # "object" | "array"
│       schema_url: str
│
├── DicomMessageBody(MessageBody)           # Future: DICOM images
│       sop_class_uid: str
│       study_instance_uid: str
│       modality: str
│
├── StreamBody(MessageBody)                 # Binary streams, files
│       filename: str
│       mime_type: str
│
└── GenericMessageBody(MessageBody)         # Catch-all
        description: str
```

**Key design decisions:**

- **Body is stored separately from header** — Multiple headers can reference the same body (e.g., when a message is sent to 3 targets, all 3 headers point to the same body). This avoids duplicating large HL7 messages.
- **Body is self-describing** — `body_class_name` enables meta-instantiation (load the right parser at runtime).
- **Raw bytes are authoritative** — Parsed representations are transient and lazy-loaded.
- **Subclasses extract protocol-specific indexed fields** — HL7 bodies index MSH fields; FHIR bodies index resource type. These enable efficient querying without parsing.

### 3.4 Database Schema — Revised

```sql
-- ═══════════════════════════════════════════════════════════════
-- message_bodies: Stores actual message content (one per unique message)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE message_bodies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    body_class_name VARCHAR(255) NOT NULL DEFAULT 'GenericMessageBody',
    content_type    VARCHAR(100) NOT NULL DEFAULT 'application/octet-stream',
    raw_content     BYTEA,
    content_preview TEXT,                -- First 500 chars for list view
    content_size    INTEGER NOT NULL DEFAULT 0,
    checksum        VARCHAR(64),         -- SHA-256 for dedup
    
    -- Protocol-specific indexed fields (populated by body subclass)
    -- HL7
    schema_category VARCHAR(20),         -- "2.3", "2.4", "2.5.1"
    schema_name     VARCHAR(100),        -- "ADT_A01"
    message_control_id VARCHAR(100),     -- MSH-10
    sending_application VARCHAR(100),    -- MSH-3
    sending_facility VARCHAR(100),       -- MSH-4
    receiving_application VARCHAR(100),  -- MSH-5
    receiving_facility VARCHAR(100),     -- MSH-6
    
    -- FHIR
    fhir_version    VARCHAR(10),         -- "R4"
    resource_type   VARCHAR(100),        -- "Patient"
    resource_id     VARCHAR(255),        -- FHIR resource ID
    
    -- Generic
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_message_bodies_checksum ON message_bodies(checksum);
CREATE INDEX idx_message_bodies_class ON message_bodies(body_class_name);

-- ═══════════════════════════════════════════════════════════════
-- message_headers: One row per message leg (the core trace table)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE message_headers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_num            BIGSERIAL,       -- Global ordering (= IRIS MessageId)
    project_id              UUID NOT NULL,
    
    -- Session & Lineage
    session_id              VARCHAR(255) NOT NULL,
    parent_header_id        UUID REFERENCES message_headers(id),
    corresponding_header_id UUID REFERENCES message_headers(id),
    super_session_id        VARCHAR(255),
    
    -- Routing (one source → one target per row)
    source_config_name      VARCHAR(255) NOT NULL,
    target_config_name      VARCHAR(255) NOT NULL,
    source_business_type    VARCHAR(50) NOT NULL CHECK (source_business_type IN ('service','process','operation')),
    target_business_type    VARCHAR(50) NOT NULL CHECK (target_business_type IN ('service','process','operation')),
    
    -- Message Classification
    message_type            VARCHAR(100),
    body_class_name         VARCHAR(255) NOT NULL DEFAULT 'GenericMessageBody',
    message_body_id         UUID REFERENCES message_bodies(id),
    
    -- Invocation
    type                    VARCHAR(20) NOT NULL DEFAULT 'Request' CHECK (type IN ('Request','Response')),
    invocation              VARCHAR(20) NOT NULL DEFAULT 'Queue' CHECK (invocation IN ('Queue','InProc')),
    priority                VARCHAR(20) NOT NULL DEFAULT 'Async' CHECK (priority IN ('Async','Sync')),
    
    -- Status & Timing
    status                  VARCHAR(50) NOT NULL DEFAULT 'created',
    is_error                BOOLEAN NOT NULL DEFAULT FALSE,
    error_status            TEXT,
    time_created            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_processed          TIMESTAMPTZ,
    
    -- Delivery
    return_queue_name       VARCHAR(255),
    target_queue_name       VARCHAR(255),
    business_process_id     VARCHAR(255),
    resent                  BOOLEAN NOT NULL DEFAULT FALSE,
    banked                  BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Extensibility
    description             TEXT,
    metadata                JSONB DEFAULT '{}'::jsonb,
    
    -- ACK (denormalized for convenience — also stored as Response header)
    ack_content             BYTEA,
    ack_type                VARCHAR(20)
);

-- Performance indexes
CREATE INDEX idx_mh_session ON message_headers(session_id);
CREATE INDEX idx_mh_project ON message_headers(project_id);
CREATE INDEX idx_mh_source ON message_headers(source_config_name);
CREATE INDEX idx_mh_target ON message_headers(target_config_name);
CREATE INDEX idx_mh_parent ON message_headers(parent_header_id);
CREATE INDEX idx_mh_corresponding ON message_headers(corresponding_header_id);
CREATE INDEX idx_mh_sequence ON message_headers(sequence_num);
CREATE INDEX idx_mh_time ON message_headers(time_created DESC);
CREATE INDEX idx_mh_type ON message_headers(message_type);
CREATE INDEX idx_mh_status ON message_headers(status);
CREATE INDEX idx_mh_body ON message_headers(message_body_id);
CREATE INDEX idx_mh_super_session ON message_headers(super_session_id);
```

### 3.5 How This Fixes the Sequence Diagram

**Before (current broken flow):**

```
portal_messages rows for ADT^A01 through PAS-In → ADT_Router → EPR_Out + RIS_Out:

Row 1: item=PAS-In,     type=service,   source=NULL,   dest=NULL,        session=SES-abc
Row 2: item=ADT_Router,  type=process,   source=NULL,   dest="EPR_Out,RIS_Out", session=SES-abc
Row 3: item=EPR_Out,     type=operation, source=NULL,   dest=NULL,        session=SES-abc
Row 4: item=RIS_Out,     type=operation, source=NULL,   dest=NULL,        session=SES-abc

→ Frontend cannot draw arrows (no source→target linkage per row)
→ Ghost swimlane "EPR_Out,RIS_Out" appears
```

**After (revised design):**

```
message_headers rows for the same flow:

Row 1: seq=1, source=PAS-In(service),     target=ADT_Router(process),  parent=NULL,  session=SES-abc
Row 2: seq=2, source=ADT_Router(process),  target=EPR_Out(operation),   parent=Row1,  session=SES-abc
Row 3: seq=3, source=ADT_Router(process),  target=RIS_Out(operation),   parent=Row1,  session=SES-abc
Row 4: seq=4, source=EPR_Out(operation),   target=EPR_System(external), parent=Row2,  session=SES-abc  [type=Response, corresponding=Row2]
Row 5: seq=5, source=RIS_Out(operation),   target=RIS_System(external), parent=Row3,  session=SES-abc  [type=Response, corresponding=Row3]

→ Frontend draws 5 arrows, each from source swimlane to target swimlane
→ Sequence is unambiguous (seq 1→2→3→4→5)
→ Tree structure: Row1 is parent of Row2+Row3; Row2 is parent of Row4; Row3 is parent of Row5
→ No ghost swimlanes — every source and target is a real item
```

**Visual result (matching IRIS Visual Trace):**

```
  SERVICE        PROCESS         OPERATION       OPERATION
  PAS-In        ADT_Router       EPR_Out         RIS_Out
    │               │               │               │
    │──ADT^A01──→│               │               │     [seq=1]
    │               │──ADT^A01──→│               │     [seq=2]
    │               │──ADT^A01──────────────────→│     [seq=3]
    │               │               │──ACK──→│        [seq=4, Response]
    │               │               │               │──ACK──→│  [seq=5, Response]
```

### 3.6 How Message Storage Changes in Host Code

**HL7TCPService (inbound):**
```python
# Creates session, stores body, creates first header
body_id = await store_message_body(raw_content=data, body_class_name="HL7v2MessageBody", ...)
header_id = await store_message_header(
    session_id=new_session_id,
    parent_header_id=None,              # First in chain
    source_config_name=self.name,       # "PAS-In"
    target_config_name=target_name,     # "ADT_Router" (from TargetConfigNames)
    source_business_type="service",
    target_business_type="process",
    message_body_id=body_id,
    ...
)
# Attach header_id to message object for downstream propagation
message.header_id = header_id
message.session_id = new_session_id
message.body_id = body_id
```

**HL7RoutingEngine (router):**
```python
# For EACH matched target, create a separate header
for target in result.targets:
    target_host = self._production.get_host(target)
    target_type = "operation" if isinstance(target_host, BusinessOperation) else "process"
    
    header_id = await store_message_header(
        session_id=message.session_id,
        parent_header_id=message.header_id,   # Links to inbound header
        source_config_name=self.name,          # "ADT_Router"
        target_config_name=target,             # "EPR_Out" (one per row!)
        source_business_type="process",
        target_business_type=target_type,
        message_body_id=message.body_id,       # Same body, no duplication
        ...
    )
    # Propagate to target
    routed_message = message.with_header_id(header_id)
    await target_host.submit(routed_message)
```

**HL7TCPOperation (outbound):**
```python
# Store outbound leg + ACK response
await update_message_header(
    header_id=message.header_id,
    status="completed",
    time_processed=now,
)
# If ACK received, store response header
if ack_bytes:
    ack_body_id = await store_message_body(raw_content=ack_bytes, ...)
    await store_message_header(
        session_id=message.session_id,
        parent_header_id=message.header_id,
        corresponding_header_id=message.header_id,  # Links ACK to request
        source_config_name=self.name,
        target_config_name=message.source or self.name,
        type="Response",
        message_body_id=ack_body_id,
        ...
    )
```

---

## 4. Cross-Platform Import Compatibility

### 4.1 IRIS Import Mapping

```
Ens.MessageHeader field          → message_headers column
─────────────────────────────────────────────────────────
MessageId                        → sequence_num
SessionId                        → session_id
CorrespondingMessageId           → corresponding_header_id (lookup by sequence_num)
SourceConfigName                 → source_config_name
TargetConfigName                 → target_config_name
SourceBusinessType               → source_business_type (map "BusinessService"→"service")
TargetBusinessType               → target_business_type
MessageBodyClassName             → body_class_name (map "EnsLib.HL7.Message"→"HL7v2MessageBody")
MessageBodyId                    → message_body_id (import body separately)
Type                             → type
Invocation                       → invocation
Priority                         → priority
Status                           → status (map "Completed"→"completed")
IsError                          → is_error
ErrorStatus                      → error_status
TimeCreated                      → time_created
TimeProcessed                    → time_processed
ReturnQueueName                  → return_queue_name
TargetQueueName                  → target_queue_name
BusinessProcessId                → business_process_id
Description                      → description
Resent                           → resent
SuperSession                     → super_session_id
Banked                           → banked
```

### 4.2 Rhapsody Import Mapping

```
Rhapsody MessageObject field     → message_headers column
─────────────────────────────────────────────────────────
messageId                        → id
correlationId                    → session_id
parentMessageId                  → parent_header_id
inputConnector                   → source_config_name
outputConnector                  → target_config_name
messageType                      → message_type
messageBody                      → message_bodies.raw_content
messageProperties                → metadata (JSONB)
processingState                  → status
timestamp                        → time_created
completedTimestamp               → time_processed
errorDetails                     → error_status
```

### 4.3 Mirth Import Mapping

```
Mirth ConnectorMessage field     → message_headers column
─────────────────────────────────────────────────────────
messageId (parent)               → session_id
metaDataId                       → sequence_num
channelName                      → metadata.channel_name
connectorName                    → source_config_name or target_config_name
status                           → status (map "SENT"→"completed")
rawData                          → message_bodies.raw_content (body_class_name="MirthRawBody")
transformedData                  → separate message_body (body_class_name="MirthTransformedBody")
encodedData                      → separate message_body (body_class_name="MirthEncodedBody")
responseData                     → ACK body (type="Response")
sendDate                         → time_created
responseDate                     → time_processed
connectorMap                     → metadata (JSONB)
```

---

## 5. Relationship to Existing Code

### 5.1 What Changes

| Component | Current | Revised |
|-----------|---------|---------|
| `portal_messages` table | Flat log, one row per item | **Replaced by** `message_headers` + `message_bodies` |
| `HL7Message` class | Ad-hoc container with `session_id`, `correlation_id` | Carries `header_id`, `session_id`, `body_id` for propagation |
| `MessageEnvelope` (message_envelope.py) | Unused by HL7 pipeline | **Retired** — replaced by MessageHeader + MessageBody |
| `Message` (message.py) | Well-designed but not used by HL7 hosts | `Envelope` class becomes the in-memory transport; MessageHeader is the persisted trace |
| `message_store.py` | `store_and_complete_message()` | **Replaced by** `store_message_body()` + `store_message_header()` + `update_header_status()` |
| `PortalMessageRepository` | Queries `portal_messages` | **Replaced by** `MessageHeaderRepository` + `MessageBodyRepository` |
| `get_session_trace()` | Reconstructs trace from flat log | Simple query: `SELECT * FROM message_headers WHERE session_id = $1 ORDER BY sequence_num` |
| `buildSequenceDiagram()` (frontend) | Guesses source/target from `source_item`/`destination_item` | Direct mapping: each row IS an arrow (source→target) |

### 5.2 What Stays

| Component | Status |
|-----------|--------|
| `Message` class (message.py) | **Keep** — excellent in-memory message model with Envelope+Payload |
| `HL7Message` class (hl7.py) | **Keep** — add `header_id` and `body_id` fields |
| `ConditionEvaluator` (routing.py) | **Keep** — unchanged |
| `HL7RoutingEngine._evaluate_rules()` | **Keep** — unchanged |
| `MessageSequenceDiagram.tsx` | **Keep** — simplify `buildSequenceDiagram()` since data is now correct |
| `SequenceSwimlane`, `SequenceArrow` | **Keep** — unchanged |

### 5.3 What Gets Simplified

The `core/message.py` `Envelope` class already has `session_id`, `correlation_id`, `causation_id`, `routing.source`, `routing.destination`, `body_class_name`, `message_type`, `priority`, `state`, and `governance`. This is very close to the revised `MessageHeader`. The key gap is:

- `Envelope` is an **in-memory transport object** (not persisted per-leg)
- `MessageHeader` is a **persisted trace record** (one per leg)

The revised design keeps both: `Envelope` travels with the message in-memory; `MessageHeader` is written to the database at each hop. The `Envelope` can be constructed from a `MessageHeader` and vice versa.

---

## 6. Migration Plan

### Phase 1: Schema Migration (non-breaking)
1. Create `message_bodies` and `message_headers` tables alongside existing `portal_messages`
2. Update `message_store.py` to write to both tables during transition
3. Update `get_session_trace()` to read from `message_headers` if available, fall back to `portal_messages`

### Phase 2: Host Code Updates
1. Update `HL7TCPService` to create body + header (one header per target)
2. Update `HL7RoutingEngine` to create one header per matched target
3. Update `HL7TCPOperation` to update header status and create ACK response headers
4. Add `header_id`, `body_id` to `HL7Message` for propagation

### Phase 3: Frontend Updates
1. Simplify `buildSequenceDiagram()` — each `message_header` row is one arrow
2. Add Body tab to message detail panel (render based on `body_class_name`)
3. Add Header tab showing all IRIS-equivalent fields

### Phase 4: Cleanup
1. Migrate historical `portal_messages` data to new tables
2. Drop `portal_messages` table
3. Remove `message_envelope.py` (superseded)

---

## 7. Summary

The current message model has three disconnected layers (`Message`/`Envelope`/`Payload` in message.py, `MessageHeader`/`MessageBody`/`MessageEnvelope` in message_envelope.py, and `portal_messages` flat table) that don't talk to each other. The HL7 pipeline bypasses all of them and uses an ad-hoc `HL7Message` container with `session_id`/`correlation_id` bolted on.

The revised design:
- **Unifies** the model into two clear concepts: `MessageHeader` (persisted trace, one per leg) and `MessageBody` (persisted content, shared across legs)
- **Matches IRIS** field-for-field while also accommodating Rhapsody and Mirth data models
- **Fixes the sequence diagram** by ensuring every arrow corresponds to exactly one `message_header` row with explicit `source_config_name` → `target_config_name`
- **Future-proofs** the body hierarchy to support HL7v2, HL7v3, FHIR R4/R5, DICOM, CSV, XML, JSON, and any custom format
- **Enables cross-platform migration** with documented field mappings for IRIS, Rhapsody, and Mirth

---

*OpenLI HIE — Healthcare Integration Engine*
