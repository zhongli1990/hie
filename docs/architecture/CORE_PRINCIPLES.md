# LI HIE Core Principles & Architecture Understanding

## What LI HIE Is

**LI HIE is a fully configurable, enterprise-grade healthcare integration engine** - NOT a Python framework or library.

### Architectural Classification

```
LI HIE = InterSystems IRIS + Orion Rhapsody + Mirth Connect
```

| Product | Type | Configuration Method |
|---------|------|---------------------|
| **InterSystems IRIS** | Integration Engine | Management Portal (Web UI) |
| **Orion Rhapsody** | Integration Engine | Rhapsody IDE (Desktop UI) |
| **Mirth Connect** | Integration Engine | Administrator Console (Web UI) |
| **LI HIE** | Integration Engine | **Portal UI (Web) + Manager API (REST)** |

## Core Principle: 100% Configuration-Driven

### ✅ What Users Do

**Administrators/Integration Developers:**
1. Log into **Portal UI** (web-based)
2. Create **Workspaces** (organizational units)
3. Create **Projects** (productions/integrations)
4. Add **Items** (services, processes, operations)
5. Configure **Connections** (message routing)
6. Click **"Deploy & Start"** (one button)
7. **Monitor** real-time (dashboards, metrics)

**Zero Python Code Required** for standard healthcare integrations.

### ❌ What Users Don't Do

Users **DO NOT**:
- ❌ Write Python code for each integration
- ❌ Deploy services manually
- ❌ Program message flows
- ❌ Write transformation logic (use visual mapper)
- ❌ Code routing rules (use visual rule builder)
- ❌ Manage Docker containers directly
- ❌ Configure worker processes manually

## Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TIER 1: Portal UI                        │
│  (User Interface - Web-based Configuration)                  │
│                                                               │
│  • Workspace management                                      │
│  • Project creation                                          │
│  • Item configuration (forms)                                │
│  • Visual workflow designer                                  │
│  • Rule builder                                              │
│  • Transformation mapper                                     │
│  • Real-time monitoring                                      │
│  • Dashboard & metrics                                       │
│                                                               │
│  User Experience: Like IRIS Management Portal                │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   TIER 2: Manager API                        │
│  (Orchestration Layer - Configuration Management)            │
│                                                               │
│  • Workspace CRUD (workspaces table)                         │
│  • Project CRUD (projects table)                             │
│  • Item CRUD (items table)                                   │
│  • Connection CRUD (connections table)                       │
│  • Production deployment                                     │
│  • Item lifecycle (start/stop/reload)                        │
│  • Metrics collection                                        │
│  • Health monitoring                                         │
│                                                               │
│  Technology: aiohttp REST API + PostgreSQL                   │
└───────────────────────────┬─────────────────────────────────┘
                            │ Configuration → Engine
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    TIER 3: Engine                            │
│  (Runtime Execution - Production Orchestrator)               │
│                                                               │
│  ProductionEngine:                                           │
│  ├─ ServiceRegistry (service lookup & routing)              │
│  ├─ Health Monitoring (_monitor_hosts background task)      │
│  ├─ Auto-Restart (restart failed hosts)                     │
│  └─ Lifecycle Management (start/stop all items)             │
│                                                               │
│  Items (Hosts) - Configured Instances:                       │
│  ├─ HL7TCPService (MLLP listener)                           │
│  ├─ FileService (directory watcher)                         │
│  ├─ BusinessProcess (rule engine)                           │
│  ├─ HL7TCPOperation (MLLP sender)                           │
│  └─ FileOperation (file writer)                             │
│                                                               │
│  Each Item:                                                  │
│  • Runs as independent service (1+ processes/threads)       │
│  • Has message queue (FIFO/Priority/LIFO/Unordered)         │
│  • Communicates via ServiceRegistry                         │
│  • Auto-restarts on failure (configurable)                  │
│  • Reports metrics to Manager                               │
│                                                               │
│  Technology: Python asyncio + multiprocessing                │
└─────────────────────────────────────────────────────────────┘
```

## Configuration-to-Runtime Flow

### 1. User Creates Item in Portal UI

**Portal UI Form:**
```yaml
Item Type: HL7 TCP Service
Name: HL7_PAS_Service
Display Name: Cerner PAS Receiver
Port: 2575
IP Address: 0.0.0.0
Execution Mode: Multiprocess
Worker Count: 4
Queue Type: Priority
Queue Size: 10000
Restart Policy: Always
```

**Click "Save"** → Portal sends to Manager API

### 2. Manager API Stores Configuration

**REST API Call:**
```http
POST /api/projects/{project_id}/items
Content-Type: application/json

