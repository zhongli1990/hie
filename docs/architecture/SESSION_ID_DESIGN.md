# Message Session ID & Visual Trace — Enterprise Design Document

**Version:** 2.0 (Revised per IRIS Visual Trace Convention)
**Date:** 2026-02-13
**Status:** ⚠️ **REVISED** — Now uses one-row-per-leg model (IRIS `Ens.MessageHeader`)
**Priority:** CRITICAL - Production Blocker

---

## 1. Executive Summary

### Problem Statement
The IRIS HealthConnect-style Visual Trace / Sequence Diagram is broken because our persistence model is fundamentally different from IRIS:

- ❌ **Flat activity log** — `portal_messages` stores one row per item, not one row per message leg
- ❌ **Comma-joined destinations** — Router stores `dest="EPR_Out,RIS_Out"` creating ghost swimlanes
- ❌ **No source→target linkage** — Operation records have `source_item=NULL`, so no arrows can be drawn
- ❌ **No ordering** — All records share timestamps, no sequence number for deterministic ordering
- ❌ **No parent→child chain** — Cannot reconstruct the message tree (which header caused which)

### Root Cause
Session_id propagation alone does NOT fix the diagram. The fundamental issue is that `portal_messages` is a **flat log** (one row per item that touched a message), whereas IRIS `Ens.MessageHeader` is a **per-leg trace** (one row per source→target crossing). Session_id groups the rows, but without per-leg rows, there's nothing to draw.

### Revised Solution
Replace `portal_messages` with two new tables following IRIS convention:
1. **`message_headers`** — One row per message leg (each row = one arrow on the diagram)
2. **`message_bodies`** — Shared message content (multiple headers can reference same body)

Key fields per header row:
- `session_id` — Groups the entire journey
- `parent_header_id` — Links to the header that caused this leg (tree structure)
- `source_config_name` / `target_config_name` — Explicit source→target per row
- `sequence_num` — Auto-increment for deterministic ordering
- `corresponding_header_id` — Links request↔response pairs

---

## 2. Requirements

### Functional Requirements
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | All messages in the same HL7 flow must share one session_id | **MUST** |
| FR-2 | Session_id must be globally unique (format: `SES-{UUID}`) | **MUST** |
| FR-3 | Session_id must survive message transformations | **MUST** |
| FR-4 | Legacy messages must be backfilled with session_id | **MUST** |
| FR-5 | Sequence diagram must display all messages in a session | **MUST** |

### Non-Functional Requirements
| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-1 | Zero performance degradation (<5ms overhead) | **MUST** |
| NFR-2 | Backward compatible with existing productions | **MUST** |
| NFR-3 | Database migration must be idempotent | **MUST** |
| NFR-4 | Session_id visible in logs for debugging | **SHOULD** |

---

## 3. Architecture Design

### 3.1 Message Flow — IRIS Visual Trace Convention

In IRIS, every time a message crosses from one item to another, a new `Ens.MessageHeader` row is created. Our revised design follows this exactly:

```
┌─────────────────────────────────────────────────────────────────┐
│            MESSAGE SESSION — ONE ROW PER LEG                     │
└─────────────────────────────────────────────────────────────────┘

1. INBOUND SERVICE (Entry Point)
   ┌──────────────────┐
   │   HL7TCPService  │  → Generate: session_id = "SES-{uuid4()}"
   │    (PAS-In)      │  → Store body in message_bodies (get body_id)
   └────────┬─────────┘  → Store header: source=PAS-In, target=ADT_Router
            │               parent=NULL, seq=1
            ▼
2. BUSINESS PROCESS (Routing)
   ┌──────────────────┐
   │  HL7RoutingEngine│  → For EACH matched target, create a SEPARATE header:
   │   (ADT_Router)   │
   └────────┬─────────┘
            │
            ├──→ Header: source=ADT_Router, target=EPR_Out,  parent=seq1, seq=2
            │    (same body_id — no content duplication)
            │
            └──→ Header: source=ADT_Router, target=RIS_Out,  parent=seq1, seq=3
                 (same body_id — no content duplication)

3. OUTBOUND OPERATIONS (Exit Points)
   ┌──────────────┐
   │HL7TCPOperation│  → Update header seq=2: status=completed, time_processed
   │   (EPR_Out)  │  → If ACK received: create Response header (seq=4, corresponding=seq2)
   └──────────────┘

   ┌──────────────┐
   │HL7TCPOperation│  → Update header seq=3: status=completed, time_processed
   │   (RIS_Out)  │  → If ACK received: create Response header (seq=5, corresponding=seq3)
   └──────────────┘
```

