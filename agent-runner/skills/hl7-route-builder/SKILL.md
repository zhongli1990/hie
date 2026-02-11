---
name: hl7-route-builder
description: Build end-to-end HL7/FHIR integration routes for OpenLI HIE using the Manager API tools
allowed-tools: hie_list_workspaces, hie_create_workspace, hie_list_projects, hie_create_project, hie_get_project, hie_create_item, hie_create_connection, hie_create_routing_rule, hie_deploy_project, hie_start_project, hie_stop_project, hie_project_status, hie_test_item, hie_list_item_types
user-invocable: true
version: "2.0"
---

# HL7 Route Builder — End-to-End Integration Skill

You are an expert at building healthcare integration routes for OpenLI HIE.
You create complete, production-ready integrations by calling HIE Manager API tools.

## Class Namespace Convention (MUST FOLLOW)

**PROTECTED — never create or modify:**
- `li.*` — Core product classes (HL7TCPService, HL7TCPOperation, HL7RoutingEngine, FileService, FileOperation)
- `Engine.li.*` — Same via fully-qualified path
- `EnsLib.*` — IRIS compatibility aliases

**DEVELOPER — all custom classes here:**
- `custom.*` — e.g. `custom.nhs.NHSValidationProcess`, `custom.sth.PatientLookup`

Developers INSTANTIATE core classes (configure them via Portal/API) but never modify their source code.
Developers CREATE custom classes only in the `custom.*` namespace by subclassing core base classes.

## Available Core Classes

| Class | Type | IRIS Equivalent | Purpose |
|-------|------|-----------------|---------|
| `li.hosts.hl7.HL7TCPService` | service | `EnsLib.HL7.Service.TCPService` | HL7 v2.x MLLP receiver |
| `li.hosts.hl7.HL7FileService` | service | `EnsLib.HL7.Service.FileService` | HL7 file watcher |
| `li.hosts.http.HTTPService` | service | `EnsLib.HTTP.Service` | HTTP/REST inbound |
| `li.hosts.routing.HL7RoutingEngine` | process | `EnsLib.HL7.MsgRouter.RoutingEngine` | Content-based router |
| `li.hosts.hl7.HL7TCPOperation` | operation | `EnsLib.HL7.Operation.TCPOperation` | HL7 v2.x MLLP sender |
| `li.hosts.file.FileOperation` | operation | `EnsLib.HL7.Operation.FileOperation` | File writer |

## E2E Route Creation Workflow

When asked to build an integration, follow these steps IN ORDER:

### Step 1: Create Workspace (if needed)
```
hie_create_workspace(name="St_Thomas_Hospital", display_name="St. Thomas' Hospital")
→ Returns workspace_id
```

### Step 2: Create Project
```
hie_create_project(workspace_id, name="ADT_Integration", description="ADT + Orders")
→ Returns project_id
```

### Step 3: Add Inbound Services
For each inbound source, call `hie_create_item`:

**HL7 MLLP Receiver:**
```
hie_create_item(
  project_id=project_id,
  name="Cerner.PAS.Receiver",
  item_type="service",
  class_name="li.hosts.hl7.HL7TCPService",
  pool_size=4,
  adapter_settings={"Port": "2575", "IPAddress": "0.0.0.0"},
  host_settings={
    "MessageSchemaCategory": "2.3",
    "TargetConfigNames": "NHS.Validation.Process",
    "AckMode": "App"
  }
)
```

**HL7 File Watcher:**
```
hie_create_item(
  project_id=project_id,
  name="Batch.File.Reader",
  item_type="service",
  class_name="li.hosts.hl7.HL7FileService",
  adapter_settings={"FilePath": "/data/inbound", "FileSpec": "*.hl7", "PollingInterval": "5"},
  host_settings={"TargetConfigNames": "NHS.Validation.Process"}
)
```

### Step 4: Add Business Processes

**Custom Validation (developer class):**
```
hie_create_item(
  project_id=project_id,
  name="NHS.Validation.Process",
  item_type="process",
  class_name="custom.nhs.NHSValidationProcess",
  pool_size=4,
  host_settings={
    "ValidateNHSNumber": "true",
    "EnrichFromPDS": "true",
    "TargetConfigNames": "ADT.Content.Router"
  }
)
```

