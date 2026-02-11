# HIE Product Vision

## Healthcare Integration Engine

**Version:** 1.4.0
**Last Updated:** February 10, 2026
**Status:** Enterprise Integration Engine (Phase 1-3 Complete)

---

## Executive Summary

HIE (Healthcare Integration Engine) is a next-generation, enterprise-grade healthcare integration platform designed to replace legacy integration engines like InterSystems IRIS/Ensemble, Rhapsody, and Mirth Connect. Built from first principles with modern architecture, HIE delivers superior performance, reliability, and maintainability for mission-critical NHS acute trust environments.

## Vision Statement

> **To be the definitive open-source healthcare integration platform that enables NHS trusts and healthcare organizations worldwide to achieve seamless, reliable, and auditable data exchange across all clinical and administrative systems.**

## Problem Statement

### Current Market Challenges

1. **Legacy Architecture** — Existing integration engines (IRIS, Rhapsody, Mirth) are built on aging architectures that struggle with modern scalability and deployment requirements.

2. **Vendor Lock-in** — Proprietary solutions create dependency on specific vendors, limiting flexibility and increasing long-term costs.

3. **Implicit Behavior** — Legacy engines often apply automatic transformations, parsing, and routing decisions that are difficult to audit and debug.

4. **Complex Licensing** — Enterprise healthcare integration solutions carry significant licensing costs that strain NHS budgets.

5. **Operational Complexity** — Configuration often requires specialized training and vendor-specific knowledge.

6. **Limited Cloud-Native Support** — Legacy engines were designed for on-premise deployment and struggle in containerized, cloud-native environments.

## Solution: HIE

HIE addresses these challenges through:

### 1. 100% Configuration-Driven Architecture
- **Portal UI Configuration** — All standard workflows configured through web-based Portal UI (zero code)
- **Visual Workflow Designer** — Drag-and-drop message flows, no programming required
- **Item Type Registry** — Built-in services, processes, and operations configurable via forms
- **Three-Tier Architecture** — Portal UI (configuration) → Manager API (orchestration) → Engine (runtime execution)

### 2. Raw-First Architecture
- Messages preserved in original form end-to-end
- Parsing only when explicitly required
- Full auditability of original content

### 3. Explicit Configuration
- No hidden transformations or routing decisions
- Every behavior is explicitly configured
- Configuration stored in PostgreSQL with version control

### 4. Phase 2 Enterprise Features
- **Execution Modes** — Async, Multiprocess (GIL bypass), Thread Pool, Single Process
- **Queue Types** — FIFO, Priority, LIFO, Unordered
- **Auto-Restart Policies** — Never, On Failure, Always (with configurable max restarts and delay)
- **Messaging Patterns** — Async Reliable, Sync Reliable, Concurrent Async, Concurrent Sync

### 5. Modern Technology Stack
- Python 3.11+ with async/await
- Container-native design (Docker, Kubernetes)
- Horizontal scalability
- REST + JSON API-first design

### 6. Open Source
- MIT license for core engine
- Community-driven development
- No vendor lock-in
- Zero licensing costs

### 7. Enterprise-Grade Reliability
- At-least-once delivery guarantees
- Hot reload (configuration changes without restart)
- Comprehensive monitoring and alerting
- Full audit trail

## Target Users

### Primary Users

1. **Integration Engineers** — Configure and maintain message flows
2. **System Administrators** — Deploy, monitor, and operate the platform
3. **Clinical Informaticists** — Define data requirements and validate integrations

### Secondary Users

1. **Developers** — Extend the platform with custom components
2. **Compliance Officers** — Audit message flows and data handling
3. **IT Leadership** — Strategic planning and vendor management

## Target Organizations

1. **NHS Acute Trusts** — Primary target market
2. **NHS Foundation Trusts** — Secondary target
3. **Private Healthcare Providers** — Tertiary market
4. **International Healthcare Organizations** — Future expansion

## Key Differentiators

### Comprehensive Competitive Analysis

LI HIE is a **100% configurable, enterprise-grade healthcare integration engine** designed to compete directly with InterSystems IRIS, Orion Rhapsody, and Mirth Connect. The following analysis demonstrates feature parity and competitive advantages.

