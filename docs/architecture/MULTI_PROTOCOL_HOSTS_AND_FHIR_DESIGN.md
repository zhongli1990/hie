# Multi-Protocol HL7 Hosts & FHIR Service Architecture

**Version:** 2.0  
**Date:** February 13, 2026  
**Status:** HL7 File/HTTP — ✅ Implemented | FHIR REST — ✅ Implemented  
**Author:** Architecture Team  
**Branch:** `feature/enterprise-topology-viewer`

---

## 1. Executive Summary

This document covers two related features:

1. **HL7 Multi-Protocol Hosts** (✅ Implemented) — File and HTTP adapters + host classes for HL7v2, matching IRIS `EnsLib.HL7.Service.FileService`, `EnsLib.HL7.Service.HTTPService`, and their operation counterparts.

2. **FHIR Service Architecture** (✅ Implemented) — HTTP REST adapters with JSON/stream payload for FHIR R4/R5 resources, following the same decoupled adapter pattern.

Both features follow the **IRIS adapter decoupling principle**: the host class handles message parsing, validation, ACK/response generation, and trace storage. The adapter handles only transport (TCP, File, HTTP). Swapping the adapter changes the transport without touching any business logic.

---

## 2. Cross-Platform Research

### 2.1 IRIS EnsLib.HL7.* Class Hierarchy

```
EnsLib.HL7.Service.Standard (abstract)
│   extends Ens.BusinessService + EnsLib.HL7.Util.IOFraming + EnsLib.EDI.ServiceInterface
│   — Contains ALL HL7 parsing, validation, ACK generation, batch handling
│   — Properties: AckMode, BatchHandling, MessageSchemaCategory, DocSchemaInfo
│   — Methods: OnProcessInput(), resolveDocType(), SendReply(), OnGetConnections()
│
├── EnsLib.HL7.Service.TCPService    → uses EnsLib.HL7.Adapter.TCPInboundAdapter (MLLP)
├── EnsLib.HL7.Service.FileService   → uses EnsLib.File.InboundAdapter (file polling)
│       Properties: AckMode, AckTargetConfigNames, SegTerminator
├── EnsLib.HL7.Service.HTTPService   → uses EnsLib.HTTP.InboundAdapter (HTTP listener)
│       extends EnsLib.HTTP.Service + EnsLib.HL7.Service.Standard (multiple inheritance)
│       Properties: EnableStandardRequests, HTTPResponseMode, SegTerminator
├── EnsLib.HL7.Service.FTPService    → uses EnsLib.FTP.InboundAdapter
├── EnsLib.HL7.Service.SOAPService   → uses EnsLib.SOAP.InboundAdapter
└── EnsLib.HL7.Service.AckInStandard → ACK-only receiver

EnsLib.HL7.Operation.Standard (abstract)
│   extends Ens.BusinessOperation
│   — Contains ALL HL7 output logic, ACK evaluation, ReplyCodeActions
│
├── EnsLib.HL7.Operation.TCPOperation  → uses EnsLib.HL7.Adapter.TCPOutboundAdapter
├── EnsLib.HL7.Operation.FileOperation → uses EnsLib.File.OutboundAdapter
│       extends EnsLib.HL7.Operation.BatchStandard (supports batch file output)
├── EnsLib.HL7.Operation.HTTPOperation → uses EnsLib.HTTP.OutboundAdapter
└── EnsLib.HL7.Operation.FTPOperation  → uses EnsLib.FTP.OutboundAdapter
```

**Key IRIS design principle**: The `Standard` base class contains ALL protocol-specific logic. The concrete classes (`FileService`, `HTTPService`, `TCPService`) only set `ADAPTER = <AdapterClass>` and add transport-specific properties. The adapter is completely decoupled.

### 2.2 IRIS FHIR Architecture

IRIS FHIR is architecturally different from HL7:

```
HS.FHIRServer.API                    — Core FHIR server API
├── HS.FHIRServer.RestHandler        — HTTP REST endpoint handler
├── HS.FHIRServer.Storage.Json       — JSON resource storage
└── HS.FHIRServer.Interop            — Interoperability production integration
    ├── Service                      — Inbound FHIR requests → production
    ├── Operation                    — Production → FHIR server
    └── Request/Response             — FHIR-specific message classes

HS.FHIR.REST.Operation               — Outbound FHIR REST client
    uses EnsLib.HTTP.OutboundAdapter  — Same HTTP adapter as HL7 HTTP!
```

