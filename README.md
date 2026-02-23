# OpenLI HIE — The First GenAI-Native Healthcare Integration Engine

[![License: Dual](https://img.shields.io/badge/License-AGPL%20v3%20%2F%20Commercial-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.9.7-green.svg)](RELEASE_NOTES.md)

**Natural language IS the development language.**

OpenLI HIE is not an integration engine with AI bolted on. It is an integration engine where English (or any human language) is the only language a developer needs to design, build, test, deploy, monitor, debug, modify, and roll back healthcare integrations — because the AI agent understands all of it.

> **© 2026 Lightweight Integration Ltd, UK** — Dual licensed under AGPL-3.0 (community) and Commercial license. See [LICENSE](LICENSE) for details.

**Version:** 1.9.7 | **License:** AGPL-3.0 / Commercial Dual License | **Last Updated:** February 2026

---

## The Problem We Solve

Every NHS trust runs dozens of clinical systems — PAS, EPR, RIS, PACS, Labs, Pharmacy — that need to exchange HL7, FHIR, and other healthcare messages reliably, 24/7. Today, building and maintaining these integrations requires:

- **Weeks of specialist training** on HL7 segment structure, MLLP transport, routing rule syntax, and vendor-specific configuration
- **Expensive proprietary licenses** — InterSystems IRIS, Rhapsody, and similar engines cost hundreds of thousands of pounds annually
- **Scarce integration engineers** who understand both the clinical data model and the technical implementation
- **Vendor lock-in** to aging architectures built before containers, APIs, and cloud-native deployment existed

## Our Answer

```
Developer says:
  "Build an ADT integration from Cerner PAS on port 5001
   to RIS on 10.0.1.50:5002 and EPR on 10.0.1.60:5003.
   Route A01 admissions and A03 discharges to both.
   Route A02 transfers to RIS only."

Time to first integration: minutes — not weeks.
```

The AI agent translates this into the correct HL7 TCPService, routing engine, MLLP operations, connections, and routing rules — without the developer ever touching a configuration form, writing a line of code, or reading an API doc.

---

## What Makes OpenLI Different

### Natural Language as a Development Language

This is the foundational innovation. Every stage of the integration lifecycle is achievable through conversation:

| Lifecycle Stage | What You Say | What the Agent Does |
|----------------|-------------|---------------------|
| **Design** | "I need an ADT feed from PAS to RIS and EPR" | Proposes architecture with services, processes, operations |
| **Build** | "Use MLLP on port 5001, route A01/A02/A03" | Creates all items, connections, routing rules |
| **Test** | "Send a test ADT A01 message" | Crafts and sends a valid HL7 message, shows result |
| **Deploy** | "Deploy to staging" | Deploys directly (or creates approval for production) |
| **Monitor** | "How many messages processed today?" | Queries metrics and presents dashboard data |
| **Debug** | "Why did message 47 fail?" | Traces message through the routing topology |
| **Modify** | "Change the RIS port to 5004" | Updates the MLLP operation configuration |
| **Rollback** | "Revert to yesterday's config" | Restores from auto-snapshot, remaps connections |

### Enterprise-Grade Guardrails

Natural language development is only safe for production NHS environments because of six guardrails that operate transparently:

| Guardrail | What It Does |
|-----------|-------------|
| **GR-1: Role-Based Access** | 7-role RBAC hierarchy filters available tools before the AI sees them |
| **GR-2: Audit Logging** | Every AI tool call is logged with PII sanitisation (NHS numbers, postcodes stripped) |
| **GR-3: Approval Workflows** | Production deployments require Clinical Safety Officer or Admin sign-off |
| **GR-4: Config Snapshots** | Every deploy auto-snapshots current config; one-command rollback to any version |
| **GR-5: Tenant Isolation** | Multi-tenant architecture — each NHS Trust sees only their own data |
| **GR-6: Namespace Enforcement** | Core engine classes (`li.*`) are read-only; developers write to `custom.*` only |

### Where We Lead the Market

| Capability | OpenLI HIE | InterSystems IRIS | Rhapsody | Mirth Connect |
|-----------|-----------|-------------------|----------|---------------|
| **NL Development** | English is the dev language | None | None | None |
| **AI Agent Integration** | Built-in (Claude, Codex) | None | None | None |
| **Hot Reload** | Config changes without restart | Requires restart | Requires restart | Requires restart |
| **True Multiprocessing** | OS processes (GIL bypass) | JVM threading | JVM threading | JVM threading |
| **Docker-Native** | First-class microservices | Complex | Complex | Limited |
| **API-First** | REST + JSON everywhere | SOAP/REST hybrid | Limited API | Limited API |
| **Open Source** | AGPL-3.0 / Commercial dual license | $$$$$ | $$$$$ | MPL (limited) |
| **NHS-First Design** | DCB0129/0160 compliance built-in | Generic | Generic | Generic |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        OpenLI HIE Platform                           │
│                                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │  Portal   │  │  Agent       │  │  Manager    │  │  Engine      │ │
│  │  (React)  │→ │  Runner      │→ │  API        │→ │  (LI Core)   │ │
│  │  Next.js  │  │  Claude/Codex│  │  REST+Auth  │  │  Productions │ │
│  └──────────┘  └──────────────┘  └─────────────┘  └──────────────┘ │
│        │              │                 │                 │          │
│  ┌─────┴──────────────┴─────────────────┴─────────────────┴───────┐ │
│  │                    PostgreSQL + Redis                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

**Five microservices**, each independently deployable:

| Service | Role | Port |
|---------|------|------|
| **Portal** | React/Next.js management UI — dashboards, topology, config, agents | 9303 |
| **Agent Runner** | GenAI agent execution — Claude & Codex, RBAC, hooks, rate limiting | 9340 |
| **Manager API** | REST API — workspaces, projects, items, connections, auth, deploy | 9302 |
| **Engine** | LI runtime — message routing, MLLP/HTTP/File I/O, transformations | 9300 |
| **Prompt Manager** | Template/skill store, audit logging, approval workflows | 9341 |

### Core Concepts

- **Workspace** — A tenant-scoped namespace containing projects (maps to an NHS Trust)
- **Project** — A production configuration: items + connections + routing rules
- **Item** — A runtime component: Service (inbound), Process (routing/transform), Operation (outbound)
- **Connection** — A message flow link between two items
- **Routing Rule** — A conditional filter that directs messages to target items

### Design Principles

1. **Raw-first, parse-on-demand** — Messages preserved in original form; parsing only when explicitly required
2. **Explicit over implicit** — No hidden transformations; every routing decision is configured and auditable
3. **Configuration-driven** — All workflows configurable through Portal UI or natural language; zero code for standard integrations
4. **Vendor-neutral core** — Clean abstractions; legacy engine concepts mapped via adapters, not core types

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An Anthropic API key (for AI agent features)

### 1. Start the Platform

```bash
git clone https://github.com/zhongli1990/hie.git
cd HIE

# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Start the full stack
docker compose up -d --build

# Wait for all services to be healthy (~60s)
docker compose ps
```

### 2. Access the Platform

| Service | URL |
|---------|-----|
| Portal (UI) | http://localhost:9303 |
| Manager API | http://localhost:9302/api/health |
| Agent Runner | http://localhost:9340/health |
| Prompt Manager | http://localhost:9341/health |
| Adminer (DB) | http://localhost:9330 |
| Redis Commander | http://localhost:9331 |

### 3. Login with Demo Users

All demo users belong to **St Thomas' Hospital NHS Foundation Trust** (STH).

| Persona | Email | Password | Can Do |
|---------|-------|----------|--------|
| **System Admin** | `admin@hie.nhs.uk` | `Admin123!` | Everything across all tenants |
| **IT Director** | `trust.admin@sth.nhs.uk` | `Demo12345!` | Full access within STH |
| **Integration Developer** | `developer@sth.nhs.uk` | `Demo12345!` | Design, Build, Test — staging deploy |
| **Clinical Safety Officer** | `cso@sth.nhs.uk` | `Demo12345!` | Review, Approve/Reject deployments |
| **Systems Operator** | `operator@sth.nhs.uk` | `Demo12345!` | Deploy, Start, Stop, Rollback |
| **Service Desk** | `viewer@sth.nhs.uk` | `Demo12345!` | Read-only monitoring |
| **IG Auditor** | `auditor@sth.nhs.uk` | `Demo12345!` | Read-only + audit log access |

---

## Protocol & Format Support

| Protocol | Status | Transport |
|----------|--------|-----------|
| **HL7 v2.x** | Production | MLLP, HTTP, File |
| **FHIR R4** | Planned | HTTP/REST |
| **DICOM** | Planned | TCP |
| **HTTP/REST** | Production | HTTP |
| **File I/O** | Production | Filesystem |
| **Database** | Production | PostgreSQL, ODBC |
| **Custom** | Extensible | Python classes in `custom.*` namespace |

---

## Testing

All tests run inside Docker containers — never on the host.

```bash
# Start the stack
docker compose up -d --build

# Run all E2E tests (recommended)
make test-e2e

# Run specific test suites
make test-e2e-smoke      # 5 tests  — service health & API smoke
make test-e2e-v194       # 38 tests — RBAC, audit, approvals, role alignment
make test-e2e-v195       # 22 tests — snapshots, CRUD, env deploy, rate limiting

# Run unit/integration tests inside the engine container
docker compose exec -T hie-engine pytest -q tests/unit
docker compose exec -T hie-engine pytest -q tests/integration
```

See [Testing Guide](docs/reference/TESTING_GUIDE.md) for full details.

---

## Project Structure

```
HIE/
├── Portal/                 # React/Next.js Management UI
│   ├── src/app/           # Pages: dashboard, projects, agents, admin
│   └── src/components/    # Sidebar, topology viewer, agent workflows
├── Engine/                 # Python Backend
│   ├── core/              # Message model, production runtime, items
│   ├── api/               # Manager API: routes, repositories, models
│   ├── auth/              # JWT auth, RBAC, password policies
│   ├── li/                # LI Engine (IRIS-compatible runtime)
│   ├── items/             # Receivers, processors, senders
│   └── persistence/       # PostgreSQL, Redis, migrations
├── agent-runner/           # GenAI Agent Service
│   └── app/               # Tools, roles, hooks, rate limiter, skills
├── prompt-manager/         # Template & Audit Service
│   └── app/               # Prompts, skills, audit, approvals
├── tests/
│   ├── unit/              # Pure unit tests (no Docker deps)
│   ├── integration/       # In-process component tests
│   ├── li/                # LI Engine subsystem tests
│   └── e2e/               # Docker-network E2E tests (65 tests)
├── scripts/
│   ├── init-db.sql        # Database schema & seed data
│   └── run_e2e_tests.sh   # Docker E2E test runner
├── docs/                   # 30+ architecture, design, and guide documents
├── docker-compose.yml      # Production stack (12 services)
└── docker-compose.dev.yml  # Development stack with hot-reload
```

---

## Documentation

### Start Here

- [Developer & User Guide](docs/guides/DEVELOPER_AND_USER_GUIDE.md) — Quickstart, NHS scenario, custom classes
- [Demo Lifecycle Guide](docs/guides/DEMO_LIFECYCLE_GUIDE.md) — Complete NL integration lifecycle in 5 acts
- [NHS Trust Demo Guide](docs/guides/NHS_TRUST_DEMO_GUIDE.md) — Reference implementation for NHS acute trusts

### Architecture & Design

- [Architecture Overview](docs/architecture/ARCHITECTURE_OVERVIEW.md) — Platform architecture
- [Feature Design: NL Development & RBAC](docs/design/FEATURE_NL_DEVELOPMENT_RBAC.md) — Primary feature design document
- [Product Vision](docs/design/PRODUCT_VISION.md) — Strategic positioning & market analysis
- [Full Documentation Index](docs/INDEX.md) — All 30+ documents

### Releases

- [v1.9.5](docs/releases/RELEASE_NOTES_v1.9.5.md) — Config Snapshots, CRUD Tools, Environment Deploy, Rate Limiting
- [v1.9.4](docs/releases/RELEASE_NOTES_v1.9.4.md) — Unified RBAC, Audit Logging, Approval Workflows, Demo Onboarding
- [v1.8.2](docs/releases/RELEASE_NOTES_v1.8.2.md) — Message Model Metadata, Session Tracking
- [All Releases](docs/INDEX.md#releases)

---

## Inspiration & Lineage

OpenLI HIE draws architectural inspiration from the best enterprise integration engines while reimagining the development experience for the GenAI era:

- **InterSystems IRIS/Ensemble** — The Service/Process/Operation item model, per-leg message header tracing, and production topology concepts inform our core architecture. We preserve the mental model that NHS integration engineers already know, then make it accessible through natural language.

- **Orion Health Rhapsody** — The emphasis on healthcare-specific compliance, clinical safety review workflows, and NHS trust deployment patterns shaped our guardrail design (DCB0129/DCB0160 compliance, approval workflows, PII sanitisation).

- **Mirth Connect** — The open-source model and channel-based message routing demonstrated that enterprise healthcare integration doesn't require proprietary licensing. We extend this principle to the AI development experience itself.

- **Claude & Large Language Models** — The realisation that LLMs can understand healthcare data standards (HL7, FHIR), networking protocols (MLLP, HTTP), and integration architecture patterns (routing, transformation, error handling) well enough to be the primary development interface — not a helper, but the developer's hands.

**The synthesis:** Take the proven enterprise architecture of IRIS, the compliance rigour of Rhapsody, the open-source ethos of Mirth, and make all of it accessible through natural language. The result is an integration engine where the barrier to entry drops from months of specialist training to a conversation in English.

---

## Contributing

OpenLI HIE is open source and welcomes contributions. By contributing, you agree to the Contributor License Agreement (CLA) described in the [LICENSE](LICENSE) file.

See the [Developer Guide](docs/guides/DEVELOPER_AND_USER_GUIDE.md) for setup instructions.

## License

This project is dual-licensed:

- **AGPL-3.0** for organizations with annual revenue below £250,000 — free to use, modify, and distribute under open source terms
- **Commercial License** for organizations with revenue ≥ £250,000 — removes AGPL obligations, includes enterprise support and NHS Trust deployment assistance

See [LICENSE](LICENSE) for full terms including:
- Community License (AGPL-3.0) obligations
- Commercial License pricing tiers (SME / Enterprise / NHS Trust)
- Trademark notice for OpenLI brand
- Contributor License Agreement (CLA)
- Healthcare disclaimer

**© 2026 Lightweight Integration Ltd, UK**

For licensing inquiries: [Zhong@li-ai.co.uk](mailto:Zhong@li-ai.co.uk)

---

*OpenLI HIE — Healthcare Integration Engine. Natural language is the development language.*

*© 2026 Lightweight Integration Ltd. All rights reserved.*
