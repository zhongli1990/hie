# OpenLI HIE — Developer & User Workflow Scenarios

**Version:** 1.7.3  
**Date:** February 11, 2026  
**Status:** Design Document — Feature Roadmap for Developer Experience  

---

## 1. Executive Summary

This document defines **how developers and users will work with OpenLI HIE** day-to-day, drawing direct parallels with established integration engines (InterSystems IRIS, Orion Rhapsody, Mirth Connect). It identifies what HIE already supports, what gaps exist, and proposes concrete scenarios that drive the next phase of feature development.

### The Core Question

> *"An IRIS developer launches the Management Portal, opens IRIS Studio or VS Code, connects to the IRIS server, and opens a Terminal. They configure routes, create custom classes, define schemas, build transformations and routing rules. How do HIE developers and users do the same?"*

### The Answer: Three Developer Personas, One Platform

| Persona | IRIS Equivalent | HIE Approach |
|---------|----------------|--------------|
| **Integration Configurator** | Portal-only user | Portal UI — zero code, 100% web-based |
| **Integration Developer** | Studio/VS Code + Portal | Portal UI + GenAI Agent + CLI |
| **Platform Engineer** | ObjectScript + Terminal | Python classes + Docker + REST API |

---

## 2. Competitive Workflow Comparison

### 2.1 InterSystems IRIS / Ensemble

```
Developer Workflow:
1. Launch Management Portal (web)          → Configure productions, monitor
2. Launch IRIS Studio or VS Code           → Write ObjectScript classes
3. Open Terminal to IRIS server             → Debug, test, inspect globals
4. In Studio: Create Business Process (BPL) → Visual drag-and-drop workflow
5. In Studio: Create Data Transformation   → Visual DTL mapper
6. In Portal: Add items to production      → Wire services → processes → operations
7. In Portal: Start/Stop production        → Deploy and monitor
8. In Terminal: Debug with zwrite/zbreak    → Inspect message flow
```

**Key tools:** Management Portal, Studio/VS Code, Terminal, BPL Editor, DTL Editor

### 2.2 Orion Rhapsody

```
Developer Workflow:
1. Launch Rhapsody IDE (desktop app)       → Full development environment
2. Create Communication Points             → Inbound/outbound connectors
3. Create Routes                           → Message flow paths
4. Create Filters                          → Transformations (JavaScript)
5. Define Message Definitions              → Schema editor
6. Connect components visually             → Drag-and-drop wiring
7. Deploy to Rhapsody Engine               → Push configuration
8. Monitor in Dashboard                    → Real-time message tracking
```

**Key tools:** Rhapsody IDE (desktop), Dashboard (web), JavaScript editor

### 2.3 Mirth Connect

```
Developer Workflow:
1. Launch Mirth Administrator (web)        → Channel management
2. Create Channel                          → Source + Destinations
3. Configure Source connector              → HL7/HTTP/File listener
4. Configure Destination connectors        → Outbound targets
5. Write Transformers (JavaScript/Python)  → Message transformation
6. Write Filters                           → Routing logic
7. Deploy Channel                          → Activate
8. Monitor Dashboard                       → Message statistics
```

**Key tools:** Administrator Console (web), JavaScript/Python editor

### 2.4 OpenLI HIE (Current + Proposed)

```
Developer Workflow:
1. Launch Portal (web)                     → Dashboard, Projects, Configure
2. Create Workspace + Project              → Organizational structure
3. Add Items (Service/Process/Operation)   → From class registry dropdown
4. Configure Item settings via forms       → Adapter settings, host settings
5. Draw Connections in visual designer     → Wire message flow
6. Define Routing Rules                    → Condition-based routing
7. Deploy & Start                          → One-click deployment
8. Monitor in real-time                    → Dashboard, Messages, Logs, Errors
9. [NEW] Use GenAI Agent to accelerate    → Natural language → configuration
10.[NEW] Use CLI for automation            → Scripted deployments, CI/CD
```

**Key tools:** Portal (web), GenAI Agent (web), CLI (terminal), Python (extensions), REST API

---

## 3. Developer Workflow Scenarios

### Scenario 1: "NHS Trust ADT Production" — Full Route (Integration Configurator)

