# LI HIE Developer & Administrator Guide
## NHS Trust Integration Scenario - Complete Configuration Guide

## Overview

**LI HIE (IRIS-compatible Healthcare Integration Engine)** is a fully configurable, enterprise-grade integration orchestrator for NHS acute trusts. Like InterSystems IRIS, Orion Rhapsody, and Mirth Connect, **all integrations are configured through the Portal UI and Manager API** - no coding required for standard workflows.

This guide demonstrates how to configure a complete production-ready NHS integration using **100% configuration** through the Portal.

## Enterprise Integration Engine Capabilities

### Comparison with Leading Platforms

| Capability | IRIS | Rhapsody | Mirth | **LI HIE** |
|------------|------|----------|-------|------------|
| Visual configuration | ✅ | ✅ | ✅ | ✅ Portal UI |
| Zero-code workflows | ✅ | ✅ | ✅ | ✅ 100% config |
| HL7 v2.x support | ✅ | ✅ | ✅ | ✅ v2.3-v2.8 |
| MLLP TCP/IP | ✅ | ✅ | ✅ | ✅ Native |
| File I/O | ✅ | ✅ | ✅ | ✅ Watch/Write |
| Business processes | ✅ | ✅ | ✅ | ✅ Rule engine |
| Message transformation | ✅ | ✅ | ✅ | ✅ DTL-style |
| Production orchestration | ✅ | ✅ | ✅ | ✅ Manager API |
| Auto-restart | ✅ | ✅ | ✅ | ✅ Phase 2 |
| Multi-process execution | ✅ | ✅ | ❌ | ✅ Phase 1 |
| Priority queues | ✅ | ✅ | ❌ | ✅ Phase 2 |
| Hot configuration reload | ✅ | ❌ | ❌ | ✅ Phase 3 |

## Clinical Scenario: St. Thomas' Hospital

**Integration Requirement:**
Connect Cerner Millennium PAS with downstream clinical systems (RIS, ICE Lab) with full audit trail and NHS compliance.

**All configuration done through Portal UI** - no code writing required.

## Step 1: Create Workspace (via Portal UI)

**Navigation:** Portal → Workspaces → Create New

```yaml
# Configuration Form in Portal UI
Workspace Name: "St. Thomas' Hospital"
Workspace ID: "st-thomas-hospital"
Description: "Main acute trust integration hub"
Tags: ["NHS", "Acute Trust", "South London"]
Region: "London"
Contact: "integration.team@sthospital.nhs.uk"
```

**Result:** Workspace created and activated

## Step 2: Create Project (via Portal UI)

**Navigation:** Portal → St. Thomas' Hospital → Projects → Create New

```yaml
# Configuration Form
Project Name: "ADT Integration Production"
Project ID: "adt-integration-prod"
Description: "Patient admission/discharge/transfer integration"
Version: "1.0.0"
Environment: "Production"
Status: "Active"
```

**Result:** Empty production ready for item configuration

## Step 3: Configure Items (via Portal UI)

### 3.1 Add HL7 Inbound Service (MLLP from Cerner PAS)

**Navigation:** Portal → Project → Items → Add New Item

**Item Type Selection:**
```
Category: Services (Inbound)
Type: HL7 TCP Service
Template: Cerner Millennium PAS Receiver
```

**Basic Configuration:**
```yaml
Name: "HL7_PAS_Service"
Display Name: "Cerner PAS HL7 Receiver"
Enabled: ✅ Yes
Pool Size: 4
Category: "Inbound | PAS"
Comment: "Receives ADT and Order messages from Cerner Millennium"
```

**Adapter Settings (TCP/MLLP):**
```yaml
Port: 2575
IP Address: 0.0.0.0 (Listen on all interfaces)
Job Per Connection: ✅ Yes
Read Timeout: 30 seconds
Stay Connected: -1 (Keep alive)
SSL Config: (none - internal network)
```

**Host Settings (HL7 Processing):**
```yaml
Message Schema Category: HL7 v2.3
Target Config Names: ["ADT_Router"] (select from dropdown)
ACK Mode: App (Application ACK after processing)
Archive IO: ✅ Yes (for audit)
```

