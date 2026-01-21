# HIE - Healthcare Integration Engine

A next-generation, enterprise-grade healthcare integration engine designed for mission-critical NHS acute trust environments.

**Version:** 0.2.0  
**Status:** User Management & Authentication Release  
**Last Updated:** January 21, 2026

## Overview

HIE is a high-performance messaging and orchestration bus that supports:
- **Any protocol** (HL7v2, FHIR, DICOM, custom)
- **Any data format** (structured, semi-structured, binary)
- **Any transformation** — applied only when explicitly required
- **Fully configurable routing** — No hardcoded Python, all routes defined via JSON/YAML
- **Visual management portal** — Web-based UI for configuration and monitoring

## Design Principles

1. **Raw-first, parse-on-demand** — Messages are stored and transported in raw form. Parsing occurs only when explicitly required by a route or item.

2. **Explicit over implicit** — No hidden behavior. Every transformation, validation, or routing decision is configured.

3. **Vendor-neutral** — No legacy engine terminology in the core. Clean abstractions that can interoperate with existing systems via adapters.

4. **Enterprise reliability** — Built for high-throughput, high-concurrency environments with proper backpressure, ordering guarantees, and retry logic.

## Architecture

### Core Concepts

- **Production** — The runtime orchestrator containing all items and routes
- **Item** — An independently configurable runtime unit (receiver, processor, or sender)
- **Route** — A message flow linking items together
- **Message** — Envelope (metadata) + Payload (raw content)

### Message Model

```
┌─────────────────────────────────────┐
│              Message                │
├─────────────────────────────────────┤
│  Envelope (Header)                  │
│  ├── message_id                     │
│  ├── correlation_id                 │
│  ├── timestamp                      │
│  ├── source                         │
│  ├── routing metadata               │
│  └── governance/audit fields        │
├─────────────────────────────────────┤
│  Payload (Body)                     │
│  ├── raw_content (bytes)            │
│  ├── content_type                   │
│  └── properties (typed, explicit)   │
└─────────────────────────────────────┘
```

## Project Structure

```
HIE/
├── core/                 # Core abstractions
│   ├── message.py        # Envelope + Payload model
│   ├── item.py           # Base Item abstraction
│   ├── route.py          # Route definition
│   ├── production.py     # Orchestrator/runtime
│   └── config.py         # Configuration loader
├── items/
│   ├── receivers/        # Inbound items (HTTP, file, MLLP)
│   ├── processors/       # Business logic, transforms
│   └── senders/          # Outbound items (MLLP, file, HTTP)
├── protocols/
│   ├── hl7v2/            # HL7v2 parsing (on-demand)
│   └── fhir/             # FHIR support
├── persistence/          # Message store (PostgreSQL, Redis)
├── management/           # REST API for portal
├── tests/
├── config/               # Example production configs
└── docs/                 # Documentation
```

## Quick Start

### Option 1: Full Stack with Docker Compose (Recommended for E2E Testing)

```bash
# Clone and setup
git clone <repository>
cd HIE

# Create data directories
mkdir -p data/{inbound,outbound,processed,archive}

# Start the full stack (backend + portal + databases)
docker-compose -f docker-compose.full.yml up --build

# Access the services:
# - Portal:           http://localhost:9303
# - Management API:   http://localhost:9302/api/health
# - HIE Engine:       http://localhost:9300/health
# - PostgreSQL:       localhost:9310
# - Redis:            localhost:9311
# - MLLP Echo:        localhost:9320
# - HTTP Echo:        localhost:9321
# - Adminer (DB UI):  http://localhost:9330
# - Redis Commander:  http://localhost:9331
```

### Option 2: Development Setup

```bash
# Backend
cd HIE
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run with example config
hie run --config config/example.yaml

# Portal (separate terminal)
cd portal
npm install
npm run dev
# Access at http://localhost:3000
```

## Configuration

HIE supports both **YAML** and **JSON** configuration formats. Routes and productions are fully configurable without any Python code changes.

### JSON Configuration (Recommended for Portal)