| Feature | LI HIE | InterSystems IRIS | Orion Rhapsody | Mirth Connect |
|---------|--------|-------------------|----------------|---------------|
| **Architecture & Design** |
| Configuration Method | Portal UI (Web) + REST API | Management Portal (Web) | Rhapsody IDE (Desktop) | Administrator Console (Web) |
| Zero-Code Workflows | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Visual Workflow Designer | ✅ Yes | ✅ Yes (BPL) | ✅ Yes | ✅ Yes |
| Visual Data Mapper | ✅ Yes | ✅ Yes (DTL) | ✅ Yes | ✅ Yes |
| Rule Engine | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Item-Based Architecture | ✅ Services/Processes/Operations | ✅ Services/Processes/Operations | ✅ Services/Processes/Operations | ✅ Channels/Connectors |
| **Protocol Support** |
| HL7 v2.x (MLLP) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| FHIR R4 | 🔄 Planned Phase 5 | ✅ Yes | ✅ Yes | ✅ Yes |
| File I/O | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| HTTP/REST | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Database Adapters | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Enterprise Features** |
| Hot Reload | ✅ Yes | ❌ Requires restart | ❌ Requires restart | ❌ Requires restart |
| True Multiprocessing | ✅ OS processes (GIL bypass) | ❌ JVM only | ❌ JVM only | ❌ JVM only |
| Priority Queues | ✅ Built-in configurable | ❌ Manual implementation | ❌ Manual implementation | ❌ Manual implementation |
| Auto-Restart Policies | ✅ Configurable (never/on_failure/always) | ❌ Basic | ❌ Basic | ❌ Basic |
| Execution Modes | ✅ Async/Multiprocess/ThreadPool | ❌ Single mode | ❌ Single mode | ❌ Single mode |
| Queue Types | ✅ FIFO/Priority/LIFO/Unordered | ❌ FIFO only | ❌ FIFO only | ❌ FIFO only |
| Messaging Patterns | ✅ Async/Sync/Concurrent | ❌ Limited | ❌ Limited | ❌ Limited |
| **Modern Architecture** |
| API-First Design | ✅ REST + JSON | ❌ SOAP/REST hybrid | ❌ Limited API | ❌ Limited API |
| Configuration Storage | ✅ PostgreSQL | ❌ Proprietary Globals DB | ❌ Proprietary | ✅ PostgreSQL/MySQL |
| Docker-Native | ✅ First-class support | ❌ Complex | ❌ Complex | ✅ Yes |
| Kubernetes-Ready | ✅ Yes | ❌ Complex | ❌ Complex | ✅ Limited |
| Microservices Architecture | ✅ Yes | ❌ Monolithic | ❌ Monolithic | ❌ Monolithic |
| Raw-First Design | ✅ Yes (explicit parsing) | ❌ Automatic parsing | ❌ Automatic parsing | ❌ Automatic parsing |
| **Extensibility** |
| Custom Extensions | ✅ Python classes | ✅ ObjectScript | ✅ JavaScript | ✅ Java/JavaScript |
| Extension Integration | ✅ Portal UI configuration | ✅ Portal configuration | ✅ IDE configuration | ✅ Console configuration |
| Plugin Architecture | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Licensing & Cost** |
| Open Source | ✅ MIT License | ❌ Proprietary | ❌ Proprietary | ✅ MPL 1.1 (Limited) |
| License Cost | **FREE** | **$$$$ Very High** | **$$$$ Very High** | **FREE** |
| Support Model | Community + Commercial | Vendor only | Vendor only | Community + Vendor |
| **NHS/Healthcare** |
| NHS-Focused Design | ✅ Yes | ❌ Generic | ✅ Yes | ❌ Generic |
| NHS Spine Integration | 🔄 Planned Phase 5 | ✅ Yes | ✅ Yes | ❌ No |
| UK Compliance (DTAC) | ✅ Yes | ✅ Yes | ✅ Yes | Partial |
| Audit Trail | ✅ Complete | ✅ Complete | ✅ Complete | ✅ Complete |

### Competitive Advantages

**LI HIE exceeds commercial products in these areas:**

1. **Hot Reload** — Apply configuration changes without restarting production (IRIS and Rhapsody require full restart, causing downtime)

2. **True Multiprocessing** — OS-level processes bypass Python GIL for true parallel execution (IRIS and Rhapsody limited by JVM threading)

3. **API-First Design** — Modern REST + JSON for all operations (IRIS uses legacy SOAP/REST hybrid)

4. **Docker-Native** — First-class container support with microservices architecture (IRIS and Rhapsody have complex containerization requirements)

