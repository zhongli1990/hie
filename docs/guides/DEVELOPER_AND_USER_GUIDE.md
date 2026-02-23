# OpenLI HIE — Developer & User Guide

**Version:** 1.9.6
**Date:** February 2026
**Status:** Production-Ready Enterprise Integration Engine

---

## Part 1: User Guide — Portal Configuration (Zero Code)

> *This section is for **Integration Configurators** — NHS integration engineers who configure message flows entirely through the Portal UI, identical to configuring productions in IRIS Management Portal or channels in Mirth Administrator.*

---

## Overview

**OpenLI HIE** is a fully configurable, enterprise-grade healthcare integration engine for NHS acute trusts. Like InterSystems IRIS, Orion Rhapsody, and Mirth Connect, **all standard integrations are configured through the Portal UI** — zero coding required.

This guide walks through a complete, production-ready NHS integration scenario with:

- **3 Inbound Services** — HL7 v2.3 MLLP, FHIR R4 REST, HL7 File Reader
- **2 Business Processes** — Validation/Transformation, Content-Based Routing
- **3 Outbound Operations** — RIS HL7 v2.5.1, Lab HL7 v2.4, File Writer

### Platform Comparison

| Capability | IRIS | Rhapsody | Mirth | **OpenLI HIE** |
|------------|------|----------|-------|----------------|
| Configuration method | Management Portal | Rhapsody IDE | Admin Console | **Portal UI (web)** |
| Zero-code workflows | Yes | Yes | Yes | **Yes — 100% config** |
| HL7 v2.x (MLLP) | Yes | Yes | Yes | **Yes — v2.3 to v2.8** |
| FHIR R4 (REST/JSON) | Yes | Yes | Yes | **Yes — native** |
| File I/O | Yes | Yes | Yes | **Yes — watch/write** |
| Visual workflow | BPL Editor | Route Designer | Channel view | **Visual Designer** |
| Hot reload | Partial | No | No | **Yes — zero downtime** |
| True multiprocessing | No (JVM) | No (JVM) | No (JVM) | **Yes — OS processes** |
| AI-assisted config | No | No | No | **Yes — GenAI Agent** |
| License cost | $$$$$ | $$$$ | Free/$$ | **Free (AGPL/Commercial)** |

### IRIS Naming Convention Alignment

OpenLI HIE follows IRIS conventions so that IRIS developers feel immediately at home:

| IRIS Concept | OpenLI HIE Equivalent | Notes |
|-------------|----------------------|-------|
| Namespace | Workspace | Organizational container |
| Production | Project | Deployable unit of integration |
| Business Service | Service (Inbound) | Receives messages from external systems |
| Business Process | Process | Validates, transforms, routes messages |
| Business Operation | Operation (Outbound) | Sends messages to external systems |
| Adapter | Adapter | Protocol-specific I/O (MLLP, HTTP, File) |
| Host Settings | Host Settings | Business logic configuration |
| Adapter Settings | Adapter Settings | Transport/protocol configuration |
| TargetConfigNames | TargetConfigNames | Downstream item routing (identical) |
| ReplyCodeActions | ReplyCodeActions | ACK/NACK handling (identical syntax) |
| Production Config | Project Config | JSON (HIE) vs XML (IRIS) |
| Class Registry | Class Registry | Dynamic class lookup (identical pattern) |
| `EnsLib.HL7.Service.TCPService` | `li.hosts.hl7.HL7TCPService` | Auto-aliased — IRIS names work too |

---

## Quickstart: Create Your First Workflow Route (10 Minutes)

> *This walkthrough creates a minimal but fully functional HL7 message route — verified end-to-end in v1.9.6. It mirrors the simplest possible IRIS production: one inbound service, one routing engine, and two outbound operations.*

### What You'll Build

```
External PAS ──MLLP──▶ PAS-In ──▶ ADT_Router ──▶ EPR_Out ──MLLP──▶ EPR System
                       (Service)   (Process)   └──▶ RIS_Out ──MLLP──▶ RIS System
```

- **PAS-In** receives ADT messages on port 10001
- **ADT_Router** evaluates routing rules and forwards to the right targets
- **EPR_Out** sends ADT A01/A02/A03 to the EPR system
- **RIS_Out** sends only ADT A01 to the RIS system

---

### Step 1: Create Workspace & Project

1. Open Portal → Sidebar → **Projects**
2. Click **"Create Workspace"**
   - Name: `My_Hospital`
   - Display Name: My Hospital
3. Inside the workspace, click **"Create Project"**
   - Name: `ADT_Route`
   - Display Name: ADT Message Route

---

### Step 2: Add the Inbound Service (PAS-In)

1. Project page → Items tab → **"Add Item"**
2. Select **HL7 TCP Service** from the class dropdown
3. Fill in:

| Field | Value |
|-------|-------|
| Name | `PAS-In` |
| Class | `HL7 TCP Service` (li.hosts.hl7.HL7TCPService) |
| Enabled | Yes |
| Pool Size | 1 |

**Adapter Settings:**

| Setting | Value |
|---------|-------|
| Port | `10001` |

**Host Settings:**

| Setting | Value |
|---------|-------|
| MessageSchemaCategory | `2.4` |
| AckMode | `Immediate` |

4. Click **Save**

---

### Step 3: Add the Routing Engine (ADT_Router)

1. Items tab → **"Add Item"**
2. Select **HL7 Routing Engine** from the class dropdown
3. Fill in:

| Field | Value |
|-------|-------|
| Name | `ADT_Router` |
| Class | `HL7 Routing Engine` (li.hosts.routing.HL7RoutingEngine) |
| Enabled | Yes |
| Pool Size | 1 |

4. Click **Save**

---

### Step 4: Add Outbound Operations (EPR_Out, RIS_Out)

**EPR_Out:**

1. Items tab → **"Add Item"**
2. Select **HL7 TCP Operation**
3. Fill in:

| Field | Value |
|-------|-------|
| Name | `EPR_Out` |
| Class | `HL7 TCP Operation` (li.hosts.hl7.HL7TCPOperation) |
| Enabled | Yes |

**Adapter Settings:**

| Setting | Value |
|---------|-------|
| IPAddress | `192.168.0.17` *(your EPR system IP)* |
| Port | `35001` |

**Host Settings:**

| Setting | Value |
|---------|-------|
| ReplyCodeActions | `:?R=F,:?E=S,:*=S` |

4. Click **Save**

**RIS_Out:** Repeat with:

| Field | Value |
|-------|-------|
| Name | `RIS_Out` |
| IPAddress | `192.168.0.17` *(your RIS system IP)* |
| Port | `35002` |
| ReplyCodeActions | `:?R=F,:?E=S,:*=S` |

---

### Step 5: Create Connections

Wire the items together so messages flow in the right direction.

1. Project page → Connections tab → **"Add Connection"**

| # | Source | Target |
|---|--------|--------|
| 1 | `PAS-In` | `ADT_Router` |
| 2 | `ADT_Router` | `EPR_Out` |
| 3 | `ADT_Router` | `RIS_Out` |

These connections tell the engine: PAS-In forwards to ADT_Router, and ADT_Router can forward to EPR_Out and RIS_Out.

---

### Step 6: Create Routing Rules

Routing rules control *which* messages go to *which* targets based on message content.

1. Project page → **Routing Rules** tab → **"New Rule"**

**Rule 1 — ADT A01/A02/A03 → EPR:**

| Field | Value |
|-------|-------|
| Name | `ADT_to_EPR` |
| Condition | `HL7.MSH:MessageType.MessageCode = "ADT" AND HL7.MSH:MessageType.TriggerEvent IN ("A01","A02","A03")` |
| Action | `send` |
| Target Items | `EPR_Out` |
| Priority | `1` |
| Enabled | Yes |

**Rule 2 — ADT A01 only → RIS:**