**Key insight**: IRIS FHIR uses the **same HTTP adapter** as HL7 HTTP. The difference is in the host class (FHIR parsing, resource validation, FHIR-specific response codes) and the message body class.

### 2.3 Rhapsody FHIR

Rhapsody uses a generic HTTP Communication Point for FHIR, with:
- **FHIR Message Definition** — Parses JSON/XML FHIR resources
- **FHIR Validation Filter** — Validates against FHIR profiles
- **FHIR Path Filter** — Extracts fields using FHIRPath expressions
- Transport: HTTP Communication Point (same as HL7 over HTTP)

### 2.4 Mirth FHIR

Mirth Connect uses:
- **FHIR Listener** — HTTP listener with FHIR-specific routing
- **FHIR Sender** — HTTP client for FHIR servers
- **FHIR Reader/Writer** — JSON/XML serialization
- Data type: `FHIR` (alongside `HL7v2`, `XML`, `JSON`, etc.)

### 2.5 Common Pattern Across All Platforms

| Aspect | IRIS | Rhapsody | Mirth | **OpenLI HIE** |
|--------|------|----------|-------|----------------|
| HL7 TCP | EnsLib.HL7.Service.TCPService | TCP Comm Point + HL7 | TCP Listener + HL7v2 | HL7TCPService |
| HL7 File | EnsLib.HL7.Service.FileService | File Comm Point + HL7 | File Reader + HL7v2 | **HL7FileService** ✅ |
| HL7 HTTP | EnsLib.HL7.Service.HTTPService | HTTP Comm Point + HL7 | HTTP Listener + HL7v2 | **HL7HTTPService** ✅ |
| FHIR REST | HS.FHIR.REST.Operation | HTTP Comm Point + FHIR | FHIR Listener/Sender | **FHIRRESTService** 📋 |
| Adapter decoupling | ✅ Adapter class per transport | ✅ Comm Point per transport | ✅ Connector per transport | ✅ Adapter class per transport |
| Same adapter for HL7+FHIR HTTP | ✅ EnsLib.HTTP.* | ✅ HTTP Comm Point | ✅ HTTP Connector | ✅ InboundHTTPAdapter |

---

## 3. HL7 Multi-Protocol Hosts (✅ Implemented)

### 3.1 Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │          HL7TCPService (existing)            │
                    │  ┌─────────────────────────────────────┐    │
                    │  │  HL7 Standard Logic (shared)         │    │
                    │  │  • Schema loading & validation       │    │
                    │  │  • Message parsing (HL7ParsedView)   │    │
                    │  │  • ACK generation (AA/AE/AR)         │    │
                    │  │  • Message trace (store_message_*)   │    │
                    │  │  • Target routing (send_to_targets)  │    │
                    │  └─────────────────────────────────────┘    │
                    │  adapter_class = MLLPInboundAdapter          │
                    └─────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
          HL7FileService        HL7TCPService       HL7HTTPService
          adapter_class =       adapter_class =     adapter_class =
          InboundFileAdapter    MLLPInboundAdapter  InboundHTTPAdapter
          AckMode="Never"       AckMode="Immediate" AckMode="Immediate"
          (no peer to ACK)      (MLLP ACK)          (HTTP response=ACK)
