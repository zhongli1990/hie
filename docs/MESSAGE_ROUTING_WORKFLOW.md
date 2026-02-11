# Message Routing Workflow — Implementation Details

**Version:** 1.7.5
**Date:** February 11, 2026
**Status:** Production Ready — E2E Verified

---

## Overview

This document describes the end-to-end message routing workflow implemented in the OpenLI HIE Engine. It covers how HL7v2 messages flow from inbound receipt through routing evaluation to outbound delivery, detailing the implementation of each host item type and the wiring that connects them.

### Architecture Summary

```
External System                                                External System
     │                                                              ▲
     ▼                                                              │
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  HL7TCP     │    │  HL7Routing  │    │  HL7TCP      │    │  HL7TCP      │
│  Service    │───▶│  Engine      │───▶│  Operation   │    │  Operation   │
│  (PAS-In)   │    │  (ADT_Router)│───▶│  (EPR_Out)   │    │  (RIS_Out)   │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
  BusinessService    BusinessProcess    BusinessOperation    BusinessOperation
  MLLP Inbound       Rule Evaluation    MLLP Outbound        MLLP Outbound
```

### IRIS Equivalents

| OpenLI Class | IRIS Class | Role |
|---|---|---|
| `li.hosts.hl7.HL7TCPService` | `EnsLib.HL7.Service.TCPService` | Inbound HL7 receiver |
| `li.hosts.routing.HL7RoutingEngine` | `EnsLib.HL7.MsgRouter.RoutingEngine` | Content-based router |
| `li.hosts.hl7.HL7TCPOperation` | `EnsLib.HL7.Operation.TCPOperation` | Outbound HL7 sender |

---

## 1. HL7TCPService (BusinessService — Inbound)

**File:** `Engine/li/hosts/hl7.py`
**Class:** `HL7TCPService` extends `BusinessService`
**Adapter:** `MLLPInboundAdapter`

### Settings

| Target | Setting | Description | Default |
|--------|---------|-------------|---------|
| Host | `MessageSchemaCategory` | Schema for validation (e.g., "2.4", "PKB") | — |
| Host | `TargetConfigNames` | Comma-separated target hosts | — |
| Host | `AckMode` | ACK generation: "Immediate", "Application", "Never" | Immediate |
| Host | `BadMessageHandler` | Target for invalid messages | — |
| Host | `AlertOnError` | Send alert on errors | true |
| Adapter | `Port` | TCP listen port (required) | — |
| Adapter | `Host` | Bind IP address | 0.0.0.0 |
| Adapter | `MaxConnections` | Max concurrent connections | 100 |
| Adapter | `ReadTimeout` | Read timeout (seconds) | 30 |

### Message Flow

```
1. External system connects via MLLP/TCP
2. MLLPInboundAdapter.on_data_received(raw_bytes)
   └─▶ HL7TCPService.on_message_received(data)
       ├─ Parse HL7 message using schema
       ├─ Validate message structure
       ├─ Generate ACK (AA/AE/AR based on validation)
       ├─ Create HL7Message envelope (raw, parsed, ack, source, errors)
       ├─ Store inbound message in portal_messages (async task)
       └─ Return HL7Message to adapter
3. Adapter returns ACK to sender immediately
4. Adapter calls host.submit(message) → queues message
5. Worker loop picks up message → _process_message(message)
   └─▶ send_to_targets(message)
       ├─ Look up target hosts via self._production.get_host(name)
       └─ Submit message to each target's queue
```

### Key Implementation Details

- **ACK is returned before forwarding**: The MLLP adapter returns the ACK to the external system synchronously, then queues the message for async processing. This ensures fast ACK response times.
- **Message storage**: Inbound messages are stored in `portal_messages` via `_store_inbound_message()` as an `asyncio.create_task()` to avoid blocking the processing pipeline.
- **`send_to_targets()`** (defined in `BusinessService` base class in `Engine/li/hosts/base.py`):
  - Reads `self.target_config_names` (comma-separated string from Host settings)
  - Looks up each target by name via `self._production.get_host(target_name)`
  - Calls `await target_host.submit(message)` to enqueue in the target's `ManagedQueue`

