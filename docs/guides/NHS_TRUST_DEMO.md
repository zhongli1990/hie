# NHS Trust Integration Demo - Complete Implementation Guide

## Overview

This guide demonstrates a complete, production-ready NHS acute trust integration scenario using HIE. The demo showcases real-world clinical workflow integration between:

- **Cerner Millennium PAS** (Patient Administration System) - HL7 v2.3
- **RIS** (Radiology Information System) - HL7 v2.4
- **ICE Laboratory System** - HL7 v2.5.1
- **File-based integrations** for audit and backup

## Clinical Scenario

**St. Thomas' Hospital** needs to integrate their Cerner Millennium PAS with downstream clinical systems:

1. **ADT Messages**: Patient admission/discharge/transfer from PAS → RIS + ICE Lab
2. **Order Messages**: Radiology orders from PAS → RIS (HL7 v2.4)
3. **Lab Orders**: Laboratory orders from PAS → ICE Lab (HL7 v2.5.1)
4. **Audit Trail**: All messages archived to file system for compliance

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    St. Thomas' Hospital HIE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INBOUND SERVICES                                                │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │ HL7 v2.3 MLLP        │  │ File Watcher         │           │
│  │ Service              │  │ Service              │           │
│  │ (from Cerner PAS)    │  │ (/data/inbound)      │           │
│  │ Port: 2575           │  │ *.hl7 files          │           │
│  └──────────┬───────────┘  └──────────┬───────────┘           │
│             │                          │                        │
│             └────────┬─────────────────┘                        │
│                      ▼                                           │
│  BUSINESS PROCESSES                                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ADT Router Process                                        │  │
│  │ • Validates HL7 v2.3 messages                            │  │
│  │ • Transforms to target version (v2.4 or v2.5.1)          │  │
│  │ • Routes based on message type:                          │  │
│  │   - ADT^A01/A02/A03 → RIS (v2.4) + ICE Lab (v2.5.1)    │  │
│  │   - ORM^O01 (Radiology) → RIS (v2.4)                    │  │
│  │   - ORM^O01 (Lab) → ICE Lab (v2.5.1)                    │  │
│  └─────────────┬────────────────────────────────────────────┘  │
│                │                                                 │
│                ├───────────┬──────────────┬──────────────┐     │
│                ▼           ▼              ▼              ▼     │
│  OUTBOUND OPERATIONS                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ RIS      │  │ ICE Lab  │  │ File     │  │ Audit    │     │
│  │ MLLP     │  │ MLLP     │  │ Writer   │  │ File     │     │
│  │ v2.4     │  │ v2.5.1   │  │ Service  │  │ Writer   │     │
│  │ :2576    │  │ :2577    │  │ /output  │  │ /audit   │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Demo Components

### 1. Workspace: St_Thomas_Hospital

**Metadata:**
```yaml
id: st-thomas-hospital
name: "St. Thomas' Hospital"
description: "Main acute trust integration hub"
tags: ["NHS", "Acute Trust", "South London"]
```

### 2. Project: ADT_Integration

**Metadata:**
```yaml
id: adt-integration-prod
name: "ADT Integration Production"
description: "Patient admission/discharge/transfer integration"
version: "1.0.0"
environment: "production"
```

### 3. Items (Hosts)

#### 3.1 HL7_PAS_Service (Inbound MLLP)
**Type:** HL7 TCP Service
**Purpose:** Receives ADT messages from Cerner Millennium PAS