```

### 3.2 New Host Classes

| Class | IRIS Equivalent | Adapter | Key Difference |
|-------|----------------|---------|----------------|
| `HL7FileService` | `EnsLib.HL7.Service.FileService` | `InboundFileAdapter` | AckMode defaults to "Never" (no TCP peer) |
| `HL7FileOperation` | `EnsLib.HL7.Operation.FileOperation` | `OutboundFileAdapter` | No ACK expected; marks header Completed on write |
| `HL7HTTPService` | `EnsLib.HL7.Service.HTTPService` | `InboundHTTPAdapter` | ACK returned as HTTP response body |
| `HL7HTTPOperation` | `EnsLib.HL7.Operation.HTTPOperation` | `OutboundHTTPAdapter` | ACK expected in HTTP response body |

### 3.3 New Adapter Classes

| Adapter | IRIS Equivalent | Transport | Key Features |
|---------|----------------|-----------|--------------|
| `InboundFileAdapter` | `EnsLib.File.InboundAdapter` | File polling | Configurable: FilePath, FileSpec, PollInterval, ArchivePath, WorkPath, SemaphoreSpec |
| `OutboundFileAdapter` | `EnsLib.File.OutboundAdapter` | File writing | Configurable: FilePath, Filename pattern (%timestamp%, %type%, %id%), Overwrite mode, atomic write |
| `InboundHTTPAdapter` | `EnsLib.HTTP.InboundAdapter` | HTTP server | Configurable: Port, SSL, AllowedMethods, BasePath, CORS, MaxBodySize |
| `OutboundHTTPAdapter` | `EnsLib.HTTP.OutboundAdapter` | HTTP client | Configurable: URL, Method, ContentType, SSL, Retries, CustomHeaders. Uses aiohttp with raw socket fallback |

### 3.4 E2E Route Verification

All combinations work through the existing routing engine:

```
HL7 File Inbound → HL7RoutingEngine → HL7 TCP Outbound     ✅
HL7 TCP Inbound  → HL7RoutingEngine → HL7 File Outbound    ✅
HL7 HTTP Inbound → HL7RoutingEngine → HL7 TCP Outbound     ✅
HL7 TCP Inbound  → HL7RoutingEngine → HL7 HTTP Outbound    ✅
HL7 File Inbound → HL7RoutingEngine → HL7 HTTP Outbound    ✅
HL7 HTTP Inbound → HL7RoutingEngine → HL7 File Outbound    ✅
```

This works because:
1. All inbound services produce the same `HL7Message` object
2. The routing engine operates on `HL7Message` (protocol-agnostic)
3. All outbound operations accept `HL7Message` and extract `.raw` bytes
4. Message trace uses the same `store_message_header/body` functions regardless of transport

### 3.5 ClassRegistry & IRIS Aliases

```python
# Core registrations
ClassRegistry._register_internal("li.hosts.hl7.HL7FileService", HL7FileService)
ClassRegistry._register_internal("li.hosts.hl7.HL7FileOperation", HL7FileOperation)
ClassRegistry._register_internal("li.hosts.hl7.HL7HTTPService", HL7HTTPService)
ClassRegistry._register_internal("li.hosts.hl7.HL7HTTPOperation", HL7HTTPOperation)

# IRIS compatibility aliases (enables IRIS config import)
ClassRegistry.register_alias("EnsLib.HL7.Service.FileService", "li.hosts.hl7.HL7FileService")
ClassRegistry.register_alias("EnsLib.HL7.Operation.FileOperation", "li.hosts.hl7.HL7FileOperation")
ClassRegistry.register_alias("EnsLib.HL7.Service.HTTPService", "li.hosts.hl7.HL7HTTPService")
ClassRegistry.register_alias("EnsLib.HL7.Operation.HTTPOperation", "li.hosts.hl7.HL7HTTPOperation")
```

---

## 4. FHIR Service Architecture (✅ Implemented)

### 4.1 Design Principles

1. **Same adapter decoupling** — FHIR services use the same `InboundHTTPAdapter` / `OutboundHTTPAdapter` as HL7 HTTP services. Only the host class differs.

2. **Same message trace model** — FHIR messages use the same `message_headers` + `message_bodies` tables. The `body_class_name` discriminator is `'FHIRMessageBody'` instead of `'EnsLib.HL7.Message'`.

3. **No design conflicts** — Our generic Message Model (Option C Hybrid) was designed for this. The `message_bodies` table already has `fhir_version`, `resource_type`, `resource_id` columns.

4. **REST-native** — Unlike HL7 (which is message-oriented), FHIR is REST-native. The service must handle GET/POST/PUT/DELETE and route based on resource type and operation.

### 4.2 Proposed Class Hierarchy

```
FHIRMessage (in-memory container, like HL7Message)
│   raw: bytes                    — Raw JSON/XML bytes
│   parsed: dict | None           — Parsed FHIR resource (lazy)
│   resource_type: str            — "Patient", "Observation", "Bundle"
│   resource_id: str | None       — FHIR resource ID
│   fhir_version: str             — "R4", "R5"
│   operation: str                — "read", "create", "update", "search", "transaction"
│   http_method: str              — "GET", "POST", "PUT", "DELETE"
│   http_path: str                — "/Patient/123", "/Observation?code=..."
│   session_id: str | None        — Session tracking
│   header_id: UUID | None        — Persisted trace header
│   body_id: UUID | None          — Persisted trace body
│
FHIRRESTService (BusinessService)
│   extends BusinessService
│   adapter_class = InboundHTTPAdapter  ← Same adapter as HL7HTTPService!
│   — Parses FHIR REST requests (GET/POST/PUT/DELETE)
│   — Validates FHIR resources against profiles
│   — Routes to targets based on resource type
│   — Returns FHIR OperationOutcome on errors
│   — Stores message trace with body_class_name='FHIRMessageBody'
│
FHIRRESTOperation (BusinessOperation)
│   extends BusinessOperation
│   adapter_class = OutboundHTTPAdapter  ← Same adapter as HL7HTTPOperation!
│   — Sends FHIR REST requests to remote FHIR servers
│   — Handles FHIR-specific response codes (200, 201, 404, 422)
│   — Parses OperationOutcome from error responses
│   — Stores message trace
│
FHIRRoutingEngine (BusinessProcess)
│   extends BusinessProcess
│   — Routes FHIR resources based on resource_type, operation, profiles
│   — Supports content-based routing (FHIRPath expressions)
│   — Creates per-target message headers (same as HL7RoutingEngine)
```

### 4.3 FHIR REST Request Handling

```python
# FHIRRESTService._handle_http_request(request: HTTPRequest) -> HTTPResponse