**Persona:** NHS Integration Engineer, no coding experience  
**Goal:** Build a complete ADT integration: 3 inbound services (HL7 MLLP, FHIR REST, File Reader) → 2 business processes (Validation, Routing) → 3 outbound operations (RIS v2.5.1, Lab v2.4, File Writer)  
**Time:** 30 minutes  

**Comparable to:** IRIS Management Portal workflow (zero code)  
**Full walkthrough:** See [Developer & User Guide](./guides/LI_HIE_DEVELOPER_GUIDE.md)

#### Steps:

```
1. LOGIN
   → Open browser to https://hie.nhs-trust.local:9303
   → Login with NHS Identity / local credentials
   → Land on Dashboard

2. CREATE WORKSPACE + PROJECT
   → Sidebar → Projects → "Create Workspace" → Name: "St_Thomas_Hospital"
   → Inside workspace → "Create Project" → Name: "ADT_Integration"
   → Empty production ready for items

3. ADD 3 INBOUND SERVICES
   a) Click "Add Item" → Service → Class: "HL7 TCP Service"
      → Name: "Cerner.PAS.Receiver"
      → Port: 2575, Schema: v2.3, Target: "NHS.Validation.Process"
      → AckMode: Application, Pool Size: 4
   
   b) Click "Add Item" → Service → Class: "FHIR HTTP Service"
      → Name: "GP.FHIR.Receiver"
      → Port: 8443 (HTTPS), FHIR R4, NormaliseToHL7: Yes
      → Target: "NHS.Validation.Process"
   
   c) Click "Add Item" → Service → Class: "HL7 File Service"
      → Name: "Batch.File.Reader"
      → Path: /data/inbound, Spec: *.hl7, Poll: 5s
      → Archive: /data/inbound/processed
      → Target: "NHS.Validation.Process"

4. ADD 2 BUSINESS PROCESSES
   a) Click "Add Item" → Process → Class: "NHS Validation Process"
      → Name: "NHS.Validation.Process"
      → ValidateNHSNumber: Yes, EnrichFromPDS: Yes
      → CheckDuplicates: Yes, ValidatePostcode: Yes
      → Target: "ADT.Content.Router"
   
   b) Click "Add Item" → Process → Class: "HL7 Routing Engine"
      → Name: "ADT.Content.Router"
      → Add 5 routing rules:
        Rule 1: ADT A01/A02/A03/A08 → RIS (v2.5.1) + Lab (v2.4) + File
        Rule 2: ORM O01 (Radiology) → RIS (v2.5.1) + File
        Rule 3: ORM O01 (Lab)       → Lab (v2.4) + File
        Rule 4: FHIR-origin         → All targets + File
        Rule 5: Default             → File archive only

5. ADD 3 OUTBOUND OPERATIONS
   a) Click "Add Item" → Operation → Class: "HL7 TCP Operation"
      → Name: "RIS.HL7.Sender"
      → IP: ris.sth.nhs.uk, Port: 2576
      → ReplyCodeActions: ":?R=F,:?E=S,:~=S,:?A=C,:*=S"
   
   b) Click "Add Item" → Operation → Class: "HL7 TCP Operation"
      → Name: "Lab.HL7.Sender"
      → IP: lab.sth.nhs.uk, Port: 2577
      → ReplyCodeActions: ":?R=F,:?E=S,:~=S,:?A=C,:*=S"
   
   c) Click "Add Item" → Operation → Class: "File Operation"
      → Name: "Archive.File.Writer"
      → Path: /data/outbound, Pattern: %Y%m%d/%H%M%S_%f.hl7

6. WIRE CONNECTIONS (Visual Designer)
   → Drag: All 3 services → NHS.Validation.Process
   → Drag: NHS.Validation.Process → ADT.Content.Router
   → Drag: ADT.Content.Router → RIS.HL7.Sender
   → Drag: ADT.Content.Router → Lab.HL7.Sender
   → Drag: ADT.Content.Router → Archive.File.Writer
   → 7 connections total

7. DEPLOY & START
   → Click "Deploy & Start"
   → All 8 items turn green (3 services + 2 processes + 3 operations)

8. TEST
   → Send HL7 ADT A01 via MLLP → see it route to RIS + Lab + File
   → Send FHIR Patient via HTTPS → see it normalise, validate, route
   → Drop HL7 file → see it picked up, processed, archived
   → Monitor real-time in Dashboard
```

