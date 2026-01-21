# HIE Feature Specification

## Healthcare Integration Engine - Complete Feature Set

**Version:** 0.2.0  
**Last Updated:** January 21, 2026  
**Status:** Initial Release

---

## Table of Contents

1. [Core Engine Features](#1-core-engine-features)
2. [Protocol Support](#2-protocol-support)
3. [Message Processing](#3-message-processing)
4. [Configuration & Management](#4-configuration--management)
5. [Management Portal](#5-management-portal)
6. [Monitoring & Observability](#6-monitoring--observability)
7. [Security](#7-security)
8. [Deployment & Operations](#8-deployment--operations)
9. [Integration Capabilities](#9-integration-capabilities)
10. [Developer Features](#10-developer-features)

---

## 1. Core Engine Features

### 1.1 Production (Orchestrator)

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Production Lifecycle | Start, stop, pause, resume productions | P0 | ✅ Done |
| Multi-Production | Run multiple productions in single instance | P1 | 🔲 Planned |
| Production Templates | Pre-built production configurations | P2 | 🔲 Planned |
| Production Versioning | Version control for production configs | P1 | 🔲 Planned |
| Production Import/Export | JSON/YAML export and import | P0 | ✅ Done |
| Production Validation | Validate config before deployment | P0 | ✅ Done |

### 1.2 Items (Business Hosts)

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Business Services (Receivers) | Inbound message handlers | P0 | ✅ Done |
| Business Processes (Processors) | Message transformation/routing | P0 | ✅ Done |
| Business Operations (Senders) | Outbound message delivery | P0 | ✅ Done |
| Item Lifecycle | Start, stop, pause, resume items | P0 | ✅ Done |
| Item Pooling | Configurable worker pools | P0 | ✅ Done |
| Item Categories | Organize items by category | P1 | ✅ Done |
| Item Templates | Pre-configured item types | P2 | 🔲 Planned |
| Dynamic Item Creation | Create items at runtime via API | P1 | ✅ Done |

### 1.3 Routes (Message Flows)

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Linear Routes | Simple A → B → C flows | P0 | ✅ Done |
| Content-Based Routing | Route based on message content | P0 | ✅ Done |
| Filter Rules | Include/exclude messages | P0 | ✅ Done |
| Error Routes | Redirect failed messages | P0 | ✅ Done |
| Dead Letter Queues | Handle undeliverable messages | P0 | ✅ Done |
| Route Branching | Fan-out to multiple destinations | P1 | ✅ Done |
| Route Joining | Aggregate from multiple sources | P1 | ✅ Done |
| Dynamic Routing | Runtime route modification | P1 | ✅ Done |
| Route Visualization | Visual route editor | P1 | 🔄 In Progress |

### 1.4 Message Model

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Envelope/Payload Separation | Clean metadata/content split | P0 | ✅ Done |
| Raw-First Storage | Preserve original bytes | P0 | ✅ Done |
| Message Immutability | Thread-safe message handling | P0 | ✅ Done |
| Correlation Tracking | Link related messages | P0 | ✅ Done |
| Causation Tracking | Track message lineage | P0 | ✅ Done |
| Message Properties | Typed key-value metadata | P0 | ✅ Done |
| Message Serialization | MsgPack, JSON formats | P0 | ✅ Done |
| Large Message Support | Handle messages >10MB | P1 | 🔲 Planned |

---

## 2. Protocol Support

### 2.1 Inbound Protocols (Receivers)

| Protocol | Description | Priority | Status |
|----------|-------------|----------|--------|
| HTTP/REST | REST API endpoints | P0 | ✅ Done |
| File System | Directory watching | P0 | ✅ Done |
| MLLP | HL7 over TCP | P1 | 🔲 Planned |
| TCP/IP | Raw TCP connections | P1 | 🔲 Planned |
| FTP/SFTP | File transfer protocols | P1 | 🔲 Planned |
| SOAP | Web services | P2 | 🔲 Planned |
| Kafka | Event streaming | P2 | 🔲 Planned |
| AMQP/RabbitMQ | Message queuing | P2 | 🔲 Planned |
| Database Polling | Query-based ingestion | P2 | 🔲 Planned |

### 2.2 Outbound Protocols (Senders)

| Protocol | Description | Priority | Status |
|----------|-------------|----------|--------|
| MLLP | HL7 over TCP | P0 | ✅ Done |
| File System | Write to directories | P0 | ✅ Done |
| HTTP/REST | REST API calls | P1 | 🔲 Planned |
| TCP/IP | Raw TCP connections | P1 | 🔲 Planned |
| FTP/SFTP | File transfer | P1 | 🔲 Planned |
| SOAP | Web services | P2 | 🔲 Planned |
| Kafka | Event publishing | P2 | 🔲 Planned |
| AMQP/RabbitMQ | Message queuing | P2 | 🔲 Planned |
| Database Insert | Direct DB writes | P2 | 🔲 Planned |
| Email/SMTP | Email notifications | P2 | 🔲 Planned |

---

## 3. Message Processing

### 3.1 Data Formats

| Format | Description | Priority | Status |
|--------|-------------|----------|--------|
| HL7 v2.x | ER7 and XML formats | P0 | ✅ Done |
| FHIR R4 | JSON and XML | P1 | 🔲 Planned |
| CSV/Delimited | Flat file formats | P0 | 🔲 Planned |
| XML | Generic XML processing | P1 | 🔲 Planned |
| JSON | Generic JSON processing | P1 | 🔲 Planned |
| HL7 v3/CDA | Clinical documents | P2 | 🔲 Planned |
| DICOM | Medical imaging metadata | P2 | 🔲 Planned |
| X12 | EDI transactions | P3 | 🔲 Planned |

### 3.2 Transformation

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Field Mapping | Map fields between formats | P0 | 🔲 Planned |
| Data Transformation | Transform field values | P0 | 🔲 Planned |
| Code Translation | Lookup tables for codes | P1 | 🔲 Planned |
| Schema Validation | Validate against schemas | P1 | 🔲 Planned |
| Custom Scripts | Python transform scripts | P0 | ✅ Done |
| Visual DTL Editor | Drag-drop transformation | P2 | 🔲 Planned |
| XSLT Support | XML transformations | P2 | 🔲 Planned |

### 3.3 Routing Rules

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Simple Filters | Field-based filtering | P0 | ✅ Done |
| Complex Rules | Multi-condition rules | P1 | ✅ Done |
| Rule Engine | Visual rule builder | P1 | 🔲 Planned |
| Lookup Tables | External data lookups | P1 | 🔲 Planned |
| Regular Expressions | Pattern matching | P0 | ✅ Done |
| XPath/JSONPath | Path-based queries | P1 | 🔲 Planned |

---

## 4. Configuration & Management

### 4.1 Configuration Format

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| JSON Configuration | Primary config format | P0 | ✅ Done |
| YAML Configuration | Human-friendly format | P0 | ✅ Done |
| XML Import | Import from IRIS/Rhapsody | P1 | 🔲 Planned |
| Config Validation | Schema-based validation | P0 | ✅ Done |
| Config Diff | Compare configurations | P1 | 🔲 Planned |
| Config History | Track config changes | P1 | 🔲 Planned |

### 4.2 Runtime Management

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| REST API | Management API | P0 | ✅ Done |
| CLI Tools | Command-line management | P0 | ✅ Done |
| Hot Reload | Update config without restart | P1 | 🔲 Planned |
| Graceful Shutdown | Complete in-flight messages | P0 | ✅ Done |
| Health Checks | Liveness/readiness probes | P0 | ✅ Done |

---

## 5. Management Portal

### 5.1 Dashboard

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Production Overview | Status of all productions | P0 | ✅ Done |
| Message Statistics | Throughput, latency metrics | P0 | ✅ Done |
| System Health | Service status indicators | P0 | ✅ Done |
| Recent Activity | Live activity feed | P0 | ✅ Done |
| Quick Actions | Common operations | P1 | ✅ Done |
| Customizable Widgets | User-configurable dashboard | P2 | 🔲 Planned |

### 5.2 Production Configuration

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Productions List | View all productions with status | P0 | ✅ Done |
| Production Detail | View production items and metrics | P0 | ✅ Done |
| Configure Page | Route and item management UI | P0 | ✅ Done |
| Route Editor | Visual route flow display | P0 | ✅ Done |
| Items Table | View and manage items | P0 | ✅ Done |
| Visual Production Editor | Drag-drop item placement | P1 | 🔲 Planned |
| Connection Drawing | Visual item connections | P1 | 🔲 Planned |
| Config Import/Export | JSON/YAML download/upload | P1 | 🔲 Planned |

### 5.3 Message Viewer

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Message Search | Find messages by criteria | P0 | ✅ Done |
| Message List | Paginated message table | P0 | ✅ Done |
| Message Detail | View full message content | P0 | ✅ Done |
| Status Filtering | Filter by status/type | P0 | ✅ Done |
| Message Trace | Follow message through route | P1 | 🔲 Planned |
| Message Resend | Replay failed messages | P1 | 🔲 Planned |
| Bulk Operations | Act on multiple messages | P2 | 🔲 Planned |

### 5.4 Monitoring

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| System Metrics | CPU, memory, connections | P0 | ✅ Done |
| Production Metrics | Per-production statistics | P0 | ✅ Done |
| Throughput Charts | Message rate visualization | P0 | ✅ Done |
| Resource Usage | System resource bars | P0 | ✅ Done |
| External Connections | Connection status table | P0 | ✅ Done |
| Real-time Updates | Auto-refresh metrics | P1 | ✅ Done |
| Alert Configuration | Set up notifications | P2 | 🔲 Planned |

### 5.5 Errors & Logs

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Error List | View errors with severity | P0 | ✅ Done |
| Error Details | Expandable error info | P0 | ✅ Done |
| Stack Traces | View error stack traces | P0 | ✅ Done |
| Error Resolution | Mark errors as resolved | P0 | ✅ Done |
| Log Viewer | Terminal-style log display | P0 | ✅ Done |
| Log Streaming | Real-time log updates | P0 | ✅ Done |
| Log Filtering | Filter by level/source | P0 | ✅ Done |
| Log Export | Download logs | P1 | 🔲 Planned |

### 5.6 Settings

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| General Settings | Site name, timezone, etc. | P0 | ✅ Done |
| Notification Settings | Email/alert preferences | P0 | ✅ Done |
| Security Settings | Session, MFA, audit | P0 | ✅ Done |
| Database Settings | Connection configuration | P0 | ✅ Done |
| API Keys | Manage API access tokens | P0 | ✅ Done |
| Email Settings | SMTP configuration | P0 | ✅ Done |
| User Management | Create/edit users | P1 | 🔲 Planned |
| Role-Based Access | Permission management | P1 | 🔲 Planned |

---

## 6. Monitoring & Observability

### 6.1 Metrics

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Prometheus Export | Metrics endpoint | P0 | 🔲 Planned |
| Message Counters | Received/processed/failed | P0 | ✅ Done |
| Latency Histograms | Processing time distribution | P0 | 🔲 Planned |
| Queue Metrics | Depth, wait time | P0 | ✅ Done |
| Custom Metrics | User-defined metrics | P1 | 🔲 Planned |

### 6.2 Logging

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Structured Logging | JSON log format | P0 | ✅ Done |
| Log Levels | Debug/Info/Warn/Error | P0 | ✅ Done |
| Correlation IDs | Track across services | P0 | ✅ Done |
| Log Aggregation | Central log collection | P1 | 🔲 Planned |
| Log Retention | Configurable retention | P1 | 🔲 Planned |

### 6.3 Tracing

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| OpenTelemetry | Distributed tracing | P1 | 🔲 Planned |
| Message Tracing | End-to-end message path | P0 | 🔲 Planned |
| Performance Profiling | Identify bottlenecks | P1 | 🔲 Planned |

### 6.4 Alerting

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Threshold Alerts | Alert on metric thresholds | P0 | 🔲 Planned |
| Error Alerts | Alert on failures | P0 | 🔲 Planned |
| Email Notifications | Send alerts via email | P1 | 🔲 Planned |
| Webhook Notifications | POST to external systems | P1 | 🔲 Planned |
| PagerDuty/Slack | Integration with tools | P2 | 🔲 Planned |

---

## 7. Security

### 7.1 Authentication

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Local Users | Built-in user database | P0 | 🔲 Planned |
| LDAP/AD | Enterprise directory | P1 | 🔲 Planned |
| OAuth2/OIDC | Modern auth protocols | P1 | 🔲 Planned |
| API Keys | Service authentication | P0 | 🔲 Planned |
| MFA | Multi-factor auth | P1 | 🔲 Planned |

### 7.2 Authorization

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Role-Based Access | RBAC model | P0 | 🔲 Planned |
| Production-Level Permissions | Per-production access | P0 | 🔲 Planned |
| Item-Level Permissions | Per-item access | P1 | 🔲 Planned |
| Audit Trail | Track all access | P0 | 🔲 Planned |

### 7.3 Data Security

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| TLS Encryption | In-transit encryption | P0 | 🔲 Planned |
| Encryption at Rest | Stored data encryption | P1 | 🔲 Planned |
| Data Masking | Hide sensitive fields | P1 | 🔲 Planned |
| Key Management | Secure key storage | P1 | 🔲 Planned |

---

## 8. Deployment & Operations

### 8.1 Deployment Options

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Docker | Container deployment | P0 | ✅ Done |
| Docker Compose | Multi-container setup | P0 | ✅ Done |
| Kubernetes | K8s deployment | P1 | 🔲 Planned |
| Helm Charts | K8s package manager | P1 | 🔲 Planned |
| Bare Metal | Direct installation | P2 | 🔲 Planned |

### 8.2 High Availability

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Active-Passive | Failover clustering | P1 | 🔲 Planned |
| Active-Active | Load-balanced cluster | P1 | 🔲 Planned |
| Database HA | PostgreSQL replication | P1 | 🔲 Planned |
| Redis HA | Redis Sentinel/Cluster | P1 | 🔲 Planned |

### 8.3 Scalability

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Horizontal Scaling | Add more nodes | P1 | 🔲 Planned |
| Auto-Scaling | Dynamic scaling | P2 | 🔲 Planned |
| Load Balancing | Distribute traffic | P1 | 🔲 Planned |
| Partitioning | Shard by route/tenant | P2 | 🔲 Planned |

---

## 9. Integration Capabilities

### 9.1 NHS Integrations

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| NHS Spine | National backbone | P1 | 🔲 Planned |
| PDS | Patient Demographics | P1 | 🔲 Planned |
| EPS | Electronic Prescriptions | P2 | 🔲 Planned |
| SCR | Summary Care Record | P2 | 🔲 Planned |
| e-RS | e-Referral Service | P2 | 🔲 Planned |
| MESH | Message Exchange | P1 | 🔲 Planned |

### 9.2 Clinical Systems

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| EPR/EHR | Electronic records | P0 | 🔲 Planned |
| PAS | Patient admin systems | P0 | 🔲 Planned |
| LIMS | Laboratory systems | P0 | 🔲 Planned |
| RIS/PACS | Radiology systems | P1 | 🔲 Planned |
| Pharmacy | Medication systems | P1 | 🔲 Planned |

---

## 10. Developer Features

### 10.1 Extensibility

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Custom Items | Create new item types | P0 | ✅ Done |
| Custom Transforms | Python transform scripts | P0 | ✅ Done |
| Plugin System | Loadable extensions | P1 | 🔲 Planned |
| Custom Protocols | Add new protocols | P1 | 🔲 Planned |

### 10.2 Development Tools

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Test Framework | Unit/integration testing | P0 | ✅ Done |
| Message Simulator | Generate test messages | P1 | 🔲 Planned |
| Debug Mode | Enhanced logging/tracing | P0 | 🔲 Planned |
| API Documentation | OpenAPI/Swagger | P1 | 🔲 Planned |

### 10.3 SDK & Libraries

| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| Python SDK | Native Python library | P0 | ✅ Done |
| REST Client | API client library | P1 | 🔲 Planned |
| TypeScript Types | Portal type definitions | P1 | 🔲 Planned |

---

## Priority Legend

- **P0** — Must have for MVP
- **P1** — Required for production use
- **P2** — Important for enterprise adoption
- **P3** — Nice to have / future consideration

## Status Legend

- ✅ **Done** — Feature complete and tested
- 🔄 **In Progress** — Currently being developed
- 🔲 **Planned** — Scheduled for development
- ❌ **Blocked** — Waiting on dependencies

---

*This document is maintained by the HIE Core Team and updated with each sprint.*