# 1. Parse FHIR REST URL
#    GET /Patient/123          → operation="read", resource_type="Patient", id="123"
#    POST /Patient             → operation="create", resource_type="Patient"
#    PUT /Patient/123          → operation="update", resource_type="Patient", id="123"
#    DELETE /Patient/123       → operation="delete", resource_type="Patient", id="123"
#    GET /Patient?name=Smith   → operation="search", resource_type="Patient"
#    POST /                    → operation="transaction" (Bundle)

# 2. Parse body (JSON or XML)
#    Content-Type: application/fhir+json → JSON parse
#    Content-Type: application/fhir+xml  → XML parse

# 3. Validate against FHIR profile (if configured)

# 4. Create FHIRMessage and route to targets

# 5. Return FHIR-compliant response
#    201 Created (with Location header) for create
#    200 OK (with resource) for read/update
#    200 OK (with Bundle) for search
#    422 Unprocessable Entity (with OperationOutcome) for validation errors
```

### 4.4 Message Model Compatibility Check

| Feature | HL7 | FHIR | Conflict? |
|---------|-----|------|-----------|
| `message_bodies.body_class_name` | `'EnsLib.HL7.Message'` | `'FHIRMessageBody'` | ✅ No conflict — discriminator pattern |
| `message_bodies.raw_content` | HL7 ER7 bytes | JSON/XML bytes | ✅ No conflict — both are bytes |
| `message_bodies.content_type` | `'application/hl7-v2+er7'` | `'application/fhir+json'` | ✅ No conflict |
| `message_bodies.schema_category` | `'2.4'` | NULL | ✅ No conflict — nullable |
| `message_bodies.fhir_version` | NULL | `'R4'` | ✅ No conflict — nullable |
| `message_bodies.resource_type` | NULL | `'Patient'` | ✅ No conflict — nullable |
| `message_headers.message_type` | `'ADT^A01'` | `'Patient/create'` | ✅ No conflict — free text |
| `message_headers.source/target` | Item names | Item names | ✅ Identical |
| `message_headers.session_id` | `'SES-{UUID}'` | `'SES-{UUID}'` | ✅ Identical |
| In-memory message class | `HL7Message` | `FHIRMessage` | ✅ Different classes, same pattern |
| Adapter | MLLP/File/HTTP | HTTP only | ✅ Reuses `InboundHTTPAdapter` |
| Routing engine | `HL7RoutingEngine` | `FHIRRoutingEngine` | ✅ Separate class, same base pattern |

**Conclusion: Zero design conflicts.** The Option C Hybrid `message_bodies` table was specifically designed for this — protocol-specific nullable columns with a `body_class_name` discriminator.

### 4.5 FHIR-Specific Adapter Settings

The `InboundHTTPAdapter` already supports everything FHIR needs:

| Setting | HL7 HTTP Value | FHIR REST Value |
|---------|---------------|-----------------|
| `AllowedMethods` | `POST` | `GET,POST,PUT,DELETE` |
| `BasePath` | `/` | `/fhir/r4` |
| `EnableCORS` | `false` | `true` (SMART on FHIR) |
| `ContentType` (outbound) | `application/hl7-v2+er7` | `application/fhir+json` |

No new adapter is needed. The `InboundHTTPAdapter` is protocol-agnostic by design.

### 4.6 Cross-Platform Migration Support

| Source Platform | FHIR Component | OpenLI HIE Equivalent |
|----------------|----------------|----------------------|
| IRIS `HS.FHIR.REST.Operation` | Outbound FHIR REST client | `FHIRRESTOperation` + `OutboundHTTPAdapter` |
| IRIS `HS.FHIRServer.Interop.Service` | Inbound FHIR → production | `FHIRRESTService` + `InboundHTTPAdapter` |
| Rhapsody HTTP Comm Point + FHIR | Inbound/Outbound FHIR | `FHIRRESTService` / `FHIRRESTOperation` |
| Mirth FHIR Listener | Inbound FHIR | `FHIRRESTService` |
| Mirth FHIR Sender | Outbound FHIR | `FHIRRESTOperation` |

---

## 5. Host Lifecycle — Unchanged

All new hosts follow the same lifecycle as existing hosts:

- Each host runs as a **standalone async worker loop** (`_worker_loop`)
- Hosts are dynamically invoked with configurable `pool_size` workers
- Hosts receive messages via `submit()` → async queue → `_process_message()`
- Hosts can call any other host via `send_to_targets()`, `send_request_async/sync()`
- Lifecycle callbacks (`on_init`, `on_start`, `on_stop`, `on_teardown`) are untouched
- Message hooks (`on_before_process`, `on_after_process`, `on_process_error`) are untouched
- The base `Host` class in `Engine/li/hosts/base.py` has **zero changes**

---

## 6. Implementation Files

### 6.1 HL7 Multi-Protocol (✅ Implemented)

| File | What |
|------|------|
| `Engine/li/adapters/file.py` | `InboundFileAdapter`, `OutboundFileAdapter` |
| `Engine/li/adapters/http.py` | `InboundHTTPAdapter`, `OutboundHTTPAdapter`, `HTTPRequest`, `HTTPResponse` |
| `Engine/li/adapters/__init__.py` | Updated exports |
| `Engine/li/hosts/hl7.py` | Added `HL7FileService`, `HL7FileOperation`, `HL7HTTPService`, `HL7HTTPOperation` + ClassRegistry registrations |

### 6.2 FHIR (✅ Implemented)

| File | What |
|------|------|
| `Engine/li/hosts/fhir.py` | `FHIRMessage`, `FHIRRESTService`, `FHIRRESTOperation`, `FHIRSendResult`, `FHIRSendError`, `parse_fhir_url()`, `build_operation_outcome()`, `_store_inbound_fhir()`, `_store_outbound_fhir()` |
| `Engine/li/hosts/fhir_routing.py` | `FHIRRoutingEngine`, `FHIRRoutingRule`, `FHIRRoutingResult`, `FHIRConditionEvaluator`, `create_resource_type_rule()`, `create_bundle_type_rule()` |
| `Engine/li/hosts/__init__.py` | Updated exports for all FHIR + HL7 File/HTTP classes |
| `Engine/li/registry/class_registry.py` | Added FHIR IRIS aliases (`HS.FHIRServer.Interop.*`) |

No new adapters needed — reuses `InboundHTTPAdapter` and `OutboundHTTPAdapter`.

---

## 7. Summary

### What's Done

- **4 new HL7 host classes** (`HL7FileService`, `HL7FileOperation`, `HL7HTTPService`, `HL7HTTPOperation`)
- **4 new adapter classes** (`InboundFileAdapter`, `OutboundFileAdapter`, `InboundHTTPAdapter`, `OutboundHTTPAdapter`)
- **3 new FHIR host classes** (`FHIRRESTService`, `FHIRRESTOperation`, `FHIRRoutingEngine`)
- **FHIRMessage** in-memory container with full field access, `with_header_id()`, and trace support
- **FHIR URL parser** (`parse_fhir_url`) — handles all FHIR REST interactions (read, create, update, delete, search, transaction, capabilities, vread, history)
- **FHIR condition evaluator** — routes by `resourceType`, `interaction`, `bundleType`, and field values
- **Full IRIS alias compatibility** (HL7: `EnsLib.HL7.*` → `HL7*`, FHIR: `HS.FHIRServer.*` → `FHIR*`)
- **E2E routing works** across all transport combinations (TCP↔File↔HTTP for HL7, HTTP for FHIR)
- **Message trace unchanged** — all hosts use the same `store_message_header/body` functions with `body_class_name` discriminator (`'EnsLib.HL7.Message'` for HL7, `'FHIRMessageBody'` for FHIR)
- **Zero design conflicts** with existing Message Model (Option C Hybrid)
- **Cross-platform migration** support for IRIS, Rhapsody, and Mirth configurations
- **All FHIR hosts run as standalone async worker loops** with configurable pool_size, queue-based message reception, full callback support, and inter-service messaging via reliable/sync/async patterns

---

*OpenLI HIE — Healthcare Integration Engine*