**What exists today:** Steps 1-8 are all supported via the Portal UI and Engine API.  
**Gap:** Visual designer needs polish; routing rule UI needs condition builder; FHIR service class needs implementation.

---

### Scenario 2: "AI-Assisted Development" — Using GenAI Agent (Integration Developer)

**Persona:** Integration Developer who wants to move fast  
**Goal:** Same as Scenario 1, but using the GenAI Agent to generate configuration  
**Time:** 5 minutes  

**No equivalent in IRIS/Rhapsody/Mirth — this is HIE's unique advantage.**

#### Steps:

```
1. LOGIN → Dashboard → Click "Agents" in sidebar

2. SELECT WORKSPACE
   → Agent page shows current workspace context
   → Select project or create new

3. NATURAL LANGUAGE PROMPT
   → Type: "Build a full ADT integration for St Thomas' Hospital:
     - Cerner PAS HL7 v2.3 on port 2575
     - GP FHIR REST on port 8443
     - Batch HL7 file reader from /data/inbound
     - NHS validation with PDS enrichment
     - Route ADT events to RIS (v2.5.1, ris.sth.nhs.uk:2576)
       and Lab (v2.4, lab.sth.nhs.uk:2577)
     - Archive everything to /data/outbound"
   
4. AGENT GENERATES CONFIGURATION
   → Agent calls HIE Engine API to:
     a) Create workspace "St_Thomas_Hospital" + project "ADT_Integration"
     b) Add 3 services: Cerner.PAS.Receiver, GP.FHIR.Receiver, Batch.File.Reader
     c) Add 2 processes: NHS.Validation.Process, ADT.Content.Router (5 rules)
     d) Add 3 operations: RIS.HL7.Sender, Lab.HL7.Sender, Archive.File.Writer
     e) Wire 7 connections
     f) Deploy & start

5. AGENT REPORTS BACK
   → "Created 'ADT_Integration' with 8 items:
      Inbound:
        ✅ Cerner.PAS.Receiver (HL7 TCP, port 2575)
        ✅ GP.FHIR.Receiver (FHIR R4 HTTPS, port 8443)
        ✅ Batch.File.Reader (File, /data/inbound/*.hl7)
      Process:
        ✅ NHS.Validation.Process (NHS#, PDS, duplicates, postcode)
        ✅ ADT.Content.Router (5 routing rules)
      Outbound:
        ✅ RIS.HL7.Sender (HL7 v2.5.1, ris.sth.nhs.uk:2576)
        ✅ Lab.HL7.Sender (HL7 v2.4, lab.sth.nhs.uk:2577)
        ✅ Archive.File.Writer (/data/outbound)
      Production running (8/8 active). Shall I send a test message?"

6. TEST VIA AGENT
   → Type: "Yes, send a test ADT A01 and a FHIR Patient"
   → Agent sends both, reports ACKs received from RIS and Lab

7. ITERATE
   → "Add an alerting email operation for validation failures"
   → Agent adds EmailAlertOperation and wires it to the exception queue
```

**What exists today:** Agent page with SSE streaming, session persistence (in progress), prompt templates.  
**Gap:** Agent needs HIE Engine API skills (create project, add items, deploy). Currently the agent is a general-purpose Claude/Codex assistant — it needs **HIE-specific tool functions**.

---

### Scenario 3: "Custom Business Process" — Python Extension (Platform Engineer)

**Persona:** Senior developer who needs custom message transformation  
**Goal:** Create a custom process that enriches ADT messages with data from a REST API  
**Time:** 30 minutes  

**Comparable to:** IRIS Studio ObjectScript class development

#### Steps:

