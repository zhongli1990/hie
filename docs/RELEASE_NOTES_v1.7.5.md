# Release Notes - v1.7.5

**Release Date:** February 11, 2026
**Code Name:** "End-to-End Message Routing"
**Status:** Production Ready — E2E Verified

---

## Release Highlights

This release delivers **fully functional end-to-end HL7 message routing** through the OpenLI HIE Engine. Messages now flow from inbound services through routing engines to outbound operations, with content-based routing rules, IRIS-compatible condition syntax, and full message audit trail in the Portal.

### Key Achievements

1. **End-to-End Message Flow** — Messages received by inbound services (e.g., PAS-In) are now correctly forwarded through connections to routing engines (e.g., ADT_Router) and on to outbound operations (e.g., EPR_Out, RIS_Out)
2. **Content-Based Routing** — Routing rules with IRIS-compatible condition expressions are evaluated correctly, routing messages to the right targets based on HL7 message content
3. **Full Audit Trail** — All host types (service, process, operation) now store message records in `portal_messages`, visible in the Portal Messages tab
4. **Portal Routing Rules UI** — Full CRUD management of routing rules directly on the project page

---

## What's New

### Engine — Message Routing Pipeline

**Inter-Host Message Forwarding:**
- `Host._production` reference allows any host to look up and submit messages to other hosts by name
- `BusinessService.send_to_targets()` forwards messages from inbound services to configured target hosts
- `HL7TCPService._process_message()` calls `send_to_targets()` after receiving and ACK-ing a message
- `HL7RoutingEngine._route_to_target()` submits routed messages to target hosts via the production engine

**Engine Deployment Wiring (`EngineManager.deploy()`):**
- Resolves connection `source_item_id`/`target_item_id` UUIDs to item names
- Sets `TargetConfigNames` on source hosts from the connection map
- Loads project routing rules into `HL7RoutingEngine` instances via `add_rule()`
- Sets `_production` reference on all hosts for inter-host messaging

**IRIS-Compatible Condition Evaluation:**
- `ConditionEvaluator._translate_iris_paths()` converts IRIS virtual property paths to field references
- Supports `HL7.MSH:MessageType.MessageCode`, `HL7.MSH:MessageType.TriggerEvent`, and 20+ other IRIS paths
- Maps to standard `{MSH-9.1}`, `{MSH-9.2}` field reference syntax
- Covers MSH, PID, PV1, EVN segments

**All-Match Rule Evaluation:**
- `_evaluate_rules()` now evaluates ALL rules and collects targets from every match
- Replaces previous first-match-wins logic that prevented multi-target routing
- Example: ADT^A01 correctly routes to both EPR_Out (via ADT rule) and RIS_Out (via A01-specific rule)

**Message Storage for All Host Types:**
- `HL7TCPService`: Stores inbound messages on receipt (already existed)
- `HL7RoutingEngine`: New — stores routing decisions with source/destination info
- `HL7TCPOperation`: New — stores outbound sends with ACK content, remote host/port, and error details

**ManagedQueue Enhancements:**
- Added `put_nowait()` for non-blocking enqueue (used by `Host.submit()`)
- Added `join()` for graceful shutdown (used by `Host._graceful_stop()`)

### Engine — API Models

**Routing Rules:**
- `RoutingRuleCreate`, `RoutingRuleUpdate`, `RoutingRuleResponse` now accept `target_items` as `list[str]` (item names) instead of `list[UUID]`
- Fixed JSONB parsing for `target_items` in `get_full_config` and `RoutingRuleRepository` methods

### Portal — Routing Rules UI

**Project Page — Routing Rules Tab:**
- Full CRUD for routing rules directly on the project page
- Create/edit modal with fields: name, condition expression, action, target items, priority, enabled toggle
- Rules table with condition preview, target badges, priority ordering
- Delete confirmation dialog
- Rule count badge on tab header

### Documentation

**New:** `docs/MESSAGE_ROUTING_WORKFLOW.md`
- Complete implementation details for each host item type
- Message flow diagrams and timelines
- Settings reference tables for HL7TCPService, HL7RoutingEngine, HL7TCPOperation
- IRIS path translation map
- Condition syntax reference
- Engine deployment wiring explanation
- End-to-end example with portal message records

---

## Bug Fixes

### Critical Fixes

1. **Messages not forwarded between hosts** (root cause of e2e failure)
   - **Problem:** PAS-In received messages and returned ACKs but never forwarded to ADT_Router
   - **Root Cause:** `EngineManager.deploy()` did not wire connections or routing rules; hosts had no `_production` reference; `send_to_targets()` was a stub
   - **Fix:** Implemented full forwarding pipeline across 4 files
   - **Files:** `Engine/api/routes/projects.py`, `Engine/li/hosts/base.py`, `Engine/li/hosts/hl7.py`, `Engine/li/hosts/routing.py`

2. **Connection UUID resolution**
   - **Problem:** Connections stored `source_item_id`/`target_item_id` as UUIDs but deploy code looked for `source_name`/`target_name`
   - **Fix:** Build `item_id_to_name` lookup from project items, resolve UUIDs to names
   - **File:** `Engine/api/routes/projects.py`