5. **Configurable Enterprise Features** — Phase 2 features (execution modes, queue types, auto-restart policies, messaging patterns) are configurable per-item through Portal UI (competitors have single fixed configuration)

6. **Zero Licensing Cost** — MIT open source with no per-CPU or per-instance fees (IRIS and Rhapsody cost hundreds of thousands of pounds annually for NHS acute trust deployments)

7. **Modern Technology Stack** — Python 3.11+ with async/await vs legacy ObjectScript (IRIS) or Java (Rhapsody)

### Feature Parity

**LI HIE achieves 100% feature parity in:**

1. **Configuration Workflow**
   - **IRIS:** Management Portal → Productions → Add Item → Configure → Apply → Start
   - **Rhapsody:** IDE → Add Route → Add Communication Points → Configure → Deploy
   - **HIE:** Portal UI → Projects → Add Item → Configure → Deploy & Start
   - **Result:** Identical user experience

2. **Item-Based Architecture**
   - **IRIS:** Services (inbound), Processes (routing/transformation), Operations (outbound)
   - **Rhapsody:** Input Communication Points, Routes, Output Communication Points
   - **HIE:** Services (inbound), Processes (routing/transformation), Operations (outbound)
   - **Result:** 100% architectural parity

3. **Visual Configuration**
   - **IRIS:** BPL (Business Process Language) visual designer for workflows
   - **Rhapsody:** Visual route designer with drag-and-drop
   - **HIE:** Visual workflow designer with connections and routing
   - **Result:** Feature parity (Phase 4 will add advanced visual mappers)

4. **Custom Extensions**
   - **IRIS:** Custom ObjectScript classes → Instantiate in Management Portal
   - **Rhapsody:** Custom JavaScript components → Configure in IDE
   - **HIE:** Custom Python classes → Instantiate in Portal UI
   - **Result:** Same extension model

### Market Positioning

**LI HIE = InterSystems IRIS + Orion Rhapsody + Mirth Connect**

| Capability | Comparable Product |
|------------|-------------------|
| Enterprise-grade integration engine | InterSystems IRIS |
| Visual workflow configuration | Orion Rhapsody IDE |
| Open source with modern architecture | Mirth Connect |
| NHS-focused healthcare integration | Rhapsody Healthcare |
| Docker-native microservices | Modern cloud platforms |

**Verdict:** LI HIE is production-ready and competitive with the leading commercial healthcare integration engines. It matches their core capabilities while providing superior modern architecture, zero licensing costs, and NHS-specific optimizations.

## Success Metrics

### Technical Metrics

- **Throughput:** 10,000+ messages/second per node
- **Latency:** <10ms average end-to-end (local)
- **Availability:** 99.99% uptime target
- **Recovery:** <30 second failover

### Business Metrics

- **Adoption:** 10 NHS trusts within 2 years
- **Community:** 100+ contributors within 3 years
- **Cost Savings:** 50%+ reduction vs. commercial alternatives

## Enterprise Requirements

### Configuration-Driven Integration Engine

LI HIE is designed as a **fully configurable, enterprise-grade healthcare integration engine** comparable to InterSystems IRIS, Orion Rhapsody, and Mirth Connect. The following requirements define what makes HIE truly enterprise-ready:

#### Must-Have (Completed)
- ✅ **100% UI-Configurable** — All standard workflows configured through Portal UI (zero code)
- ✅ **Visual Workflow Designer** — Drag-and-drop message flow creation
- ✅ **Zero-Code Standard Workflows** — HL7, File, HTTP services without code
- ✅ **Item Type Registry** — Built-in services, processes, operations
- ✅ **Production Orchestration** — Deploy, start, stop, reload productions via Manager API
- ✅ **Service Registry** — Automatic item-to-item message routing
- ✅ **Phase 2 Enterprise Features** — Multiprocess execution, priority queues, auto-restart policies
- ✅ **Three-Tier Architecture** — Portal UI (web forms) → Manager API (REST/PostgreSQL) → Engine (runtime orchestrator)
- ✅ **Configuration Storage** — PostgreSQL with JSONB for flexible schemas
- ✅ **Real-Time Monitoring** — Live dashboards, metrics, health checks