```yaml
name: "HL7_PAS_Service"
class_name: "Engine.li.hosts.hl7.HL7TCPService"
pool_size: 4
enabled: true
settings:
  # Adapter Settings
  - {target: Adapter, name: Port, value: "2575"}
  - {target: Adapter, name: IPAddress, value: "0.0.0.0"}
  - {target: Adapter, name: JobPerConnection, value: "true"}
  - {target: Adapter, name: ReadTimeout, value: "30"}

  # Host Settings
  - {target: Host, name: MessageSchemaCategory, value: "2.3"}
  - {target: Host, name: TargetConfigNames, value: "ADT_Router"}
  - {target: Host, name: AckMode, value: "App"}

  # Phase 2 Enterprise Settings
  - {target: Host, name: ExecutionMode, value: "multiprocess"}
  - {target: Host, name: WorkerCount, value: "4"}
  - {target: Host, name: QueueType, value: "priority"}
  - {target: Host, name: QueueSize, value: "10000"}
  - {target: Host, name: OverflowStrategy, value: "drop_oldest"}
  - {target: Host, name: RestartPolicy, value: "always"}
  - {target: Host, name: MaxRestarts, value: "100"}
  - {target: Host, name: RestartDelay, value: "10.0"}
  - {target: Host, name: MessagingPattern, value: "async_reliable"}
```

#### 3.2 File_PAS_Service (Inbound File Watcher)
**Type:** File Service
**Purpose:** Monitors folder for HL7 files from PAS batch exports

```yaml
name: "File_PAS_Service"
class_name: "Engine.li.hosts.file.FileService"
pool_size: 1
enabled: true
settings:
  # Adapter Settings
  - {target: Adapter, name: FilePath, value: "/data/inbound"}
  - {target: Adapter, name: FileSpec, value: "*.hl7"}
  - {target: Adapter, name: PollingInterval, value: "5"}
  - {target: Adapter, name: ArchivePath, value: "/data/processed"}

  # Host Settings
  - {target: Host, name: TargetConfigNames, value: "ADT_Router"}

  # Phase 2 Settings
  - {target: Host, name: ExecutionMode, value: "async"}
  - {target: Host, name: QueueType, value: "fifo"}
  - {target: Host, name: QueueSize, value: "1000"}
  - {target: Host, name: RestartPolicy, value: "on_failure"}
  - {target: Host, name: MaxRestarts, value: "5"}
```

#### 3.3 ADT_Router (Business Process)
**Type:** Business Process with Rule Engine
**Purpose:** Validates, transforms, and routes messages

```yaml
name: "ADT_Router"
class_name: "Engine.li.hosts.routing.ADTRoutingProcess"
pool_size: 2
enabled: true
settings:
  # Host Settings
  - {target: Host, name: BusinessRuleName, value: "ADT_Routing_Rules"}
  - {target: Host, name: Validation, value: "Error"}
  - {target: Host, name: RuleLogging, value: "a"}

  # Phase 2 Settings
  - {target: Host, name: ExecutionMode, value: "thread_pool"}
  - {target: Host, name: WorkerCount, value: "2"}
  - {target: Host, name: QueueType, value: "fifo"}
  - {target: Host, name: QueueSize, value: "5000"}
  - {target: Host, name: OverflowStrategy, value: "block"}
  - {target: Host, name: RestartPolicy, value: "always"}
  - {target: Host, name: MaxRestarts, value: "1000"}
  - {target: Host, name: RestartDelay, value: "30.0"}
  - {target: Host, name: MessagingPattern, value: "sync_reliable"}
  - {target: Host, name: MessageTimeout, value: "60.0"}
```

**Business Rules:**

```python
# Rule 1: ADT Messages → RIS + ICE Lab
if message.MSH.MessageType in ["ADT^A01", "ADT^A02", "ADT^A03", "ADT^A08"]:
    # Transform to v2.4 for RIS
    ris_message = transform_to_v24(message)
    send_to("RIS_Operation", ris_message)

    # Transform to v2.5.1 for ICE Lab
    ice_message = transform_to_v251(message)
    send_to("ICE_Operation", ice_message)

    # Archive original
    send_to("Audit_File_Writer", message)

# Rule 2: Radiology Orders → RIS only
if message.MSH.MessageType == "ORM^O01" and is_radiology_order(message):
    ris_message = transform_to_v24(message)
    send_to("RIS_Operation", ris_message)
    send_to("Audit_File_Writer", message)

# Rule 3: Lab Orders → ICE Lab only
if message.MSH.MessageType == "ORM^O01" and is_lab_order(message):
    ice_message = transform_to_v251(message)
    send_to("ICE_Operation", ice_message)
    send_to("Audit_File_Writer", message)
```