3. **IRIS condition syntax not recognized**
   - **Problem:** Routing rules used IRIS-style paths (`HL7.MSH:MessageType.MessageCode`) but evaluator only understood `{MSH-9.1}` syntax — conditions silently failed, all messages fell to default targets
   - **Fix:** Added `_translate_iris_paths()` with `IRIS_FIELD_MAP` covering MSH, PID, PV1, EVN segments
   - **File:** `Engine/li/hosts/routing.py`

4. **First-match-wins routing prevented multi-target delivery**
   - **Problem:** `_evaluate_rules()` returned on first matching rule — ADT^A01 only routed to EPR_Out, never reached RIS rule
   - **Fix:** Changed to all-match logic that collects targets from every matching rule
   - **File:** `Engine/li/hosts/routing.py`

5. **ADT_Router invisible in Portal Messages tab**
   - **Problem:** `HL7RoutingEngine` processed messages but never stored to `portal_messages`
   - **Fix:** Added `_store_routing_message()` with source/destination tracking
   - **File:** `Engine/li/hosts/routing.py`

6. **EPR_Out/RIS_Out invisible in Portal Messages tab**
   - **Problem:** `HL7TCPOperation.on_message()` sent via MLLP but never stored to `portal_messages` (only manual test sends stored)
   - **Fix:** Added `_store_outbound_message()` for both success and failure paths
   - **File:** `Engine/li/hosts/hl7.py`

7. **`ManagedQueue` missing `put_nowait` and `join`**
   - **Problem:** `Host.submit()` called `self._queue.put_nowait()` which didn't exist on `ManagedQueue`
   - **Fix:** Added `put_nowait()` and `join()` methods
   - **File:** `Engine/core/queues.py`

8. **Routing rules API rejected item names**
   - **Problem:** API models expected `target_items` as `list[UUID]` but UI and agent tools send item names as strings
   - **Fix:** Changed to `list[str]`, fixed JSONB parsing in repository
   - **Files:** `Engine/api/models.py`, `Engine/api/repositories.py`

### Minor Fixes

- Fixed extra closing parenthesis in Portal configure page
- Fixed JSONB parsing for `target_items` in `get_full_config`

---

## Files Changed

### New Files (1)
- `docs/MESSAGE_ROUTING_WORKFLOW.md` — Workflow implementation documentation

### Modified Files (8)

**Engine Core:**
- `Engine/core/queues.py` — `put_nowait()`, `join()` methods on ManagedQueue
- `Engine/li/hosts/base.py` — `_production` reference, `send_to_targets()` implementation
- `Engine/li/hosts/hl7.py` — `_process_message()` forwarding, `_store_outbound_message()`
- `Engine/li/hosts/routing.py` — IRIS path translation, all-match evaluation, `_store_routing_message()`
- `Engine/api/routes/projects.py` — Connection/rule wiring in `deploy()`
- `Engine/api/models.py` — `target_items` as `list[str]`
- `Engine/api/repositories.py` — JSONB parsing fixes

**Portal:**
- `Portal/src/app/(app)/projects/[id]/page.tsx` — Routing Rules tab with CRUD

---

## Commits (8)

| Hash | Description |
|------|-------------|
| `f40430f` | fix(portal): remove extra closing parenthesis in configure page |
| `d40a021` | feat(portal): add Routing Rules tab to project page with full CRUD |
| `f1441dc` | fix(engine): routing rules accept item names (strings) not UUIDs |
| `a328cea` | fix(engine): add put_nowait and join to ManagedQueue |
| `2dd17d2` | feat(engine): implement end-to-end message routing pipeline |
| `bdebce1` | feat(engine): add message storage for HL7RoutingEngine (ADT_Router) |
| `54f6f03` | feat(engine): add message storage for HL7TCPOperation outbound sends |
| `2f0dacb` | fix(engine): fix routing rule evaluation — IRIS path translation + all-match logic |

---

## Testing

### E2E Verification (Manual)

| Test | Result |
|------|--------|
| PAS-In receives ADT^A01, returns ACK | Passed |
| PAS-In forwards to ADT_Router | Passed |
| ADT_Router evaluates rules, routes to EPR_Out + RIS_Out | Passed |
| EPR_Out sends via MLLP to 192.168.0.17:35001 | Passed |
| RIS_Out sends via MLLP to 192.168.0.17:35002 | Passed |
| ADT^A02 routes only to EPR_Out (not RIS_Out) | Passed |
| All 4 items appear in Portal Messages tab | Passed |
| Routing rules CRUD in Portal UI | Passed |

---

## Migration Guide

### From v1.7.4 to v1.7.5

```bash
# Rebuild Manager with routing fixes
docker compose build hie-manager

# Restart Manager
docker compose up -d hie-manager

# Re-deploy your project in the Portal (Deploy & Start)
# This is required to wire connections and routing rules into the engine
```

No database migrations required. No breaking changes.

---

## Statistics

- **9 files changed** (1 new, 8 modified)
- **~400 insertions**
- **~20 deletions**
- **8 commits**
- **8 bugs fixed** (3 critical, 3 major, 2 minor)

---

*OpenLI HIE — Healthcare Integration Engine*
*Release v1.7.5 — February 11, 2026*