**🆕 Phase 2 Enterprise Settings (Performance & Reliability):**
```yaml
# Execution Configuration
Execution Mode: Multiprocess (4 OS processes)
Worker Count: 4 (match CPU cores)

# Queue Configuration
Queue Type: Priority (urgent messages first)
Queue Size: 10000
Overflow Strategy: Drop Oldest (prevent memory overflow)

# Auto-Restart Configuration
Restart Policy: Always (mission-critical)
Max Restarts: 100
Restart Delay: 10 seconds

# Messaging Configuration
Messaging Pattern: Async Reliable (fire-and-forget)
Message Timeout: 30 seconds
```

**Portal Actions:**
- Click "Save" → Item saved to database
- Click "Deploy" → Item configuration sent to Engine
- Click "Start" → Service starts listening on port 2575

**Result:** ✅ HL7 PAS Service **running** and **accepting connections**

---

### 3.2 Add File Watcher Service

**Navigation:** Portal → Items → Add New Item → File Service

**Basic Configuration:**
```yaml
Name: "File_PAS_Service"
Display Name: "PAS Batch File Watcher"
Enabled: ✅ Yes
```

**Adapter Settings:**
```yaml
File Path: /data/inbound
File Spec: *.hl7
Polling Interval: 5 seconds
Archive Path: /data/processed
Recursive: ❌ No
```

**Host Settings:**
```yaml
Target Config Names: ["ADT_Router"]
```

**Phase 2 Settings:**
```yaml
Execution Mode: Async (single event loop sufficient)
Queue Type: FIFO (process files in order)
Queue Size: 1000
Restart Policy: On Failure
Max Restarts: 5
```

**Portal Actions:** Save → Deploy → Start

**Result:** ✅ File watcher **running** and **monitoring** /data/inbound

---

### 3.3 Add Business Process (ADT Router with Rule Engine)

**Navigation:** Portal → Items → Add New Item → Business Process

**Item Type Selection:**
```
Type: HL7 Routing Engine
Template: ADT Message Router
```

**Basic Configuration:**
```yaml
Name: "ADT_Router"
Display Name: "ADT Routing & Transformation Process"
Enabled: ✅ Yes
Pool Size: 2
Category: "Business Process | Routing"
```

**Host Settings (Rule Engine):**
```yaml
Business Rule Name: "ADT_Routing_Rules"
Validation: Error (fail on invalid messages)
Rule Logging: All Rules (full audit trail)
```

**Business Rules Configuration (Visual Rule Builder in Portal):**

**Rule 1: ADT Messages → RIS + ICE Lab**
```
IF message.MSH.MessageType IN ["ADT^A01", "ADT^A02", "ADT^A03", "ADT^A08"]
THEN:
  1. Transform message to HL7 v2.4 → Send to "RIS_Operation"
  2. Transform message to HL7 v2.5.1 → Send to "ICE_Operation"
  3. Send original to "Audit_File_Writer"
```

**Rule 2: Radiology Orders → RIS Only**
```
IF message.MSH.MessageType = "ORM^O01"
   AND message.ORC.OrderControl = "NW"
   AND message.OBR.UniversalServiceID contains "RAD"
THEN:
  1. Transform to HL7 v2.4 → Send to "RIS_Operation"
  2. Send original to "Audit_File_Writer"
```

**Rule 3: Lab Orders → ICE Lab Only**
```
IF message.MSH.MessageType = "ORM^O01"
   AND message.ORC.OrderControl = "NW"
   AND message.OBR.UniversalServiceID contains "LAB"
THEN:
  1. Transform to HL7 v2.5.1 → Send to "ICE_Operation"
  2. Send original to "Audit_File_Writer"
```

**Transformation Configuration (Visual Mapper):**
```yaml
# HL7 v2.3 → v2.4 Transformation
Source Schema: 2.3
Target Schema: 2.4
Mappings:
  - MSH.SendingApplication: "HIE"
  - MSH.VersionID: "2.4"
  - PID.* → PID.* (copy all)
  - PV1.* → PV1.* (copy all)
  - Custom: Add Z-segment for audit trail

# HL7 v2.3 → v2.5.1 Transformation
Source Schema: 2.3
Target Schema: 2.5.1
Mappings:
  - MSH.SendingApplication: "HIE"
  - MSH.VersionID: "2.5.1"
  - MSH.MessageStructure: "ADT_A01" (required in v2.5+)
  - PID.* → PID.* (copy all)
  - PV1.* → PV1.* (update delimiters for v2.5.1)
```