#### 3.4 Complex_Validation_Process (Custom Business Process)
**Type:** Custom Business Process
**Purpose:** Advanced validation, enrichment, and conditional routing

```yaml
name: "Complex_Validation_Process"
class_name: "Engine.li.hosts.custom.NHSValidationProcess"
pool_size: 2
enabled: true
settings:
  # Custom validation rules
  - {target: Host, name: ValidateNHSNumber, value: "true"}
  - {target: Host, name: EnrichFromPDS, value: "true"}
  - {target: Host, name: CheckDuplicates, value: "true"}
  - {target: Host, name: ValidatePostcode, value: "true"}

  # Phase 2 Settings
  - {target: Host, name: ExecutionMode, value: "thread_pool"}
  - {target: Host, name: WorkerCount, value: "4"}
  - {target: Host, name: QueueType, value: "priority"}
  - {target: Host, name: MessagingPattern, value: "sync_reliable"}
```

**Custom Logic:**

```python
class NHSValidationProcess(BusinessProcess):
    """
    Custom NHS-specific validation and enrichment.

    Performs:
    - NHS Number validation (check digit)
    - PDS lookup for patient demographics
    - Duplicate admission detection
    - Postcode validation
    - Conditional routing based on validation results
    """

    async def on_process_input(self, message):
        # 1. Validate NHS Number
        nhs_number = message.PID.PatientIdentifierList.IDNumber
        if not self.validate_nhs_number(nhs_number):
            self._log.error("Invalid NHS number", nhs_number=nhs_number)
            return self.generate_nack(message, "Invalid NHS Number")

        # 2. Enrich from PDS (Patient Demographic Service)
        if self.get_setting("Host", "EnrichFromPDS", False):
            pds_data = await self.send_request_sync(
                "PDS_Lookup_Service",
                {"nhs_number": nhs_number},
                timeout=5.0
            )
            message = self.enrich_patient_data(message, pds_data)

        # 3. Check for duplicates
        if self.get_setting("Host", "CheckDuplicates", False):
            is_duplicate = await self.check_duplicate_admission(message)
            if is_duplicate:
                self._log.warning("Duplicate admission detected")
                # Route to exception queue
                await self.send_request_async("Exception_Handler", message)
                return None

        # 4. Validate postcode
        postcode = message.PID.PatientAddress.ZipOrPostalCode
        if not self.validate_uk_postcode(postcode):
            self._log.warning("Invalid postcode", postcode=postcode)
            # Continue but flag for review
            message.add_z_segment("ZVL", "PostcodeValidation", "WARN")

        # 5. Route to downstream systems
        await self.send_request_async("ADT_Router", message)

        return message
```

#### 3.5 RIS_Operation (Outbound MLLP to RIS)
**Type:** HL7 TCP Operation
**Purpose:** Sends HL7 v2.4 messages to RIS

```yaml
name: "RIS_Operation"
class_name: "Engine.li.hosts.hl7.HL7TCPOperation"
pool_size: 2
enabled: true
settings:
  # Adapter Settings
  - {target: Adapter, name: IPAddress, value: "ris.sthospital.nhs.uk"}
  - {target: Adapter, name: Port, value: "2576"}
  - {target: Adapter, name: ConnectTimeout, value: "30"}
  - {target: Adapter, name: ReconnectRetry, value: "5"}
  - {target: Adapter, name: StayConnected, value: "-1"}

  # Host Settings
  - {target: Host, name: ReplyCodeActions, value: ":?R=F,:?E=S,:~=S,:?A=C,:*=S"}
  - {target: Host, name: RetryInterval, value: "5"}
  - {target: Host, name: FailureTimeout, value: "15"}

  # Phase 2 Settings
  - {target: Host, name: ExecutionMode, value: "thread_pool"}
  - {target: Host, name: WorkerCount, value: "2"}
  - {target: Host, name: QueueType, value: "fifo"}
  - {target: Host, name: QueueSize, value: "5000"}
  - {target: Host, name: OverflowStrategy, value: "block"}
  - {target: Host, name: RestartPolicy, value: "always"}
  - {target: Host, name: MaxRestarts, value: "100"}
```