{
  "name": "HL7_PAS_Service",
  "class_name": "Engine.li.hosts.hl7.HL7TCPService",
  "pool_size": 4,
  "adapter_settings": {
    "Port": 2575,
    "IPAddress": "0.0.0.0"
  },
  "host_settings": {
    "ExecutionMode": "multiprocess",
    "WorkerCount": 4,
    "QueueType": "priority",
    "QueueSize": 10000,
    "RestartPolicy": "always"
  }
}
```

**Manager API Action:**
```python
# Store in PostgreSQL
await item_repo.create(
    project_id=proj_uuid,
    name="HL7_PAS_Service",
    class_name="Engine.li.hosts.hl7.HL7TCPService",
    pool_size=4,
    adapter_settings=adapter_settings,
    host_settings=host_settings,
)
```

### 3. User Clicks "Deploy & Start"

**Manager API Call:**
```http
POST /api/projects/{project_id}/deploy
POST /api/projects/{project_id}/start
```

**Engine Instantiation:**
```python
# Manager loads configuration from database
items = await item_repo.list_by_project(project_id)

# Create ProductionEngine
engine = ProductionEngine(config)

# For each item, instantiate Host
for item_config in items:
    # Dynamically instantiate class
    HostClass = import_class(item_config.class_name)

    # Create host instance with configuration
    host = HostClass(
        name=item_config.name,
        pool_size=item_config.pool_size,
        adapter_settings=item_config.adapter_settings,
        host_settings=item_config.host_settings,
    )

    # Register with production
    engine.register_host(host, item_config)

    # Register with ServiceRegistry
    service_registry.register(host.name, host)
    host.set_service_registry(service_registry, host.name)

# Start production (all items start)
await engine.start()
```

### 4. Runtime: Items Running as Services

**Each Item Becomes a Running Service:**
```python
# HL7_PAS_Service is now:
- Listening on port 2575 (TCP server)
- Running 4 OS processes (multiprocess mode)
- Each process has priority queue (10,000 capacity)
- Auto-restart policy active
- Reporting metrics to Manager

# When message arrives:
1. TCP connection accepted
2. MLLP framing decoded
3. HL7 message parsed
4. Message added to priority queue
5. Worker picks from queue
6. on_before_process() hook called
7. on_process_input() processes message
8. on_after_process() hook called
9. Message sent to target via ServiceRegistry
10. ACK generated and sent back
```

## Item Configuration = Service Instance

### Key Concept: Items Are Configured, Not Coded

**In IRIS:**
```
Management Portal → Productions → Add New Item
→ Select: EnsLib.HL7.Service.TCPService
→ Configure: Port, Target, Settings
→ Click: Apply → Start
→ Result: Service running and accepting HL7
```

**In LI HIE:**
```
Portal UI → Projects → Add New Item
→ Select: HL7 TCP Service
→ Configure: Port, Target, Phase 2 Settings
→ Click: Save → Deploy → Start
→ Result: Service running and accepting HL7
```

**Both are identical workflows** - zero code required.

## Standard vs Custom Items

### Standard Items (Built-in, Zero Code)

**Users configure these through Portal UI:**
- **HL7 TCP Service** (`Engine.li.hosts.hl7.HL7TCPService`)
- **HL7 TCP Operation** (`Engine.li.hosts.hl7.HL7TCPOperation`)
- **File Service** (`Engine.li.hosts.file.FileService`)
- **File Operation** (`Engine.li.hosts.file.FileOperation`)
- **HTTP Service** (`Engine.li.hosts.http.HTTPService`)
- **HTTP Operation** (`Engine.li.hosts.http.HTTPOperation`)
- **Business Process** (`Engine.li.hosts.routing.RoutingProcess`)
- **Transform Process** (`Engine.li.hosts.transform.TransformProcess`)

**Configuration only** - no code writing.

### Custom Items (Optional Extensions)

**Advanced users can create custom classes:**

```python
# Custom business process (like IRIS ObjectScript class)
class NHSValidationProcess(BusinessProcess):
    """Custom NHS-specific validation."""

    async def on_process_input(self, message):
        # Custom logic
        nhs_number = self._extract_nhs_number(message)
        if not self._validate_nhs_number(nhs_number):
            return self._generate_nack(message, "Invalid NHS Number")

        # Route to next service
        await self.send_request_async("ADT_Router", message)
        return message