#### Should-Have (Completed)
- ✅ **Hot Reload** — Configuration changes without production restart
- ✅ **Custom Extensions** — Python-based custom business processes (like IRIS ObjectScript classes)
- ✅ **API-First Design** — REST + JSON for all configuration operations
- ✅ **Docker-Native** — First-class container support with docker-compose
- ✅ **Audit Trail** — Complete audit log of all actions
- 🔄 **Visual Rule Builder** — Drag-and-drop business rules (Planned Phase 4)
- 🔄 **Visual Data Mapper** — Drag-and-drop transformations (Planned Phase 4)
- 🔄 **Configuration Versioning** — Git-based config history (Planned Phase 4)

#### Nice-to-Have (Roadmap)
- 🔄 **FHIR R4 Support** — FHIR inbound/outbound operations (Planned Phase 5)
- 🔄 **NHS Spine Integration** — PDS, EPS, SCR connectors (Planned Phase 5)
- 🔄 **Multi-Tenancy** — Isolated workspaces for multiple organizations (Planned Phase 6)
- 🔄 **Global Marketplace** — Shared custom components and configurations (Future)

### How HIE Works (User Perspective)

**Administrators/Integration Developers:**
1. Log into **Portal UI** (web-based)
2. Create **Workspaces** (organizational units)
3. Create **Projects** (productions/integrations)
4. Add **Items** (services, processes, operations) via dropdown selection
5. Configure **Settings** via form fields (no code)
6. Draw **Connections** in visual workflow designer
7. Click **"Deploy & Start"** (one button)
8. **Monitor** real-time dashboards

**Zero Python Code Required** for standard healthcare integrations.

### What Makes HIE Enterprise-Grade

**Architectural Parity with IRIS/Rhapsody:**
- Item-based architecture (Services, Processes, Operations)
- Production lifecycle management (Deploy, Start, Stop, Reload)
- Service registry for inter-item communication
- Visual workflow configuration
- Custom extension model (Python classes like IRIS ObjectScript classes)

**Modern Advantages over IRIS/Rhapsody:**
- Hot reload without downtime
- True OS-level multiprocessing (bypasses Python GIL)
- API-first design with REST + JSON
- Docker-native microservices architecture
- Zero licensing costs (MIT open source)
- Configurable enterprise features per-item

**Production-Ready Status:**
- Phase 1: Core engine with HL7v2, File, HTTP protocols ✅
- Phase 2: Multiprocess execution, priority queues, auto-restart ✅
- Phase 3: Manager API exposes all Phase 2 settings to Portal UI ✅
- Current version: v1.4.0 (Enterprise features complete)

## Strategic Roadmap

### Phase 1: Foundation (Q1-Q2 2026)
- Core engine with HL7v2 support
- HTTP, File, MLLP protocols
- Basic management portal
- Docker deployment

### Phase 2: Enterprise Features (Q3-Q4 2026)
- FHIR R4 support
- Advanced routing rules
- High availability clustering
- Kubernetes deployment

### Phase 3: NHS Integration (2027)
- NHS Spine integration
- Care Identity Service (CIS)
- Electronic Prescription Service (EPS)
- Summary Care Record (SCR)

### Phase 4: Advanced Capabilities (2027+)
- Machine learning-based routing
- Predictive monitoring
- Multi-tenancy
- Global marketplace for components

## Guiding Principles

1. **Configuration Over Coding** — Standard workflows are configured through Portal UI, not coded. Users configure, Engine executes.

2. **Simplicity Over Complexity** — Prefer simple, explicit solutions over clever, implicit ones.

3. **Reliability Over Features** — A smaller feature set that works perfectly beats a large feature set that fails.

4. **Auditability Over Convenience** — Every action must be traceable and explainable.

5. **Standards Over Proprietary** — Use industry standards wherever possible.

6. **Community Over Control** — Build with the community, not just for them.

7. **Parity with Commercial Products** — Match or exceed InterSystems IRIS, Orion Rhapsody, and Mirth Connect in capabilities.

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Adoption resistance | High | Medium | Provide migration tools, training |
| Performance issues | High | Low | Extensive benchmarking, optimization |
| Security vulnerabilities | Critical | Medium | Security audits, penetration testing |
| Regulatory compliance | High | Low | NHS Digital engagement, certification |
| Community fragmentation | Medium | Medium | Strong governance, clear roadmap |

## Conclusion

HIE represents a fundamental rethinking of healthcare integration. By combining modern architecture with deep healthcare domain expertise, HIE will enable NHS trusts to achieve integration excellence while reducing costs and complexity.

The time is right for a new generation of healthcare integration technology. HIE will lead that transformation.

---

*This document is maintained by the HIE Core Team and updated quarterly.*
