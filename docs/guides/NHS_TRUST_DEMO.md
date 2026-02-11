# NHS Trust Integration Demo — Complete Technical Reference

**Version:** 1.7.3  
**Date:** February 11, 2026  
**Status:** Production-Ready Reference Implementation  

---

## Overview

This document is the **technical implementation reference** for a complete, production-ready NHS acute trust integration using OpenLI HIE. It complements the [Developer & User Guide](./LI_HIE_DEVELOPER_GUIDE.md) with full configuration payloads, sample messages, and deployment details.

### Clinical Scenario: St. Thomas' Hospital

**Requirement:** Integrate Cerner Millennium PAS, GP FHIR endpoints, and batch HL7 file drops with downstream clinical systems (RIS, ICE Lab) and a local file archive.

### Route Topology: 3 Inbound → 2 Process → 3 Outbound

| Layer | Item | Protocol | Endpoint |
|-------|------|----------|----------|
| **Inbound** | Cerner.PAS.Receiver | HL7 v2.3 MLLP | Port 2575 |
| **Inbound** | GP.FHIR.Receiver | FHIR R4 JSON/REST | Port 8443 (HTTPS) |
| **Inbound** | Batch.File.Reader | HL7 File Watcher | /data/inbound/*.hl7 |
| **Process** | NHS.Validation.Process | Internal | Validation + PDS enrichment |
| **Process** | ADT.Content.Router | Internal | Content-based routing engine |
| **Outbound** | RIS.HL7.Sender | HL7 v2.5.1 MLLP | ris.sth.nhs.uk:2576 |
| **Outbound** | Lab.HL7.Sender | HL7 v2.4 MLLP | lab.sth.nhs.uk:2577 |
| **Outbound** | Archive.File.Writer | File I/O | /data/outbound/ |

---

## Architecture Diagram

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
│  │ EnsLib.HL7.Service   │ │ Custom.FHIR.Service │ │ EnsLib.HL7.Service  │   │
│  │ .TCPService          │ │ .HTTPService        │ │ .FileService        │   │
│  └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘   │
│             │                        │                        │              │
│             └────────────┬───────────┴────────────────────────┘              │
│                          ▼                                                    │
│  BUSINESS PROCESSES (2)                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ NHS.Validation.Process                                                │   │
│  │ Class: custom.nhs.NHSValidationProcess                               │   │
│  │ • NHS Number validation (Modulus 11)                                  │   │
│  │ • PDS demographic lookup & enrichment                                 │   │
│  │ • Duplicate admission detection (60s window)                          │   │
│  │ • UK postcode validation                                              │   │
│  │ • FHIR→HL7 normalisation (Patient→ADT A28, Encounter→ADT A01)       │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                              ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ADT.Content.Router                                                    │   │
│  │ Class: li.hosts.routing.RoutingEngine                                │   │
│  │ (IRIS alias: EnsLib.HL7.MsgRouter.RoutingEngine)                     │   │
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
│  │ ris.sth.nhs.uk:2576  │ │ lab.sth.nhs.uk:2577 │ │ Timestamped files   │   │
│  │ EnsLib.HL7.Operation │ │ EnsLib.HL7.Operation │ │ EnsLib.HL7.Operation│   │
│  │ .TCPOperation        │ │ .TCPOperation        │ │ .FileOperation      │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Workspace Configuration

```yaml
# API: POST /api/workspaces
name: "St_Thomas_Hospital"
display_name: "St. Thomas' Hospital"
description: "Main acute trust integration hub — South London"
settings:
  region: "London"
  trust_code: "RJ1"
  contact: "integration.team@gstt.nhs.uk"
  tags: ["NHS", "Acute Trust", "South London", "Cerner"]
```

## 2. Project Configuration

```yaml
# API: POST /api/workspaces/{ws_id}/projects
name: "ADT_Integration"
display_name: "ADT Integration Production"
description: "Patient ADT + Orders: Cerner PAS + GP FHIR → RIS + Lab + Archive"
version: "1.0.0"
environment: "production"
```

---

## 3. Item Configurations (Full Payloads)

### 3.1 Cerner.PAS.Receiver — HL7 v2.3 MLLP Inbound

**IRIS equivalent class:** `EnsLib.HL7.Service.TCPService`  
**HIE class:** `li.hosts.hl7.HL7TCPService`

```yaml
# API: POST /api/workspaces/{ws_id}/projects/{proj_id}/items
name: "Cerner.PAS.Receiver"
display_name: "Cerner Millennium PAS — HL7 v2.3 MLLP Receiver"
item_type: "service"
class_name: "li.hosts.hl7.HL7TCPService"
enabled: true
pool_size: 4
category: "Inbound | PAS"
comment: "Receives real-time ADT and ORM messages from Cerner Millennium PAS"

adapter_settings:
  Port: "2575"
  IPAddress: "0.0.0.0"
  JobPerConnection: "true"
  ReadTimeout: "30"
  StayConnected: "-1"

host_settings:
  MessageSchemaCategory: "2.3"
  TargetConfigNames: "NHS.Validation.Process"
  AckMode: "App"
  ArchiveIO: "true"

  # Phase 2 Enterprise Settings
  ExecutionMode: "multiprocess"
  WorkerCount: "4"
  QueueType: "priority"
  QueueSize: "10000"
  OverflowStrategy: "drop_oldest"
  RestartPolicy: "always"
  MaxRestarts: "100"
  RestartDelay: "10.0"
  MessagingPattern: "async_reliable"
  MessageTimeout: "30.0"
```

**IRIS equivalent configuration (for comparison):**
```objectscript
// In IRIS Management Portal → Production → Business Services → Add
Class = EnsLib.HL7.Service.TCPService
Item Name = Cerner.PAS.Receiver
Port = 2575
TargetConfigNames = NHS.Validation.Process
MessageSchemaCategory = 2.3
AckMode = App
ArchiveIO = 1
```

---

### 3.2 GP.FHIR.Receiver — FHIR R4 JSON/REST Inbound

**IRIS equivalent:** Custom `EnsLib.HTTP.Service` subclass with FHIR parsing  
**HIE class:** `custom.nhs.FHIRHTTPService`

```yaml
name: "GP.FHIR.Receiver"
display_name: "GP Connect — FHIR R4 JSON/REST Receiver"
item_type: "service"
class_name: "custom.nhs.FHIRHTTPService"
enabled: true
pool_size: 2
category: "Inbound | FHIR"
comment: "Receives FHIR R4 Patient/Encounter resources from GP systems via HTTPS"

adapter_settings:
  Port: "8443"
  SSLEnabled: "true"
  SSLCertFile: "/certs/hie-server.pem"
  SSLKeyFile: "/certs/hie-server.key"
  BasePath: "/fhir/r4"
  Authentication: "bearer"

host_settings:
  FHIRVersion: "R4"
  AcceptedResources: "Patient,Encounter,Bundle"
  NormaliseToHL7: "true"
  TargetConfigNames: "NHS.Validation.Process"
  ArchiveIO: "true"

  # Enterprise Settings
  ExecutionMode: "async"
  QueueType: "fifo"
  QueueSize: "5000"
  RestartPolicy: "always"
  MaxRestarts: "50"
  MessagingPattern: "async_reliable"
```

**FHIR→HL7 Normalisation Mapping:**

| FHIR Resource | HL7 Event | Mapping |
|---------------|-----------|---------|
| Patient (create) | ADT^A28 | Add person information |
| Patient (update) | ADT^A31 | Update person information |
| Encounter (create) | ADT^A01 | Admit/visit notification |
| Encounter (discharge) | ADT^A03 | Discharge/end visit |
| Bundle | Multiple | One HL7 message per entry |

**Sample FHIR→HL7 conversion:**

Input (FHIR R4):
```json
{
  "resourceType": "Patient",
  "identifier": [
    {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9876543210"}
  ],
  "name": [{"family": "Smith", "given": ["John", "Q"]}],
  "gender": "male",
  "birthDate": "1980-01-01",
  "address": [
    {"line": ["123 High St"], "city": "London", "postalCode": "SW1A 1AA", "country": "UK"}
  ]
}
```

Output (HL7 v2.3 — normalised):
```
MSH|^~\&|FHIR-GP|GP-SURGERY|HIE|STH|20260211120000||ADT^A28|FHIR-001|P|2.3
EVN|A28|20260211120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
```

---

### 3.3 Batch.File.Reader — HL7 File Watcher Inbound

**IRIS equivalent class:** `EnsLib.HL7.Service.FileService`  
**HIE class:** `li.hosts.hl7.HL7FileService`

```yaml
name: "Batch.File.Reader"
display_name: "PAS Batch File Reader — HL7 File Watcher"
item_type: "service"
class_name: "li.hosts.hl7.HL7FileService"
enabled: true
pool_size: 1
category: "Inbound | File"
comment: "Watches /data/inbound for HL7 files from overnight PAS batch exports"

adapter_settings:
  FilePath: "/data/inbound"
  FileSpec: "*.hl7"
  PollingInterval: "5"
  ArchivePath: "/data/inbound/processed"
  Recursive: "false"
  DeleteAfterRead: "false"

host_settings:
  MessageSchemaCategory: "2.3"
  TargetConfigNames: "NHS.Validation.Process"

  # Enterprise Settings
  ExecutionMode: "async"
  QueueType: "fifo"
  QueueSize: "1000"
  RestartPolicy: "on_failure"
  MaxRestarts: "5"
```

**File processing behaviour:**
1. Poll `/data/inbound/` every 5 seconds for `*.hl7` files
2. Read file contents as HL7 message(s)
3. If file contains multiple messages (separated by `\r\n\r\n`), split into individual messages
4. Forward each message to `NHS.Validation.Process`
5. Move processed file to `/data/inbound/processed/` with timestamp suffix
6. On error, leave file in place for retry on next poll cycle

---

### 3.4 NHS.Validation.Process — Validation & Transformation

**IRIS equivalent:** Custom `Ens.BusinessProcessBPL` subclass  
**HIE class:** `custom.nhs.NHSValidationProcess`

```yaml
name: "NHS.Validation.Process"
display_name: "NHS Validation, Enrichment & Normalisation"
item_type: "process"
class_name: "custom.nhs.NHSValidationProcess"
enabled: true
pool_size: 4
category: "Process | Validation"
comment: "Validates NHS numbers, enriches from PDS, detects duplicates, normalises FHIR"

host_settings:
  ValidateNHSNumber: "true"
  EnrichFromPDS: "true"
  PDSEndpoint: "https://pds.spine.nhs.uk/api"
  PDSTimeout: "5.0"
  CheckDuplicates: "true"
  DuplicateWindow: "60"
  ValidatePostcode: "true"
  FHIRNormalisation: "true"
  TargetConfigNames: "ADT.Content.Router"
  OnValidationFail: "nack_and_exception_queue"

  # Enterprise Settings
  ExecutionMode: "thread_pool"
  WorkerCount: "4"
  QueueType: "priority"
  QueueSize: "5000"
  OverflowStrategy: "block"
  RestartPolicy: "always"
  MaxRestarts: "1000"
  RestartDelay: "5.0"
  MessagingPattern: "sync_reliable"
  MessageTimeout: "10.0"
```

**Processing Pipeline (step by step):**

```
┌─────────────────────────────────────────────────────────────┐
│ NHS.Validation.Process — Message Processing Pipeline         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. RECEIVE message from any inbound service                 │
│     │                                                        │
│  2. IF message is FHIR JSON:                                 │
│     │  → Convert FHIR Patient → HL7 ADT A28                │
│     │  → Convert FHIR Encounter → HL7 ADT A01              │
│     │  → Set MSH.SendingApplication = "FHIR-{source}"      │
│     │                                                        │
│  3. VALIDATE NHS Number (PID-3):                             │
│     │  → Modulus 11 check digit verification                │
│     │  → IF invalid → NACK + Exception Queue → STOP        │
│     │                                                        │
│  4. ENRICH from PDS:                                         │
│     │  → GET https://pds.spine.nhs.uk/api/Patient/{nhs#}   │
│     │  → Merge demographics into PID segment                │
│     │  → Add ZPD segment with PDS trace metadata            │
│     │  → IF PDS timeout → Continue with original data       │
│     │                                                        │
│  5. CHECK DUPLICATES:                                        │
│     │  → Query 60-second sliding window                     │
│     │  → Key: NHS Number + Event Type + Sending Application │
│     │  → IF duplicate → Log + Exception Queue → STOP        │
│     │                                                        │
│  6. VALIDATE POSTCODE (PID-11):                              │
│     │  → UK postcode regex validation                       │
│     │  → IF invalid → Add ZVL|PostcodeValidation|WARN       │
│     │  → CONTINUE (don't reject for bad postcode)           │
│     │                                                        │
│  7. FORWARD to ADT.Content.Router                            │
│     │                                                        │
│  8. RETURN ACK to sender                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Custom Python class:** See [Developer Guide — Part 2](./LI_HIE_DEVELOPER_GUIDE.md#writing-custom-host-classes) for the full implementation.

---

### 3.5 ADT.Content.Router — Content-Based Routing Engine

**IRIS equivalent class:** `EnsLib.HL7.MsgRouter.RoutingEngine`  
**HIE class:** `li.hosts.routing.RoutingEngine`

```yaml
name: "ADT.Content.Router"
display_name: "ADT Content-Based Routing Engine"
item_type: "process"
class_name: "li.hosts.routing.RoutingEngine"
enabled: true
pool_size: 2
category: "Process | Routing"
comment: "Routes validated messages to RIS, Lab, and Archive based on content"

host_settings:
  BusinessRuleName: "ADT_Routing_Rules"
  Validation: "Error"
  RuleLogging: "a"

  # Enterprise Settings
  ExecutionMode: "thread_pool"
  WorkerCount: "2"
  QueueType: "fifo"
  QueueSize: "5000"
  OverflowStrategy: "block"
  RestartPolicy: "always"
  MaxRestarts: "1000"
  RestartDelay: "30.0"
  MessagingPattern: "sync_reliable"
  MessageTimeout: "60.0"
```

**Routing Rules:**

```yaml
# API: POST /api/workspaces/{ws_id}/projects/{proj_id}/routing-rules
rules:
  - name: "Route ADT to RIS and Lab"
    priority: 1
    enabled: true
    condition_expression: >
      MSH.MessageType.MessageCode = "ADT"
      AND MSH.MessageType.TriggerEvent IN ("A01","A02","A03","A08")
    actions:
      - action: "send"
        target_items: ["RIS.HL7.Sender"]
        transform_name: "v23_to_v251_RIS"
      - action: "send"
        target_items: ["Lab.HL7.Sender"]
        transform_name: "v23_to_v24_Lab"
      - action: "send"
        target_items: ["Archive.File.Writer"]

  - name: "Route Radiology Orders to RIS"
    priority: 2
    enabled: true
    condition_expression: >
      MSH.MessageType.MessageCode = "ORM"
      AND MSH.MessageType.TriggerEvent = "O01"
      AND OBR.UniversalServiceIdentifier CONTAINS "RAD"
    actions:
      - action: "send"
        target_items: ["RIS.HL7.Sender"]
        transform_name: "v23_to_v251_RIS"
      - action: "send"
        target_items: ["Archive.File.Writer"]

  - name: "Route Lab Orders to Lab"
    priority: 3
    enabled: true
    condition_expression: >
      MSH.MessageType.MessageCode = "ORM"
      AND MSH.MessageType.TriggerEvent = "O01"
      AND OBR.UniversalServiceIdentifier CONTAINS "LAB"
    actions:
      - action: "send"
        target_items: ["Lab.HL7.Sender"]
        transform_name: "v23_to_v24_Lab"
      - action: "send"
        target_items: ["Archive.File.Writer"]

  - name: "Route FHIR-origin messages to all"
    priority: 4
    enabled: true
    condition_expression: >
      MSH.SendingApplication CONTAINS "FHIR"
    actions:
      - action: "send"
        target_items: ["RIS.HL7.Sender"]
        transform_name: "v23_to_v251_RIS"
      - action: "send"
        target_items: ["Lab.HL7.Sender"]
        transform_name: "v23_to_v24_Lab"
      - action: "send"
        target_items: ["Archive.File.Writer"]

  - name: "Default Archive"
    priority: 99
    enabled: true
    condition_expression: "1=1"
    actions:
      - action: "send"
        target_items: ["Archive.File.Writer"]
```

**IRIS equivalent (for comparison):**
```objectscript
// In IRIS Management Portal → Business Rules → ADT_Routing_Rules
// Rule 1:
//   Constraint: HL7.{MSH:MessageType} In ("ADT^A01","ADT^A02","ADT^A03","ADT^A08")
//   Actions:
//     Send to RIS.HL7.Sender (Transform: v23_to_v251_RIS)
//     Send to Lab.HL7.Sender (Transform: v23_to_v24_Lab)
//     Send to Archive.File.Writer
```

---

### 3.6 Transformation Definitions

**Transform: v23_to_v251_RIS (HL7 v2.3 → v2.5.1 for RIS)**

```yaml
name: "v23_to_v251_RIS"
source_schema: "2.3"
target_schema: "2.5.1"
description: "Transform HL7 v2.3 messages to v2.5.1 for RIS"

field_mappings:
  # MSH — Message Header
  MSH.SendingApplication: "HIE"
  MSH.SendingFacility: "{source.MSH.SendingFacility}"
  MSH.ReceivingApplication: "RIS"
  MSH.ReceivingFacility: "{source.MSH.ReceivingFacility}"
  MSH.DateTimeOfMessage: "{NOW()}"
  MSH.MessageType: "{source.MSH.MessageType}"
  MSH.MessageControlID: "{source.MSH.MessageControlID}-RIS"
  MSH.ProcessingID: "{source.MSH.ProcessingID}"
  MSH.VersionID: "2.5.1"
  MSH.MessageStructure: "ADT_A01"  # Required in v2.5+

  # EVN — Event Type (copy)
  EVN: "{source.EVN}"

  # PID — Patient Identification (copy all)
  PID: "{source.PID}"

  # PV1 — Patient Visit (copy, update facility format for v2.5.1)
  PV1.SetID: "{source.PV1.SetID}"
  PV1.PatientClass: "{source.PV1.PatientClass}"
  PV1.AssignedPatientLocation: "{source.PV1.AssignedPatientLocation}^^^^STH"
  PV1.AttendingDoctor: "{source.PV1.AttendingDoctor}"
  PV1.HospitalService: "{source.PV1.HospitalService}"
  PV1.VisitNumber: "{source.PV1.VisitNumber}"

  # ZAU — Audit Trail (custom Z-segment)
  ZAU.1: "{source.MSH.MessageControlID}"
  ZAU.2: "{NOW()}"
  ZAU.3: "v23_to_v251_RIS"
```

**Transform: v23_to_v24_Lab (HL7 v2.3 → v2.4 for Lab)**

```yaml
name: "v23_to_v24_Lab"
source_schema: "2.3"
target_schema: "2.4"
description: "Transform HL7 v2.3 messages to v2.4 for ICE Laboratory"

field_mappings:
  MSH.SendingApplication: "HIE"
  MSH.ReceivingApplication: "ICE-LAB"
  MSH.ReceivingFacility: "{source.MSH.ReceivingFacility}"
  MSH.DateTimeOfMessage: "{NOW()}"
  MSH.MessageControlID: "{source.MSH.MessageControlID}-LAB"
  MSH.VersionID: "2.4"

  EVN: "{source.EVN}"
  PID: "{source.PID}"
  PV1: "{source.PV1}"
  OBR: "{source.OBR}"  # Preserve order details for ORM messages
  ORC: "{source.ORC}"  # Preserve order control for ORM messages

  ZAU.1: "{source.MSH.MessageControlID}"
  ZAU.2: "{NOW()}"
  ZAU.3: "v23_to_v24_Lab"
```

---

### 3.7 RIS.HL7.Sender — HL7 v2.5.1 MLLP Outbound

**IRIS equivalent class:** `EnsLib.HL7.Operation.TCPOperation`  
**HIE class:** `li.hosts.hl7.HL7TCPOperation`

```yaml
name: "RIS.HL7.Sender"
display_name: "RIS Radiology — HL7 v2.5.1 MLLP Sender"
item_type: "operation"
class_name: "li.hosts.hl7.HL7TCPOperation"
enabled: true
pool_size: 2
category: "Outbound | RIS"
comment: "Sends transformed HL7 v2.5.1 messages to RIS via MLLP"

adapter_settings:
  IPAddress: "ris.sth.nhs.uk"
  Port: "2576"
  ConnectTimeout: "30"
  ReconnectRetry: "5"
  ReconnectInterval: "10"
  StayConnected: "-1"

host_settings:
  # IRIS-identical ReplyCodeActions syntax
  ReplyCodeActions: ":?R=F,:?E=S,:~=S,:?A=C,:*=S"
  RetryInterval: "5"
  FailureTimeout: "15"
  ArchiveIO: "true"

  # Enterprise Settings
  ExecutionMode: "thread_pool"
  WorkerCount: "2"
  QueueType: "fifo"
  QueueSize: "5000"
  OverflowStrategy: "block"
  RestartPolicy: "always"
  MaxRestarts: "100"
```

**ReplyCodeActions reference (IRIS-identical syntax):**

| Pattern | Meaning | Action |
|---------|---------|--------|
| `:?R=F` | Reply contains Reject | **F**ail the message |
| `:?E=S` | Reply contains Error | **S**uspend for review |
| `:~=S` | Malformed reply | **S**uspend for review |
| `:?A=C` | Reply is ACK (Accept) | **C**omplete successfully |
| `:*=S` | Anything else | **S**uspend for review |

---

### 3.8 Lab.HL7.Sender — HL7 v2.4 MLLP Outbound

**IRIS equivalent class:** `EnsLib.HL7.Operation.TCPOperation`  
**HIE class:** `li.hosts.hl7.HL7TCPOperation`

```yaml
name: "Lab.HL7.Sender"
display_name: "ICE Laboratory — HL7 v2.4 MLLP Sender"
item_type: "operation"
class_name: "li.hosts.hl7.HL7TCPOperation"
enabled: true
pool_size: 2
category: "Outbound | Lab"
comment: "Sends transformed HL7 v2.4 messages to ICE Lab via MLLP"

adapter_settings:
  IPAddress: "lab.sth.nhs.uk"
  Port: "2577"
  ConnectTimeout: "30"
  ReconnectRetry: "5"
  ReconnectInterval: "10"
  StayConnected: "-1"

host_settings:
  ReplyCodeActions: ":?R=F,:?E=S,:~=S,:?A=C,:*=S"
  RetryInterval: "5"
  FailureTimeout: "15"
  ArchiveIO: "true"

  # Enterprise Settings
  ExecutionMode: "thread_pool"
  WorkerCount: "2"
  QueueType: "fifo"
  QueueSize: "5000"
  OverflowStrategy: "block"
  RestartPolicy: "always"
  MaxRestarts: "100"
```

---

### 3.9 Archive.File.Writer — Local File Archive Outbound

**IRIS equivalent class:** `EnsLib.HL7.Operation.FileOperation`  
**HIE class:** `li.hosts.file.FileOperation`

```yaml
name: "Archive.File.Writer"
display_name: "Local Archive — Timestamped File Writer"
item_type: "operation"
class_name: "li.hosts.file.FileOperation"
enabled: true
pool_size: 1
category: "Outbound | Archive"
comment: "Writes all processed messages to /data/outbound for compliance audit"

adapter_settings:
  FilePath: "/data/outbound"
  FileName: "%Y%m%d/%H%M%S_%f.hl7"
  CreateDirectories: "true"
  Overwrite: "false"

host_settings:
  QueueType: "fifo"
  QueueSize: "50000"
  OverflowStrategy: "drop_oldest"
  RestartPolicy: "always"
```

**File output structure:**
```
/data/outbound/
  20260211/
    120000_000001.hl7    ← ADT A01 from Cerner PAS
    120001_000002.hl7    ← Same message (archive copy)
    120500_000003.hl7    ← FHIR-normalised ADT A28
    ...
  20260212/
    000100_000001.hl7    ← Overnight batch file messages
    ...
```

---

## 4. Connection Configuration

```yaml
# API: POST /api/workspaces/{ws_id}/projects/{proj_id}/connections (bulk)
connections:
  # All 3 inbound services → Validation process
  - source_item: "Cerner.PAS.Receiver"
    target_item: "NHS.Validation.Process"
    messaging_pattern: "async_reliable"

  - source_item: "GP.FHIR.Receiver"
    target_item: "NHS.Validation.Process"
    messaging_pattern: "async_reliable"

  - source_item: "Batch.File.Reader"
    target_item: "NHS.Validation.Process"
    messaging_pattern: "async_reliable"

  # Validation → Router
  - source_item: "NHS.Validation.Process"
    target_item: "ADT.Content.Router"
    messaging_pattern: "sync_reliable"

  # Router → All 3 outbound operations
  - source_item: "ADT.Content.Router"
    target_item: "RIS.HL7.Sender"
    messaging_pattern: "sync_reliable"

  - source_item: "ADT.Content.Router"
    target_item: "Lab.HL7.Sender"
    messaging_pattern: "sync_reliable"

  - source_item: "ADT.Content.Router"
    target_item: "Archive.File.Writer"
    messaging_pattern: "async_reliable"
```

**Total: 7 connections** wiring 8 items into a complete message flow.

---

## 5. Message Flow Examples

### Example 1: ADT^A01 Patient Admission (from Cerner PAS)

**Inbound (HL7 v2.3 via MLLP on port 2575):**
```
MSH|^~\&|PAS|STH|HIE|STH|20260211120000||ADT^A01|MSG0001|P|2.3
EVN|A01|20260211120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
```

**Processing trace:**
```
[  0ms] Cerner.PAS.Receiver     → Received, parsed as HL7 v2.3 ADT^A01
[  5ms] NHS.Validation.Process  → NHS# 9876543210: VALID (Modulus 11 ✓)
[200ms] NHS.Validation.Process  → PDS lookup: VERIFIED, demographics enriched
[210ms] NHS.Validation.Process  → Duplicate check: PASSED
[215ms] NHS.Validation.Process  → Postcode SW1A 1AA: VALID
[220ms] ADT.Content.Router      → Rule 1 matched: ADT A01
[225ms] ADT.Content.Router      → Transform v23→v251 → RIS.HL7.Sender
[230ms] ADT.Content.Router      → Transform v23→v24  → Lab.HL7.Sender
[235ms] ADT.Content.Router      → Original           → Archive.File.Writer
[350ms] RIS.HL7.Sender          → Sent to ris.sth.nhs.uk:2576, ACK: AA
[360ms] Lab.HL7.Sender          → Sent to lab.sth.nhs.uk:2577, ACK: AA
[365ms] Archive.File.Writer     → Written: /data/outbound/20260211/120000_000001.hl7
[370ms] Cerner.PAS.Receiver     → ACK sent to Cerner PAS
```

**Outbound to RIS (HL7 v2.5.1):**
```
MSH|^~\&|HIE|STH|RIS|STH|20260211120000||ADT^A01^ADT_A01|MSG0001-RIS|P|2.5.1
EVN|A01|20260211120000|||
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1^^^^STH||||12345^Jones^Sarah|||MED||||||||V123456
ZPD|9876543210|VERIFIED|20260211120000|PDS-SPINE
ZAU|MSG0001|20260211120000|v23_to_v251_RIS
```

**Outbound to Lab (HL7 v2.4):**
```
MSH|^~\&|HIE|STH|ICE-LAB|STH|20260211120000||ADT^A01|MSG0001-LAB|P|2.4
EVN|A01|20260211120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
ZPD|9876543210|VERIFIED|20260211120000|PDS-SPINE
ZAU|MSG0001|20260211120000|v23_to_v24_Lab
```

---

### Example 2: FHIR Patient from GP System

**Inbound (FHIR R4 JSON via HTTPS on port 8443):**
```json
POST /fhir/r4/Patient HTTP/1.1
Content-Type: application/fhir+json

{
  "resourceType": "Patient",
  "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9876543210"}],
  "name": [{"family": "Smith", "given": ["John", "Q"]}],
  "gender": "male",
  "birthDate": "1980-01-01",
  "address": [{"line": ["123 High St"], "city": "London", "postalCode": "SW1A 1AA"}]
}
```

**Processing trace:**
```
[  0ms] GP.FHIR.Receiver        → Received FHIR R4 Patient resource
[ 10ms] GP.FHIR.Receiver        → Normalised to HL7 ADT^A28 (add person info)
[ 15ms] NHS.Validation.Process  → NHS# 9876543210: VALID
[200ms] NHS.Validation.Process  → PDS enrichment applied
[210ms] ADT.Content.Router      → Rule 4 matched: FHIR-origin → All targets
[350ms] RIS.HL7.Sender          → Sent v2.5.1, ACK: AA
[360ms] Lab.HL7.Sender          → Sent v2.4, ACK: AA
[365ms] Archive.File.Writer     → Written to file
```

**FHIR response to GP system:**
```json
HTTP/1.1 200 OK
Content-Type: application/fhir+json

{
  "resourceType": "OperationOutcome",
  "issue": [
    {
      "severity": "information",
      "code": "informational",
      "diagnostics": "Patient accepted and routed to RIS, Lab, and Archive"
    }
  ]
}
```

---

### Example 3: ORM^O01 Radiology Order

**Inbound (HL7 v2.3):**
```
MSH|^~\&|PAS|STH|HIE|STH|20260211130000||ORM^O01|MSG0002|P|2.3
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M
PV1|1|I|WARD1^ROOM1^BED1
ORC|NW|ORD001||||||20260211130000
OBR|1|ORD001||RAD-CT-HEAD^CT Head^LOCAL|||20260211130000
```

**Processing trace:**
```
[  0ms] Cerner.PAS.Receiver     → Received ORM^O01
[220ms] NHS.Validation.Process  → Validated
[225ms] ADT.Content.Router      → Rule 2 matched: Radiology order (OBR contains "RAD")
[350ms] RIS.HL7.Sender          → Sent v2.5.1 to RIS, ACK: AA
[355ms] Archive.File.Writer     → Written to file
        Lab.HL7.Sender          → NOT sent (Rule 2 targets RIS only)
```

---

### Example 4: ORM^O01 Lab Order

**Inbound (HL7 v2.3):**
```
MSH|^~\&|PAS|STH|HIE|STH|20260211140000||ORM^O01|MSG0003|P|2.3
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M
PV1|1|I|WARD1^ROOM1^BED1
ORC|NW|ORD002||||||20260211140000
OBR|1|ORD002||LAB-FBC^Full Blood Count^LOCAL|||20260211140000
```

**Processing trace:**
```
[  0ms] Cerner.PAS.Receiver     → Received ORM^O01
[220ms] NHS.Validation.Process  → Validated
[225ms] ADT.Content.Router      → Rule 3 matched: Lab order (OBR contains "LAB")
[350ms] Lab.HL7.Sender          → Sent v2.4 to Lab, ACK: AA
[355ms] Archive.File.Writer     → Written to file
        RIS.HL7.Sender          → NOT sent (Rule 3 targets Lab only)
```

---

### Example 5: Batch HL7 File

**File dropped:** `/data/inbound/overnight_extract_20260211.hl7`

Contains 150 HL7 messages separated by blank lines.

**Processing trace:**
```
[  0ms] Batch.File.Reader       → Detected file: overnight_extract_20260211.hl7
[ 50ms] Batch.File.Reader       → Parsed 150 messages from file
[ 55ms] Batch.File.Reader       → Forwarding message 1/150 to NHS.Validation.Process
  ...
[45000ms] Batch.File.Reader     → All 150 messages forwarded
[45050ms] Batch.File.Reader     → File moved to /data/inbound/processed/overnight_extract_20260211_20260211060050.hl7

Summary: 150 messages processed
  - 142 routed successfully (95 ADT → RIS+Lab, 30 ORM-RAD → RIS, 17 ORM-LAB → Lab)
  - 5 rejected (invalid NHS Number)
  - 3 flagged (invalid postcode, continued with warning)
```

---

## 6. Monitoring Dashboard

**Portal → Dashboard** shows real-time production metrics:

```
┌─────────────────────────────────────────────────────────────────────┐
│  ADT Integration Production              Status: 🟢 RUNNING         │
│  Uptime: 8h 15m    Messages: 4,892      Failed: 12   Rate: 99.75% │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Item                        Status  Queue      Workers  msg/hr     │
│  ───────────────────────────────────────────────────────────────    │
│  Cerner.PAS.Receiver         🟢 RUN   45/10000    4/4     380      │
│  GP.FHIR.Receiver            🟢 RUN    2/5000     2/2      45      │
│  Batch.File.Reader           🟢 RUN    0/1000     1/1      18      │
│  NHS.Validation.Process      🟢 RUN   18/5000     4/4     443      │
│  ADT.Content.Router          🟢 RUN   12/5000     2/2     436      │
│  RIS.HL7.Sender              🟢 RUN   28/5000     2/2     295      │
│  Lab.HL7.Sender              🟢 RUN   22/5000     2/2     290      │
│  Archive.File.Writer         🟢 RUN  156/50000    1/1     436      │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Message Flow:                                                       │
│                                                                      │
│  Cerner PAS ──380/hr──┐                                             │
│  GP FHIR    ── 45/hr──┼──► Validation ──► Router ──┬──► RIS  295/hr│
│  File Batch ── 18/hr──┘    (443/hr)      (436/hr)  ├──► Lab  290/hr│
│                                                      └──► File 436/hr│
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Alerts:                                                             │
│  ⚠️  RIS.HL7.Sender: Auto-restarted 2× (connection timeout)        │
│  ℹ️  NHS.Validation.Process: 12 messages rejected (invalid NHS#)    │
│  ✅  All critical items running normally                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Deployment

### Docker Compose

```yaml
services:
  hie-engine:
    image: openli/hie-engine:v1.7.3
    environment:
      - DATABASE_URL=postgresql://hie:hie@postgres:5432/hie
      - LOG_LEVEL=INFO
      - METRICS_ENABLED=true
    volumes:
      - ./data/inbound:/data/inbound
      - ./data/outbound:/data/outbound
      - ./custom:/app/custom:ro          # Custom Python classes
      - ./certs:/certs:ro                # SSL certificates for FHIR
    ports:
      - "2575:2575"   # HL7 MLLP (Cerner PAS)
      - "8443:8443"   # FHIR HTTPS (GP Connect)
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G

  hie-portal:
    image: openli/hie-portal:v1.7.3
    ports:
      - "9303:9303"   # Portal UI
    environment:
      - ENGINE_URL=http://hie-engine:9300

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=hie
      - POSTGRES_USER=hie
      - POSTGRES_PASSWORD=hie
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "9310:5432"

volumes:
  pgdata:
```

### Data Directories

```bash
mkdir -p data/inbound data/inbound/processed data/outbound certs custom
```

---

## 8. Testing Strategy

### Smoke Tests

```bash
# Test HL7 MLLP connectivity
echo -e "\x0bMSH|^~\&|TEST|STH|HIE|STH|20260211||ADT^A01|TEST001|P|2.3\rPID|1||9876543210^^^NHS||Test^Patient\x1c\r" | nc localhost 2575

# Test FHIR endpoint
curl -X POST https://localhost:8443/fhir/r4/Patient \
  -H "Content-Type: application/fhir+json" \
  -d '{"resourceType":"Patient","identifier":[{"system":"https://fhir.nhs.uk/Id/nhs-number","value":"9876543210"}]}'

# Test file drop
cp test_messages/sample_adt_a01.hl7 data/inbound/

# Check production status
curl http://localhost:9300/api/workspaces/{ws_id}/projects/{proj_id}/status
```

### Load Tests

| Metric | Target | Method |
|--------|--------|--------|
| Throughput | 10,000 msg/hr sustained | MLLP load generator |
| Burst | 50,000 msg/hr peak | Concurrent MLLP connections |
| Latency | <500ms end-to-end | Message trace timing |
| Queue depth | <80% capacity | Monitoring dashboard |
| Error rate | <0.5% | Error log analysis |

---

## 9. Compliance

### NHS Digital Standards
- HL7 v2.x interoperability (v2.3, v2.4, v2.5.1)
- FHIR R4 compliance (UK Core profiles)
- NHS Number validation (Modulus 11)
- Audit trail (7 years retention, timestamped files)
- GDPR data handling (encryption at rest and in transit)
- DCB0129 clinical safety compliance

### Clinical Safety
- Message persistence (WAL — Write-Ahead Log)
- Duplicate detection (sliding window)
- Validation before routing (never route invalid data)
- Error handling with NACK generation
- Auto-restart for resilience (zero message loss)
- Exception queue for manual review of rejected messages

---

## See Also

- [Developer & User Guide](./LI_HIE_DEVELOPER_GUIDE.md) — Step-by-step Portal walkthrough + Python extension guide
- [Developer Workflow Scenarios](../DEVELOPER_WORKFLOW_SCENARIOS.md) — 8 workflow scenarios with competitive analysis
- [Product Vision](../PRODUCT_VISION.md) — Strategic positioning
- [Configuration Reference](../CONFIGURATION_REFERENCE.md) — All settings reference