```json
{
  "name": "NHS-ADT-Integration",
  "description": "ADT message integration for NHS acute trust",
  "enabled": true,
  "settings": {
    "actorPoolSize": 4,
    "gracefulShutdownTimeout": 60,
    "autoStart": true
  },
  "items": [
    {
      "id": "HTTP_ADT_Receiver",
      "name": "HTTP ADT Receiver",
      "type": "receiver.http",
      "category": "service",
      "enabled": true,
      "settings": {
        "port": 8080,
        "path": "/api/hl7/adt"
      }
    },
    {
      "id": "ADT_Router",
      "type": "processor.router",
      "category": "process",
      "enabled": true
    },
    {
      "id": "PAS_MLLP_Sender",
      "type": "sender.mllp",
      "category": "operation",
      "settings": {
        "host": "pas.nhs.local",
        "port": 2575
      }
    }
  ],
  "connections": [
    {"sourceId": "HTTP_ADT_Receiver", "targetId": "ADT_Router"},
    {"sourceId": "ADT_Router", "targetId": "PAS_MLLP_Sender"}
  ],
  "routingRules": [
    {
      "name": "Route A01 to PAS",
      "sourceItemId": "ADT_Router",
      "targetItemIds": ["PAS_MLLP_Sender"],
      "filterGroup": {
        "operator": "and",
        "conditions": [
          {"field": "MSH.9.2", "operator": "equals", "value": "A01"}
        ]
      }
    }
  ]
}
```

### YAML Configuration

```yaml
production:
  name: "ADT-Feed"
  
items:
  - id: http_receiver
    type: receiver.http
    config:
      port: 8080
      path: /hl7
      
  - id: hl7_transformer
    type: processor.transform
    config:
      script: transforms/adt_transform.py
      
  - id: mllp_sender
    type: sender.mllp
    config:
      host: downstream.nhs.uk
      port: 2575

routes:
  - id: adt_route
    path: [http_receiver, hl7_transformer, mllp_sender]
```

## Canonical Message Format

HIE uses an internal canonical message format that all external formats (HL7v2, FHIR, CSV, etc.) can be converted to and from:

```
External Format → Parser → CanonicalMessage → Serializer → External Format

HL7v2 ADT^A01 → HL7v2Parser → CanonicalMessage → FHIRSerializer → FHIR Bundle
```

This enables:
- Protocol-agnostic processing and routing
- Unified transformation logic
- Format conversion between any supported protocols

## E2E Testing

The full Docker Compose stack includes test servers:

```bash
# Send a test HL7v2 message to the HTTP receiver
curl -X POST http://localhost:9300/hl7 \
  -H "Content-Type: application/hl7-v2" \
  -d 'MSH|^~\&|SENDING|FACILITY|RECEIVING|FACILITY|20260121120000||ADT^A01|123|P|2.5
PID|1||12345^^^NHS^NH||DOE^JOHN||19800101|M'

# Check the MLLP echo server received it
docker logs hie-mllp-echo

# View messages in the portal
open http://localhost:9303/messages
```

## Documentation

- [Product Vision](docs/PRODUCT_VISION.md)
- [Feature Specification](docs/FEATURE_SPEC.md)
- [Requirements Specification](docs/REQUIREMENTS_SPEC.md)
- [Development Roadmap](docs/ROADMAP.md)

## License

Open Source (License TBD)

## Status

✅ **v0.1.0 Released** — Initial release with core engine and management portal.

### What's Included in v0.1.0

**Core Engine:**
- Production orchestrator with lifecycle management
- HTTP and File receivers
- MLLP and File senders
- Message routing with content-based filtering
- PostgreSQL and Redis persistence
- Immutable message model with envelope/payload separation

**Management Portal:**
- Dashboard with real-time metrics
- Productions list and detail views
- Configure page with route editor
- Messages page with search and filtering
- Monitoring page with system metrics
- Errors page with severity tracking
- Logs page with real-time streaming
- Settings page with configuration panels

**Infrastructure:**
- Docker and Docker Compose deployment
- Full E2E testing stack with echo servers
- Management REST API