```
1. WRITE PYTHON CLASS (in IDE or via Agent)

   # File: custom/enrichment/patient_lookup.py
   
   from Engine.li.hosts.base import BusinessProcess
   from Engine.li.registry.class_registry import register_host
   
   @register_host("custom.enrichment.PatientLookupProcess")
   class PatientLookupProcess(BusinessProcess):
       """Enrich ADT messages with patient demographics from PDS."""
       
       async def on_message(self, message):
           # Extract PID-3 (patient ID)
           raw = message.raw.decode('utf-8')
           pid_segment = [s for s in raw.split('\r') if s.startswith('PID')][0]
           patient_id = pid_segment.split('|')[3].split('^')[0]
           
           # Call PDS API
           import aiohttp
           async with aiohttp.ClientSession() as session:
               async with session.get(
                   f"https://pds.nhs-trust.local/Patient/{patient_id}"
               ) as resp:
                   patient_data = await resp.json()
           
           # Enrich message with NHS number
           nhs_number = patient_data.get('nhsNumber', '')
           # ... add to PID-3.5
           
           return message

2. UPLOAD TO HIE (via Portal or Docker volume)
   → Portal: Admin → Skills → Upload Custom Class
   → Or: Mount volume in docker-compose.yml:
     volumes:
       - ./custom:/app/custom:ro

3. REGISTER IN PORTAL
   → Projects → Select Project → Add Item
   → Class dropdown now shows: "custom.enrichment.PatientLookupProcess"
   → Configure settings
   → Wire into existing flow: PAS.ADT.Receiver → PatientLookup → ADT.Router

4. DEPLOY & TEST
   → Deploy & Start
   → Send test message
   → Verify enrichment in Messages tab

5. ALTERNATIVELY — USE AGENT
   → "Create a custom business process that looks up patient demographics 
      from PDS API and enriches the ADT message with NHS number"
   → Agent generates the Python class
   → Agent registers it in the project
```

**What exists today:** ClassRegistry with `@register_host` decorator, dynamic import via `get_or_import_host_class`, IRIS alias mapping.  
**Gap:** No file upload UI for custom classes. No "hot deploy" of custom Python without container restart. Need a `/api/extensions` endpoint.

---

### Scenario 4: "Data Transformation" — Visual Mapping (Integration Configurator)

**Persona:** Integration analyst who needs to map fields between systems  
**Goal:** Transform HL7 ADT A01 from PAS format to EPR format  
**Time:** 20 minutes  

**Comparable to:** IRIS DTL Editor, Rhapsody Filter Editor

#### Steps:

```
1. NAVIGATE TO PROJECT → Select "ADT Receiver" project

2. CREATE TRANSFORMATION
   → Click "Add Item" → Type: Process
   → Class: "Data Transformation" (from dropdown)
   → Name: "ADT.PAStoEPR.Transform"

3. OPEN VISUAL MAPPER [FUTURE]
   → Left panel: Source schema (PAS ADT A01)
   → Right panel: Target schema (EPR ADT A01)
   → Draw lines between fields:
     - PAS PID-3.1 → EPR PID-3.1 (MRN)
     - PAS PID-5.1 → EPR PID-5.1 (Family Name)  
     - PAS PID-5.2 → EPR PID-5.2 (Given Name)
     - PAS PV1-3.1 → EPR PV1-3.1 (Ward) [with lookup table]
   → Add computed field: EPR PID-3.5 = NHS Number (from PDS lookup)

4. ALTERNATIVELY — USE PROMPT TEMPLATE
   → Go to Prompts page
   → Select "FHIR Resource Mapping" template
   → Fill in variables:
     - source_format: "HL7 ADT A01 (PAS)"
     - target_format: "HL7 ADT A01 (EPR)"
     - mapping_requirements: "Map MRN, name, ward with lookup table"
   → Send to Agent → Agent generates transformation code

5. WIRE INTO FLOW
   → ADT.Router → ADT.PAStoEPR.Transform → EPR.Sender
   → Deploy & Start

6. TEST WITH SAMPLE MESSAGE
   → Messages tab → Send test
   → Compare input vs output in message viewer
```

**What exists today:** Routing rules with condition expressions, prompt templates for FHIR mapping.  
**Gap:** No visual DTL/mapping editor (planned Phase 4). Agent can generate transformation code but can't yet deploy it directly.

---

### Scenario 5: "Schema Management" — HL7 Message Definitions (Integration Developer)

**Persona:** Developer who needs to define/customize message schemas  
**Goal:** Define a custom Z-segment for local ADT messages  
**Time:** 10 minutes  

**Comparable to:** IRIS Schema Editor, Rhapsody Message Definition Editor

#### Steps:

```
1. NAVIGATE TO ADMIN → Schemas [FUTURE PAGE]

2. VIEW BUILT-IN SCHEMAS
   → HL7 v2.4 (standard segments: MSH, PID, PV1, OBX, etc.)
   → HL7 v2.5.1
   → FHIR R4 (future)

3. CREATE CUSTOM SCHEMA
   → Click "Create Schema"
   → Base: HL7 v2.4
   → Add Z-Segment:
     Name: ZPI
     Fields:
       ZPI-1: NHS Number (ST)
       ZPI-2: GP Practice Code (ST)
       ZPI-3: CCG Code (ST)
       ZPI-4: Ethnicity Code (CE)
   → Save as "NHS-ADT-v2.4-Custom"

4. ASSIGN TO SERVICE
   → PAS.ADT.Receiver → Settings → MessageSchemaCategory: "NHS-ADT-v2.4-Custom"
   → Now the service validates and parses using the custom schema

5. ALTERNATIVELY — USE AGENT
   → "Define a custom Z-segment ZPI with NHS Number, GP Practice Code, 
      CCG Code, and Ethnicity Code fields for our ADT messages"
   → Agent generates schema definition and registers it
```

**What exists today:** `Engine/li/schemas/hl7/` with schema definitions, `SchemaRegistry` class.  
**Gap:** No Portal UI for schema management. No schema editor page. Schemas are code-only.

---

### Scenario 6: "Import Existing IRIS Production" — Migration (Platform Engineer)

**Persona:** Engineer migrating from IRIS to HIE  
**Goal:** Import an existing IRIS production XML export  
**Time:** 30 minutes  

**No equivalent in other engines — this is HIE's migration advantage.**

#### Steps:

```
1. EXPORT FROM IRIS
   → In IRIS Management Portal: System > Configuration > Productions
   → Export production as XML

2. IMPORT INTO HIE
   → Portal → Projects → "Import IRIS Configuration"
   → Upload XML file
   → HIE parses:
     - EnsLib.HL7.Service.TCPService → li.hosts.hl7.HL7TCPService
     - EnsLib.HL7.MsgRouter.RoutingEngine → li.hosts.hl7.HL7RoutingEngine
     - EnsLib.HL7.Operation.TCPOperation → li.hosts.hl7.HL7TCPOperation
   → Preview: "Found 12 items, 8 connections, 3 routing rules"
   → Click "Import"

3. REVIEW & ADJUST
   → Open imported project in visual designer
   → Verify connections and settings
   → Adjust any IRIS-specific settings to HIE equivalents

4. DEPLOY & TEST
   → Deploy & Start
   → Run integration tests
   → Compare message flow with IRIS production
```

**What exists today:** `IRISXMLLoader` in `Engine/li/config/iris_xml_loader.py`, `import_iris_config` endpoint in projects API, IRIS alias mapping in ClassRegistry.  
**Gap:** Portal UI for import exists but needs file upload component. No side-by-side comparison view.

---

### Scenario 7: "CI/CD Pipeline" — Automated Deployment (DevOps Engineer)

**Persona:** DevOps engineer setting up automated deployments  
**Goal:** Deploy HIE configuration changes via Git push  
**Time:** Initial setup 1 hour, then automatic  

**Comparable to:** IRIS %Installer, Rhapsody REST API deployment

#### Steps:

```
1. STORE CONFIGURATION IN GIT
   → Export project config: GET /api/workspaces/{id}/projects/{id}/export
   → Commit JSON to Git repository
   → Structure:
     hie-config/
       workspaces/
         pas-integration/
           workspace.json
           projects/
             adt-receiver/
               project.json
               items/
               connections/
               routing-rules/

2. CI/CD PIPELINE (GitHub Actions / GitLab CI)
   → On push to main:
     a) Run validation tests
     b) Call HIE API to import configuration
     c) Deploy & start
     d) Run smoke tests
     e) Report status

3. EXAMPLE GITHUB ACTION:
   
   name: Deploy HIE Configuration
   on:
     push:
       branches: [main]
       paths: ['hie-config/**']
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - name: Deploy to HIE
           run: |
             # Import configuration
             curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects/import \
               -H "Authorization: Bearer $HIE_TOKEN" \
               -F "file=@hie-config/projects/adt-receiver/project.json"
             
             # Deploy & start
             curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects/$PROJ_ID/deploy \
               -H "Authorization: Bearer $HIE_TOKEN" \
               -d '{"start_after_deploy": true}'
             
             # Smoke test
             curl -X POST $HIE_URL/api/workspaces/$WS_ID/projects/$PROJ_ID/items/EPR.Sender/test

4. HIE CLI (FUTURE)
   → hie login --url https://hie.nhs-trust.local:9303
   → hie project deploy ./adt-receiver --start
   → hie project test ./adt-receiver --smoke
```