### Portal Message Record

| Field | Value |
|-------|-------|
| `item_name` | e.g., "PAS-In" |
| `item_type` | "service" |
| `direction` | "inbound" |
| `status` | "completed" or "error" |

---

## 2. HL7RoutingEngine (BusinessProcess — Router)

**File:** `Engine/li/hosts/routing.py`
**Class:** `HL7RoutingEngine` extends `BusinessProcess`
**Adapter:** None (process host — no external I/O)

### Settings

| Target | Setting | Description | Default |
|--------|---------|-------------|---------|
| Host | `BusinessRuleName` | Name of the routing rule set | — |
| Host | `Validation` | Validation mode: "None", "Warn", "Error" | None |
| Host | `BadMessageHandler` | Target for invalid messages | — |
| Host | `ResponseFrom` | Which target's response to return | — |
| Host | `AlertOnBadMessage` | Alert on invalid messages | true |
| Host | `TargetConfigNames` | Default targets (fallback if no rule matches) | — |

### Routing Rules

Rules are defined in the Portal UI and stored in `project_routing_rules` table. During `EngineManager.deploy()`, rules are loaded into the engine via `host.add_rule()`.

Each rule has:
- **name**: Human-readable identifier
- **condition_expression**: Condition to evaluate against the message
- **action**: `send`, `transform`, `discard`
- **target_items**: List of target host names
- **priority**: Evaluation order
- **enabled**: Active/inactive toggle

### Condition Syntax

The `ConditionEvaluator` supports two syntaxes:

**Native field references:**
```
{MSH-9.1} = "ADT" AND {MSH-9.2} IN ("A01","A02","A03")
```

**IRIS virtual property paths** (auto-translated at evaluation time):
```
HL7.MSH:MessageType.MessageCode = "ADT" AND HL7.MSH:MessageType.TriggerEvent IN ("A01","A02","A03")
```

**Supported operators:** `=`, `!=`, `<`, `>`, `<=`, `>=`, `Contains`, `StartsWith`, `EndsWith`, `IN`
**Logical operators:** `AND`, `OR`, `NOT`
**Grouping:** Parentheses `( )`

### IRIS Path Translation Map

| IRIS Path | Field Reference | HL7 Position |
|-----------|----------------|--------------|
| `HL7.MSH:MessageType.MessageCode` | `{MSH-9.1}` | MSH field 9, component 1 |
| `HL7.MSH:MessageType.TriggerEvent` | `{MSH-9.2}` | MSH field 9, component 2 |
| `HL7.MSH:MessageType.MessageStructure` | `{MSH-9.3}` | MSH field 9, component 3 |
| `HL7.MSH:SendingApplication` | `{MSH-3}` | MSH field 3 |
| `HL7.MSH:SendingFacility` | `{MSH-4}` | MSH field 4 |
| `HL7.MSH:MessageControlID` | `{MSH-10}` | MSH field 10 |
| `HL7.PID:PatientID` | `{PID-3.1}` | PID field 3, component 1 |
| `HL7.PID:PatientName.FamilyName` | `{PID-5.1}` | PID field 5, component 1 |
| `HL7.PID:Sex` | `{PID-8}` | PID field 8 |
| `HL7.PV1:PatientClass` | `{PV1-2}` | PV1 field 2 |
| `HL7.EVN:EventTypeCode` | `{EVN-1}` | EVN field 1 |

### Message Flow