**Result:** 5 header rows, all sharing `session_id=SES-abc`. Each row = one arrow on the Visual Trace.

### 3.2 Data Model — Revised (Replaces portal_messages)

See [MESSAGE_MODEL.md](MESSAGE_MODEL.md) §Persisted Trace Layer for full schema.

**Summary:**

```sql
-- message_bodies: One row per unique message content
CREATE TABLE message_bodies (
    id UUID PRIMARY KEY, body_class_name, content_type,
    raw_content BYTEA, content_preview, content_size, checksum,
    schema_category, schema_name, message_control_id, ...
);

-- message_headers: One row per message leg (= IRIS Ens.MessageHeader)
CREATE TABLE message_headers (
    id UUID PRIMARY KEY,
    sequence_num BIGSERIAL,              -- Global ordering (= IRIS MessageId)
    project_id UUID NOT NULL,
    session_id VARCHAR(255) NOT NULL,    -- Groups entire journey
    parent_header_id UUID,               -- Tree structure (which header caused this)
    corresponding_header_id UUID,        -- Request↔Response linking
    source_config_name VARCHAR(255),     -- Item that SENT
    target_config_name VARCHAR(255),     -- Item that RECEIVED
    source_business_type VARCHAR(50),    -- "service"|"process"|"operation"
    target_business_type VARCHAR(50),
    message_type VARCHAR(100),           -- "ADT^A01"
    body_class_name VARCHAR(255),        -- "HL7v2MessageBody"
    message_body_id UUID,               -- FK to message_bodies
    type VARCHAR(20) DEFAULT 'Request', -- "Request"|"Response"
    status VARCHAR(50) DEFAULT 'created',
    is_error BOOLEAN DEFAULT FALSE,
    error_status TEXT,
    time_created TIMESTAMPTZ DEFAULT NOW(),
    time_processed TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);
```

### 3.3 Session Identification Logic

**Session_id generation:** At the inbound service (entry point), generate `SES-{uuid4()}`.

**Session_id propagation:** Attach to the in-memory `HL7Message` object. Every downstream host extracts it and passes it when creating header rows.

**Parent_header_id propagation:** Each host stores the header_id of the row that caused this leg. The inbound service's header has `parent_header_id=NULL`. The router's headers have `parent_header_id` pointing to the inbound header. The operation's ACK headers have `parent_header_id` pointing to the router's header.

**Sequence_num ordering:** Auto-increment `BIGSERIAL` — no timestamp collisions, deterministic ordering.

---

## 4. Implementation Design (Revised)

### 4.1 New Storage Functions

**File:** `Engine/api/services/message_store.py` — Replace `store_and_complete_message()` with:

```python
async def store_message_body(
    raw_content: bytes,
    body_class_name: str = "GenericMessageBody",
    content_type: str = "application/octet-stream",
    **protocol_fields,  # schema_category, schema_name, message_control_id, etc.
) -> UUID | None:
    """Store message content in message_bodies. Returns body_id."""
    checksum = hashlib.sha256(raw_content).hexdigest()
    # Dedup: if checksum exists, return existing body_id
    # Otherwise INSERT and return new body_id

async def store_message_header(
    project_id: UUID,
    session_id: str,
    source_config_name: str,
    target_config_name: str,
    source_business_type: str,
    target_business_type: str,
    message_body_id: UUID | None = None,
    parent_header_id: UUID | None = None,
    corresponding_header_id: UUID | None = None,
    message_type: str | None = None,
    body_class_name: str = "GenericMessageBody",
    type: str = "Request",
    status: str = "created",
    **kwargs,
) -> UUID | None:
    """Store one message leg in message_headers. Returns header_id."""
    # INSERT INTO message_headers (...) VALUES (...) RETURNING id

async def update_header_status(
    header_id: UUID,
    status: str,
    is_error: bool = False,
    error_status: str | None = None,
) -> bool:
    """Update a header's status and time_processed."""
    # UPDATE message_headers SET status=$2, time_processed=NOW(), ... WHERE id=$1
```

### 4.2 HL7TCPService (Inbound) — Revised

**File:** `Engine/li/hosts/hl7.py`