**Phase 2 Settings (Mission-Critical Process):**
```yaml
Execution Mode: Thread Pool (2 workers for blocking I/O)
Worker Count: 2
Queue Type: FIFO (ordered processing required)
Queue Size: 5000
Overflow Strategy: Block (never drop clinical messages)
Restart Policy: Always (never stay down)
Max Restarts: 1000 (extremely high tolerance)
Restart Delay: 30 seconds (allow recovery)
Messaging Pattern: Sync Reliable (wait for downstream ACKs)
Message Timeout: 60 seconds
```

**Portal Actions:** Save → Deploy → Start

**Result:** ✅ ADT Router **running** with **active rule engine**

---

### 3.4 Add Custom Validation Process (NHS-Specific)

**Navigation:** Portal → Items → Add New Item → Business Process → Custom

**Item Type Selection:**
```
Type: Custom Business Process
Class: NHS Validation Process (from library)
```

**Basic Configuration:**
```yaml
Name: "Complex_Validation_Process"
Display Name: "NHS Validation & Enrichment"
Enabled: ✅ Yes
Pool Size: 2
```

**Custom Host Settings (NHS-Specific):**
```yaml
Validate NHS Number: ✅ Yes (Modulus 11 check)
Enrich From PDS: ✅ Yes (lookup patient demographics)
Check Duplicates: ✅ Yes (prevent duplicate admissions)
Validate Postcode: ✅ Yes (UK postcode format)
PDS Endpoint: "https://pds.spine.nhs.uk/api"
PDS Timeout: 5 seconds
Duplicate Window: 60 seconds
```

**Phase 2 Settings:**
```yaml
Execution Mode: Thread Pool (for PDS API calls)
Worker Count: 4
Queue Type: Priority
Restart Policy: Always
Messaging Pattern: Sync Reliable (wait for PDS response)
Message Timeout: 10 seconds
```

**Portal Actions:** Save → Deploy → Start

**Result:** ✅ NHS Validation **running** with **PDS integration**

---

### 3.5 Add Outbound Operation (RIS - Radiology)

**Navigation:** Portal → Items → Add New Item → Operations (Outbound)

**Item Type Selection:**
```
Type: HL7 TCP Operation
Template: RIS MLLP Sender
```

**Basic Configuration:**
```yaml
Name: "RIS_Operation"
Display Name: "RIS Radiology System Sender"
Enabled: ✅ Yes
Pool Size: 2
```

**Adapter Settings (MLLP Client):**
```yaml
IP Address: ris.sthospital.nhs.uk
Port: 2576
Connect Timeout: 30 seconds
Reconnect Retry: 5 attempts
Reconnect Interval: 10 seconds
Stay Connected: -1 (persistent connection)
SSL Config: (none)
```

**Host Settings (Send Behavior):**
```yaml
Reply Code Actions: ":?R=F,:?E=S,:~=S,:?A=C,:*=S" (IRIS-style retry logic)
Retry Interval: 5 seconds
Failure Timeout: 15 seconds
Archive IO: ✅ Yes
```

**Phase 2 Settings:**
```yaml
Execution Mode: Thread Pool
Worker Count: 2
Queue Type: FIFO
Queue Size: 5000
Overflow Strategy: Block
Restart Policy: Always
Max Restarts: 100
```

**Portal Actions:** Save → Deploy → Start

**Result:** ✅ RIS Operation **running** and **connected** to RIS

---

### 3.6 Add Outbound Operation (ICE Lab)

**Configuration:** (Similar to RIS, but different endpoint)

```yaml
Name: "ICE_Operation"
IP Address: ice.sthospital.nhs.uk
Port: 2577
# Same Phase 2 settings as RIS
```

**Result:** ✅ ICE Operation **running** and **connected** to Lab

---

### 3.7 Add File Writer (Processed Messages)