```

**Then configure instance in Portal UI:**
```yaml
Item Type: Custom Business Process
Class: demos.nhs_trust.lib.nhs_validation_process.NHSValidationProcess
Name: Complex_Validation_Process
Configuration: (form fields for custom settings)
```

**This is like:**
- IRIS: Custom ObjectScript class → instantiate in Management Portal
- Rhapsody: Custom JavaScript → configure in IDE
- Mirth: Custom Java/JavaScript → configure in channels

## Phase 2 Enterprise Features in Action

### Configuration Example (Portal UI)

**Item: HL7_PAS_Service**

**Performance & Execution Tab:**
```yaml
Execution Mode: [Multiprocess ▼]  # Dropdown
  Options:
  - Async (Event Loop) - Best for I/O-bound
  - Multiprocess (GIL Bypass) - Best for CPU-bound ✓ Selected
  - Thread Pool - Best for blocking I/O
  - Single Process - Debug mode

Worker Count: [4] # Number input, range 1-32
```

**Queue Configuration Tab:**
```yaml
Queue Type: [Priority ▼]  # Dropdown
  Options:
  - FIFO - First-In-First-Out (strict ordering)
  - Priority - Priority-based routing ✓ Selected
  - LIFO - Last-In-First-Out (stack)
  - Unordered - Maximum throughput

Queue Size: [10000]  # Number input, range 1-100000

Overflow Strategy: [Drop Oldest ▼]  # Dropdown
  Options:
  - Block - Wait for space (provides backpressure)
  - Drop Oldest - Remove oldest message ✓ Selected
  - Drop Newest - Reject incoming message
  - Reject - Raise exception
```

**Auto-Restart Tab:**
```yaml
Restart Policy: [Always ▼]  # Dropdown
  Options:
  - Never - Manual intervention required
  - On Failure - Only restart on ERROR state
  - Always - Restart regardless of reason ✓ Selected

Max Restarts: [100]  # Number input, range 0-1000

Restart Delay: [10.0] seconds  # Number input, range 0-300
```

**Messaging Tab:**
```yaml
Messaging Pattern: [Async Reliable ▼]  # Dropdown
  Options:
  - Async Reliable - Non-blocking, persisted ✓ Selected
  - Sync Reliable - Blocking request/reply
  - Concurrent Async - Parallel non-blocking
  - Concurrent Sync - Parallel blocking workers

Message Timeout: [30.0] seconds  # Number input, range 1-300
```

### Runtime Result

**Portal UI Dashboard Shows:**
```
HL7_PAS_Service Status: 🟢 RUNNING

Current Configuration:
├─ Execution: 4 multiprocess workers
├─ Queue: Priority queue, 45/10000 messages
├─ Restart: Always policy, 0 restarts (no failures)
└─ Messaging: Async reliable pattern

Metrics (last 5 minutes):
├─ Messages received: 1,250
├─ Messages processed: 1,247
├─ Messages failed: 3
├─ Success rate: 99.76%
├─ Average latency: 120ms
├─ Queue utilization: 0.45%
└─ Worker utilization: 65%

Health: ✅ All workers healthy
Last restart: Never
Uptime: 2 hours 15 minutes
```

## Service-to-Service Communication

### Configuration (Visual Designer)

**Portal UI → Connections → Visual Workflow Designer:**
```
[HL7_PAS_Service] ──async_reliable──> [Complex_Validation_Process]
                                              │
                                              ├──sync_reliable──> [ADT_Router]
                                              │                        │
                                              │                        ├──> [RIS_Operation]
                                              │                        ├──> [ICE_Operation]
                                              │                        └──> [Audit_File_Writer]
                                              │
                                              └──async──> [Exception_Handler]