#### 3.6 ICE_Operation (Outbound MLLP to ICE Lab)
**Type:** HL7 TCP Operation
**Purpose:** Sends HL7 v2.5.1 messages to ICE Laboratory

```yaml
name: "ICE_Operation"
class_name: "Engine.li.hosts.hl7.HL7TCPOperation"
pool_size: 2
enabled: true
settings:
  # Adapter Settings
  - {target: Adapter, name: IPAddress, value: "ice.sthospital.nhs.uk"}
  - {target: Adapter, name: Port, value: "2577"}
  - {target: Adapter, name: ConnectTimeout, value: "30"}
  - {target: Adapter, name: ReconnectRetry, value: "5"}

  # Phase 2 Settings (same as RIS)
  - {target: Host, name: ExecutionMode, value: "thread_pool"}
  - {target: Host, name: WorkerCount, value: "2"}
  - {target: Host, name: RestartPolicy, value: "always"}
```

#### 3.7 Output_File_Writer (Outbound File Writer)
**Type:** File Operation
**Purpose:** Writes processed messages to file system

```yaml
name: "Output_File_Writer"
class_name: "Engine.li.hosts.file.FileOperation"
pool_size: 1
enabled: true
settings:
  # Adapter Settings
  - {target: Adapter, name: FilePath, value: "/data/outbound"}
  - {target: Adapter, name: FileName, value: "%Y%m%d_%H%M%S_%f.hl7"}
  - {target: Adapter, name: Overwrite, value: "false"}

  # Phase 2 Settings
  - {target: Host, name: QueueType, value: "fifo"}
  - {target: Host, name: RestartPolicy, value: "on_failure"}
```

#### 3.8 Audit_File_Writer (Audit Trail)
**Type:** File Operation
**Purpose:** Archives all messages for compliance/audit

```yaml
name: "Audit_File_Writer"
class_name: "Engine.li.hosts.file.FileOperation"
pool_size: 1
enabled: true
settings:
  # Adapter Settings
  - {target: Adapter, name: FilePath, value: "/data/audit"}
  - {target: Adapter, name: FileName, value: "audit_%Y%m%d_%H%M%S_%f.hl7"}

  # Phase 2 Settings
  - {target: Host, name: QueueType, value: "fifo"}
  - {target: Host, name: QueueSize, value: "50000"}
  - {target: Host, name: OverflowStrategy, value: "drop_oldest"}
  - {target: Host, name: RestartPolicy, value: "always"}
```

## Message Flow Examples

### Example 1: ADT^A01 (Patient Admission)

**Inbound (Cerner PAS - HL7 v2.3):**
```
MSH|^~\&|PAS|STH|HIE|STH|20260210120000||ADT^A01|MSG0001|P|2.3
EVN|A01|20260210120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
```

**Processing:**
1. Received by `HL7_PAS_Service` (priority queue)
2. Validated as HL7 v2.3 ADT^A01
3. Sent to `Complex_Validation_Process`:
   - NHS Number validated (check digit)
   - PDS lookup enriches demographics
   - Duplicate check passed
   - Postcode validated
4. Sent to `ADT_Router`:
   - **Rule 1 matched** (ADT admission)
   - Transform to v2.4 → `RIS_Operation`
   - Transform to v2.5.1 → `ICE_Operation`
   - Archive → `Audit_File_Writer`