| Field | Value |
|-------|-------|
| Name | `ADT_A01_to_RIS` |
| Condition | `HL7.MSH:MessageType.MessageCode = "ADT" AND HL7.MSH:MessageType.TriggerEvent = "A01"` |
| Action | `send` |
| Target Items | `RIS_Out` |
| Priority | `2` |
| Enabled | Yes |

> **Note:** The engine evaluates ALL rules (not first-match-wins). An ADT^A01 message will match both rules and route to both EPR_Out and RIS_Out. An ADT^A02 only matches Rule 1 and routes to EPR_Out only.

---

### Step 7: Deploy & Start

1. Click **"Deploy & Start"** on the project page
2. The engine will:
   - Create all host instances
   - Wire connections (set TargetConfigNames from your connections)
   - Load routing rules into ADT_Router
   - Start all items

You should see:
```
✅ PAS-In         — listening on port 10001 (MLLP)
✅ ADT_Router     — routing engine started, 2 rules loaded
✅ EPR_Out        — ready to send to 192.168.0.17:35001
✅ RIS_Out        — ready to send to 192.168.0.17:35002

Production Status: RUNNING (4/4 items active)
```

---

### Step 8: Send a Test Message

Send an ADT^A01 message to PAS-In on port 10001 using any MLLP client, or use the Portal test feature on an outbound operation.

**Sample ADT^A01:**
```
MSH|^~\&|PAS|HOSPITAL|HIE|HIE|20260211120000||ADT^A01|MSG00001|P|2.4
EVN|A01|20260211120000
PID|1||PAT123^^^MRN||Smith^John^Q||19800101|M|||123 Main St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
```

**Expected result:**

| Step | Item | What Happens |
|------|------|-------------|
| 1 | PAS-In | Receives message, parses HL7, returns ACK to sender |
| 2 | ADT_Router | Evaluates rules — Rule 1 matches (A01) → EPR_Out, Rule 2 matches (A01) → RIS_Out |
| 3 | EPR_Out | Sends via MLLP to 192.168.0.17:35001, receives ACK |
| 4 | RIS_Out | Sends via MLLP to 192.168.0.17:35002, receives ACK |

**Check the Messages tab** — you should see 4 records:

| Item | Type | Direction | Status |
|------|------|-----------|--------|
| PAS-In | service | inbound | completed |
| ADT_Router | process | inbound | completed |
| EPR_Out | operation | outbound | sent |
| RIS_Out | operation | outbound | sent |

**Now send an ADT^A02 (transfer):**
```
MSH|^~\&|PAS|HOSPITAL|HIE|HIE|20260211130000||ADT^A02|MSG00002|P|2.4
EVN|A02|20260211130000
PID|1||PAT456^^^MRN||Smith^Jane^A||19750315|F|||456 Oak Ave^^London^^EC1A 1BB^UK
PV1|1|I|WARD2^ROOM3^BED2|U|||67890^Jones^Robert|||SUR||||||||V789012
```

**Expected:** Routes to EPR_Out only (Rule 1 matches A02, Rule 2 does not — it only matches A01). RIS_Out should **not** receive this message.

---

### Step 9: Verify Routing Logic

| Message Type | Rules Matched | Routed To |
|-------------|--------------|-----------|
| ADT^A01 | ADT_to_EPR + ADT_A01_to_RIS | EPR_Out + RIS_Out |
| ADT^A02 | ADT_to_EPR only | EPR_Out only |
| ADT^A03 | ADT_to_EPR only | EPR_Out only |
| ORM^O01 | None | Default targets (if set) or no routing |

### Condition Syntax Reference

You can write conditions in either format:

**IRIS-style (recommended for IRIS developers):**
```
HL7.MSH:MessageType.MessageCode = "ADT"
HL7.MSH:MessageType.TriggerEvent IN ("A01","A02","A03")
HL7.PID:PatientName.FamilyName = "Smith"
```

**Field reference style:**
```
{MSH-9.1} = "ADT"
{MSH-9.2} IN ("A01","A02","A03")
{PID-5.1} = "Smith"
```

**Operators:** `=`, `!=`, `<`, `>`, `<=`, `>=`, `Contains`, `StartsWith`, `EndsWith`, `IN`
**Logic:** `AND`, `OR`, `NOT`, parentheses `( )`

For the complete IRIS path translation map and implementation details, see [Message Routing Workflow](../reference/MESSAGE_ROUTING_WORKFLOW.md).

---

> *Now that you've built your first route, the next section walks through a full NHS production scenario with 8 items, validation, transformation, and multi-protocol inbound.*

---

## Clinical Scenario: St. Thomas' Hospital