```
1. Message arrives in queue (submitted by upstream service)
2. Worker loop picks up message → on_message(message)
   ├─ Wrap raw bytes in HL7Message if needed
   ├─ Validate message (if Validation != "None")
   ├─ _evaluate_rules(message)
   │   ├─ For each enabled rule:
   │   │   ├─ _translate_iris_paths(condition) → convert IRIS syntax
   │   │   ├─ _substitute_fields(condition, parsed) → replace {SEG-N} with values
   │   │   └─ _evaluate_expression(substituted) → boolean result
   │   ├─ Collect ALL matching rules' targets (not first-match-wins)
   │   └─ If no rules match → fall back to TargetConfigNames
   ├─ For each matched target:
   │   └─ _route_to_target(message, target, transform)
   │       ├─ Apply transform (if specified, future)
   │       ├─ self._production.get_host(target)
   │       └─ await target_host.submit(message)
   └─ Store routing decision in portal_messages (async task)
```

### Rule Evaluation: All-Match Logic

Unlike IRIS (which uses first-match-wins), the OpenLI routing engine evaluates **all** rules and collects targets from every matching rule. This allows a single message to be routed to multiple targets based on different rule conditions.

**Example:**
```
Rule 1: "ADT_to_EPR"
  Condition: HL7.MSH:MessageType.MessageCode = "ADT" AND
             HL7.MSH:MessageType.TriggerEvent IN ("A01","A02","A03")
  Target: EPR_Out

Rule 2: "ADT_A01_to_RIS"
  Condition: HL7.MSH:MessageType.MessageCode = "ADT" AND
             HL7.MSH:MessageType.TriggerEvent = "A01"
  Target: RIS_Out
```

| Message | Rules Matched | Routed To |
|---------|--------------|-----------|
| ADT^A01 | Rule 1 + Rule 2 | EPR_Out + RIS_Out |
| ADT^A02 | Rule 1 only | EPR_Out only |
| ADT^A03 | Rule 1 only | EPR_Out only |
| ORM^O01 | None | Default targets (if set) |

### Portal Message Record

| Field | Value |
|-------|-------|
| `item_name` | e.g., "ADT_Router" |
| `item_type` | "process" |
| `direction` | "inbound" |
| `status` | "completed" or "no_match" |
| `source_item` | e.g., "PAS-In" |
| `destination_item` | e.g., "EPR_Out,RIS_Out" |

---

## 3. HL7TCPOperation (BusinessOperation — Outbound)

**File:** `Engine/li/hosts/hl7.py`
**Class:** `HL7TCPOperation` extends `BusinessOperation`
**Adapter:** `MLLPOutboundAdapter`

### Settings

| Target | Setting | Description | Default |
|--------|---------|-------------|---------|
| Host | `MessageSchemaCategory` | Schema for validation | — |
| Host | `ReplyCodeActions` | ACK code handling rules | `:*=S` |
| Host | `ArchiveIO` | Archive messages for debugging | false |
| Host | `AlertOnError` | Alert on errors | true |
| Host | `FailureTimeout` | Timeout before marking failed (seconds) | -1 (disabled) |
| Host | `RetryInterval` | Retry interval (seconds) | 5 |
| Adapter | `IPAddress` | Remote host IP/hostname (required) | — |
| Adapter | `Port` | Remote TCP port (required) | — |
| Adapter | `ConnectTimeout` | Connection timeout (seconds) | 10 |
| Adapter | `AckTimeout` | ACK wait timeout (seconds) | 30 |
| Adapter | `MaxRetries` | Maximum send retries | 3 |

### ReplyCodeActions Format

Pattern=Action pairs separated by commas. Patterns match ACK codes from the remote system.

| Pattern | Matches | Example |
|---------|---------|---------|
| `:AA` | Application Accept | Positive ACK |
| `:AE` | Application Error | Error ACK |
| `:AR` | Application Reject | Reject ACK |
| `:?E` | Any error (AE, CE) | — |
| `:?R` | Any reject (AR, CR) | — |
| `:*` | Any code | Catch-all |

| Action | Meaning |
|--------|---------|
| `S` | Success — message delivered |
| `F` | Fail — mark as failed |
| `R` | Retry — re-queue for retry |
| `W` | Warning — log warning, treat as success |

**Example:** `:?R=F,:?E=S,:*=S` — Reject=Fail, Error=Success (log and continue), Any other=Success

### Message Flow