**Navigation:** Portal → Items → Add New Item → File Operation

```yaml
Name: "Output_File_Writer"
File Path: /data/outbound
File Name Pattern: %Y%m%d_%H%M%S_%f.hl7
Overwrite: ❌ No (preserve all messages)
```

**Result:** ✅ File writer **active**

---

### 3.8 Add Audit File Writer (Compliance)

```yaml
Name: "Audit_File_Writer"
File Path: /data/audit
File Name Pattern: audit_%Y%m%d_%H%M%S_%f.hl7
Queue Size: 50000 (large buffer for audit trail)
Overflow Strategy: Drop Oldest (audit not mission-critical)
```

**Result:** ✅ Audit writer **active**

---

## Step 4: Configure Connections (via Portal UI)

**Navigation:** Portal → Project → Connections → Visual Designer

**Connection 1: PAS Service → Validation Process**
```
Drag: HL7_PAS_Service → Complex_Validation_Process
Type: Async Reliable
Filter: (none - process all messages)
```

**Connection 2: File Service → Validation Process**
```
Drag: File_PAS_Service → Complex_Validation_Process
```

**Connection 3: Validation → ADT Router**
```
Drag: Complex_Validation_Process → ADT_Router
```

**Connection 4: ADT Router → RIS**
```
Drag: ADT_Router → RIS_Operation
Filter: IF transformation = "v2.4"
```

**Connection 5: ADT Router → ICE Lab**
```
Drag: ADT_Router → ICE_Operation
Filter: IF transformation = "v2.5.1"
```

**Connection 6: ADT Router → Audit**
```
Drag: ADT_Router → Audit_File_Writer
Filter: (all messages)
```

**Result:** Visual workflow diagram showing complete message flow

---

## Step 5: Deploy & Start Production (via Portal UI)

**Navigation:** Portal → Project → Production Controls

### Deploy Production
```
Click: "Deploy Production"
Status: Deploying... (sending config to Engine)
Result: ✅ Production deployed to Engine
```

### Start Production
```
Click: "Start Production"
Status: Starting all enabled items...

Starting:
✅ HL7_PAS_Service (port 2575 listening)
✅ File_PAS_Service (watching /data/inbound)
✅ Complex_Validation_Process (2 workers active)
✅ ADT_Router (rule engine initialized)
✅ RIS_Operation (connected to ris.sthospital.nhs.uk:2576)
✅ ICE_Operation (connected to ice.sthospital.nhs.uk:2577)
✅ Output_File_Writer (ready)
✅ Audit_File_Writer (ready)

Production Status: ✅ RUNNING (8/8 items active)
```

---

## Step 6: Monitor Production (via Portal UI)

**Navigation:** Portal → Project → Monitoring → Dashboard

### Real-Time Metrics Display

**Production Overview:**
```
Status: 🟢 RUNNING
Uptime: 2 hours 15 minutes
Messages Processed: 1,247
Messages Failed: 3
Success Rate: 99.76%
```

**Item Status:**
```
Item Name                      Status    Queue    Workers  Restarts  Throughput
HL7_PAS_Service               🟢 RUN    45/10000    4/4      0       250 msg/hr
File_PAS_Service              🟢 RUN     0/1000     1/1      0        12 msg/hr
Complex_Validation_Process    🟢 RUN    12/5000     2/2      0       262 msg/hr
ADT_Router                    🟢 RUN     8/5000     2/2      0       260 msg/hr
RIS_Operation                 🟢 RUN    23/5000     2/2      1       180 msg/hr
ICE_Operation                 🟢 RUN    18/5000     2/2      0       180 msg/hr
Output_File_Writer            🟢 RUN     0/1000     1/1      0       260 msg/hr
Audit_File_Writer             🟢 RUN   102/50000    1/1      0       260 msg/hr
```

**Message Flow Visualization:**
```
[Cerner PAS] ──250 msg/hr──> [HL7_PAS_Service]
                                    │
                                    ├──250 msg/hr──> [Validation]
                                    │                      │
                                    │                      ├──240 msg/hr──> [ADT_Router]
                                    │                      │                      │
                                    │                      │                      ├──120 msg/hr──> [RIS]
                                    │                      │                      ├──120 msg/hr──> [ICE Lab]
                                    │                      │                      └──240 msg/hr──> [Audit]
                                    │                      │
                                    │                      └──10 msg/hr──> [Validation Failed]
```