**Integration Requirement:**  
Connect Cerner Millennium PAS, a GP FHIR endpoint, and batch HL7 file drops with downstream clinical systems (RIS, ICE Lab) and a local file archive — with full audit trail and NHS compliance.

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     St. Thomas' Hospital — ADT Production                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INBOUND SERVICES (3)                                                        │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │ Cerner.PAS.Receiver  │ │ GP.FHIR.Receiver    │ │ Batch.File.Reader   │   │
│  │ HL7 v2.3 MLLP       │ │ FHIR R4 JSON/REST   │ │ HL7 File Watcher    │   │
│  │ Port: 2575           │ │ Port: 8443 (HTTPS)  │ │ /data/inbound/*.hl7 │   │
│  │ (BusinessService)    │ │ (BusinessService)    │ │ (BusinessService)    │   │
│  └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘   │
│             │                        │                        │              │
│             └────────────┬───────────┴────────────────────────┘              │
│                          ▼                                                    │
│  BUSINESS PROCESSES (2)                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ NHS.Validation.Process  (BusinessProcess)                             │   │
│  │ • NHS Number validation (Modulus 11)                                  │   │
│  │ • PDS demographic lookup & enrichment                                 │   │
│  │ • Duplicate admission detection                                       │   │
│  │ • UK postcode validation                                              │   │
│  │ • FHIR→HL7 normalisation (converts FHIR Patient to HL7 ADT)         │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                              ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ADT.Content.Router  (BusinessProcess — HL7 Routing Engine)            │   │
│  │ • Rule 1: ADT A01/A02/A03/A08 → RIS (v2.5.1) + Lab (v2.4) + File  │   │
│  │ • Rule 2: ORM O01 (Radiology)  → RIS (v2.5.1) + File               │   │
│  │ • Rule 3: ORM O01 (Lab)        → Lab (v2.4) + File                  │   │
│  │ • Rule 4: FHIR-origin msgs     → All targets + File                  │   │
│  │ • Default: Archive to file only                                       │   │
│  └───────┬──────────────────────┬──────────────────────┬────────────────┘   │
│          ▼                      ▼                      ▼                     │
│  OUTBOUND OPERATIONS (3)                                                     │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │ RIS.HL7.Sender       │ │ Lab.HL7.Sender      │ │ Archive.File.Writer │   │
│  │ HL7 v2.5.1 MLLP     │ │ HL7 v2.4 MLLP       │ │ /data/outbound/     │   │
│  │ ris.nhs:2576         │ │ lab.nhs:2577         │ │ Timestamped files   │   │
│  │ (BusinessOperation)  │ │ (BusinessOperation)  │ │ (BusinessOperation) │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Total: 8 items** — 3 Services + 2 Processes + 3 Operations  
**Comparable IRIS Production:** Would have identical item count and wiring.

---

## Step 1: Create Workspace & Project

### 1.1 Create Workspace

**Portal Navigation:** Sidebar → Projects → "Create Workspace"

| Field | Value | IRIS Equivalent |
|-------|-------|-----------------|
| Name | `St_Thomas_Hospital` | Namespace name |
| Display Name | St. Thomas' Hospital | Namespace description |
| Description | Main acute trust integration hub | — |
| Tags | NHS, Acute Trust, South London | — |

**IRIS equivalent:** `zn "ST-THOMAS"` — switching to a namespace.

### 1.2 Create Project (Production)

**Portal Navigation:** Inside workspace → "Create Project"

| Field | Value | IRIS Equivalent |
|-------|-------|-----------------|
| Name | `ADT_Integration` | Production name |
| Display Name | ADT Integration Production | Production description |
| Description | Patient ADT + Orders integration | — |
| Version | 1.0.0 | — |

**IRIS equivalent:** Creating a new Production class `STH.ADT.Production` in Studio.

---

## Step 2: Add Inbound Services (3)

### 2.1 Cerner PAS HL7 v2.3 MLLP Receiver

**Portal Navigation:** Project → Items → "Add Item" → Service

This is the primary inbound — receives real-time ADT and Order messages from Cerner Millennium PAS over MLLP/TCP, exactly like `EnsLib.HL7.Service.TCPService` in IRIS.

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `Cerner.PAS.Receiver` |
| | Display Name | Cerner Millennium PAS — HL7 v2.3 |
| | Class | HL7 TCP Service *(dropdown)* |
| | Enabled | Yes |
| | Pool Size | 4 |
| | Category | Inbound \| PAS |
| **Adapter** | Port | `2575` |
| | IP Address | `0.0.0.0` |
| | Job Per Connection | Yes |
| | Read Timeout | `30` seconds |
| | Stay Connected | `-1` (keep alive) |
| **Host** | Message Schema Category | `2.3` |
| | TargetConfigNames | `NHS.Validation.Process` |
| | ACK Mode | `Application` |
| | Archive IO | Yes |
| **Enterprise** | Execution Mode | `Multiprocess` |
| | Worker Count | `4` |
| | Queue Type | `Priority` |
| | Queue Size | `10000` |
| | Overflow Strategy | `Drop Oldest` |
| | Restart Policy | `Always` |
| | Max Restarts | `100` |
| | Restart Delay | `10` seconds |
| | Messaging Pattern | `Async Reliable` |

**Click:** Save → Deploy → Start  
**Result:** Service listening on port 2575, accepting MLLP connections from Cerner PAS.

**IRIS equivalent configuration:**
```
// In IRIS Management Portal → Production → Add Business Service
Class: EnsLib.HL7.Service.TCPService
Name: Cerner.PAS.Receiver
Port: 2575
TargetConfigNames: NHS.Validation.Process
MessageSchemaCategory: 2.3
AckMode: App
```

---

### 2.2 GP FHIR R4 REST/JSON Receiver

**Portal Navigation:** Project → Items → "Add Item" → Service

This service receives FHIR R4 Patient/Encounter resources as JSON over HTTPS from GP systems. No IRIS equivalent exists natively — this is an HIE advantage.

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `GP.FHIR.Receiver` |
| | Display Name | GP Connect — FHIR R4 JSON/REST |
| | Class | FHIR HTTP Service *(dropdown)* |
| | Enabled | Yes |
| | Pool Size | 2 |
| | Category | Inbound \| FHIR |
| **Adapter** | Port | `8443` |
| | SSL/TLS | Yes (NHS Spine TLS) |
| | Base Path | `/fhir/r4` |
| | Accepted Resources | `Patient, Encounter, Bundle` |
| | Authentication | `Bearer Token` (NHS Identity) |
| **Host** | FHIR Version | `R4` |
| | TargetConfigNames | `NHS.Validation.Process` |
| | Normalise to HL7 | Yes *(converts FHIR→HL7 ADT before routing)* |
| | Archive IO | Yes |
| **Enterprise** | Execution Mode | `Async` |
| | Queue Type | `FIFO` |
| | Queue Size | `5000` |
| | Restart Policy | `Always` |
| | Max Restarts | `50` |

**Click:** Save → Deploy → Start  
**Result:** HTTPS endpoint live at `https://hie.sth.nhs.uk:8443/fhir/r4`

**Sample inbound FHIR request:**
```json
POST /fhir/r4/Patient HTTP/1.1
Host: hie.sth.nhs.uk:8443
Content-Type: application/fhir+json
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...

{
  "resourceType": "Patient",
  "identifier": [
    {
      "system": "https://fhir.nhs.uk/Id/nhs-number",
      "value": "9876543210"
    }
  ],
  "name": [
    {
      "family": "Smith",
      "given": ["John", "Q"]
    }
  ],
  "gender": "male",
  "birthDate": "1980-01-01",
  "address": [
    {
      "line": ["123 High St"],
      "city": "London",
      "postalCode": "SW1A 1AA",
      "country": "UK"
    }
  ]
}
```

The service normalises this to an HL7 ADT A28 (add person information) before passing to the validation process, so downstream routing rules work uniformly on HL7 messages regardless of inbound protocol.

---

### 2.3 Batch HL7 File Reader

**Portal Navigation:** Project → Items → "Add Item" → Service

This service watches a directory for HL7 files dropped by batch processes (e.g., overnight PAS extracts), exactly like `EnsLib.HL7.Service.FileService` in IRIS.

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `Batch.File.Reader` |
| | Display Name | PAS Batch File Reader |
| | Class | HL7 File Service *(dropdown)* |
| | Enabled | Yes |
| | Pool Size | 1 |
| | Category | Inbound \| File |
| **Adapter** | File Path | `/data/inbound` |
| | File Spec | `*.hl7` |
| | Polling Interval | `5` seconds |
| | Archive Path | `/data/inbound/processed` |
| | Recursive | No |
| | Delete After Read | No *(move to archive)* |
| **Host** | Message Schema Category | `2.3` |
| | TargetConfigNames | `NHS.Validation.Process` |
| **Enterprise** | Execution Mode | `Async` |
| | Queue Type | `FIFO` |
| | Queue Size | `1000` |
| | Restart Policy | `On Failure` |
| | Max Restarts | `5` |

**Click:** Save → Deploy → Start  
**Result:** Watching `/data/inbound/` for `*.hl7` files every 5 seconds.

**IRIS equivalent:**
```
Class: EnsLib.HL7.Service.FileService
Name: Batch.File.Reader
FilePath: /data/inbound
FileSpec: *.hl7
ArchivePath: /data/inbound/processed
TargetConfigNames: NHS.Validation.Process
```

---

## Step 3: Add Business Processes (2)

### 3.1 NHS Validation & Transformation Process

**Portal Navigation:** Project → Items → "Add Item" → Process

This process validates every inbound message (regardless of source) and enriches it with PDS data. It is the equivalent of a custom `Ens.BusinessProcessBPL` in IRIS that calls out to PDS.

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `NHS.Validation.Process` |
| | Display Name | NHS Validation, Enrichment & Normalisation |
| | Class | NHS Validation Process *(from class library)* |
| | Enabled | Yes |
| | Pool Size | 4 |
| | Category | Process \| Validation |
| **Host** | Validate NHS Number | Yes *(Modulus 11 check digit)* |
| | Enrich From PDS | Yes |
| | PDS Endpoint | `https://pds.spine.nhs.uk/api` |
| | PDS Timeout | `5` seconds |
| | Check Duplicates | Yes |
| | Duplicate Window | `60` seconds |
| | Validate Postcode | Yes *(UK format)* |
| | FHIR Normalisation | Yes *(FHIR→HL7 if not already HL7)* |
| | TargetConfigNames | `ADT.Content.Router` |
| | On Validation Fail | `NACK + route to Exception Queue` |
| **Enterprise** | Execution Mode | `Thread Pool` |
| | Worker Count | `4` |
| | Queue Type | `Priority` |
| | Queue Size | `5000` |
| | Overflow Strategy | `Block` |
| | Restart Policy | `Always` |
| | Max Restarts | `1000` |
| | Messaging Pattern | `Sync Reliable` |
| | Message Timeout | `10` seconds |

**Click:** Save → Deploy → Start

**What this process does (step by step):**

```
1. RECEIVE message from any inbound service
2. IF message is FHIR JSON:
   → Convert FHIR Patient/Encounter to HL7 ADT A28/A01
   → Set MSH.SendingApplication = original FHIR source
3. VALIDATE NHS Number (PID-3):
   → Modulus 11 check digit verification
   → IF invalid → NACK to sender, route to Exception Queue, STOP
4. ENRICH from PDS:
   → Call NHS PDS API with NHS Number
   → Merge demographics (name, address, GP) into PID segment
   → Add ZPD segment with PDS trace metadata
5. CHECK DUPLICATES:
   → Query 60-second sliding window for same NHS Number + Event Type
   → IF duplicate → Log warning, route to Exception Queue, STOP
6. VALIDATE POSTCODE (PID-11):
   → UK postcode regex validation
   → IF invalid → Add ZVL|PostcodeValidation|WARN segment, CONTINUE
7. FORWARD validated message to ADT.Content.Router
```

**IRIS equivalent:** A custom `Ens.BusinessProcessBPL` class with call activities to PDS lookup service and validation logic in ObjectScript.

---

### 3.2 ADT Content-Based Router

**Portal Navigation:** Project → Items → "Add Item" → Process

This is the core routing engine — it examines each validated message and routes it to the correct outbound operations with the appropriate HL7 version transformation. Directly equivalent to `EnsLib.HL7.MsgRouter.RoutingEngine` in IRIS.

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `ADT.Content.Router` |
| | Display Name | ADT Content-Based Routing Engine |
| | Class | HL7 Routing Engine *(dropdown)* |
| | Enabled | Yes |
| | Pool Size | 2 |
| | Category | Process \| Routing |
| **Host** | Business Rule Name | `ADT_Routing_Rules` |
| | Validation | `Error` |
| | Rule Logging | `All Rules` |
| **Enterprise** | Execution Mode | `Thread Pool` |
| | Worker Count | `2` |
| | Queue Type | `FIFO` |
| | Queue Size | `5000` |
| | Overflow Strategy | `Block` *(never drop clinical messages)* |
| | Restart Policy | `Always` |
| | Max Restarts | `1000` |
| | Restart Delay | `30` seconds |
| | Messaging Pattern | `Sync Reliable` |
| | Message Timeout | `60` seconds |

**Click:** Save → Deploy → Start

#### Routing Rules (configured in Portal Rule Builder)

**Rule 1 — ADT Events → RIS + Lab + File Archive**
```
Name:       Route ADT to RIS and Lab
Priority:   1
Condition:  MSH.MessageType.MessageCode = "ADT"
            AND MSH.MessageType.TriggerEvent IN ("A01","A02","A03","A08")
Actions:
  1. Transform: HL7 v2.3 → v2.5.1  →  Send to: RIS.HL7.Sender
  2. Transform: HL7 v2.3 → v2.4    →  Send to: Lab.HL7.Sender
  3. Send original                  →  Send to: Archive.File.Writer
```

**Rule 2 — Radiology Orders → RIS + File Archive**
```
Name:       Route Radiology Orders to RIS
Priority:   2
Condition:  MSH.MessageType.MessageCode = "ORM"
            AND MSH.MessageType.TriggerEvent = "O01"
            AND OBR.UniversalServiceIdentifier CONTAINS "RAD"
Actions:
  1. Transform: HL7 v2.3 → v2.5.1  →  Send to: RIS.HL7.Sender
  2. Send original                  →  Send to: Archive.File.Writer
```

**Rule 3 — Lab Orders → Lab + File Archive**
```
Name:       Route Lab Orders to Lab
Priority:   3
Condition:  MSH.MessageType.MessageCode = "ORM"
            AND MSH.MessageType.TriggerEvent = "O01"
            AND OBR.UniversalServiceIdentifier CONTAINS "LAB"
Actions:
  1. Transform: HL7 v2.3 → v2.4    →  Send to: Lab.HL7.Sender
  2. Send original                  →  Send to: Archive.File.Writer
```

**Rule 4 — FHIR-Origin Messages → All Targets + File**
```
Name:       Route FHIR-normalised messages
Priority:   4
Condition:  MSH.SendingApplication CONTAINS "FHIR"
Actions:
  1. Transform: HL7 v2.3 → v2.5.1  →  Send to: RIS.HL7.Sender
  2. Transform: HL7 v2.3 → v2.4    →  Send to: Lab.HL7.Sender
  3. Send original                  →  Send to: Archive.File.Writer
```

**Default Rule — Archive Only**
```
Name:       Default Archive
Priority:   99
Condition:  (always)
Actions:
  1. Send original                  →  Send to: Archive.File.Writer
```

#### Transformation Definitions

**Transform: HL7 v2.3 → v2.5.1 (for RIS)**
```yaml
Name: "v23_to_v251_RIS"
Source Schema: 2.3
Target Schema: 2.5.1
Field Mappings:
  MSH.SendingApplication:    "HIE"
  MSH.SendingFacility:       source.MSH.SendingFacility
  MSH.ReceivingApplication:  "RIS"
  MSH.ReceivingFacility:     source.MSH.ReceivingFacility
  MSH.VersionID:             "2.5.1"
  MSH.MessageStructure:      "ADT_A01"  # Required in v2.5+
  PID.*:                     source.PID.*  # Copy all patient data
  PV1.*:                     source.PV1.*  # Copy all visit data
  ZAU.1:                     source.MSH.MessageControlID  # Audit trail
  ZAU.2:                     NOW()  # Transformation timestamp
```

**Transform: HL7 v2.3 → v2.4 (for Lab)**
```yaml
Name: "v23_to_v24_Lab"
Source Schema: 2.3
Target Schema: 2.4
Field Mappings:
  MSH.SendingApplication:    "HIE"
  MSH.ReceivingApplication:  "ICE-LAB"
  MSH.VersionID:             "2.4"
  PID.*:                     source.PID.*
  PV1.*:                     source.PV1.*
  OBR.*:                     source.OBR.*  # Preserve order details
  ZAU.1:                     source.MSH.MessageControlID
  ZAU.2:                     NOW()
```

**IRIS equivalent:** Two DTL (Data Transformation Language) classes created in Studio's visual DTL editor, with field-by-field mapping.

---

## Step 4: Add Outbound Operations (3)

### 4.1 RIS HL7 v2.5.1 MLLP Sender

**Portal Navigation:** Project → Items → "Add Item" → Operation

Sends transformed HL7 v2.5.1 messages to the Radiology Information System over MLLP. Equivalent to `EnsLib.HL7.Operation.TCPOperation` in IRIS.

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `RIS.HL7.Sender` |
| | Display Name | RIS Radiology — HL7 v2.5.1 Sender |
| | Class | HL7 TCP Operation *(dropdown)* |
| | Enabled | Yes |
| | Pool Size | 2 |
| | Category | Outbound \| RIS |
| **Adapter** | IP Address | `ris.sth.nhs.uk` |
| | Port | `2576` |
| | Connect Timeout | `30` seconds |
| | Reconnect Retry | `5` |
| | Reconnect Interval | `10` seconds |
| | Stay Connected | `-1` (persistent) |
| **Host** | ReplyCodeActions | `:?R=F,:?E=S,:~=S,:?A=C,:*=S` |
| | Retry Interval | `5` seconds |
| | Failure Timeout | `15` seconds |
| | Archive IO | Yes |
| **Enterprise** | Execution Mode | `Thread Pool` |
| | Worker Count | `2` |
| | Queue Type | `FIFO` |
| | Queue Size | `5000` |
| | Overflow Strategy | `Block` |
| | Restart Policy | `Always` |
| | Max Restarts | `100` |

**ReplyCodeActions explained** (identical to IRIS syntax):
- `:?R=F` — If reply contains error code R → mark as **F**ailed
- `:?E=S` — If reply contains error code E → **S**uspend message
- `:~=S` — If reply is malformed → **S**uspend
- `:?A=C` — If reply is ACK → mark **C**ompleted
- `:*=S` — Anything else → **S**uspend

**Click:** Save → Deploy → Start  
**Result:** Connected to `ris.sth.nhs.uk:2576`, ready to send.

---

### 4.2 Lab HL7 v2.4 MLLP Sender

**Portal Navigation:** Project → Items → "Add Item" → Operation

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `Lab.HL7.Sender` |
| | Display Name | ICE Laboratory — HL7 v2.4 Sender |
| | Class | HL7 TCP Operation *(dropdown)* |
| | Enabled | Yes |
| | Pool Size | 2 |
| | Category | Outbound \| Lab |
| **Adapter** | IP Address | `lab.sth.nhs.uk` |
| | Port | `2577` |
| | Connect Timeout | `30` seconds |
| | Reconnect Retry | `5` |
| | Stay Connected | `-1` |
| **Host** | ReplyCodeActions | `:?R=F,:?E=S,:~=S,:?A=C,:*=S` |
| | Retry Interval | `5` seconds |
| | Failure Timeout | `15` seconds |
| | Archive IO | Yes |
| **Enterprise** | Execution Mode | `Thread Pool` |
| | Worker Count | `2` |
| | Queue Type | `FIFO` |
| | Queue Size | `5000` |
| | Overflow Strategy | `Block` |
| | Restart Policy | `Always` |
| | Max Restarts | `100` |

**Click:** Save → Deploy → Start  
**Result:** Connected to `lab.sth.nhs.uk:2577`, ready to send.

---

### 4.3 Archive File Writer

**Portal Navigation:** Project → Items → "Add Item" → Operation

Writes all processed messages (original + transformed) to timestamped files for compliance audit. Equivalent to `EnsLib.HL7.Operation.FileOperation` in IRIS.

| Section | Setting | Value |
|---------|---------|-------|
| **Basic** | Name | `Archive.File.Writer` |
| | Display Name | Local Archive — File Writer |
| | Class | File Operation *(dropdown)* |
| | Enabled | Yes |
| | Pool Size | 1 |
| | Category | Outbound \| Archive |
| **Adapter** | File Path | `/data/outbound` |
| | File Name Pattern | `%Y%m%d/%H%M%S_%f.hl7` |
| | Create Directories | Yes |
| | Overwrite | No |
| **Enterprise** | Queue Type | `FIFO` |
| | Queue Size | `50000` |
| | Overflow Strategy | `Drop Oldest` *(archive not mission-critical)* |
| | Restart Policy | `Always` |

**Click:** Save → Deploy → Start  
**Result:** Writing to `/data/outbound/YYYYMMDD/HHMMSS_nnnnn.hl7`

---

## Step 5: Configure Connections (Visual Designer)

**Portal Navigation:** Project → Configure → Visual Designer

Wire the items together by dragging connections:

| # | Source | Target | Type |
|---|--------|--------|------|
| 1 | `Cerner.PAS.Receiver` | `NHS.Validation.Process` | Async Reliable |
| 2 | `GP.FHIR.Receiver` | `NHS.Validation.Process` | Async Reliable |
| 3 | `Batch.File.Reader` | `NHS.Validation.Process` | Async Reliable |
| 4 | `NHS.Validation.Process` | `ADT.Content.Router` | Sync Reliable |
| 5 | `ADT.Content.Router` | `RIS.HL7.Sender` | Sync Reliable |
| 6 | `ADT.Content.Router` | `Lab.HL7.Sender` | Sync Reliable |
| 7 | `ADT.Content.Router` | `Archive.File.Writer` | Async Reliable |

**Visual Designer shows:**
```
Cerner.PAS.Receiver ──┐
GP.FHIR.Receiver    ──┼──► NHS.Validation.Process ──► ADT.Content.Router ──┬──► RIS.HL7.Sender
Batch.File.Reader   ──┘                                                     ├──► Lab.HL7.Sender
                                                                             └──► Archive.File.Writer
```

**IRIS equivalent:** Identical wiring in the Production Configuration page, setting TargetConfigNames on each item.

---

## Step 6: Deploy & Start Production

**Portal Navigation:** Project → "Deploy & Start"

```
Deploying ADT_Integration to Engine...

Starting all enabled items:
  ✅ Cerner.PAS.Receiver      — port 2575 listening (MLLP)
  ✅ GP.FHIR.Receiver          — port 8443 listening (HTTPS/FHIR)
  ✅ Batch.File.Reader         — watching /data/inbound/*.hl7
  ✅ NHS.Validation.Process    — 4 workers active
  ✅ ADT.Content.Router        — rule engine initialised, 5 rules loaded
  ✅ RIS.HL7.Sender            — connected to ris.sth.nhs.uk:2576
  ✅ Lab.HL7.Sender            — connected to lab.sth.nhs.uk:2577
  ✅ Archive.File.Writer       — ready, writing to /data/outbound/

Production Status: ✅ RUNNING (8/8 items active)
```

**IRIS equivalent:** Production → "Start" button, or `do ##class(Ens.Director).StartProduction("STH.ADT.Production")`

---

## Step 7: Test Message Flow

### Test 1: HL7 ADT A01 from Cerner PAS

**Portal Navigation:** Project → Testing → "Send Test Message"

**Select target:** `Cerner.PAS.Receiver`

**Input (HL7 v2.3):**
```
MSH|^~\&|PAS|STH|HIE|STH|20260211120000||ADT^A01|MSG0001|P|2.3
EVN|A01|20260211120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
```

**Message Journey (shown in Portal):**
```
1. ✅ Received by Cerner.PAS.Receiver              [  0ms]
2. ✅ Validated by NHS.Validation.Process           [250ms]
     • NHS Number 9876543210: VALID (Modulus 11 ✓)
     • PDS Lookup: VERIFIED — demographics enriched
     • Duplicate check: PASSED (no prior A01 in 60s window)
     • Postcode SW1A 1AA: VALID
3. ✅ Routed by ADT.Content.Router                  [ 50ms]
     • Rule 1 matched: ADT A01 → RIS + Lab + Archive
     • Transform v2.3→v2.5.1 applied for RIS
     • Transform v2.3→v2.4 applied for Lab
4. ✅ Sent to RIS.HL7.Sender                        [120ms]
     • ACK received: MSA|AA|MSG0001-RIS
5. ✅ Sent to Lab.HL7.Sender                        [130ms]
     • ACK received: MSA|AA|MSG0001-LAB
6. ✅ Written by Archive.File.Writer                [  5ms]
     • File: /data/outbound/20260211/120000_00001.hl7

Total Journey: 555ms  |  Status: ✅ SUCCESS
```

**Outbound to RIS (HL7 v2.5.1):**
```
MSH|^~\&|HIE|STH|RIS|STH|20260211120000||ADT^A01^ADT_A01|MSG0001-RIS|P|2.5.1
EVN|A01|20260211120000|||
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1^^^^STH||||12345^Jones^Sarah|||MED||||||||V123456
ZAU|MSG0001|20260211120000|v23_to_v251_RIS
```

**Outbound to Lab (HL7 v2.4):**
```
MSH|^~\&|HIE|STH|ICE-LAB|STH|20260211120000||ADT^A01|MSG0001-LAB|P|2.4
EVN|A01|20260211120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
ZAU|MSG0001|20260211120000|v23_to_v24_Lab
```

### Test 2: FHIR Patient from GP System

**Select target:** `GP.FHIR.Receiver`

**Input (FHIR R4 JSON):**
```json
{
  "resourceType": "Patient",
  "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9876543210"}],
  "name": [{"family": "Smith", "given": ["John"]}],
  "gender": "male",
  "birthDate": "1980-01-01"
}
```

**Message Journey:**
```
1. ✅ Received by GP.FHIR.Receiver                 [  0ms]
     • Parsed as FHIR R4 Patient resource
     • Normalised to HL7 ADT A28 (add person information)
2. ✅ Validated by NHS.Validation.Process           [200ms]
     • NHS Number: VALID
     • PDS enrichment applied
3. ✅ Routed by ADT.Content.Router                  [ 40ms]
     • Rule 4 matched: FHIR-origin → All targets + Archive
4. ✅ Sent to RIS (v2.5.1), Lab (v2.4), Archive    [250ms]

Total Journey: 490ms  |  Status: ✅ SUCCESS
```

### Test 3: Batch HL7 File

**Drop file:** `/data/inbound/overnight_extract_20260211.hl7`

```
1. ✅ Picked up by Batch.File.Reader               [  0ms]
     • File moved to /data/inbound/processed/
2. ✅ Validated → Routed → Delivered                [600ms]
     • Same journey as Test 1
```

---

## Step 8: Monitor Production

**Portal Navigation:** Sidebar → Dashboard / Monitoring

### Real-Time Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  ADT Integration Production          Status: 🟢 RUNNING         │
│  Uptime: 4h 32m    Messages: 2,847   Failed: 7   Rate: 99.75% │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Item                        Status  Queue     Workers  msg/hr  │
│  ─────────────────────────────────────────────────────────────  │
│  Cerner.PAS.Receiver         🟢 RUN   45/10000   4/4     380   │
│  GP.FHIR.Receiver            🟢 RUN    2/5000    2/2      45   │
│  Batch.File.Reader           🟢 RUN    0/1000    1/1      12   │
│  NHS.Validation.Process      🟢 RUN   18/5000    4/4     437   │
│  ADT.Content.Router          🟢 RUN   12/5000    2/2     430   │
│  RIS.HL7.Sender              🟢 RUN   28/5000    2/2     290   │
│  Lab.HL7.Sender              🟢 RUN   22/5000    2/2     285   │
│  Archive.File.Writer         🟢 RUN  156/50000   1/1     430   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Alerts:                                                         │
│  ⚠️  RIS.HL7.Sender: Auto-restarted 1× (connection timeout)    │
│  ℹ️  NHS.Validation.Process: 7 messages rejected (invalid NHS#) │
│  ✅  All critical items running normally                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 9: Hot Reload & Failure Recovery

### Hot Reload (Zero Downtime)

**Scenario:** Increase RIS sender pool size under load.

```
Portal → RIS.HL7.Sender → Edit → Pool Size: 2 → 4 → "Save & Reload"

🔄 Hot reloading RIS.HL7.Sender...
✅ Configuration updated (queue preserved)
✅ Workers scaled: 2 → 4
✅ Zero messages lost, zero downtime
```

**IRIS equivalent:** Changing pool size in Management Portal and clicking "Apply" — but IRIS requires a production restart for most changes. HIE does not.

### Auto-Restart Recovery

**Scenario:** RIS system goes down for maintenance.

```
14:00  RIS.HL7.Sender: Connection refused → State: ERROR
14:00  Engine: Auto-restart scheduled (delay: 10s, policy: Always)
14:00  Attempt 1: Connection refused
14:00  Attempt 2: Connection refused
...
14:15  RIS comes back online
14:15  Attempt 15: ✅ Connected
14:15  State: RUNNING → Draining 847 queued messages
14:19  Queue empty → Normal operation resumed

Messages lost: 0  |  Manual intervention: None
```

---

## Part 2: Developer Guide — Custom Extensions (Python)

> *This section is for **Platform Engineers** who need to extend HIE with custom Python classes, equivalent to writing ObjectScript classes in IRIS Studio.*

---

## Writing Custom Host Classes

### Custom Business Process Example

**Equivalent to:** Creating a custom `Ens.BusinessProcessBPL` subclass in IRIS Studio.

```python
# File: custom/nhs/validation_process.py

from Engine.li.hosts.base import BusinessProcess
from Engine.li.registry.class_registry import register_host

@register_host("custom.nhs.NHSValidationProcess")
class NHSValidationProcess(BusinessProcess):
    """
    NHS-specific validation and enrichment process.
    
    Equivalent to a custom Ens.BusinessProcessBPL in IRIS that:
    - Validates NHS Numbers (Modulus 11)
    - Calls PDS for demographic enrichment
    - Detects duplicate admissions
    - Validates UK postcodes
    
    All settings are configurable via Portal UI — no code changes
    needed to adjust validation behaviour.
    """
    
    # Configurable settings (appear as form fields in Portal)
    SETTINGS = {
        "ValidateNHSNumber": {"type": "bool", "default": True, "category": "Validation"},
        "EnrichFromPDS": {"type": "bool", "default": True, "category": "Enrichment"},
        "PDSEndpoint": {"type": "str", "default": "https://pds.spine.nhs.uk/api", "category": "Enrichment"},
        "PDSTimeout": {"type": "float", "default": 5.0, "category": "Enrichment"},
        "CheckDuplicates": {"type": "bool", "default": True, "category": "Validation"},
        "DuplicateWindow": {"type": "int", "default": 60, "category": "Validation"},
        "ValidatePostcode": {"type": "bool", "default": True, "category": "Validation"},
    }
    
    async def on_process_input(self, request):
        """
        Main processing method — called for every inbound message.
        
        IRIS equivalent: OnRequest() method in a BusinessProcess class.
        """
        message = request.body
        
        # 1. Validate NHS Number
        if self.get_setting("ValidateNHSNumber"):
            nhs_number = self._extract_nhs_number(message)
            if not self._validate_nhs_modulus11(nhs_number):
                self._log.error("invalid_nhs_number", nhs_number=nhs_number)
                return self._generate_nack(message, "AE", "Invalid NHS Number")
        
        # 2. Enrich from PDS
        if self.get_setting("EnrichFromPDS"):
            pds_data = await self._call_pds(nhs_number)
            if pds_data:
                message = self._enrich_demographics(message, pds_data)
        
        # 3. Check duplicates
        if self.get_setting("CheckDuplicates"):
            window = self.get_setting("DuplicateWindow")
            if await self._is_duplicate(message, window_seconds=window):
                self._log.warning("duplicate_detected", nhs_number=nhs_number)
                return self._generate_nack(message, "AR", "Duplicate admission")
        
        # 4. Validate postcode
        if self.get_setting("ValidatePostcode"):
            postcode = self._extract_postcode(message)
            if postcode and not self._validate_uk_postcode(postcode):
                self._log.warning("invalid_postcode", postcode=postcode)
                # Continue but flag — don't reject for bad postcode
                message = self._add_z_segment(message, "ZVL", ["PostcodeValidation", "WARN"])
        
        # 5. Forward to routing engine
        await self.send_request_async(
            self.get_setting("TargetConfigNames", "ADT.Content.Router"),
            message
        )
        
        return self._generate_ack(message)
    
    def _validate_nhs_modulus11(self, nhs_number: str) -> bool:
        """NHS Number check digit validation (Modulus 11 algorithm)."""
        if not nhs_number or len(nhs_number) != 10 or not nhs_number.isdigit():
            return False
        weights = [10, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(int(nhs_number[i]) * weights[i] for i in range(9))
        remainder = total % 11
        check_digit = 11 - remainder
        if check_digit == 11:
            check_digit = 0
        if check_digit == 10:
            return False  # Invalid — no valid check digit
        return check_digit == int(nhs_number[9])
    
    def _validate_uk_postcode(self, postcode: str) -> bool:
        """UK postcode format validation."""
        import re
        pattern = r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$'
        return bool(re.match(pattern, postcode.strip().upper()))
    
    async def _call_pds(self, nhs_number: str) -> dict | None:
        """Call NHS PDS API for patient demographics."""
        import aiohttp
        endpoint = self.get_setting("PDSEndpoint")
        timeout = self.get_setting("PDSTimeout")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{endpoint}/Patient/{nhs_number}",
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    headers={"Accept": "application/fhir+json"}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            self._log.warning("pds_lookup_failed", error=str(e))
        return None
    
    # ... helper methods for message manipulation
```

### Custom Business Service Example

**Equivalent to:** Creating a custom `Ens.BusinessService` subclass in IRIS.

```python
# File: custom/nhs/fhir_service.py

from Engine.li.hosts.base import BusinessService
from Engine.li.registry.class_registry import register_host

@register_host("custom.nhs.FHIRHTTPService")
class FHIRHTTPService(BusinessService):
    """
    FHIR R4 HTTP/REST inbound service.
    
    Accepts FHIR resources as JSON over HTTPS and normalises
    them to HL7 v2 messages for uniform downstream processing.
    
    IRIS equivalent: Custom EnsLib.HTTP.Service subclass with
    FHIR parsing logic in OnProcessInput().
    """
    
    SETTINGS = {
        "Port": {"type": "int", "default": 8443, "category": "Adapter"},
        "BasePath": {"type": "str", "default": "/fhir/r4", "category": "Adapter"},
        "FHIRVersion": {"type": "str", "default": "R4", "category": "Host"},
        "AcceptedResources": {"type": "str", "default": "Patient,Encounter,Bundle", "category": "Host"},
        "NormaliseToHL7": {"type": "bool", "default": True, "category": "Host"},
        "SSLEnabled": {"type": "bool", "default": True, "category": "Adapter"},
    }
    
    async def on_process_input(self, request):
        """Process inbound FHIR resource."""
        fhir_resource = request.body  # Parsed JSON
        resource_type = fhir_resource.get("resourceType")
        
        # Validate resource type
        accepted = self.get_setting("AcceptedResources").split(",")
        if resource_type not in accepted:
            return {"status": 400, "error": f"Resource type {resource_type} not accepted"}
        
        # Normalise to HL7 if configured
        if self.get_setting("NormaliseToHL7"):
            hl7_message = self._fhir_to_hl7(fhir_resource)
        else:
            hl7_message = fhir_resource  # Pass through as-is
        
        # Forward to target
        await self.send_request_async(
            self.get_setting("TargetConfigNames"),
            hl7_message
        )
        
        return {"status": 200, "message": "Accepted"}
    
    def _fhir_to_hl7(self, fhir_resource: dict) -> bytes:
        """Convert FHIR Patient/Encounter to HL7 ADT message."""
        resource_type = fhir_resource.get("resourceType")
        
        if resource_type == "Patient":
            return self._patient_to_adt_a28(fhir_resource)
        elif resource_type == "Encounter":
            return self._encounter_to_adt_a01(fhir_resource)
        else:
            return self._bundle_to_hl7(fhir_resource)
    
    # ... FHIR→HL7 conversion methods
```

### Deploying Custom Classes

**Option A: Docker Volume Mount (recommended for development)**
```yaml
# docker-compose.yml
services:
  hie-engine:
    volumes:
      - ./custom:/app/custom:ro
```

**Option B: Portal Upload (future — v1.8.0)**
```
Portal → Admin → Extensions → Upload Python Class → Select file → Register
```

**Option C: Build into Docker Image (recommended for production)**
```dockerfile
FROM hie-engine:v1.7.3
COPY custom/ /app/custom/
```

After deployment, the custom class appears in the Portal's class dropdown when adding new items, just like a custom ObjectScript class appears in IRIS Management Portal after compilation.

---

## Part 3: GenAI Agent Guide — AI-Assisted Configuration (v1.9.6)

> *This section is for developers who want to use the **GenAI Agent** to accelerate configuration — a capability no other integration engine offers. Everything described below has been verified end-to-end with live API calls.*

---

### Architecture

The GenAI Agent is powered by three microservices:

| Service | Port | Role |
|---------|------|------|
| **Agent Runner** | 9340 (internal 8082) | Runs the LLM agent loop, manages tools, enforces RBAC |
| **Prompt Manager** | 9341 (internal 8083) | Stores prompt templates, skills, audit logs, approvals |
| **Manager API** | 9302 (internal 8081) | Backend for workspace/project/item CRUD operations |

The Portal's Agents page connects to the Agent Runner via **SSE (Server-Sent Events)** for real-time streaming of tool calls and responses.

### Available Tools (24 hie_* tools)

All tools call the Manager API. The agent selects which tools to call based on the user's natural language request.

| Tool | What It Does | API Call |
|------|-------------|----------|
| `hie_list_workspaces` | List available workspaces | GET /api/workspaces |
| `hie_create_workspace` | Create a new workspace | POST /api/workspaces |
| `hie_list_projects` | List projects in a workspace | GET /api/workspaces/{ws}/projects |
| `hie_create_project` | Create a new project | POST /api/workspaces/{ws}/projects |
| `hie_get_project` | Get full project config | GET /api/workspaces/{ws}/projects/{p} |
| `hie_create_item` | Add service/process/operation | POST /api/projects/{p}/items |
| `hie_update_item` | Modify item settings | PUT /api/projects/{p}/items/{i} |
| `hie_delete_item` | Remove an item | DELETE /api/projects/{p}/items/{i} |
| `hie_create_connection` | Wire two items together | POST /api/projects/{p}/connections |
| `hie_update_connection` | Modify a connection | PUT /api/projects/{p}/connections/{c} |
| `hie_delete_connection` | Remove a connection | DELETE /api/projects/{p}/connections/{c} |
| `hie_create_routing_rule` | Add a routing rule | POST /api/projects/{p}/routing-rules |
| `hie_update_routing_rule` | Modify a routing rule | PUT /api/projects/{p}/routing-rules/{r} |
| `hie_delete_routing_rule` | Remove a routing rule | DELETE /api/projects/{p}/routing-rules/{r} |
| `hie_deploy_project` | Deploy config to engine | POST /api/workspaces/{ws}/projects/{p}/deploy |
| `hie_start_project` | Start all items | POST /api/workspaces/{ws}/projects/{p}/start |
| `hie_stop_project` | Stop all items | POST /api/workspaces/{ws}/projects/{p}/stop |
| `hie_project_status` | Get runtime status | GET /api/workspaces/{ws}/projects/{p}/status |
| `hie_test_item` | Send test message | POST /api/.../items/{name}/test |
| `hie_list_item_types` | List available classes | GET /api/item-types |
| `hie_reload_custom_classes` | Reload custom.* classes | POST /api/item-types/reload-custom |
| `hie_list_versions` | List config snapshots | GET /api/projects/{p}/versions |
| `hie_get_version` | Get a specific snapshot | GET /api/projects/{p}/versions/{v} |
| `hie_rollback_project` | Rollback to a version | POST /api/projects/{p}/rollback/{v} |

### RBAC — Who Can Use Which Tools

Each role sees only its permitted tools. The agent literally cannot call tools outside its role's set.

| Role | Build | Deploy | Start/Stop | Test | Rollback | Tools |
|------|-------|--------|------------|------|----------|-------|
| **platform_admin** | All | All | All | All | All | 24 |
| **tenant_admin** | All | All | All | All | All | 23 |
| **developer** | All CRUD | Staging only | No | Yes | No | 22 |
| **clinical_safety_officer** | No | No | No | Yes | No | 8 |
| **operator** | No | Yes | Yes | No | Yes | 11 |
| **auditor** | No | No | No | No | No | 8 |
| **viewer** | No | No | No | No | No | 6 |

**Security layers:**
- **Layer 1 (Proactive):** Tools not in the role's set are removed before the LLM sees them
- **Layer 2 (Defensive):** Pre-tool-use hook validates permissions again before execution
- **Layer 3 (Namespace):** `li.*`, `Engine.li.*`, `EnsLib.*` writes blocked for non-admins
- **Layer 4 (File Path):** File writes restricted to `custom/` directory for non-admins

### Using the Agent to Build Integrations

**Portal Navigation:** Sidebar → Agents

**Full lifecycle example (as developer):**

```
You:    Build a complete ADT integration for St Thomas' Hospital:
        - Inbound "Cerner.PAS.Receiver" on port 5001 (HL7 TCP, Application AckMode)
        - Routing engine "ADT.Router"
        - Outbound "RIS.Sender" to 10.0.1.50:5002 (A01, A02, A03)
        - Outbound "EPR.Sender" to 10.0.1.60:5003 (A01, A03 only)
        Wire everything and create routing rules.

Agent:  I'll build that integration. Let me start by finding the workspace...

        [hie_list_workspaces] → Found "STH Integrations"
        [hie_create_project] → Created "Cerner ADT Integration"
        [hie_create_item] × 4 → Created receiver, router, RIS sender, EPR sender
        [hie_create_connection] × 3 → Wired receiver→router→RIS, router→EPR
        [hie_create_routing_rule] × 2 → A01/A02/A03→RIS, A01/A03→EPR

        Integration built! 4 items, 3 connections, 2 routing rules.
        Shall I test it?

You:    Test with an A01 admission and an A02 transfer.

Agent:  [hie_test_item] → Sent A01 admission → Routed to RIS + EPR
        [hie_test_item] → Sent A02 transfer → Routed to RIS only (EPR excluded)

        Routing works correctly. A01 goes to both, A02 to RIS only.

You:    Deploy to production.

Agent:  I can't deploy to production — my role (Integration Developer)
        doesn't have permission. I'll create a deployment approval request
        so a Clinical Safety Officer or Admin can review and approve it.
```

### Using Skills

The agent has access to role-specific skills (seeded from `agent-runner/skills/`):

| Skill | Available To | What It Does |
|-------|-------------|-------------|
| `hl7-route-builder` | developer | Generates HL7 routing configurations |
| `fhir-mapper` | developer | Maps FHIR resources to HL7 segments |
| `integration-test` | developer, cso | Generates and runs integration test plans |
| `nhs-compliance-check` | developer, cso | Validates NHS data handling compliance |
| `clinical-safety-review` | cso | Runs 32-item DCB0129/DCB0160 safety checklist |

Seed skills into the database:
```bash
curl -X POST http://localhost:9341/seed/skills
curl -X POST http://localhost:9341/seed/templates
```

### Using Prompt Templates

**Portal Navigation:** Sidebar → Admin → Skills (for skills) or Prompts page

Pre-built templates for common healthcare integration tasks:

| Template | Purpose |
|----------|---------|
| HL7 Message Transformation | Generate field mappings between HL7 versions |
| FHIR Resource Mapping | Map FHIR resources to HL7 segments |
| NHS Validation Rules | Generate NHS-specific validation logic |
| Integration Route Design | Design message flow for a clinical scenario |
| Error Handling Strategy | Configure retry/failover for an operation |

### Audit Trail

Every tool call made by the agent is automatically logged to the audit system:
- **PII sanitisation**: NHS numbers → `[NHS_NUMBER]`, UK postcodes → `[POSTCODE]`
- **Denied actions recorded**: RBAC-blocked tool calls are logged with `result_status: denied`
- **Portal view**: Admin → Audit Log — with stats cards, filters, expandable details

### Approval Workflow

Production deployments require CSO/Admin approval:
1. Developer requests deploy → creates `pending` approval record
2. CSO reviews in Admin → Approvals → clicks Approve/Reject with notes
3. Operator deploys the approved project

API endpoints:
```bash
# Create approval (called by agent-runner when developer requests deploy)
POST http://localhost:9341/approvals

# List approvals
GET http://localhost:9341/approvals?status=pending

# Approve (CSO/Admin only — returns 403 for viewer/developer)
POST http://localhost:9341/approvals/{id}/approve

# Reject
POST http://localhost:9341/approvals/{id}/reject
```

### Demo Users for Agent Testing

See [DEMO_LIFECYCLE_GUIDE.md](DEMO_LIFECYCLE_GUIDE.md) for the complete 7-act walkthrough with all 7 demo users. Quick reference:

| Role | Login | Agent Chat Capabilities |
|------|-------|------------------------|
| Developer | `developer@sth.nhs.uk` / `Demo12345!` | Design, Build, Test |
| CSO | `cso@sth.nhs.uk` / `Demo12345!` | Review, Test, Approve/Reject |
| Operator | `operator@sth.nhs.uk` / `Demo12345!` | Deploy, Start/Stop, Rollback |
| Admin | `admin@hie.nhs.uk` / `Admin123!` | Everything |

---

## Appendix A: Complete API Reference for This Scenario

All Portal actions map to REST API calls. For CI/CD automation:

```bash
# Create workspace
curl -X POST $HIE_URL/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "St_Thomas_Hospital", "display_name": "St. Thomas Hospital"}'

# Create project
curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects \
  -d '{"name": "ADT_Integration", "description": "ADT Integration Production"}'

# Add inbound service
curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects/$PROJ_ID/items \
  -d '{
    "name": "Cerner.PAS.Receiver",
    "item_type": "service",
    "class_name": "li.hosts.hl7.HL7TCPService",
    "enabled": true,
    "pool_size": 4,
    "adapter_settings": {"Port": "2575", "IPAddress": "0.0.0.0"},
    "host_settings": {"MessageSchemaCategory": "2.3", "TargetConfigNames": "NHS.Validation.Process", "AckMode": "App"}
  }'

# Deploy & start
curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects/$PROJ_ID/deploy
curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects/$PROJ_ID/start

# Send test message
curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects/$PROJ_ID/items/RIS.HL7.Sender/test \
  -d '{"message": "MSH|^~\\&|PAS|STH|HIE|STH|20260211||ADT^A01|TEST001|P|2.3\rPID|1||9876543210^^^NHS||Smith^John||19800101|M"}'
```

---

## Appendix B: IRIS Migration Quick Reference

| IRIS Action | HIE Equivalent |
|-------------|---------------|
| `zn "NAMESPACE"` | Select Workspace in Portal |
| Studio → New Production | Portal → Create Project |
| Studio → Add Business Service | Portal → Add Item → Service |
| Studio → Add Business Process | Portal → Add Item → Process |
| Studio → Add Business Operation | Portal → Add Item → Operation |
| Studio → New DTL Class | Portal → Add Transformation (or Agent) |
| Studio → New BPL Class | Portal → Add Process with Rules |
| Portal → Production → Apply | Portal → Deploy & Start |
| Portal → Production → Start | Portal → Start |
| Terminal → `do ##class(Ens.Director).StartProduction()` | `curl -X POST .../deploy` |
| Terminal → `zwrite ^Ens.MessageHeader` | Portal → Messages tab |
| Terminal → `zwrite ^Ens.Util.Log` | Portal → Logs tab |
| Portal → Message Viewer | Portal → Messages tab |
| Portal → Event Log | Portal → Errors tab |
| Export Production XML | `GET /api/.../projects/.../export` |
| Import Production XML | `POST /api/.../projects/import` (IRIS XML supported) |

---

## See Also

- [Developer Workflow Scenarios](DEVELOPER_WORKFLOW_SCENARIOS.md) — 8 detailed workflow scenarios with competitive analysis
- [NHS Trust Demo](NHS_TRUST_DEMO_GUIDE.md) — Technical implementation reference
- [Product Vision](../design/PRODUCT_VISION.md) — Strategic positioning
- [Configuration Reference](../reference/CONFIGURATION_REFERENCE.md) — All settings reference
- [UI Configuration Guide](UI_CONFIGURATION_GUIDE.md) — Portal UI implementation
- [Message Routing Workflow](../reference/MESSAGE_ROUTING_WORKFLOW.md) — E2E routing implementation details