```
1. Message arrives in queue (submitted by upstream router)
2. Worker loop picks up message → on_message(message)
   ├─ Extract raw bytes from HL7Message
   ├─ Send via MLLPOutboundAdapter.send(data)
   │   ├─ Connect to remote host:port (if not connected)
   │   ├─ Frame message with MLLP envelope (VT + data + FS + CR)
   │   ├─ Send and wait for ACK
   │   ├─ Retry on failure (up to MaxRetries)
   │   └─ Return ACK bytes
   ├─ Parse ACK response (extract MSA-1 code)
   ├─ Evaluate ACK code against ReplyCodeActions
   │   ├─ S → return success
   │   ├─ F → raise HL7SendError
   │   ├─ R → raise HL7RetryError
   │   └─ W → log warning, return success
   └─ Store outbound message in portal_messages (async task)
       ├─ On success: status="sent", includes ACK content
       └─ On failure: status="failed", includes error message
```

### Portal Message Record

| Field | Value |
|-------|-------|
| `item_name` | e.g., "EPR_Out" |
| `item_type` | "operation" |
| `direction` | "outbound" |
| `status` | "sent" or "failed" |
| `remote_host` | e.g., "192.168.0.17" |
| `remote_port` | e.g., 35001 |
| `ack_content` | Raw ACK bytes from remote |

---

## 4. Engine Deployment Wiring

**File:** `Engine/api/routes/projects.py`
**Class:** `EngineManager`
**Method:** `deploy(project_id, config)`

When a project is deployed, the `EngineManager` performs three critical wiring steps:

### Step 1: Set Production Reference

```python
for host in engine._all_hosts.values():
    host.project_id = project_id
    host._production = engine
```

Every host gets a reference to the `ProductionEngine` instance. This allows hosts to look up other hosts by name via `self._production.get_host(name)` for inter-host message forwarding.

### Step 2: Wire Connections → TargetConfigNames

Connections in the database store `source_item_id` and `target_item_id` as UUIDs. The deploy method:

1. Builds an `item_id_to_name` lookup from project items
2. Resolves connection UUIDs to item names
3. Builds a `target_map: source_name → [target_names]`
4. Sets `TargetConfigNames` on each source host

```python
# Example result:
# PAS-In.TargetConfigNames = "ADT_Router"
# ADT_Router.TargetConfigNames = "EPR_Out,RIS_Out"
```

### Step 3: Wire Routing Rules → HL7RoutingEngine

For each `HL7RoutingEngine` host in the engine, the deploy method loads all project routing rules:

1. Filters enabled rules
2. Maps action string to `RuleAction` enum
3. Creates one `RoutingRule` per target item (rules can have multiple targets)
4. Calls `host.add_rule(engine_rule)` on the routing engine

---

## 5. Message Storage (Portal Messages)

**File:** `Engine/api/services/message_store.py`

All three host types store messages in the `portal_messages` table for UI visibility:

| Host Type | When Stored | Method |
|-----------|------------|--------|
| HL7TCPService | On message receipt | `_store_inbound_message()` via `asyncio.create_task()` |
| HL7RoutingEngine | After rule evaluation | `_store_routing_message()` via `asyncio.create_task()` |
| HL7TCPOperation | After send (success or failure) | `_store_outbound_message()` via `asyncio.create_task()` |

All storage is fire-and-forget (`asyncio.create_task`) to avoid blocking the message processing pipeline.

### portal_messages Schema (Key Fields)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `project_id` | UUID | Project this message belongs to |
| `item_name` | VARCHAR | Host name (e.g., "PAS-In", "ADT_Router") |
| `item_type` | VARCHAR | "service", "process", or "operation" |
| `direction` | VARCHAR | "inbound" or "outbound" |
| `message_type` | VARCHAR | HL7 message type (e.g., "ADT^A01") |
| `status` | VARCHAR | "completed", "sent", "failed", "error", "no_match" |
| `raw_content` | BYTEA | Raw HL7 message bytes |
| `ack_content` | BYTEA | ACK response bytes |
| `source_item` | VARCHAR | Upstream host name |
| `destination_item` | VARCHAR | Downstream target(s) |
| `remote_host` | VARCHAR | External system IP |
| `remote_port` | INTEGER | External system port |
| `latency_ms` | INTEGER | Processing time |
| `error_message` | TEXT | Error details (if failed) |