**What exists today:** Full REST API for all CRUD operations, export endpoint, import endpoint.  
**Gap:** No CLI tool. No Git-based config sync. No GitHub Action. Export format needs standardization.

---

### Scenario 8: "Real-Time Monitoring & Debugging" — Operations (System Administrator)

**Persona:** On-call system administrator  
**Goal:** Investigate why ADT messages are failing  
**Time:** 5-10 minutes  

**Comparable to:** IRIS Message Viewer + Event Log, Rhapsody Dashboard

#### Steps:

```
1. ALERT RECEIVED
   → Email/Slack: "EPR.Sender error rate >5% in last 10 minutes"

2. OPEN DASHBOARD
   → Portal → Dashboard
   → See: EPR.Sender showing red (error state)
   → Message throughput graph shows drop at 14:32

3. CHECK ERRORS
   → Portal → Errors
   → Filter by item: "EPR.Sender"
   → See: "Connection refused: epr.nhs-trust.local:10002"
   → 47 messages queued, 12 failed

4. CHECK MESSAGES
   → Portal → Messages
   → Filter by status: "failed"
   → Click message → See full HL7 content + error details
   → See retry history

5. CHECK LOGS
   → Portal → Logs
   → Filter by item: "EPR.Sender"
   → See connection attempt logs with timestamps

6. INVESTIGATE
   → EPR system is down for maintenance
   → Messages are queuing (at-least-once delivery)

7. RESOLVE
   → EPR comes back online
   → Queued messages automatically retry
   → Error rate drops to 0%
   → Dashboard turns green

8. ALTERNATIVELY — ASK AGENT
   → "Why is EPR.Sender failing?"
   → Agent checks status API, reads logs, reports:
     "EPR.Sender has 47 queued messages. Connection refused to 
      epr.nhs-trust.local:10002 since 14:32. The EPR system appears 
      to be unreachable. Messages will auto-retry when connection 
      is restored."
```

**What exists today:** Dashboard, Monitoring, Errors, Logs, Messages pages all exist in Portal. Engine provides metrics and health checks.  
**Gap:** No alerting system (email/Slack). No message retry UI. Agent doesn't have monitoring skills yet.

---

## 4. Feature Gap Analysis

### What HIE Has Today (v1.7.3)

| Category | Feature | Status |
|----------|---------|--------|
| **Portal UI** | Dashboard with real-time metrics | ✅ |
| | Projects page (CRUD, deploy, start/stop) | ✅ |
| | Configure page (visual item editor) | ✅ |
| | Messages page (message viewer) | ✅ |
| | Monitoring page (health, metrics) | ✅ |
| | Errors page (error log) | ✅ |
| | Logs page (structured logs) | ✅ |
| | Settings page | ✅ |
| **GenAI** | Agent page (Claude/Codex SSE streaming) | ✅ |
| | Chat page (conversational interface) | ✅ |
| | Prompt templates (10 healthcare templates) | ✅ |
| | Skills management (5 platform skills) | ✅ |
| | Hooks configuration (security, audit, compliance) | ✅ |
| **Engine** | HL7 TCP Service/Operation (MLLP) | ✅ |
| | Routing Engine with condition rules | ✅ |
| | ClassRegistry with IRIS aliases | ✅ |
| | Dynamic class import (`get_or_import_host_class`) | ✅ |
| | IRIS XML import | ✅ |
| | Project export (JSON) | ✅ |
| | Deploy, Start, Stop, Status API | ✅ |
| | Test message sending | ✅ |
| | Message persistence & store | ✅ |
| | Multiprocess execution, priority queues | ✅ |
| | Auto-restart policies | ✅ |
| | Hot reload | ✅ |
| **Admin** | User management page | ✅ |
| | JWT authentication | ✅ |
| | Workspace/tenant isolation | ✅ |