```

### Runtime Execution

**Behind the scenes (automatic):**
```python
# In Complex_Validation_Process
async def on_process_input(self, message):
    # Validate
    if not valid:
        # Send to exception handler (async, fire-and-forget)
        await self.send_request_async("Exception_Handler", message)
        return None

    # Send to router (sync, wait for response)
    response = await self.send_request_sync(
        "ADT_Router",
        message,
        timeout=60.0
    )
    return response
```

**ServiceRegistry handles routing:**
```python
# Automatic service lookup
target_host = service_registry.get("ADT_Router")

# Create message envelope
envelope = MessageEnvelope(
    message=message,
    source="Complex_Validation_Process",
    target="ADT_Router",
    pattern=MessagingPattern.SYNC_RELIABLE,
)

# Route message (blocks until response for sync)
response = await service_registry.route_message(envelope)
```

**ADT_Router receives message:**
```python
# Message arrives in ADT_Router's priority queue
# Worker picks it up
# Processes according to business rules
# Sends responses back via ServiceRegistry
```

**All automatic** - configured, not coded.

## Deployment Model

### Docker-Native

**docker-compose.yml (generated from Portal):**
```yaml
version: '3.8'

services:
  # Manager API
  hie-manager:
    image: hie-manager:v1.4.0
    ports:
      - "8081:8081"
    environment:
      - DATABASE_URL=postgresql://hie:password@postgres:5432/hie
    depends_on:
      - postgres

  # Engine (Production Runtime)
  hie-engine:
    image: hie-engine:v1.4.0
    ports:
      - "2575:2575"  # HL7_PAS_Service
      - "9300:9300"  # Metrics
    volumes:
      - ./data/inbound:/data/inbound
      - ./data/outbound:/data/outbound
      - ./data/audit:/data/audit
    environment:
      - PRODUCTION_ID=${PRODUCTION_ID}
      - MANAGER_API_URL=http://hie-manager:8081
      - EXECUTION_MODE=multi_process
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G

  # Portal UI
  hie-portal:
    image: hie-portal:v1.4.0
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://hie-manager:8081
    depends_on:
      - hie-manager

  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=hie
      - POSTGRES_USER=hie
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
```

**Deployment Steps:**
1. User clicks "Deploy" in Portal
2. Portal sends configuration to Manager API
3. Manager stores in PostgreSQL
4. Manager signals Engine to reload
5. Engine fetches configuration
6. Engine instantiates all items
7. Items start running

**All automatic** - one click deployment.

## Key Differentiators from IRIS/Rhapsody/Mirth

| Feature | Implementation | Advantage |
|---------|---------------|-----------|
| **Configuration API** | REST + JSON | Modern, language-agnostic |
| **Hot Reload** | Live config updates | Zero downtime |
| **Multi-process** | True OS processes | Better than JVM |
| **Priority Queues** | Built-in | Enterprise-grade |
| **Auto-restart** | Configurable policies | Production-ready |
| **Docker-native** | Microservices | Cloud-ready |
| **Open Source** | Free + extensible | No licensing costs |

## Summary

### LI HIE = Enterprise Integration Engine

✅ **Configurable** (not a framework)
✅ **Portal UI** (web-based administration)
✅ **Manager API** (REST configuration)
✅ **Production Engine** (orchestrates services)
✅ **Zero code** (for standard workflows)
✅ **Enterprise features** (Phase 1 & 2 complete)
✅ **Docker-native** (modern deployment)
✅ **NHS-ready** (HL7, compliance, audit)

### Users Configure, Engine Executes

**Users don't write code** - they:
1. Select item types from dropdown
2. Fill in configuration forms
3. Draw connections in visual designer
4. Click "Deploy & Start"
5. Monitor real-time dashboards

**Engine handles everything**:
- Service lifecycle management
- Message routing
- Queue management
- Auto-restart
- Metrics collection
- Health monitoring

This is **exactly how IRIS, Rhapsody, and Mirth work** - LI HIE does it better with modern architecture and zero licensing costs.
