# Message Session ID - Enterprise Design Document

**Version:** 1.0
**Date:** 2026-02-12
**Status:** Design Review
**Priority:** CRITICAL - Production Blocker

---

## 1. Executive Summary

### Problem Statement
The IRIS HealthConnect-style Sequence Diagram feature requires **message sessions** to track a single HL7 message as it flows through the integration pipeline. Currently:

- ❌ Messages are stored WITHOUT session_id linkage
- ❌ Each message is isolated (1 session = 1 message)
- ❌ Sequence diagrams show only ONE item instead of the full pipeline
- ❌ New messages aren't linked together

### Business Impact
- **User Experience**: Sequence diagram feature is broken
- **Clinical Workflow**: Cannot trace message flows for troubleshooting
- **Compliance**: Message audit trail is incomplete

### Solution Overview
Implement **end-to-end session_id propagation** through the entire message lifecycle:
1. Generate session_id at entry point (inbound service)
2. Propagate through processing pipeline (routing, operations)
3. Link all related messages with the same session_id

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

### 3.1 Message Flow and Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE SESSION LIFECYCLE                     │
└─────────────────────────────────────────────────────────────────┘

1. INBOUND SERVICE (Entry Point)
   ┌──────────────────┐
   │   HL7TCPService  │
   │    (PAS-In)      │ → Generate: session_id = "SES-{uuid4()}"
   └────────┬─────────┘    Store: portal_messages (session_id)
            │
            ▼
2. BUSINESS PROCESS (Routing)
   ┌──────────────────┐
   │  HL7RoutingEngine│
   │   (ADT_Router)   │ → Inherit: session_id from inbound message
   └────────┬─────────┘    Store: portal_messages (SAME session_id)
            │
            ├─────────────────┬──────────────────┐
            ▼                 ▼                  ▼
3. OUTBOUND OPERATIONS (Exit Points)
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │HL7TCPOperation│ │HL7TCPOperation│ │HL7TCPOperation│
   │   (EPR_Out)  │ │   (RIS_Out)  │ │(Testharness) │
   └──────────────┘  └──────────────┘  └──────────────┘
   → Inherit: session_id from routing message
     Store: portal_messages (SAME session_id)
```

### 3.2 Data Model

#### portal_messages Table (Existing)
```sql
CREATE TABLE portal_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),  -- SESSION TRACKING COLUMN
    correlation_id VARCHAR(255),
    source_item VARCHAR(255),  -- LINKAGE: where message came from
    destination_item TEXT,     -- LINKAGE: where message going to
    received_at TIMESTAMPTZ NOT NULL,
    ...
);

CREATE INDEX idx_portal_messages_session ON portal_messages(session_id);
```

#### Session Identification Logic

**Option A: Explicit Propagation (RECOMMENDED)**
- Session_id passed explicitly through function parameters
- Stored in Message metadata/properties
- Requires code changes in all hosts

**Option B: Implicit Linking (FALLBACK)**
- Post-process messages to build chains using source_item/destination_item
- Assign same session_id to chained messages
- Works for legacy messages without code changes

**DECISION: Hybrid Approach**
- New messages use Option A (explicit)
- Legacy messages use Option B (backfill via migration)

---

## 4. Implementation Design

### 4.1 Core Components

#### Component 1: Message Store Service
**File:** `Engine/api/services/message_store.py`

**Changes:**
```python
async def store_message(
    ...
    session_id: str | None = None,  # NEW PARAMETER
) -> UUID | None:
    """Store message with session tracking."""

    # Session ID generation rules:
    # 1. If provided, use it (propagated from upstream)
    # 2. If not provided, this is an entry point - generate new one
    if not session_id:
        session_id = f"SES-{uuid4()}"

    query = """
        INSERT INTO portal_messages (..., session_id, ...)
        VALUES (..., $N, ...)
    """
    # Store and return message_id
```

#### Component 2: HL7TCPService (Inbound)
**File:** `Engine/li/hosts/hl7.py`

**Session Generation Point:**
```python
class HL7TCPService(BusinessService):
    async def _process_hl7_data(self, data: bytes, ...):
        # STEP 1: Generate session_id for NEW message flow
        session_id = f"SES-{uuid4()}"

        # STEP 2: Store inbound message with session_id
        await _store_inbound_message(..., session_id=session_id)

        # STEP 3: Attach session_id to message for downstream propagation
        message = self._schema.parse(data)
        message._metadata = {"session_id": session_id}  # or similar

        # STEP 4: Forward to targets (session_id will propagate)
        await self.send_to_targets(message)
```

#### Component 3: HL7RoutingEngine (Processing)
**File:** `Engine/li/hosts/routing.py`

**Session Propagation:**
```python
class HL7RoutingEngine(BusinessProcess):
    async def _route_to_target(self, message, target_name):
        # STEP 1: Extract session_id from incoming message
        session_id = getattr(message, '_metadata', {}).get('session_id')

        # STEP 2: Store routing message with SAME session_id
        await self._store_routing_message(
            ...
            session_id=session_id,
            source_item=self.name,  # Current item
            destination_item=target_name,
        )

        # STEP 3: Forward message (session_id preserved in metadata)
        target_host.queue.put_nowait(message)
```

#### Component 4: HL7TCPOperation (Outbound)
**File:** `Engine/li/hosts/hl7.py`

**Session Propagation:**
```python
class HL7TCPOperation(BusinessOperation):
    async def _send_message(self, message):
        # STEP 1: Extract session_id from incoming message
        session_id = getattr(message, '_metadata', {}).get('session_id')

        # STEP 2: Store outbound message with SAME session_id
        await self._store_outbound_message(
            ...
            session_id=session_id,
        )

        # STEP 3: Send to remote system
        await self._send_hl7_tcp(message)
```

### 4.2 Message Metadata Enhancement

**Problem:** Current Message class doesn't have extensible metadata.

**Solution:** Add `_session_id` attribute to HL7Message objects.

```python
# In hl7.py parsing logic
class HL7Message:
    def __init__(self, ...):
        self._session_id: str | None = None  # NEW

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str):
        self._session_id = value
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