---

## 6. End-to-End Example

### Scenario: ADT^A01 from PAS to EPR and RIS

**Project Configuration:**
- **PAS-In** (HL7TCPService) — listens on port 10001
- **ADT_Router** (HL7RoutingEngine) — evaluates routing rules
- **EPR_Out** (HL7TCPOperation) — sends to 192.168.0.17:35001
- **RIS_Out** (HL7TCPOperation) — sends to 192.168.0.17:35002

**Connections:**
- PAS-In → ADT_Router
- ADT_Router → EPR_Out
- ADT_Router → RIS_Out

**Routing Rules:**
1. ADT A01/A02/A03 → EPR_Out
2. ADT A01 → RIS_Out

### Message Flow Timeline

```
T+0ms    External PAS sends ADT^A01 via MLLP to port 10001
T+1ms    PAS-In: MLLPInboundAdapter receives raw bytes
T+2ms    PAS-In: on_message_received() parses HL7, validates, generates ACK
T+3ms    PAS-In: Returns ACK to external PAS (synchronous)
T+3ms    PAS-In: Stores inbound message in portal_messages
T+4ms    PAS-In: submit(HL7Message) → queues for async processing
T+5ms    PAS-In: _process_message() → send_to_targets()
T+5ms    PAS-In: Submits message to ADT_Router queue

T+6ms    ADT_Router: Worker picks up message from queue
T+6ms    ADT_Router: on_message() evaluates routing rules
T+7ms    ADT_Router: Rule "ADT_to_EPR" matches → target EPR_Out
T+7ms    ADT_Router: Rule "ADT_A01_to_RIS" matches → target RIS_Out
T+8ms    ADT_Router: Submits message to EPR_Out queue
T+8ms    ADT_Router: Submits message to RIS_Out queue
T+8ms    ADT_Router: Stores routing decision in portal_messages

T+9ms    EPR_Out: Worker picks up message from queue
T+9ms    EPR_Out: on_message() → adapter.send() via MLLP to 192.168.0.17:35001
T+15ms   EPR_Out: Receives ACK from EPR system
T+15ms   EPR_Out: Evaluates ACK code → Success
T+15ms   EPR_Out: Stores outbound message in portal_messages

T+9ms    RIS_Out: Worker picks up message from queue (parallel)
T+9ms    RIS_Out: on_message() → adapter.send() via MLLP to 192.168.0.17:35002
T+12ms   RIS_Out: Receives ACK from RIS system
T+12ms   RIS_Out: Evaluates ACK code → Success
T+12ms   RIS_Out: Stores outbound message in portal_messages
```

### Portal Messages Tab (after one ADT^A01)

| Item | Type | Direction | Status | Destination |
|------|------|-----------|--------|-------------|
| PAS-In | service | inbound | completed | — |
| ADT_Router | process | inbound | completed | EPR_Out,RIS_Out |
| EPR_Out | operation | outbound | sent | — |
| RIS_Out | operation | outbound | sent | — |

---

## 7. ManagedQueue

**File:** `Engine/core/queues.py`

Each host has a `ManagedQueue` that buffers messages between processing stages. Key methods:

| Method | Usage |
|--------|-------|
| `put_nowait(item)` | Non-blocking enqueue (used by `Host.submit()`) |
| `get()` | Async dequeue (used by worker loop) |
| `join()` | Wait for all items processed (used by graceful shutdown) |

Queue configuration per host:
- **Type:** FIFO (default) or Priority
- **Size:** 1000 (default)
- **Overflow:** Block (default) or Drop

---

*OpenLI HIE — Healthcare Integration Engine*
*Document Version: 1.7.5*