### What HIE Needs Next (Proposed v1.8.x — v2.0)

| Priority | Feature | Enables Scenario | Effort |
|----------|---------|-----------------|--------|
| **P0 — Critical** |
| | Agent HIE Skills (create project, add items, deploy via API) | Scenario 2 | 2 weeks |
| | File Upload UI for custom classes | Scenario 3 | 1 week |
| | Schema management page | Scenario 5 | 2 weeks |
| | IRIS import UI with file upload | Scenario 6 | 1 week |
| **P1 — High** |
| | Visual routing rule builder (condition editor) | Scenario 1 | 2 weeks |
| | Message retry/resubmit UI | Scenario 8 | 1 week |
| | Alerting system (email, Slack, webhook) | Scenario 8 | 2 weeks |
| | Agent monitoring skills (check status, read logs) | Scenario 8 | 1 week |
| **P2 — Medium** |
| | CLI tool (`hie` command) | Scenario 7 | 3 weeks |
| | Git-based config sync | Scenario 7 | 2 weeks |
| | Visual data transformation editor (DTL) | Scenario 4 | 4 weeks |
| | Side-by-side message comparison | Scenario 8 | 1 week |
| **P3 — Future** |
| | GitHub Action for CI/CD | Scenario 7 | 1 week |
| | FHIR R4 adapters | All | 6 weeks |
| | NHS Spine connectors (PDS, EPS, SCR) | All | 8 weeks |
| | Marketplace for shared components | All | 4 weeks |

---

## 5. HIE's Unique Advantage: GenAI-Assisted Integration

No competing product offers AI-assisted integration development. This is HIE's **killer differentiator**.

### What the Agent Needs to Become Useful

The agent currently operates as a general-purpose LLM assistant. To become an **HIE Integration Agent**, it needs:

#### 5.1 HIE Engine Skills (Tool Functions)

```python
# Skills the agent needs to call HIE Engine API:

# Workspace & Project Management
create_workspace(name, description)
create_project(workspace_id, name, description)
list_projects(workspace_id)
delete_project(workspace_id, project_id)

# Item Management
add_item(project_id, name, item_type, class_name, settings)
update_item(project_id, item_id, settings)
remove_item(project_id, item_id)
list_available_classes()  # From ClassRegistry

# Connection Management
add_connection(project_id, source_item, target_item)
remove_connection(project_id, connection_id)

# Routing Rules
add_routing_rule(project_id, name, condition, action, targets)
update_routing_rule(project_id, rule_id, ...)

# Deployment & Control
deploy_project(workspace_id, project_id, start=True)
start_project(workspace_id, project_id)
stop_project(workspace_id, project_id)
get_project_status(workspace_id, project_id)

# Testing
send_test_message(workspace_id, project_id, item_name, message)

# Monitoring
get_dashboard_metrics()
get_error_log(item_name, limit)
get_message_log(item_name, status, limit)

# Schema Management
list_schemas()
get_schema(name)
create_custom_schema(name, base, segments)

# Import/Export
import_iris_config(workspace_id, xml_content)
export_project(workspace_id, project_id)
```

#### 5.2 Agent Conversation Examples

**Example 1: Build from scratch**
```
User: "I need to receive HL7 ORM messages from the lab system on port 10005 
       and forward them to the pharmacy at pharmacy.nhs-trust.local:10006"

Agent: I'll create that integration for you.

[Calls: create_project("Lab-Pharmacy ORM Bridge")]
[Calls: add_item(project, "Lab.ORM.Receiver", "service", "HL7TCPService", {port: 10005})]
[Calls: add_item(project, "Pharmacy.Sender", "operation", "HL7TCPOperation", {ip: "pharmacy.nhs-trust.local", port: 10006})]
[Calls: add_connection(project, "Lab.ORM.Receiver", "Pharmacy.Sender")]
[Calls: deploy_project(project, start=True)]

Agent: Done! Created "Lab-Pharmacy ORM Bridge" with:
  ✅ Lab.ORM.Receiver — listening on port 10005
  ✅ Pharmacy.Sender — sending to pharmacy.nhs-trust.local:10006
  Production is running. Want me to send a test ORM message?
```