```python
class HL7TCPService(BusinessService):
    async def on_message_received(self, data: bytes) -> Any:
        # ... parse, validate, generate ACK ...

        # STEP 1: Generate session_id
        session_id = f"SES-{uuid4()}"

        # STEP 2: Store body (once)
        body_id = await store_message_body(
            raw_content=data,
            body_class_name="HL7v2MessageBody",
            content_type="application/hl7-v2+er7",
            schema_name=message_type,
        )

        # STEP 3: Store header — one row per target
        for target_name in self.target_config_names:
            target_host = self._production.get_host(target_name)
            target_type = _get_business_type(target_host)
            header_id = await store_message_header(
                project_id=project_id,
                session_id=session_id,
                source_config_name=self.name,        # "PAS-In"
                target_config_name=target_name,      # "ADT_Router"
                source_business_type="service",
                target_business_type=target_type,
                message_body_id=body_id,
                parent_header_id=None,               # First in chain
                message_type=message_type,
            )

        # STEP 4: Attach trace IDs to message for downstream propagation
        message = HL7Message(
            raw=data, parsed=parsed, ack=ack,
            session_id=session_id,
            header_id=header_id,   # NEW: for parent chain
            body_id=body_id,       # NEW: for body sharing
        )
        return message
```

### 4.3 HL7RoutingEngine (Router) — Revised

**File:** `Engine/li/hosts/routing.py`

```python
class HL7RoutingEngine(BusinessProcess):
    async def on_message(self, message: Any) -> Any:
        result = self._evaluate_rules(message)

        # For EACH matched target, create a SEPARATE header row
        for target in result.targets:
            target_host = self._production.get_host(target)
            target_type = _get_business_type(target_host)

            header_id = await store_message_header(
                project_id=project_id,
                session_id=message.session_id,
                source_config_name=self.name,          # "ADT_Router"
                target_config_name=target,             # "EPR_Out" (ONE per row!)
                source_business_type="process",
                target_business_type=target_type,
                message_body_id=message.body_id,       # Same body, no duplication
                parent_header_id=message.header_id,    # Links to inbound header
                message_type=message.message_type,
            )

            # Forward with updated header_id
            routed_msg = message.with_header_id(header_id)
            await target_host.submit(routed_msg)
```

### 4.4 HL7TCPOperation (Outbound) — Revised

**File:** `Engine/li/hosts/hl7.py`

```python
class HL7TCPOperation(BusinessOperation):
    async def on_message(self, message: Any) -> Any:
        # ... send via adapter, get ACK ...

        # Update the header that caused this leg
        await update_header_status(
            header_id=message.header_id,
            status="completed",
        )

        # If ACK received, store Response header
        if ack_bytes:
            ack_body_id = await store_message_body(
                raw_content=ack_bytes,
                body_class_name="HL7v2MessageBody",
            )
            await store_message_header(
                project_id=project_id,
                session_id=message.session_id,
                source_config_name=self.name,
                target_config_name=message.source or self.name,
                source_business_type="operation",
                target_business_type="process",
                message_body_id=ack_body_id,
                parent_header_id=message.header_id,
                corresponding_header_id=message.header_id,  # Links ACK→Request
                type="Response",
                status="completed",
            )
```

### 4.5 HL7Message Enhancement

**File:** `Engine/li/hosts/hl7.py`

```python
class HL7Message:
    def __init__(self, ...,
        session_id: str | None = None,
        correlation_id: str | None = None,
        header_id: UUID | None = None,    # NEW: persisted header ID for parent chain
        body_id: UUID | None = None,      # NEW: persisted body ID for sharing
    ):
        ...
        self.header_id = header_id
        self.body_id = body_id

    def with_header_id(self, header_id: UUID) -> HL7Message:
        """Return copy with updated header_id (for downstream propagation)."""
        return HL7Message(
            raw=self.raw, parsed=self.parsed, ack=self.ack,
            received_at=self.received_at, source=self.source,
            validation_errors=self.validation_errors, error=self.error,
            session_id=self.session_id, correlation_id=self.correlation_id,
            header_id=header_id, body_id=self.body_id,
        )
```

---

## 5. Database Migration Strategy

### 5.1 Backfill Logic

**Goal:** Assign session_id to existing messages by chaining them together.