**Alerts:**
```
⚠️  RIS_Operation: Auto-restarted 1 time (connection timeout)
ℹ️  Complex_Validation_Process: 10 messages rejected (invalid NHS Number)
✅  All critical items running normally
```

---

## Step 7: Test Message Flow (via Portal UI)

**Navigation:** Portal → Project → Testing → Send Test Message

### Test 1: ADT^A01 (Patient Admission)

**Input Message (HL7 v2.3):**
```
MSH|^~\&|PAS|STH|HIE|STH|20260210120000||ADT^A01|MSG0001|P|2.3
EVN|A01|20260210120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
```

**Click:** "Send Test Message" → Select "HL7_PAS_Service"

**Portal Shows Message Journey:**
```
1. ✅ Received by HL7_PAS_Service (100ms)
2. ✅ Validated by Complex_Validation_Process (250ms)
   - NHS Number valid: 9876543210
   - PDS lookup: VERIFIED
   - No duplicate found
   - Postcode valid: SW1A 1AA
3. ✅ Routed by ADT_Router (50ms)
   - Rule matched: ADT admission
   - Transformed to v2.4 → RIS_Operation
   - Transformed to v2.5.1 → ICE_Operation
   - Archived → Audit_File_Writer
4. ✅ Sent to RIS (120ms) - ACK received
5. ✅ Sent to ICE Lab (130ms) - ACK received
6. ✅ Written to audit file

Total Journey: 650ms
Status: ✅ SUCCESS
```

**View Message Trace:**
- Click message ID → Full audit trail with all transformations
- Download original message
- Download transformed messages (v2.4, v2.5.1)
- View ACKs from downstream systems

---

## Step 8: Hot Reload Configuration (No Downtime)

**Scenario:** Need to increase RIS operation pool size due to high load

**Navigation:** Portal → Items → RIS_Operation → Edit

**Change:**
```yaml
Pool Size: 2 → 4 (increase workers)
Queue Size: 5000 → 10000 (increase buffer)
```

**Click:** "Save & Reload"

**Portal Shows:**
```
🔄 Hot reloading RIS_Operation...
✅ Configuration updated (messages in queue preserved)
✅ New workers spawned (2 → 4)
✅ No messages lost
✅ No downtime

RIS_Operation Status: 🟢 RUNNING (4/4 workers active)
```

**Result:** Configuration changed **without stopping production**

---

## Step 9: Handle Failures (Auto-Restart Demonstration)

**Scenario:** RIS system becomes unavailable

**What Happens Automatically:**

```
Time    Event                               Engine Action
───────────────────────────────────────────────────────────────────
12:00   RIS_Operation: Connection failed    Queues messages (5000 buffer)
12:00   RIS_Operation: State → ERROR        Auto-restart policy: ALWAYS
12:00   Engine: Scheduling restart...       Delay: 10 seconds
12:00   RIS_Operation: Restart attempt 1    Connection failed
12:00   Engine: Scheduling restart...       Delay: 10 seconds
12:01   RIS_Operation: Restart attempt 2    Connection failed
12:01   Engine: Scheduling restart...       Delay: 10 seconds
...
12:15   RIS system: Back online
12:15   RIS_Operation: Restart attempt 15   ✅ Connection successful
12:15   RIS_Operation: State → RUNNING      Processing queued messages
12:16   RIS_Operation: Queue draining...    5000 → 4500 → 4000 → ...
12:20   RIS_Operation: Queue empty          Back to normal operation

Restart count: 15
Max restarts: 100 (still within limit)
Messages lost: 0 (all preserved in queue)
```

**Portal Alert:**
```
ℹ️  RIS_Operation auto-restarted 15 times
✅  Now running normally
📊  Queue drained in 4 minutes
```

**Result:** ✅ **Zero message loss**, **zero manual intervention**, **automatic recovery**

---

## Enterprise-Grade Features Demonstrated