**Example 2: Troubleshoot**
```
User: "Why are messages failing on the EPR sender?"

Agent: Let me check.

[Calls: get_project_status(workspace, project)]
[Calls: get_error_log("EPR.Sender", limit=10)]

Agent: EPR.Sender has 23 failed messages in the last hour. 
  Error: "Connection refused: epr.nhs-trust.local:10002"
  The EPR system appears unreachable since 14:32.
  
  12 messages are queued and will auto-retry when the connection is restored.
  Would you like me to:
  1. Check if the EPR system is responding to ping?
  2. Increase the retry interval?
  3. Route messages to a backup EPR?
```

**Example 3: Migrate from IRIS**
```
User: "Import this IRIS production" [uploads XML]

Agent: Analyzing IRIS production XML...

[Calls: import_iris_config(workspace, xml_content)]

Agent: Imported "PAS.Production" with:
  - 4 Services (HL7 TCP, HTTP, File)
  - 2 Processes (Routing Engine, Sequence Manager)  
  - 6 Operations (HL7 TCP × 3, Email Alert, File, HTTP)
  - 8 Connections
  - 3 Routing Rules
  
  ⚠️ 2 items use custom ObjectScript classes that need Python equivalents:
  - Custom.PAS.ADTProcess → Needs Python implementation
  - Custom.PAS.NHSLookup → Needs Python implementation
  
  Want me to generate Python equivalents based on the class names and settings?
```

---

## 6. Proposed Development Roadmap

### Phase 7: Developer Experience (v1.8.0 — v1.9.0)

**Sprint 1 (2 weeks): Agent HIE Skills**
- Implement agent tool functions for HIE Engine API
- Register as agent-runner skills
- Test with Scenario 2 conversations

**Sprint 2 (2 weeks): Portal Enhancements**
- File upload UI for IRIS XML import
- File upload UI for custom Python classes
- Visual routing rule condition builder

**Sprint 3 (2 weeks): Schema & Monitoring**
- Schema management Portal page
- Message retry/resubmit UI
- Agent monitoring skills

### Phase 8: Automation & CI/CD (v2.0.0)

**Sprint 4 (3 weeks): CLI & Git Sync**
- `hie` CLI tool (Python, pip-installable)
- Git-based configuration sync
- GitHub Action for automated deployment

**Sprint 5 (4 weeks): Visual Editors**
- Visual data transformation editor (DTL equivalent)
- Visual BPL-style workflow editor
- Side-by-side message comparison

### Phase 9: NHS Ecosystem (v2.1.0+)

- FHIR R4 adapters
- NHS Spine connectors (PDS, EPS, SCR)
- NHS Identity integration
- Alerting system (email, Slack, Teams)

---

## 7. Summary: How HIE Developers Work

| Task | IRIS | Rhapsody | Mirth | **HIE** |
|------|------|----------|-------|---------|
| Configure routes | Management Portal | Rhapsody IDE | Admin Console | **Portal UI** |
| Write custom code | Studio (ObjectScript) | IDE (JavaScript) | Console (JS/Python) | **IDE (Python) + Agent** |
| Debug/test | Terminal + Message Viewer | Dashboard | Dashboard | **Portal + Agent** |
| Deploy | Portal → Apply | IDE → Deploy | Console → Deploy | **Portal → Deploy & Start** |
| Monitor | Portal Dashboard | Dashboard | Dashboard | **Portal Dashboard** |
| Automate | %Installer + REST | REST API | REST API | **CLI + REST API + Agent** |
| **AI-Assisted** | ❌ | ❌ | ❌ | **✅ GenAI Agent** |
| **Natural Language** | ❌ | ❌ | ❌ | **✅ "Create an HL7 receiver..."** |
| **Migration** | N/A | Manual | Manual | **✅ IRIS XML Import** |

### The HIE Developer Experience in One Sentence

> **"Open the Portal, tell the Agent what you need in plain English, review the generated configuration, click Deploy — or do it all manually through the visual UI if you prefer."**

---

*Document maintained by the HIE Core Team. Next review: Sprint 1 kickoff.*