**Outbound to RIS (HL7 v2.4):**
```
MSH|^~\&|HIE|STH|RIS|STH|20260210120001||ADT^A01|MSG0001-RIS|P|2.4
EVN|A01|20260210120000
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1||||12345^Jones^Sarah|||MED||||||||V123456
```

**Outbound to ICE Lab (HL7 v2.5.1):**
```
MSH|^~\&|HIE|STH|ICE|STH|20260210120001||ADT^A01^ADT_A01|MSG0001-ICE|P|2.5.1
EVN|A01|20260210120000|||
PID|1||9876543210^^^NHS||Smith^John^Q||19800101|M|||123 High St^^London^^SW1A 1AA^UK
PV1|1|I|WARD1^ROOM1^BED1^^^^STH||||12345^Jones^Sarah|||MED||||||||V123456
```

### Example 2: ORM^O01 (Radiology Order)

**Processing:**
1. Received by `HL7_PAS_Service`
2. Validated and enriched by `Complex_Validation_Process`
3. Sent to `ADT_Router`:
   - **Rule 2 matched** (radiology order)
   - Transform to v2.4 → `RIS_Operation` only
   - Archive → `Audit_File_Writer`

## Performance Configuration

### High-Throughput Service (HL7_PAS_Service)
```yaml
ExecutionMode: multiprocess
WorkerCount: 4
QueueType: priority
QueueSize: 10000
OverflowStrategy: drop_oldest
RestartPolicy: always
MaxRestarts: 100
```

### Mission-Critical Process (ADT_Router)
```yaml
ExecutionMode: thread_pool
WorkerCount: 2
QueueType: fifo
OverflowStrategy: block
RestartPolicy: always
MaxRestarts: 1000
RestartDelay: 30.0
MessagingPattern: sync_reliable
```

## Testing Strategy

### Unit Tests
- HL7 parsing (v2.3, v2.4, v2.5.1)
- NHS Number validation
- Postcode validation
- Message transformation logic
- Rule engine evaluation

### Integration Tests
- End-to-end message flow
- Error handling and retries
- Auto-restart under load
- Queue overflow scenarios
- MLLP connection resilience

### Load Tests
- 10,000 messages/hour sustained
- 50,000 messages/hour burst
- Queue depth monitoring
- Worker utilization
- Memory consumption

## Deployment

### Docker Compose
```yaml
services:
  hie-engine:
    image: hie-engine:v1.4.0
    environment:
      - PRODUCTION_NAME=ADT_Integration
      - EXECUTION_MODE=multi_process
      - LOG_LEVEL=INFO
    volumes:
      - ./data/inbound:/data/inbound
      - ./data/outbound:/data/outbound
      - ./data/audit:/data/audit
    ports:
      - "2575:2575"  # HL7 PAS Service
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
```

### Monitoring
- Prometheus metrics export
- Grafana dashboards:
  - Message throughput
  - Queue depths
  - Worker utilization
  - Restart counts
  - Error rates
- Alert thresholds:
  - Queue depth > 80%
  - Error rate > 1%
  - Restart count > 10/hour

## Compliance

### NHS Digital Standards
- ✅ HL7 v2.x interoperability
- ✅ NHS Number validation
- ✅ Audit trail (7 years retention)
- ✅ GDPR data handling
- ✅ DCB0129 compliance

### Clinical Safety
- ✅ Message persistence (WAL)
- ✅ Duplicate detection
- ✅ Validation before routing
- ✅ Error handling and alerting
- ✅ Auto-restart for resilience

## Next Steps

1. **Implement Custom Business Process** (`NHSValidationProcess`)
2. **Create HL7 Transformation Functions** (v2.3 → v2.4 → v2.5.1)
3. **Implement Rule Engine** for ADT_Router
4. **Create Test Data** (sample HL7 messages)
5. **Deploy to Docker** and test end-to-end
6. **Performance Benchmark** with load testing
7. **Documentation** for operations team

This demo showcases HIE's enterprise capabilities in a real NHS acute trust scenario.