**Algorithm:**
```sql
-- Step 1: Identify message chains using source/destination relationships
WITH RECURSIVE message_chains AS (
    -- Base case: Start with inbound messages (no source_item)
    SELECT
        id,
        project_id,
        item_name,
        source_item,
        destination_item,
        received_at,
        'SES-' || id::text AS session_id,  -- Root session_id
        id AS root_id,
        1 AS level
    FROM portal_messages
    WHERE source_item IS NULL OR source_item = ''

    UNION ALL

    -- Recursive case: Follow destination → source chains
    SELECT
        m.id,
        m.project_id,
        m.item_name,
        m.source_item,
        m.destination_item,
        m.received_at,
        mc.session_id,  -- Inherit parent's session_id
        mc.root_id,
        mc.level + 1
    FROM portal_messages m
    JOIN message_chains mc ON (
        m.source_item = mc.item_name
        AND m.project_id = mc.project_id
        AND m.received_at >= mc.received_at
        AND m.received_at <= mc.received_at + INTERVAL '1 minute'  -- Same flow window
    )
    WHERE m.session_id IS NULL
)
-- Step 2: Update messages with computed session_id
UPDATE portal_messages pm
SET session_id = mc.session_id
FROM message_chains mc
WHERE pm.id = mc.id AND pm.session_id IS NULL;
```

**Migration File:** `scripts/migrations/002_fix_session_id_chains.sql`

---

## 6. Testing Strategy

### 6.1 Unit Tests
| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| UT-1 | Generate session_id at inbound | `session_id = "SES-{UUID}"` format |
| UT-2 | Propagate session_id through routing | Same session_id in routing message |
| UT-3 | Propagate session_id to operations | Same session_id in all operations |

### 6.2 Integration Tests
| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| IT-1 | E2E message flow (Service → Router → 2 Operations) | All 4 messages have SAME session_id |
| IT-2 | Sequence diagram query with session_id | Returns all 4 messages in correct order |
| IT-3 | Migration backfill on 50 existing messages | Chains linked, <10 distinct sessions |

### 6.3 Acceptance Criteria
- [ ] Send 1 HL7 message to PAS-In
- [ ] Verify 4 messages stored: PAS-In, ADT_Router, EPR_Out, RIS_Out
- [ ] All 4 messages have SAME session_id
- [ ] Sequence diagram displays all 4 items with arrows
- [ ] Timing labels show correct latencies

---

## 7. Rollout Plan

### Phase 1: Code Implementation (Day 1)
1. Update message_store.py to accept session_id
2. Update HL7TCPService to generate session_id
3. Update routing engine to propagate session_id
4. Update operations to propagate session_id
5. Unit tests for each component

### Phase 2: Migration (Day 1)
1. Create backfill migration script
2. Test on dev database copy
3. Apply to production database

### Phase 3: Integration Testing (Day 1)
1. Send test messages through full pipeline
2. Verify session_id propagation
3. Test sequence diagram rendering

### Phase 4: Deployment (Day 1)
1. Rebuild Docker images
2. Apply database migration
3. Restart services
4. Smoke test sequence diagram

---

## 8. Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration fails on large datasets | HIGH | Test on copy, add batching logic |
| Performance degradation | MEDIUM | Benchmark before/after, optimize indexes |
| Backward compatibility broken | HIGH | Ensure session_id is optional parameter |
| Complex message flows not chained | MEDIUM | Fallback to time-based grouping |

---

## 9. Success Metrics

- ✅ **100% new messages** have session_id assigned
- ✅ **>95% legacy messages** successfully chained
- ✅ **Sequence diagrams** display average 3-5 items per session
- ✅ **Zero performance regression** in message throughput

---

## 10. Appendix

### A. Session ID Format Specification
```
Format: SES-{UUID}
Example: SES-a1b2c3d4-5e6f-7g8h-9i0j-k1l2m3n4o5p6
Length: 40 characters (fixed)
Uniqueness: Guaranteed via UUID v4
```

### B. Database Indexes
```sql
-- Required for efficient session queries
CREATE INDEX IF NOT EXISTS idx_portal_messages_session
ON portal_messages(session_id);

-- Composite index for message chaining
CREATE INDEX IF NOT EXISTS idx_portal_messages_chain
ON portal_messages(project_id, source_item, destination_item, received_at);
```

---

**Document Owner:** Claude Sonnet 4.5
**Review Status:** PENDING USER APPROVAL
**Next Action:** Implement after design approval

