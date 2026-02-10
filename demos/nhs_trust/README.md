# NHS Acute Trust Integration Demo

**Complete Healthcare Integration Engine deployment for NHS acute trusts.**

This demo showcases a production-ready HIE deployment for a typical NHS acute trust, demonstrating:
- HL7 v2.3 message processing (PAS, A&E, Outpatients)
- NHS-specific validation (NHS numbers, postcodes, dates)
- Multi-system routing and transformation
- Enterprise execution modes (multiprocess, thread pools, priority queues)
- Hot reload configuration management
- Production monitoring and metrics

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Portal UI Walkthrough](#portal-ui-walkthrough)
4. [Deployment Guide](#deployment-guide)
5. [Testing the Demo](#testing-the-demo)
6. [Configuration Deep Dive](#configuration-deep-dive)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NHS ACUTE TRUST                               │
│                                                                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐         │
│  │  Cerner  │   │ TrakCare │   │   SCI    │   │ TeleForm │         │
│  │   PAS    │   │   A&E    │   │ Gateway  │   │   EDMS   │         │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘         │
│       │              │              │              │                │
│       │ HL7/TCP      │ HL7/TCP      │ HL7/File     │ HL7/File      │
│       │              │              │              │                │
└───────┼──────────────┼──────────────┼──────────────┼────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      HIE INTEGRATION ENGINE                          │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                 INBOUND SERVICES (Receivers)                   │  │
│  │                                                                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐ │  │
│  │  │Cerner_PAS  │  │TrakCare_AE │  │SCI_Gateway │  │TeleForm │ │  │
│  │  │ Receiver   │  │  Receiver  │  │  Receiver  │  │Receiver │ │  │
│  │  │            │  │            │  │            │  │         │ │  │
│  │  │ TCP:2575   │  │ TCP:2576   │  │ File:      │  │File:    │ │  │
│  │  │ 4 workers  │  │ 4 workers  │  │ /inbound/  │  │/edms/   │ │  │
│  │  │ Multiproc  │  │ Multiproc  │  │ 2 workers  │  │1 worker │ │  │
│  │  │ Priority Q │  │ Priority Q │  │ Thread     │  │Thread   │ │  │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────┬────┘ │  │
│  └────────┼────────────────┼────────────────┼──────────────┼──────┘  │
│           │                │                │              │         │
│           └────────────────┴────────────────┴──────────────┘         │
│                              │                                        │
│  ┌───────────────────────────▼──────────────────────────────────┐   │
│  │              NHS VALIDATION & ROUTING PROCESS                 │   │
│  │                                                                │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ NHS_Validation_Router                                 │    │   │
│  │  │                                                        │    │   │
│  │  │  • Validate NHS numbers (Modulus 11 checksum)        │    │   │
│  │  │  • Validate UK postcodes (format + existence)        │    │   │
│  │  │  • Validate dates (format + reasonableness)          │    │   │
│  │  │  • Route by message type (ADT, ORU, ORM)             │    │   │
│  │  │  • Route by facility (Royal Hospital, City Clinic)   │    │   │
│  │  │  • Priority-based processing (urgent vs routine)     │    │   │
│  │  │                                                        │    │   │
│  │  │  4 workers | Multiprocess | Priority Queue           │    │   │
│  │  └──────────────────────┬─────────────────────────────┬─┘    │   │
│  └─────────────────────────┼─────────────────────────────┼──────┘   │
│                            │                             │          │
│                     Valid  │                    Invalid  │          │
│  ┌─────────────────────────▼─────────┐   ┌──────────────▼────────┐ │
│  │   OUTBOUND OPERATIONS (Senders)   │   │  ERROR HANDLING       │ │
│  │                                    │   │                       │ │
│  │  ┌────────────┐  ┌──────────────┐ │   │  ┌─────────────────┐ │ │
│  │  │   EPR      │  │  NHS Spine   │ │   │  │  DLQ / Alerts   │ │ │
│  │  │  Sender    │  │   Sender     │ │   │  │                 │ │ │
│  │  │            │  │              │ │   │  │  Dead Letter Q  │ │ │
│  │  │ TCP:3575   │  │ HTTPS        │ │   │  │  Email Alerts   │ │ │
│  │  │ 4 workers  │  │ 2 workers    │ │   │  │  SMS Alerts     │ │ │
│  │  │ Multiproc  │  │ Thread       │ │   │  └─────────────────┘ │ │
│  │  │ Async Rel  │  │ Sync Rel     │ │   └───────────────────────┘ │
│  │  └────────────┘  └──────────────┘ │                             │
│  └────────────────────────────────────┘                             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
          │                        │
          ▼                        ▼
    ┌─────────┐            ┌──────────────┐
    │   EPR   │            │  NHS Spine   │
    │ System  │            │ (PDS/SCR)    │
    └─────────┘            └──────────────┘
```

**Key Features:**
- **8 configurable items** (4 services, 1 process, 3 operations)
- **Phase 2 enterprise execution**: Multiprocess, thread pools, priority queues
- **Phase 3 configuration management**: Hot reload, auto-restart policies
- **NHS-specific validation**: NHS numbers, postcodes, date validation
- **10,000-50,000 messages/sec capacity** (single-node)

---

## System Components

### 1. Inbound Services (Receivers)

| Service | Protocol | Port/Path | Workers | Execution | Queue | Purpose |
|---------|----------|-----------|---------|-----------|-------|---------|
| **Cerner_PAS_Receiver** | HL7/TCP | 2575 | 4 | Multiprocess | Priority | Receive ADT messages from Cerner PAS |
| **TrakCare_AE_Receiver** | HL7/TCP | 2576 | 4 | Multiprocess | Priority | Receive ADT/ORU from TrakCare A&E |
| **SCI_Gateway_Receiver** | HL7/File | /inbound/sci | 2 | Thread Pool | FIFO | Poll SCI Gateway directory |
| **TeleForm_EDMS_Receiver** | HL7/File | /inbound/edms | 1 | Thread Pool | FIFO | Poll TeleForm EDMS directory |

**Configuration Highlights:**
- **Auto-restart policy**: `always` (unlimited restarts, 10s delay)
- **Messaging pattern**: `async_reliable` (fire-and-forget with confirmation)
- **Queue size**: 10,000 messages per service
- **Priority levels**: 0-9 (0=highest, 9=lowest)

### 2. Business Process (Validation & Routing)

**NHS_Validation_Router**
- **Type**: Business Process (routing engine)
- **Workers**: 4 (multiprocess)
- **Queue**: Priority (10,000 capacity)
- **Execution**: Multiprocess
- **Restart**: On failure (max 100 restarts, 10s delay)

**Validation Rules:**
1. **NHS Number Validation** (Modulus 11 checksum)
   - Format: 10 digits (e.g., 9434765870)
   - Checksum: `(11 - ((Σ(digit[i] × weight[i])) % 11)) % 11`
   - Invalid example: 9434765999 ✗

2. **UK Postcode Validation**
   - Format: AA9A 9AA, A9A 9AA, A9 9AA, A99 9AA, AA9 9AA, AA99 9AA
   - Existence check against ONS Postcode Directory
   - Invalid example: "INVALID_POSTCODE" ✗

3. **Date Validation**
   - Format: YYYYMMDD
   - Reasonableness: 1900-01-01 to today + 1 year
   - Invalid example: Birth date in future ✗

**Routing Logic:**
- **By Message Type**: ADT_A01/A03/A08 → EPR, ORU → Lab System
- **By Facility**: Royal Hospital → EPR, City Clinic → Local EPR
- **By Priority**: Urgent (0-3) → Fast lane, Routine (4-9) → Normal
- **Error Routing**: Validation failures → DLQ + Alerts

### 3. Outbound Operations (Senders)

| Operation | Protocol | Endpoint | Workers | Execution | Pattern | Purpose |
|-----------|----------|----------|---------|-----------|---------|---------|
| **EPR_Sender** | HL7/TCP | 10.20.30.40:3575 | 4 | Multiprocess | Async Reliable | Send validated ADT to EPR |
| **NHS_Spine_Sender** | HTTPS | spine.nhs.uk | 2 | Thread Pool | Sync Reliable | Send to NHS Spine (PDS/SCR) |
| **DLQ_Alert_Operation** | Email/SMS | alert@nhs.uk | 1 | Thread Pool | Async | Send validation failure alerts |

---

## Portal UI Walkthrough

### Step 1: Create Workspace

Navigate to: **Admin → Workspaces → Create Workspace**

```
Workspace Name:       NHS Royal Hospital Trust
Workspace Type:       NHS Acute Trust
Description:          Production integration for Royal Hospital NHS Trust
Environment:          Production
```

Click **Create** → Workspace ID generated (e.g., `ws_nhs_royal_2026`)

---

### Step 2: Create Project

Navigate to: **Workspace → Projects → Create Project**

```
Project Name:         Royal Hospital ADT Integration
Project Type:         HL7 v2.x Integration
Description:          ADT message routing for PAS, A&E, and ancillary systems
Version:              1.0.0
```

Click **Create** → Project ID generated (e.g., `proj_royal_adt_001`)

---

### Step 3: Add Inbound Service (Cerner PAS Receiver)

Navigate to: **Project → Items → Add Item**

**Basic Configuration:**
```
Item Name:            Cerner_PAS_Receiver
Display Name:         Cerner PAS Receiver (ADT Messages)
Item Type:            SERVICE
Class Name:           Engine.li.hosts.hl7.HL7TCPService
Enabled:              ✓ Yes
Pool Size:            4
```

**Adapter Settings (Target: Adapter):**
```
Host:                 0.0.0.0
Port:                 2575
Protocol:             HL7v2_MLLP
Encoding:             UTF-8
```

**Host Settings (Target: Host):**
```
ExecutionMode:        multiprocess
WorkerCount:          4
QueueType:            priority
QueueSize:            10000
RestartPolicy:        always
MaxRestarts:          -1 (unlimited)
RestartDelay:         10.0
MessagingPattern:     async_reliable
TargetConfigNames:    NHS_Validation_Router
MessageSchemaCategory: HL7v23_ADT
```

**Explanation:**
- **multiprocess**: Each worker runs in a separate OS process (bypasses Python GIL)
- **priority queue**: Messages with priority 0-3 processed before 4-9
- **always restart**: Auto-restart on any failure (critical service)
- **async_reliable**: Fire-and-forget with confirmation (high throughput)

Click **Create Item** → Service created

---

### Step 4: Add Business Process (NHS Validation Router)

Navigate to: **Project → Items → Add Item**

**Basic Configuration:**
```
Item Name:            NHS_Validation_Router
Display Name:         NHS Validation & Routing Process
Item Type:            PROCESS
Class Name:           Engine.li.hosts.routing.RoutingEngine
Enabled:              ✓ Yes
Pool Size:            4
```

**Host Settings:**
```
ExecutionMode:        multiprocess
WorkerCount:          4
QueueType:            priority
QueueSize:            10000
RestartPolicy:        on_failure
MaxRestarts:          100
RestartDelay:         10.0
MessagingPattern:     async_reliable
```

**Routing Rules (JSON):**
```json
{
  "rules": [
    {
      "name": "NHS Number Validation",
      "condition": "message.pid.patient_id.id_number",
      "action": "validate_nhs_number",
      "on_failure": "route_to_dlq"
    },
    {
      "name": "Postcode Validation",
      "condition": "message.pid.patient_address.postal_code",
      "action": "validate_uk_postcode",
      "on_failure": "route_to_dlq"
    },
    {
      "name": "Route ADT to EPR",
      "condition": "message.msh.message_type == 'ADT'",
      "action": "route_to",
      "target": "EPR_Sender"
    },
    {
      "name": "Route to NHS Spine",
      "condition": "message.msh.sending_facility == 'ROYAL_HOSPITAL'",
      "action": "route_to",
      "target": "NHS_Spine_Sender"
    }
  ]
}
```

Click **Create Item** → Process created

---

### Step 5: Add Outbound Operation (EPR Sender)

Navigate to: **Project → Items → Add Item**

**Basic Configuration:**
```
Item Name:            EPR_Sender
Display Name:         EPR System Sender (Validated ADT)
Item Type:            OPERATION
Class Name:           Engine.li.hosts.hl7.HL7TCPOperation
Enabled:              ✓ Yes
Pool Size:            4
```

**Adapter Settings:**
```
Host:                 10.20.30.40
Port:                 3575
Protocol:             HL7v2_MLLP
Encoding:             UTF-8
ConnectionTimeout:    30.0
RetryCount:           3
RetryDelay:           5.0
```

**Host Settings:**
```
ExecutionMode:        multiprocess
WorkerCount:          4
QueueType:            priority
QueueSize:            5000
RestartPolicy:        on_failure
MaxRestarts:          50
RestartDelay:         10.0
MessagingPattern:     async_reliable
```

Click **Create Item** → Operation created

---

### Step 6: Deploy Production

Navigate to: **Project → Deploy → Production Deployment**

**Review Configuration:**
- Items: 8 (4 services, 1 process, 3 operations)
- Total workers: 26 (across all items)
- Expected throughput: 10,000-50,000 msg/sec
- Memory estimate: ~4GB (multiprocess overhead)

Click **Deploy** → Production starts

**Deployment Steps (Automatic):**
1. Create production in Manager API
2. Create project in Manager API
3. Create all 8 items sequentially
4. Start items in dependency order:
   - Operations first (EPR_Sender, NHS_Spine_Sender, DLQ)
   - Processes second (NHS_Validation_Router)
   - Services last (Cerner, TrakCare, SCI, TeleForm receivers)

**Deployment Time**: ~30 seconds

---

### Step 7: Monitor Production

Navigate to: **Dashboard → Production Status**

**Health Checks (http://localhost:9302/health):**
```json
{
  "status": "healthy",
  "checks": {
    "host:Cerner_PAS_Receiver": "healthy",
    "host:TrakCare_AE_Receiver": "healthy",
    "host:SCI_Gateway_Receiver": "healthy",
    "host:TeleForm_EDMS_Receiver": "healthy",
    "host:NHS_Validation_Router": "healthy",
    "host:EPR_Sender": "healthy",
    "host:NHS_Spine_Sender": "healthy",
    "host:DLQ_Alert_Operation": "healthy"
  }
}
```

**Metrics (http://localhost:9303/metrics):**
```
# Production metrics
hie_host_status{host="Cerner_PAS_Receiver",type="BusinessService",running="true"} 1
hie_host_messages_received{host="Cerner_PAS_Receiver"} 1523
hie_host_messages_processed{host="NHS_Validation_Router"} 1523
hie_host_messages_sent{host="EPR_Sender"} 1498
hie_host_messages_failed{host="NHS_Validation_Router"} 25

# Queue metrics
hie_host_queue_size{host="Cerner_PAS_Receiver"} 0
hie_host_queue_size{host="NHS_Validation_Router"} 5

# Processing time metrics
hie_host_avg_processing_time_ms{host="NHS_Validation_Router"} 2.3
```

---

## Deployment Guide

### Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ (for local development)
- 8GB RAM minimum (16GB recommended for production)
- Ports available: 2575, 2576, 3575, 9300, 9302, 9303

### Quick Start (Docker)

```bash
# 1. Navigate to demo directory
cd demos/nhs_trust

# 2. Start all services
docker-compose up -d

# 3. Wait for services to start (~30s)
docker-compose ps

# 4. Deploy production
python scripts/deploy_production.py

# 5. Check health
curl http://localhost:9302/health

# 6. Send test message
cat test_data/adt_a01_admission.hl7 | nc localhost 2575
```

### Manual Deployment (Without Docker)

```bash
# 1. Install HIE Engine
cd ../../
pip install -e ".[dev]"

# 2. Start Manager API
python -c "import asyncio; from Engine.api.server import run_server; asyncio.run(run_server())" &

# 3. Deploy production
cd demos/nhs_trust
python scripts/deploy_production.py
```

---

## Testing the Demo

### Test Case 1: Valid ADT A01 (Admission)

**Send Message:**
```bash
cat test_data/adt_a01_admission.hl7 | nc localhost 2575
```

**Expected Flow:**
1. Cerner_PAS_Receiver receives message on TCP:2575
2. NHS_Validation_Router validates:
   - ✓ NHS number: 9434765870 (valid checksum)
   - ✓ Postcode: LS1 1AB (valid UK postcode)
   - ✓ Birth date: 19850515 (reasonable)
3. Routes to EPR_Sender
4. EPR_Sender sends to EPR system (10.20.30.40:3575)
5. Routes to NHS_Spine_Sender (Royal Hospital facility)
6. NHS_Spine_Sender sends to NHS Spine (async)

**Check Metrics:**
```bash
curl http://localhost:9303/metrics | grep messages_received
curl http://localhost:9303/metrics | grep messages_processed
```

### Test Case 2: Invalid NHS Number

**Send Message:**
```bash
cat test_data/adt_a01_invalid_nhs_number.hl7 | nc localhost 2575
```

**Expected Flow:**
1. Cerner_PAS_Receiver receives message
2. NHS_Validation_Router validates:
   - ✗ NHS number: 9434765999 (invalid checksum)
3. **Routes to DLQ** (Dead Letter Queue)
4. DLQ_Alert_Operation sends email alert
5. Metrics: `hie_host_messages_failed` increments

**Check Logs:**
```bash
docker-compose logs -f hie-engine | grep validation_failed
```

### Test Case 3: Invalid Postcode

**Send Message:**
```bash
cat test_data/adt_a01_invalid_postcode.hl7 | nc localhost 2575
```

**Expected Flow:**
1. Cerner_PAS_Receiver receives message
2. NHS_Validation_Router validates:
   - ✓ NHS number valid
   - ✗ Postcode: "INVALID_POSTCODE" (not a valid UK postcode format)
3. **Routes to DLQ**
4. Alert sent

### Test Case 4: High-Priority Message

**Modify Message:**
```hl7
MSH|^~\&|CERNER|ROYAL_HOSPITAL|HIE|NHS_TRUST|...|PRIORITY^URGENT|MSG00001|P|2.3
```

**Expected Behavior:**
- Priority=URGENT → mapped to priority=1 (highest)
- Priority queue processes this message before routine messages
- Faster processing (< 1ms latency)

### Test Case 5: Load Test (10,000 messages)

```bash
# Generate 10,000 test messages
for i in {1..10000}; do
  cat test_data/adt_a01_admission.hl7 | nc localhost 2575
done

# Monitor throughput
watch -n 1 'curl -s http://localhost:9303/metrics | grep messages_processed'
```

**Expected Throughput:**
- **Single-node**: 10,000-50,000 msg/sec
- **Multiprocess (4 workers per service)**: ~40,000 msg/sec sustained
- **Latency**: < 5ms average (priority messages < 1ms)

---

## Configuration Deep Dive

### ExecutionMode Options

| Mode | When to Use | GIL Bypass | Overhead | Max Throughput |
|------|-------------|------------|----------|----------------|
| **multiprocess** | CPU-intensive, high throughput | ✓ Yes | High (separate processes) | 50,000+ msg/sec |
| **thread_pool** | I/O-bound, blocking calls | ✗ No | Low (shared memory) | 10,000 msg/sec |
| **async** | Pure async I/O | ✗ No | Very low | 5,000 msg/sec |

**Best Practice:**
- Services/Operations with high volume → **multiprocess**
- File polling, database queries → **thread_pool**
- Lightweight routing → **async**

### QueueType Options

| Type | Order | Use Case |
|------|-------|----------|
| **priority** | Priority (0-9) | Critical messages need fast lane |
| **fifo** | First-In-First-Out | Strict ordering required |
| **lifo** | Last-In-First-Out | Stack-based processing |
| **unordered** | Fastest available | Order doesn't matter |

### RestartPolicy Options

| Policy | Behavior | Use Case |
|--------|----------|----------|
| **never** | Don't restart | Development/testing |
| **always** | Always restart | Critical services (inbound) |
| **on_failure** | Restart only on failure | Most services/operations |

### MessagingPattern Options

| Pattern | Blocking | Confirmation | Use Case |
|---------|----------|--------------|----------|
| **async_reliable** | No | Yes (via WAL) | High-throughput (default) |
| **sync_reliable** | Yes | Yes (reply) | Request/reply (NHS Spine) |
| **concurrent_async** | No | No | Fire-and-forget |
| **concurrent_sync** | Yes | Yes (multiple) | Parallel requests |

---

## Troubleshooting

### Issue: Service won't start

**Symptom:**
```
host_start_failed: Cerner_PAS_Receiver: Address already in use
```

**Solution:**
```bash
# Check if port is in use
lsof -i:2575

# Kill process or change port in config
```

### Issue: Messages not being processed

**Symptom:**
```
hie_host_queue_size{host="Cerner_PAS_Receiver"} 10000
hie_host_messages_processed{host="NHS_Validation_Router"} 0
```

**Solution:**
```bash
# Check if router is running
curl http://localhost:9302/health | jq '.checks."host:NHS_Validation_Router"'

# Check logs
docker-compose logs -f hie-engine | grep NHS_Validation_Router

# Restart if needed
curl -X POST http://localhost:9300/api/productions/{prod_id}/items/NHS_Validation_Router/restart
```

### Issue: High latency (> 100ms)

**Symptoms:**
```
hie_host_avg_processing_time_ms{host="NHS_Validation_Router"} 150.5
```

**Solutions:**
1. **Increase workers**: `pool_size: 4` → `pool_size: 8`
2. **Upgrade to multiprocess**: `ExecutionMode: thread_pool` → `ExecutionMode: multiprocess`
3. **Optimize queue type**: `QueueType: fifo` → `QueueType: priority`
4. **Check resource limits**: CPU/memory saturation

### Issue: Validation failures increasing

**Symptom:**
```
hie_host_messages_failed{host="NHS_Validation_Router"} 250 (10% failure rate)
```

**Investigation:**
```bash
# Check DLQ for error patterns
curl http://localhost:9300/api/productions/{prod_id}/dlq | jq '.messages[].error'

# Common errors:
# - Invalid NHS numbers from source system
# - Missing required fields (PID-3)
# - Incorrect postcode formats
```

**Solution:**
1. Contact source system team to fix data quality
2. Add preprocessing/normalization step
3. Adjust validation rules (if appropriate)

---

## Next Steps

### Phase 5 Enhancements (Q1-Q2 2027)

1. **NHS Spine Integration**
   - PDS (Patient Demographics Service) lookups
   - SCR (Summary Care Record) updates
   - EPS (Electronic Prescription Service) submissions
   - MESH (Message Exchange for Social Care and Health) secure file transfer

2. **FHIR R4 Support**
   - HL7 v2 → FHIR transformation
   - FHIR REST API endpoints
   - FHIR validation (profiles)

3. **Advanced Features**
   - Distributed tracing (Jaeger)
   - Circuit breakers (prevent cascade failures)
   - Rate limiting (protect downstream systems)

### Phase 6 Scale-Out (Q3-Q4 2027)

1. **Kafka Sharding** (1M+ msg/sec)
2. **Multi-Region Deployment** (DR)
3. **ML-Based Routing** (intelligent routing)

---

## Support & Resources

- **Documentation**: `/docs/`
- **API Reference**: `http://localhost:9300/docs` (Swagger UI)
- **Health Checks**: `http://localhost:9302/health`
- **Metrics**: `http://localhost:9303/metrics` (Prometheus)
- **GitHub**: https://github.com/your-org/hie
- **Email**: hie-support@nhs.uk

---

**Version**: 1.0.0
**Last Updated**: February 10, 2026
**Maintainer**: HIE Core Team