### ✅ 100% Configuration-Driven
- **Zero code** written for entire integration
- All configuration via Portal UI
- Visual workflow designer
- Hot reload without downtime

### ✅ Production Orchestration
- Centralized management of all services
- Start/Stop entire production with one click
- Individual item control
- Health monitoring and alerting

### ✅ High Availability (Phase 2)
- **Auto-restart:** Services automatically recover from failures
- **Queue buffering:** Messages preserved during outages
- **Multi-process:** True parallel processing
- **Priority queues:** Critical messages processed first

### ✅ Performance & Scalability
- **Multiprocess execution:** Bypass Python GIL for CPU-bound tasks
- **Configurable workers:** Scale per service
- **Large queues:** Handle burst traffic (10,000+ messages)
- **Overflow strategies:** Prevent memory exhaustion

### ✅ Clinical Safety & Compliance
- **Message validation:** NHS Number, postcode, duplicates
- **Audit trail:** All messages archived (7 years retention)
- **Transformation verification:** HL7 version mapping
- **Error handling:** NACK generation, exception queues

### ✅ Real-Time Monitoring
- **Live dashboards:** Message flow visualization
- **Metrics:** Throughput, queue depth, worker utilization
- **Alerts:** Failures, restarts, threshold breaches
- **Message tracing:** Full journey audit trail

---

## Comparison with IRIS/Rhapsody/Mirth

| Feature | IRIS | Rhapsody | Mirth | **LI HIE** | Notes |
|---------|------|----------|-------|------------|-------|
| **Configuration** | Management Portal | IDE | Administrator | Portal UI | ✅ Equal |
| **Zero-code workflows** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Equal |
| **Visual workflow** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | Better than Mirth |
| **Hot reload** | ✅ Yes | ❌ No | ❌ No | ✅ Yes | **Better** |
| **Auto-restart** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Equal |
| **Multi-process** | ✅ Yes | ✅ Yes | ❌ Single JVM | ✅ Yes | Better than Mirth |
| **Priority queues** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | Better than Mirth |
| **Message transformation** | DTL | Mapper | JavaScript | DTL-style | ✅ Equal |
| **Rule engine** | BPL | Rules | JavaScript | Rules | ✅ Equal |
| **API-first** | ❌ Legacy | ❌ SOAP | ❌ Limited | ✅ REST API | **Better** |
| **Docker-native** | ❌ No | ❌ No | ⚠️ Partial | ✅ Yes | **Better** |
| **License cost** | $$$$$ | $$$$ | Free/$$$ | **Free** | **Better** |

**Verdict:** LI HIE matches or exceeds IRIS/Rhapsody/Mirth in key areas, with **modern architecture** and **zero licensing costs**.

---

## Next Steps

### For Developers
1. **Deploy demo:** Use this guide to configure the St. Thomas' demo
2. **Test end-to-end:** Send real HL7 messages through the workflow
3. **Customize:** Adapt for your trust's specific systems
4. **Extend:** Add custom validation logic if needed

### For Administrators
1. **Monitor production:** Use Portal dashboards
2. **Configure alerts:** Set thresholds for your environment
3. **Scale workers:** Adjust based on load
4. **Review audit trail:** Ensure compliance

### For Integration Team
1. **Document endpoints:** Map your actual systems (PAS, RIS, Lab, etc.)
2. **Test connectivity:** Verify MLLP/File access
3. **Define rules:** Business logic for your workflows
4. **Performance test:** Load test with realistic message volumes

---

## Conclusion

LI HIE is a **true enterprise integration engine** that matches the capabilities of InterSystems IRIS, Orion Rhapsody, and Mirth Connect - but with:

✅ **100% configuration-driven** (no coding for standard workflows)
✅ **Modern API-first architecture** (REST APIs, not legacy protocols)
✅ **Docker-native deployment** (containerized microservices)
✅ **Enterprise-grade features** (auto-restart, multi-process, priority queues)
✅ **Zero licensing costs** (open source)

**Everything is configured through the Portal UI** - creating, deploying, monitoring, and managing complete healthcare integrations without writing code.

This is **exactly how IRIS, Rhapsody, and Mirth work** - and HIE does it better.