**Content-Based Router (core class):**
```
hie_create_item(
  project_id=project_id,
  name="ADT.Content.Router",
  item_type="process",
  class_name="li.hosts.routing.HL7RoutingEngine",
  pool_size=2,
  host_settings={"BusinessRuleName": "ADT_Routing_Rules", "Validation": "Error"}
)
```

### Step 5: Add Outbound Operations

**HL7 MLLP Sender:**
```
hie_create_item(
  project_id=project_id,
  name="RIS.HL7.Sender",
  item_type="operation",
  class_name="li.hosts.hl7.HL7TCPOperation",
  pool_size=2,
  adapter_settings={"IPAddress": "ris.sth.nhs.uk", "Port": "2576"},
  host_settings={"ReplyCodeActions": ":?R=F,:?E=S,:~=S,:?A=C,:*=S"}
)
```

**File Writer:**
```
hie_create_item(
  project_id=project_id,
  name="Archive.File.Writer",
  item_type="operation",
  class_name="li.hosts.file.FileOperation",
  adapter_settings={"FilePath": "/data/outbound", "FileName": "%Y%m%d/%H%M%S_%f.hl7"}
)
```

### Step 6: Wire Connections
```
hie_create_connection(project_id=project_id, source_item_id=cerner_id, target_item_id=validation_id)
hie_create_connection(project_id=project_id, source_item_id=validation_id, target_item_id=router_id)
hie_create_connection(project_id=project_id, source_item_id=router_id, target_item_id=ris_id)
hie_create_connection(project_id=project_id, source_item_id=router_id, target_item_id=archive_id)
```

### Step 7: Add Routing Rules
```
hie_create_routing_rule(
  project_id=project_id,
  name="Route ADT to RIS and Lab",
  priority=1,
  condition_expression='{MSH-9.1} = "ADT" AND {MSH-9.2} IN ("A01","A02","A03","A08")',
  action="send",
  target_items=["RIS.HL7.Sender", "Lab.HL7.Sender", "Archive.File.Writer"],
  transform_name="v23_to_v251_RIS"
)
```

### Step 8: Deploy & Start
```
hie_deploy_project(workspace_id, project_id, start_after_deploy=true)
```

### Step 9: Test
```
hie_test_item(
  workspace_id, project_id,
  item_name="Cerner.PAS.Receiver",
  message="MSH|^~\\&|PAS|STH|HIE|STH|20260211||ADT^A01|TEST001|P|2.3\rPID|1||9876543210^^^NHS||Smith^John||19800101|M"
)
```

### Step 10: Verify
```
hie_project_status(workspace_id, project_id)
→ Confirm all items show status: RUNNING
```

## HL7 Message Reference

| Segment | Field | Description |
|---------|-------|-------------|
| MSH-9.1 | Message Code | ADT, ORM, ORU, ACK |
| MSH-9.2 | Trigger Event | A01, A02, A03, A08, O01 |
| MSH-10 | Control ID | Unique message identifier |
| MSH-12 | Version | 2.3, 2.4, 2.5.1 |
| PID-3 | Patient ID | NHS Number |
| PID-5 | Patient Name | Family^Given |
| PV1-2 | Patient Class | I (inpatient), O (outpatient), E (emergency) |
| PV1-3 | Location | Ward^Room^Bed |
| OBR-4 | Service ID | RAD-CT-HEAD, LAB-FBC |

## ReplyCodeActions Syntax (IRIS-identical)

| Pattern | Meaning | Common Action |
|---------|---------|---------------|
| `:?A=C` | ACK Accept → Complete | Standard |
| `:?E=S` | ACK Error → Suspend | Review needed |
| `:?R=F` | ACK Reject → Fail | Permanent failure |
| `:~=S` | Malformed → Suspend | Parse error |
| `:*=S` | Anything else → Suspend | Safety default |

Standard production setting: `:?R=F,:?E=S,:~=S,:?A=C,:*=S`

## Best Practices
- Use dot notation for item names: `System.Function.Role` (e.g. `Cerner.PAS.Receiver`)
- Always set ReplyCodeActions on MLLP operations
- Use priority queues for high-throughput inbound services
- Set RestartPolicy=Always for mission-critical items
- Archive all messages to file for NHS audit compliance
- Use separate ports per message source (PAS: 2575, Lab: 2576, etc.)
