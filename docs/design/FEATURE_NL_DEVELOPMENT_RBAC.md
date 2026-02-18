# Feature Design Proposal: The First GenAI-Native Integration Engine

**Document:** OpenLI HIE Feature Design — Natural Language Development Platform
**Version:** 1.2
**Date:** 2026-02-13
**Status:** Phases 1-4 IMPLEMENTED (v1.9.4) — Phase 5 Pending
**Target Release:** v2.0.0

---

## Table of Contents

1. [Product Vision: The First GenAI-Native Integration Engine](#1-product-vision)
2. [Feature Requirements: NL Development Lifecycle (FR-1 to FR-14)](#2-feature-requirements-nl-development-lifecycle)
3. [What Exists Today vs What's Needed](#3-what-exists-today-vs-whats-needed)
4. [Current Architecture (What We Have)](#4-current-architecture-what-we-have)
5. [**Design: NL Development Experience (Primary Feature)**](#5-design-nl-development-experience-primary-feature)
6. [Design: Guardrails — Role-Gated Tool Access](#6-design-guardrails--role-gated-tool-access)
7. [Design: Audit Logging](#7-design-audit-logging)
8. [Design: Approval Workflows](#8-design-approval-workflows)
9. [Design: Configuration Snapshots & Rollback](#9-design-configuration-snapshots--rollback)
10. [Implementation Phases & Priority](#10-implementation-phases--priority)
11. [Critical File Inventory](#11-critical-file-inventory)
12. [Verification & Acceptance Criteria](#12-verification--acceptance-criteria)
13. [Open Questions & Design Decisions](#13-open-questions--design-decisions)
14. [Risks & Mitigations](#14-risks--mitigations)

---

## 1. Product Vision

### The First GenAI-Native Integration Engine

OpenLI HIE is not an integration engine with AI bolted on. It is an integration engine where **natural language IS the development language**. English (or any human language) is the only language a developer needs to design, build, test, deploy, monitor, debug, modify, and roll back healthcare integrations.

**No HL7 syntax to memorise. No class hierarchies to navigate. No configuration forms to fill. No API documentation to read. No code to write.**

A developer who speaks English but knows nothing about HL7, FHIR, MLLP, InterSystems IRIS, class registries, or REST APIs can build and manage production NHS healthcare integrations — because the AI agent understands all of it.

### What This Means

**Before (every other integration engine):**
```
Developer needs to know:
  → HL7 v2.x message structure (MSH, PID, PV1, OBR segments)
  → MLLP transport protocol (port config, ACK handling, ReplyCodeActions syntax)
  → Class hierarchy (EnsLib.HL7.Service.TCPService vs li.hosts.hl7.HL7TCPService)
  → Routing rule syntax ({MSH-9.1} = "ADT" AND {MSH-9.2} IN ("A01","A02"))
  → Configuration objects (Services → Processes → Operations → Connections → Rules)
  → Deployment lifecycle (deploy → start → monitor → stop → rollback)
  → NHS compliance standards (DCB0129, DCB0160, ITK3, MESH, Spine)

Time to first integration: weeks of training + days of configuration
```

**After (OpenLI HIE with NL Development):**
```
Developer says:
  "Build an ADT integration from Cerner PAS on port 5001
   to RIS on 10.0.1.50:5002 and EPR on 10.0.1.60:5003.
   Route A01 admissions and A03 discharges to both.
   Route A02 transfers to RIS only."

Time to first integration: minutes
```

### Design Principle

> **Natural language first, guardrails second.** The primary feature is that every lifecycle stage works through natural language. RBAC, audit, and approvals are guardrails that make this safe for NHS production — they enable the NL development experience, they are not the experience itself.

---

## 2. Feature Requirements: NL Development Lifecycle

> **These are the primary feature requirements.** Every requirement below represents a lifecycle stage that must be achievable entirely through natural language conversation with the AI agent.

| ID | Lifecycle Stage | Natural Language Input (Example) | Engine Action |
|----|----------------|----------------------------------|--------------|
| **FR-1** | **Design** | "I need an ADT integration from Cerner PAS to RIS and EPR" | AI understands HL7 ADT message types, identifies required services/processes/operations, proposes architecture with a visual topology |
| **FR-2** | **Build** | "Build it with MLLP on port 5001, route A01/A02/A03 to RIS on 10.0.1.50:5002 and EPR on 10.0.1.60:5003" | AI creates all items (service, routing engine, operations), connections, and routing rules — no code, no UI forms, no config files |
| **FR-3** | **Configure** | "Set the AckMode to Application and add ReplyCodeActions for error handling" | AI modifies host/adapter settings using correct HL7 syntax (`:?R=F,:?E=S,:~=S,:?A=C,:*=S`) |
| **FR-4** | **Test** | "Test it with a sample ADT A01 message for patient John Smith" | AI generates valid HL7 test message, sends via `hie_test_item`, reports routing result, shows which targets received it |
| **FR-5** | **Review** | "Run a clinical safety review on this integration" | AI executes 32-item DCB0129/DCB0160 checklist, flags risks, produces structured compliance report |
| **FR-6** | **Compliance** | "Check NHS compliance for this route" | AI validates against NHS Digital standards (ITK3, MESH, Spine, HL7 UK Edition, FHIR UK Core) |
| **FR-7** | **Deploy** | "Deploy this to staging" / "Deploy to production" | AI deploys configuration to engine, starts production, confirms all items running |
| **FR-8** | **Monitor** | "What's the status of the ADT integration?" | AI reports runtime status, queue depths, error rates, per-item states, uptime |
| **FR-9** | **Debug** | "Why are messages failing on the RIS outbound?" | AI checks project status, examines error queues, traces message path, diagnoses root cause, suggests fix |
| **FR-10** | **Modify** | "Add pathology results routing to the Lab system on port 5004" | AI adds new operation, connection, and routing rule to existing live project — no rebuild |
| **FR-11** | **Extend** | "Create a custom validation process that checks NHS number format before routing" | AI creates `custom.nhs.NHSNumberValidator` class file, writes the Python code, registers it via `hie_reload_custom_classes`, wires it into the route |
| **FR-12** | **Rollback** | "Roll back the last deployment, something is wrong" | AI restores previous configuration snapshot, restarts with known-good config |
| **FR-13** | **Discover** | "What item types are available?" / "Show me the core HL7 classes" | AI lists available classes from ClassRegistry with descriptions, capabilities, and usage examples |
| **FR-14** | **Teach** | "Explain how HL7 routing rules work in this system" | AI explains using actual platform concepts, with concrete examples from the user's own workspace |

### What Makes This GenAI-Native (Not GenAI-Assisted)

| GenAI-Assisted (what others do) | GenAI-Native (what OpenLI HIE does) |
|--------------------------------|-------------------------------------|
| AI suggests config, human types it into forms | AI creates config directly via tools — no forms |
| AI generates code, human reviews and deploys | AI writes, registers, and wires custom classes |
| AI answers questions about docs | AI operates the engine: build, deploy, test, monitor, rollback |
| Human drives, AI assists | **Human describes intent, AI executes the full lifecycle** |
| AI is a feature of the product | **AI is the development environment** |

### Guardrail Requirements (Supporting)

These guardrails make the NL development lifecycle safe for NHS production. They are supporting requirements, not primary features:

| ID | Guardrail | Purpose | Enables |
|----|-----------|---------|---------|
| **GR-1** | Role-Based Tool Access | Ensure each user role can only trigger appropriate lifecycle stages | FR-7 (Deploy) is safe — developers can't deploy to production without approval |
| **GR-2** | Audit Logging | Record every AI action for NHS compliance (DCB0129/DCB0160) | FR-1–FR-14 are auditable and traceable |
| **GR-3** | Approval Workflows | Human review gate before production deployment | FR-7 (Deploy to production) requires CSO sign-off |
| **GR-4** | Configuration Snapshots | Immutable record of every deployment state | FR-12 (Rollback) has something to roll back to |
| **GR-5** | Tenant Isolation | Multi-tenant workspace boundaries | All FRs operate within correct tenant scope |
| **GR-6** | Namespace Enforcement | `custom.*` only for developer-written classes | FR-11 (Extend) cannot corrupt core platform classes |

---

## 3. What Exists Today vs What's Needed

| Feature Requirement | Status Today | What's Needed |
|-------------------|-------------|--------------|
| FR-1 Design | **Working** — AI proposes architecture via skills; QuickStartPanel templates delivered | **DONE** — Phase 1 |
| FR-2 Build | **Working** — 19 HIE tools create all config objects | Already functional |
| FR-3 Configure | **Working** — `hie_create_item` accepts adapter/host settings | Already functional |
| FR-4 Test | **Working** — `hie_test_item` sends test messages | Already functional |
| FR-5 Review | **Working** — `clinical-safety-review` skill runs 32-item checklist | Already functional |
| FR-6 Compliance | **Working** — `nhs-compliance-check` skill validates standards | Already functional |
| FR-7 Deploy | **SAFE** — RBAC blocks developer deploy (GR-1), approval workflow gates production (GR-3), audit trail records all actions (GR-2) | **DONE** — Phase 1 (RBAC) + Phase 3 (Audit) + Phase 4 (Approvals) |
| FR-8 Monitor | **Working** — `hie_project_status` returns runtime metrics | Already functional |
| FR-9 Debug | **Partial** — status available but no message trace integration | Future: integrate with Visual Trace |
| FR-10 Modify | **IMPLEMENTED** — `hie_update_item`, `hie_update_connection`, `hie_update_routing_rule` + delete tools | **DONE** — v1.9.5 |
| FR-11 Extend | **Working + guarded** — `write_file` + `hie_reload_custom_classes` + GR-6 namespace enforcement | **DONE** — Phase 1 |
| FR-12 Rollback | **IMPLEMENTED** — `hie_rollback_project` tool + auto-snapshot on deploy + `ProjectVersionRepository` | **DONE** — v1.9.5 (GR-4) |
| FR-13 Discover | **Working** — `hie_list_item_types` + ClassRegistry | Already functional |
| FR-14 Teach | **Working** — system prompt includes full architecture context | Already functional |
| GR-1 RBAC | **IMPLEMENTED** — 7-role hierarchy with DB-to-agent role mapping, Layer 1 tool filtering + Layer 2 hook validation | **DONE** — Phase 1 + Phase 2 (role alignment) |
| GR-2 Audit | **IMPLEMENTED** — `AuditLog` model, `/audit` API with PII sanitisation, Portal audit viewer with stats/filters/CSV export | **DONE** — Phase 3, commit `f75976a` |
| GR-3 Approvals | **IMPLEMENTED** — `DeploymentApproval` model, `/approvals` API, Portal approval UI with approve/reject, hook intercept on production deploy | **DONE** — Phase 4, commit `f75976a` |
| GR-4 Snapshots | **IMPLEMENTED** — Auto-snapshot on deploy, `ProjectVersionRepository`, 3 version/rollback API endpoints, 3 agent tools | **DONE** — v1.9.5 (Phase 5) |
| GR-5 Tenant Isolation | **IMPLEMENTED** — JWT tenant_id extracted and passed through hook context | **DONE** — Phase 1 |
| GR-6 Namespace Enforcement | **IMPLEMENTED** — `is_class_name_writable()` + `is_file_path_writable()` enforce `custom.*` only for non-admin roles | **DONE** — Phase 1 |

**Key takeaway:** 12 of 14 feature requirements implemented. **All 6 guardrails fully implemented.** Remaining: FR-3 (configure — partial, update tools now available), FR-9 (debug — partial, status available but no message trace integration).

### Gap Analysis: Production Readiness Status

| Gap | Status | Resolution |
|-----|--------|-----------|
| ~~**No permission boundaries**~~ | **RESOLVED** (Phase 1+2) | 7-role RBAC hierarchy with DB-to-agent role mapping, Layer 1+2 defense-in-depth enforcement. Developers cannot deploy/stop production. |
| ~~**No approval workflows**~~ | **RESOLVED** (Phase 4) | `DeploymentApproval` model + `/approvals` API + Portal approval UI. Developers request → CSO/Admin approve/reject with notes. |
| ~~**No audit trail**~~ | **RESOLVED** (Phase 3) | `AuditLog` model + `/audit` API with PII sanitisation (NHS numbers, postcodes). Portal audit viewer with stats, filters, CSV export. |
| **No rollback** | **Pending** (Phase 5) | Needs `ConfigSnapshot` model + `hie_rollback_project` tool. Pre/post deploy snapshots not yet implemented. |
| **No cost/usage controls** | **Deferred** | Rate limiting defined but not enforced. Separate effort — not an NHS compliance blocker. |

## 4. Current Architecture (What We Have)

> **Design Highlight:** The existing codebase already provides 80% of the infrastructure needed. 10 of 14 feature requirements already work. This proposal extends existing mechanisms to add the guardrails that unlock production readiness.

### 4.1 Existing Components

| Component | Location | Capability |
|-----------|----------|-----------|
| **19 HIE Tools** | `agent-runner/app/tools.py` | Full CRUD for workspaces, projects, items, connections, routing rules, deployment lifecycle, testing, class registry |
| **4 Standard Tools** | `agent-runner/app/tools.py` | `read_file`, `write_file`, `list_files`, `bash` |
| **Skills System** | `agent-runner/app/skills.py` + `skills/*/SKILL.md` | Loads skills with YAML frontmatter including `allowed-tools` field; builds system prompt with full HIE context |
| **Hooks System** | `agent-runner/app/hooks.py` | Pre/post tool-use validation: blocks dangerous bash patterns, path traversal, SQL injection patterns, NHS number exposure |
| **Agent Loop** | `agent-runner/app/agent.py` | Streaming Claude agent with tool execution, hook integration, SSE events |
| **DB Skills** | `prompt-manager/app/models.py` (Skill model) | Versioned skills with `allowed_tools`, `tenant_id`, `scope`, `is_published` |
| **JWT Auth** | `prompt-manager/app/auth.py` | `CurrentUser` with `user_id`, `tenant_id`, `role` (admin/user); shared `JWT_SECRET_KEY` |
| **Codex Runner** | `codex-runner/src/server.ts` | OpenAI Codex agent with AGENTS.md context injection, skills loading |
| **ClassRegistry** | HIE Manager | `li.*` protected, `custom.*` developer-extensible, hot-reload via `hie_reload_custom_classes` |
| **5 Platform Skills** | `agent-runner/skills/` | hl7-route-builder, fhir-mapper, clinical-safety-review, nhs-compliance-check, integration-test |

### 4.2 Existing Skill `allowed-tools` Example

From `agent-runner/skills/hl7-route-builder/SKILL.md`:
```yaml
---
name: hl7-route-builder
description: Build end-to-end HL7 integration routes for OpenLI HIE
allowed-tools: hie_create_workspace, hie_create_project, hie_create_item, hie_create_connection, hie_create_routing_rule, hie_deploy_project, hie_start_project, hie_test_item, hie_project_status, hie_list_item_types, hie_list_workspaces, hie_list_projects, hie_get_project
---
```

This is the foundation for RBAC: **skills already declare which tools they need**. We add role-based filtering on top.

### 4.3 Existing Hooks Pattern

From `agent-runner/app/hooks.py`:
```python
async def pre_tool_use_hook(input_data, tool_use_id, context):
    # Already blocks: dangerous bash patterns, path traversal, SQL injection
    # We extend this with: role-based tool permission checks
```

### 4.4 Existing JWT Auth Pattern

From `prompt-manager/app/auth.py`:
```python
class CurrentUser:
    def __init__(self, user_id, tenant_id=None, role="user"):
        # role is already in the JWT payload
        # We reuse this exact pattern in agent-runner
```

---

## 5. Design: NL Development Experience (Primary Feature)

> **This section defines the primary feature.** Everything in Sections 6-9 exists to make this section safe for production.

### 5.1 The AI Agent IS the Development Environment

Today's integration engines require developers to navigate complex UIs, write configuration files, understand vendor-specific class hierarchies, and read protocol specifications. OpenLI HIE eliminates all of this.

The AI agent has:
- **Full domain knowledge** — System prompt includes HIE architecture, class namespace conventions, HL7 message structures, FHIR resource types, routing rule syntax, ReplyCodeActions syntax
- **19 HIE tools** — Direct API access to create workspaces, projects, items, connections, routing rules, and manage the full deployment lifecycle
- **5 platform skills** — Pre-built expertise for HL7 route building, FHIR mapping, clinical safety review, NHS compliance checks, and integration testing
- **Custom class authoring** — Can write Python classes in the `custom.*` namespace, register them via hot-reload, and wire them into live integrations

The developer's only interface is a chat window. They describe what they want. The AI executes.

### 5.2 NL Workflow: End-to-End Example

This example demonstrates FR-1 through FR-8 in a single conversation:

```
DEVELOPER: I need an ADT integration. Cerner PAS sends ADT messages on port
           5001. I need A01 admissions and A03 discharges to go to both RIS
           (10.0.1.50:5002) and EPR (10.0.1.60:5003). A02 transfers go to
           RIS only.

AI AGENT:  I'll build this integration for you. Let me create the project
           and all the components.

           [Creates workspace "Cerner_PAS_Integration" if needed]
           [Creates project "ADT_Route"]
           [Creates service: Cerner.PAS.Receiver (HL7TCPService, port 5001)]
           [Creates process: ADT.Router (HL7RoutingEngine)]
           [Creates operation: RIS.Sender (HL7TCPOperation, 10.0.1.50:5002)]
           [Creates operation: EPR.Sender (HL7TCPOperation, 10.0.1.60:5003)]
           [Creates connections: Receiver→Router, Router→RIS, Router→EPR]
           [Creates routing rule: A01+A03 → RIS, EPR]
           [Creates routing rule: A02 → RIS only]

           Done. I've created:
           • 1 inbound service (MLLP port 5001)
           • 1 routing engine with 2 rules
           • 2 outbound operations
           • 4 connections

           Want me to deploy to staging and run a test?

DEVELOPER: Yes, deploy and test with a sample A01.

AI AGENT:  [Deploys project to staging]
           [Sends test ADT A01 message]

           Test results:
           ✓ Message received on port 5001
           ✓ Routed to RIS.Sender — ACK received
           ✓ Routed to EPR.Sender — ACK received
           ✓ A01 matched rule "Route ADT A01/A03 to RIS and EPR"

           All items running. Queue depths: 0. No errors.

DEVELOPER: Looks good. Can you run a safety review before we go to production?

AI AGENT:  [Runs clinical-safety-review skill — 32-item DCB0129 checklist]

           Clinical Safety Review — ADT_Route
           ═══════════════════════════════════
           ✓ 28/32 checks passed
           ⚠ 4 advisory items:
             • Consider adding ReplyCodeActions for NACK handling
             • No transform applied — messages forwarded as-is
             • No error queue routing configured
             • No message schema validation on inbound

           Overall: PASS with advisories. Safe for production with
           recommended improvements.

DEVELOPER: Deploy to production.

AI AGENT:  [If developer role → creates approval request]
           Your production deployment request has been submitted.
           A Clinical Safety Officer must approve before it goes live.
           Approval ID: APR-2026-0042
```

### 5.3 Guided Workflow Templates (QuickStartPanel)

For developers who are new to the platform, the Portal provides pre-built natural language templates as clickable cards:

| Card | Pre-filled Prompt | Maps to FRs |
|------|------------------|-------------|
| **Build ADT Integration** | "Build an ADT A01/A02/A03 integration from [source] at [host:port] to [targets] at [host:port]" | FR-1, FR-2 |
| **Build ORM Route** | "Build an ORM O01 order routing integration from [source] to [lab/radiology] systems" | FR-1, FR-2 |
| **Add New Outbound** | "Add a new HL7 outbound operation to [system] at [host:port] in project [name]" | FR-10 |
| **Create Custom Process** | "Create a custom validation process that [description] and wire it into project [name]" | FR-11 |
| **Run Safety Review** | "Run a DCB0129 clinical safety review of project [name]" | FR-5 |
| **Run Integration Tests** | "Run integration tests for project [name] using standard test patients" | FR-4 |
| **Check NHS Compliance** | "Run NHS compliance checks on project [name]" | FR-6 |
| **View Project Status** | "Show the runtime status of project [name]" | FR-8 |
| **Diagnose Issues** | "Why are messages failing on [item name] in project [name]?" | FR-9 |
| **Roll Back Deployment** | "Roll back project [name] to the previous configuration" | FR-12 |

Each card is visible only to roles that have permission to execute the underlying tools.

### 5.4 Skill-Driven Expertise

Platform skills are the AI agent's domain expertise. Each skill contains detailed instructions for a specific healthcare integration task:

| Skill | What It Teaches the AI | Key FR |
|-------|----------------------|--------|
| `hl7-route-builder` | 10-step E2E route creation workflow, class namespace conventions, HL7 message reference, ReplyCodeActions syntax | FR-1, FR-2, FR-3 |
| `fhir-mapper` | FHIR resource mapping, transformation rules, UK Core profiles | FR-2, FR-3 |
| `clinical-safety-review` | DCB0129/DCB0160 compliance, 32-item checklist across 6 categories | FR-5 |
| `nhs-compliance-check` | NHS Digital standards — ITK3, MESH, Spine, HL7 UK Edition | FR-6 |
| `integration-test` | Test levels, HL7 test message templates, standard test patients with synthetic NHS numbers | FR-4 |

**Extensibility:** NHS Trusts can create workspace-level skills (in `.claude/skills/`) that teach the AI about their specific systems, naming conventions, and integration patterns. These override global skills automatically.

---

## 6. Design: Guardrails — Role-Gated Tool Access

> **This section defines the guardrails that make Section 5 safe for production.** The AI agent only sees tools its role permits. Two enforcement layers (tool filtering + hook validation) ensure defense-in-depth.

### 6.1 Role Hierarchy

```
Platform Admin (full access, all tenants)
  └── Tenant Admin (full access within own tenant)
       ├── Integration Developer (build + test, deploy to staging only)
       ├── Clinical Safety Officer (review + approve, read + test)
       ├── Operator (deploy + start/stop + monitor, cannot create)
       ├── Auditor (read-only + audit log access)
       └── Viewer (read-only monitoring)
```

**DB-to-Agent Role Mapping (Phase 2):**

The database uses NHS-appropriate role names (e.g., `integration_engineer`), while the agent-runner uses functional role keys (e.g., `developer`). The `resolve_agent_role()` function in `roles.py` bridges this gap:

| DB Role (JWT `role` claim) | Agent Role Key | Primary Use Case |
|---|---|---|
| `super_admin` | `platform_admin` | OpenLI platform operators managing the multi-tenant environment |
| `tenant_admin` | `tenant_admin` | NHS Trust IT leads managing their own workspace |
| `integration_engineer` | `developer` | Integration engineers building routes via natural language |
| `clinical_safety_officer` | `clinical_safety_officer` | DCB0129-qualified reviewers approving production deployments |
| `operator` | `operator` | Systems operators: deploy, start/stop, monitor — cannot create items |
| `auditor` | `auditor` | IG auditors: read-only with audit log access |
| `viewer` | `viewer` | Monitoring dashboards, read-only status checks |

### 6.2 Tool Permission Matrix

> **Design Highlight:** This matrix is the single source of truth for all tool access. Review carefully — each cell represents a deliberate design decision.

| Tool | Platform Admin | Tenant Admin | Developer | CSO | Viewer |
|------|:-:|:-:|:-:|:-:|:-:|
| **Workspace Management** |
| `hie_list_workspaces` | all | own tenant | own tenant | own tenant | own tenant |
| `hie_create_workspace` | yes | yes | no | no | no |
| **Project Management** |
| `hie_list_projects` | yes | yes | yes | yes | yes |
| `hie_create_project` | yes | yes | yes | no | no |
| `hie_get_project` | yes | yes | yes | yes | yes |
| **Items, Connections, Rules** |
| `hie_create_item` | yes | yes | yes | no | no |
| `hie_create_connection` | yes | yes | yes | no | no |
| `hie_create_routing_rule` | yes | yes | yes | no | no |
| **Production Lifecycle** |
| `hie_deploy_project` | yes | yes | **staging only** | no | no |
| `hie_start_project` | yes | yes | **staging only** | no | no |
| `hie_stop_project` | yes | yes | **staging only** | no | no |
| `hie_project_status` | yes | yes | yes | yes | yes |
| **Testing & Registry** |
| `hie_test_item` | yes | yes | yes | yes | no |
| `hie_list_item_types` | yes | yes | yes | yes | yes |
| `hie_reload_custom_classes` | yes | yes | yes | no | no |
| **Standard Tools** |
| `bash` | yes | restricted | restricted | no | no |
| `write_file` | yes | `custom.*` only | `custom.*` only | no | no |
| `read_file` | yes | yes | yes | yes | yes |
| `list_files` | yes | yes | yes | yes | yes |

**Key design decisions to review:**

1. **Developer cannot deploy/start/stop production** — Only staging. Production requires CSO approval (Phase 3).
2. **CSO can test but not build** — Safety officers need to test integrations during review, but should not create or modify configurations.
3. **`write_file` restricted to `custom.*` namespace** — Prevents developer role from modifying core platform files. Only `custom.nhs.YourClass` files.
4. **`bash` restricted for tenant_admin and developer** — Bash access is needed for some workflows but filtered against `BLOCKED_BASH_PATTERNS` plus additional restrictions.
5. **Viewer is truly read-only** — Cannot test, cannot write, cannot execute.

### 6.3 Request Flow (End-to-End)

> **Design Highlight:** This diagram shows the complete journey of a natural language request through the RBAC system.

```
User types: "Build an ADT integration from Cerner PAS to RIS and EPR"
        │
        ▼
┌─ Portal (agents/page.tsx) ────────────────────────────────────────┐
│  1. User's JWT token attached to POST /runs request               │
│  2. workspace_id included in thread context                       │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Agent Runner API (main.py) ──────────────────────────────────────┐
│  3. Extract JWT → decode → get { user_id, tenant_id, role }       │
│  4. No token? → Fall back to DEV_USER (platform_admin in dev)     │
│  5. Pass role + tenant_id into run_agent_loop()                   │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Agent Loop (agent.py) ──────────────────────────────────────────┐
│  LAYER 1 — TOOL FILTERING (proactive)                             │
│  6. permitted_tools = filter_tools(TOOLS, role)                   │
│     → Developer sees: create_item, create_connection, test, etc.  │
│     → Developer does NOT see: deploy_project, stop_project        │
│  7. permitted_skills = filter_skills(all_skills, role)            │
│     → Developer sees: hl7-route-builder, integration-test         │
│     → Developer does NOT see: clinical-safety-review              │
│  8. System prompt includes role context:                          │
│     "Your role is: developer. You can only use the tools below."  │
│  9. Claude API called with permitted_tools only                   │
│                                                                   │
│  LAYER 2 — HOOK VALIDATION (defensive)                            │
│  10. Claude requests tool_use: hie_create_item                    │
│  11. pre_tool_use_hook() validates:                               │
│      ├─ Is tool in role's allowed list? → YES                     │
│      ├─ Does workspace belong to user's tenant? → YES             │
│      └─ If write_file: is path custom.*? → YES                   │
│  12. execute_tool() runs → returns result                         │
│  13. post_tool_use_hook() logs to audit trail                     │
│                                                                   │
│  If Claude requests hie_deploy_project:                           │
│  14. pre_tool_use_hook() → DENIED (not in developer's tools)      │
│  15. Agent receives: "Tool blocked: role 'developer' does not     │
│      have permission to use hie_deploy_project"                   │
│  16. Agent tells user: "I've built the integration. To deploy to  │
│      production, a Tenant Admin or CSO must approve."             │
└───────────────────────────────────────────────────────────────────┘
```

### 6.4 Defense-in-Depth Enforcement

> **Design Highlight:** Two independent enforcement layers ensure that even if one is bypassed, the other catches unauthorized access.

**Layer 1 — Tool Filtering (in `agent.py`):**
The AI model literally cannot see or call tools outside its role's permission set. The `tools` parameter sent to the Claude API only contains permitted tools. This is the primary enforcement.

**Layer 2 — Hook Validation (in `hooks.py`):**
Even if a tool somehow appears in the API call (e.g., prompt injection, model hallucination), the pre-tool-use hook independently checks the role permission matrix before execution. This is the secondary enforcement.

```python
# Layer 1: agent.py — proactive filtering
permitted_tools = filter_tools(TOOLS, user_role)  # removes tools from Claude's view
# ...
client.messages.stream(tools=permitted_tools)  # Claude can only use filtered tools

# Layer 2: hooks.py — defensive validation
async def pre_tool_use_hook(input_data, tool_use_id, context):
    role = context.get("user_role", "viewer")
    tool_name = input_data.get("tool_name", "")
    if tool_name not in ROLE_TOOL_PERMISSIONS.get(role, set()):
        return {"hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Role '{role}' cannot use {tool_name}"
        }}
```

**Additional hook-level enforcement:**

| Check | Description |
|-------|------------|
| **Tenant isolation** | Workspace in tool input must belong to the user's `tenant_id` |
| **Namespace enforcement** | `write_file` paths must start with `custom.` for non-admin roles |
| **Staging-only deploy** | Developer role's deploy calls checked for `environment=staging` |

### 6.5 Implementation Detail: `roles.py`

New file `agent-runner/app/roles.py`:

```python
ROLE_TOOL_PERMISSIONS = {
    "platform_admin": {"*"},  # All tools

    "tenant_admin": {
        "hie_list_workspaces", "hie_create_workspace",
        "hie_list_projects", "hie_create_project", "hie_get_project",
        "hie_create_item", "hie_create_connection", "hie_create_routing_rule",
        "hie_deploy_project", "hie_start_project", "hie_stop_project",
        "hie_project_status", "hie_test_item",
        "hie_list_item_types", "hie_reload_custom_classes",
        "read_file", "write_file", "list_files", "bash",
    },

    "developer": {
        "hie_list_workspaces", "hie_list_projects", "hie_create_project",
        "hie_get_project", "hie_create_item", "hie_create_connection",
        "hie_create_routing_rule", "hie_project_status",
        "hie_test_item", "hie_list_item_types", "hie_reload_custom_classes",
        "read_file", "write_file", "list_files", "bash",
    },

    "clinical_safety_officer": {
        "hie_list_workspaces", "hie_list_projects", "hie_get_project",
        "hie_project_status", "hie_test_item", "hie_list_item_types",
        "read_file", "list_files",
    },

    "viewer": {
        "hie_list_workspaces", "hie_list_projects", "hie_get_project",
        "hie_project_status", "hie_list_item_types",
        "read_file", "list_files",
    },
}

ROLE_SKILL_PERMISSIONS = {
    "platform_admin": {"*"},
    "tenant_admin": {"*"},
    "developer": {
        "hl7-route-builder", "fhir-mapper", "integration-test",
        "nhs-compliance-check",
    },
    "clinical_safety_officer": {
        "clinical-safety-review", "nhs-compliance-check",
        "integration-test",
    },
    "viewer": set(),
}


def filter_tools(tools: list[dict], role: str) -> list[dict]:
    """Filter tool definitions to only those permitted for the role."""
    allowed = ROLE_TOOL_PERMISSIONS.get(role, set())
    if "*" in allowed:
        return tools
    return [t for t in tools if t["name"] in allowed]


def filter_skills(skills: list[dict], role: str) -> list[dict]:
    """Filter skills to only those permitted for the role."""
    allowed = ROLE_SKILL_PERMISSIONS.get(role, set())
    if "*" in allowed:
        return skills
    return [s for s in skills if s["name"] in allowed]
```

### 6.6 Changes to Existing Files

**`agent-runner/app/main.py`** (~20 lines added):
- Import `jose` JWT decoder (same pattern as `prompt-manager/app/auth.py`)
- Add `extract_user_context(request)` function to decode JWT from `Authorization` header
- Pass `user_role` and `tenant_id` through `_execute_run()` → `run_agent_loop()`
- Fallback to `DEV_USER` (platform_admin) when no token provided

**`agent-runner/app/agent.py`** (~15 lines changed):
- `run_agent_loop()` accepts `user_role` and `tenant_id` parameters
- Calls `filter_tools(TOOLS, user_role)` → passes filtered list to Claude API
- Calls `filter_skills(all_skills, user_role)` → filters skills before system prompt
- Adds role context to system prompt: "Your role is: {role}."

**`agent-runner/app/hooks.py`** (~30 lines added):
- Accepts `context` dict with `user_role` and `tenant_id`
- In `pre_tool_use_hook()`: checks tool against `ROLE_TOOL_PERMISSIONS[role]`
- Checks `tenant_id` matches workspace's tenant
- Enforces `custom.*` namespace for `write_file` if role != admin

---

## 7. Design: Audit Logging

> **Design Highlight:** Every AI tool call is logged with who, what, when, and the result. This is an NHS compliance requirement under DCB0129/DCB0160.

### 7.1 Audit Log Schema

New model in `prompt-manager/app/models.py`:

```python
class AuditLog(Base):
    __tablename__ = "audit_log"

    id          = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID, nullable=True, index=True)
    user_id     = Column(UUID, nullable=False, index=True)
    user_role   = Column(String(32), nullable=False)
    session_id  = Column(UUID, nullable=True, index=True)  # thread_id
    run_id      = Column(UUID, nullable=True)
    action      = Column(String(128), nullable=False, index=True)  # tool name
    target_type = Column(String(64), nullable=True)    # workspace/project/item
    target_id   = Column(UUID, nullable=True)
    input_summary  = Column(Text, nullable=True)       # sanitised (no PII)
    result_status  = Column(String(16), nullable=False) # success/denied/error
    result_summary = Column(Text, nullable=True)       # sanitised
    created_at  = Column(DateTime(timezone=True), default=utcnow)
```

### 7.2 Data Flow

```
agent.py → execute_tool() → result
              │
              ▼
        hooks.py: post_tool_use_hook()
              │
              ├─ Sanitise PII from input/output
              │  (Strip NHS numbers, patient names, postcodes)
              │
              └─ POST /audit → prompt-manager API
                                    │
                                    ▼
                              audit_log table
```

### 7.3 Audit API

New router `prompt-manager/app/routers/audit.py`:

| Endpoint | Method | Access | Description |
|----------|--------|--------|-------------|
| `/audit` | GET | Admin, CSO | List audit logs with filters (tenant, user, action, date range) |
| `/audit` | POST | Agent Runner (internal) | Create audit log entry |
| `/audit/export` | GET | Admin | Export filtered audit logs as CSV |

**Query parameters for GET /audit:**
- `tenant_id` — filter by tenant
- `user_id` — filter by user
- `action` — filter by tool name
- `result_status` — filter by success/denied/error
- `from_date` / `to_date` — date range
- `limit` / `offset` — pagination

### 7.4 PII Sanitisation

Before logging, input and output are sanitised:
- NHS Numbers (10-digit pattern) → `[NHS_NUMBER]`
- Patient names in PID segments → `[PATIENT_NAME]`
- UK postcodes → `[POSTCODE]`
- The sanitisation patterns are already defined in `hooks.py` (`SENSITIVE_DATA_PATTERNS`)

---

## 8. Design: Approval Workflows

> **Design Highlight:** AI-generated configurations require human approval before reaching production. This is the change management gate that makes NL development safe for NHS.

### 8.1 Workflow

```
Developer (via AI): "Deploy this ADT integration to production"
        │
        ▼
┌─ pre_tool_use_hook ──────────────────────────────┐
│  Role = developer, tool = hie_deploy_project      │
│  Developer cannot deploy to production directly   │
│  → Create DeploymentApproval record               │
│  → Return to AI: "Submitted for approval"         │
└───────────────────────────────────────────────────┘
        │
        ▼
┌─ Portal: Approvals Page ─────────────────────────┐
│  CSO sees pending approval with:                  │
│  • Full project configuration snapshot            │
│  • Who requested it and when                      │
│  • "Run Safety Review" button                     │
│  → CSO clicks "Run Safety Review"                 │
│  → Triggers clinical-safety-review skill          │
│  → 32-item checklist evaluated                    │
│  → CSO approves or rejects with notes             │
└───────────────────────────────────────────────────┘
        │
        ▼
┌─ On Approval ────────────────────────────────────┐
│  1. Config snapshot saved (for rollback)          │
│  2. hie_deploy_project executed                   │
│  3. Audit log: "deployment approved by CSO X"     │
│  4. Developer notified of result                  │
└───────────────────────────────────────────────────┘
```

### 8.2 Deployment Approval Schema

New model in `prompt-manager/app/models.py`:

```python
class DeploymentApproval(Base):
    __tablename__ = "deployment_approvals"

    id              = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id       = Column(UUID, nullable=False, index=True)
    requested_by    = Column(UUID, nullable=False)      # user_id
    workspace_id    = Column(UUID, nullable=False)
    project_id      = Column(UUID, nullable=False)
    environment     = Column(String(16), nullable=False) # staging / production
    status          = Column(String(16), nullable=False, default="pending")
                      # pending / approved / rejected
    reviewed_by     = Column(UUID, nullable=True)
    review_notes    = Column(Text, nullable=True)
    safety_report   = Column(JSON, nullable=True)        # clinical-safety-review output
    config_snapshot = Column(JSON, nullable=False)        # full project config at request time
    created_at      = Column(DateTime(timezone=True), default=utcnow)
    reviewed_at     = Column(DateTime(timezone=True), nullable=True)
```

### 8.3 Approvals API

New router `prompt-manager/app/routers/approvals.py`:

| Endpoint | Method | Access | Description |
|----------|--------|--------|-------------|
| `/approvals` | GET | Admin, CSO | List pending/all approvals |
| `/approvals` | POST | Agent Runner | Create approval request |
| `/approvals/{id}` | GET | Admin, CSO | Get approval detail with config snapshot |
| `/approvals/{id}/approve` | POST | CSO, Admin | Approve deployment |
| `/approvals/{id}/reject` | POST | CSO, Admin | Reject with notes |

### 8.4 When Approval Is Required

| Role | Staging Deploy | Production Deploy |
|------|:-:|:-:|
| Platform Admin | Direct | Direct |
| Tenant Admin | Direct | Direct |
| Developer | Direct | **Requires approval** |
| CSO | No access | No access (but can approve) |
| Viewer | No access | No access |

---

## 9. Design: Configuration Snapshots & Rollback

> **Design Highlight:** Every deployment creates an immutable snapshot. If something breaks, any admin can roll back to the previous known-good state.

### 9.1 Snapshot Schema

```python
class ConfigSnapshot(Base):
    __tablename__ = "config_snapshots"

    id           = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(UUID, nullable=False, index=True)
    workspace_id = Column(UUID, nullable=False)
    project_id   = Column(UUID, nullable=False, index=True)
    snapshot_type = Column(String(32), nullable=False)  # pre_deploy / post_deploy
    config_data  = Column(JSON, nullable=False)  # full project config
    created_by   = Column(UUID, nullable=False)
    created_at   = Column(DateTime(timezone=True), default=utcnow)
    description  = Column(Text, nullable=True)
```

### 9.2 Snapshot Lifecycle

1. **Before deploy:** `pre_tool_use_hook` captures current project config → saves as `pre_deploy` snapshot
2. **After deploy:** `post_tool_use_hook` captures deployed config → saves as `post_deploy` snapshot
3. **On rollback:** `hie_rollback_project` tool restores the most recent `pre_deploy` snapshot

### 9.3 New Tool: `hie_rollback_project`

Added to `agent-runner/app/tools.py`:

```python
{
    "name": "hie_rollback_project",
    "description": "Roll back a project to its previous configuration snapshot",
    "input_schema": {
        "type": "object",
        "properties": {
            "workspace_id": {"type": "string"},
            "project_id": {"type": "string"},
            "snapshot_id": {"type": "string", "description": "Optional specific snapshot to restore"}
        },
        "required": ["workspace_id", "project_id"]
    }
}
```

**Access:** Platform Admin and Tenant Admin only.

---

## 10. Implementation Phases & Priority

| Phase | Description | Status | Commit |
|-------|-------------|--------|--------|
| **Phase 1** | RBAC Guardrails + Portal NL Experience — roles.py, JWT auth, Layer 1+2 enforcement, namespace protection, QuickStartPanel, role badge, capabilities sidebar | **DONE** | `bbb0b3c` on `feature/nl-development-rbac` |
| **Phase 2** | Unified RBAC Role Alignment — DB-to-agent role mapping (`resolve_agent_role()`), 7-role hierarchy (added operator + auditor), Portal role mapping fix, lifecycle stepper | **DONE** | `f75976a` on `feature/nl-development-rbac` |
| **Phase 3** | Audit Logging — `AuditLog` model, `/audit` API with PII sanitisation, Portal audit viewer with stats/filters/CSV export, agent-runner hook integration | **DONE** | `f75976a` on `feature/nl-development-rbac` |
| **Phase 4** | Approval Workflows + Demo Onboarding — `DeploymentApproval` model, `/approvals` API, Portal approval UI, CSO role in DB, 6 demo users, demo tenant/workspace | **DONE** | `f75976a` on `feature/nl-development-rbac` |

### Remaining Phases

| Phase | Description | Effort | Impact | Priority |
|-------|-------------|--------|--------|----------|
| **Phase 5** | Configuration Snapshots & Rollback — `ConfigSnapshot` model, `hie_rollback_project` tool, auto-snapshot on deploy | 1 day | **Medium** — Safety net for FR-12 | **P2** |

### Phase 1 Delivery Summary (Completed)

**Branch:** `feature/nl-development-rbac`
**Files delivered:** 7 files, 856 insertions

| Component | File | What Was Built |
|-----------|------|---------------|
| RBAC Engine | `agent-runner/app/roles.py` (NEW) | 5-role hierarchy, tool/skill permission matrices, `is_class_name_writable()`, `is_file_path_writable()` |
| JWT Auth | `agent-runner/app/main.py` | `extract_user_context()`, `/roles`, `/roles/me` endpoints |
| Layer 1 Enforcement | `agent-runner/app/agent.py` | `filter_tools()` + `filter_skills()` before Claude API call; role preamble with namespace instructions |
| Layer 2 Enforcement | `agent-runner/app/hooks.py` | RBAC validation, namespace enforcement, lifecycle protection, audit logging with role context |
| NL Workflow Templates | `Portal/src/components/AgentWorkflows/QuickStartPanel.tsx` (NEW) | 11 role-filtered template cards across 5 categories |
| Portal UX | `Portal/src/app/(app)/agents/page.tsx` | Role badge, capabilities panel, QuickStartPanel, JWT forwarding, namespace hint |
| Dependency | `agent-runner/requirements.txt` | `python-jose[cryptography]` |

**All work on feature branch** `feature/nl-development-rbac` for isolated review before merging to main.

### Phase 2 Delivery Summary (Completed — Unified RBAC Role Alignment)

**Branch:** `feature/nl-development-rbac`
**Commit:** `f75976a`

| Component | File | What Was Built |
|-----------|------|---------------|
| DB-to-Agent Role Mapping | `agent-runner/app/roles.py` | `DB_ROLE_TO_AGENT_ROLE` dict, `resolve_agent_role()` function, operator + auditor permission sets in `ROLE_TOOL_PERMISSIONS`, `ROLE_SKILL_PERMISSIONS`, `ROLE_DISPLAY_NAMES`, `ROLE_DESCRIPTIONS` |
| JWT Role Resolution | `agent-runner/app/main.py` | `extract_user_context()` now calls `resolve_agent_role()` instead of passthrough |
| Role Preambles | `agent-runner/app/agent.py` | Operator and auditor role preambles added |
| Portal Role Mapping | `Portal/src/components/AgentWorkflows/QuickStartPanel.tsx` | 7-role `AgentRole` type, expanded `mapPortalRoleToAgentRole()`, `ROLE_DISPLAY` for all 7 roles, 6-step lifecycle stepper with `sessionStorage` persistence |
| Portal Capabilities | `Portal/src/app/(app)/agents/page.tsx` | Operator and auditor capability list blocks |

### Phase 3 Delivery Summary (Completed — Audit Logging)

**Branch:** `feature/nl-development-rbac`
**Commit:** `f75976a`

| Component | File | What Was Built |
|-----------|------|---------------|
| AuditLog Model | `prompt-manager/app/models.py` | `AuditLog` SQLAlchemy model with tenant_id, user_id, user_role, session_id, run_id, action, target_type/id, input/result summaries, result_status |
| Audit Repository | `prompt-manager/app/repositories/audit_repo.py` (NEW) | CRUD operations, PII sanitisation (NHS numbers, UK postcodes), date range filtering |
| Audit Router | `prompt-manager/app/routers/audit.py` (NEW) | `POST /audit`, `GET /audit`, `GET /audit/stats` endpoints |
| Router Registration | `prompt-manager/app/main.py` | Audit router registered |
| DB Migration | `prompt-manager/alembic/versions/002_audit_approvals_tables.py` (NEW) | `audit_log` + `deployment_approvals` table creation |
| Hook Integration | `agent-runner/app/hooks.py` | `post_tool_use_hook()` POSTs to `/audit` after every tool execution |
| Portal Audit Viewer | `Portal/src/app/(app)/admin/audit/page.tsx` (NEW) | Stats cards, filter tabs (All/Success/Denied/Error), data table with expandable rows, CSV export, pagination |
| Sidebar Links | `Portal/src/components/Sidebar.tsx` | Audit Log and Approvals links added to admin section |

### Phase 4 Delivery Summary (Completed — Approval Workflows + Demo Onboarding)

**Branch:** `feature/nl-development-rbac`
**Commit:** `f75976a`

| Component | File | What Was Built |
|-----------|------|---------------|
| DeploymentApproval Model | `prompt-manager/app/models.py` | `DeploymentApproval` model with status (pending/approved/rejected), safety_report, config_snapshot |
| Approval Repository | `prompt-manager/app/repositories/approval_repo.py` (NEW) | CRUD + `approve()` + `reject()` with timestamp/reviewer tracking |
| Approval Router | `prompt-manager/app/routers/approvals.py` (NEW) | `POST /approvals`, `GET /approvals`, `GET /approvals/{id}`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject` |
| Router Registration | `prompt-manager/app/main.py` | Approvals router registered |
| Hook Intercept | `agent-runner/app/hooks.py` | Production deploy by developer → creates approval request instead of deploying |
| Portal Approval UI | `Portal/src/app/(app)/admin/approvals/page.tsx` (NEW) | Stats cards (pending/approved/rejected), filter tabs, data table, approve/reject buttons with review modal, expandable detail with config snapshot |
| CSO Role in DB | `scripts/init-db.sql` | `clinical_safety_officer` role (UUID `000...007`) with `approvals:approve`, `approvals:reject` permissions |
| Demo Tenant | `scripts/init-db.sql` | "St Thomas' Hospital NHS Foundation Trust" (code: STH) |
| Demo Users | `scripts/init-db.sql` | 6 demo users (trust.admin, developer, cso, operator, viewer, auditor) all with password `Demo12345!` |
| Demo Workspace | `scripts/init-db.sql` | "STH Integrations" workspace linked to STH tenant |

---

## 11. Critical File Inventory

### Delivered Files (Phase 1)

| File | Status | Purpose |
|------|--------|---------|
| `agent-runner/app/roles.py` | **NEW** | Role definitions, tool/skill permission matrices, namespace enforcement |
| `Portal/src/components/AgentWorkflows/QuickStartPanel.tsx` | **NEW** | 11 NL workflow template cards with role filtering |
| `agent-runner/app/main.py` | **MODIFIED** | JWT extraction, `/roles` + `/roles/me` endpoints |
| `agent-runner/app/agent.py` | **MODIFIED** | Layer 1 tool/skill filtering, role preamble in system prompt |
| `agent-runner/app/hooks.py` | **MODIFIED** | Layer 2 RBAC, namespace enforcement, lifecycle protection, audit logging |
| `agent-runner/requirements.txt` | **MODIFIED** | Added `python-jose[cryptography]` |
| `Portal/src/app/(app)/agents/page.tsx` | **MODIFIED** | Role badge, capabilities panel, QuickStartPanel, JWT forwarding |

### Delivered Files (Phase 2 — Role Alignment)

| File | Status | Purpose |
|------|--------|---------|
| `agent-runner/app/roles.py` | **MODIFIED** | DB-to-agent role mapping, operator/auditor permission sets |
| `agent-runner/app/main.py` | **MODIFIED** | Wire `resolve_agent_role()` in JWT extraction |
| `agent-runner/app/agent.py` | **MODIFIED** | Operator/auditor role preambles |
| `Portal/src/components/AgentWorkflows/QuickStartPanel.tsx` | **MODIFIED** | 7-role support, lifecycle stepper |
| `Portal/src/app/(app)/agents/page.tsx` | **MODIFIED** | Operator/auditor capabilities |

### Delivered Files (Phase 3 — Audit Logging)

| File | Status | Purpose |
|------|--------|---------|
| `prompt-manager/app/repositories/audit_repo.py` | **NEW** | Audit log CRUD with PII sanitisation |
| `prompt-manager/app/routers/audit.py` | **NEW** | `POST /audit`, `GET /audit`, `GET /audit/stats` |
| `prompt-manager/alembic/versions/002_audit_approvals_tables.py` | **NEW** | DB migration for audit_log + deployment_approvals tables |
| `prompt-manager/app/models.py` | **MODIFIED** | Added `AuditLog` + `DeploymentApproval` models |
| `prompt-manager/app/main.py` | **MODIFIED** | Registered audit + approvals routers, version 1.9.0 |
| `agent-runner/app/hooks.py` | **MODIFIED** | Audit POST integration in `post_tool_use_hook()` |
| `agent-runner/app/config.py` | **NEW** | `PROMPT_MANAGER_URL` config for inter-service communication |
| `Portal/src/app/(app)/admin/audit/page.tsx` | **NEW** | Full audit log viewer with stats, filters, CSV export |
| `Portal/src/components/Sidebar.tsx` | **MODIFIED** | Added Audit Log + Approvals sidebar links |

### Delivered Files (Phase 4 — Approvals + Demo Onboarding)

| File | Status | Purpose |
|------|--------|---------|
| `prompt-manager/app/repositories/approval_repo.py` | **NEW** | Approval CRUD with approve/reject lifecycle |
| `prompt-manager/app/routers/approvals.py` | **NEW** | Deployment approval workflow API (5 endpoints) |
| `Portal/src/app/(app)/admin/approvals/page.tsx` | **NEW** | Approval review UI with approve/reject, review modal |
| `scripts/init-db.sql` | **MODIFIED** | CSO role, demo tenant, 6 demo users, demo workspace |

### Delivered Files (Bug Fixes + E2E Tests)

| File | Status | Purpose |
|------|--------|---------|
| `prompt-manager/app/auth.py` | **MODIFIED** | `ADMIN_ROLES` set, `is_admin` property, null tenant_id fix |
| `prompt-manager/app/routers/audit.py` | **MODIFIED** | Replaced hardcoded role checks with `user.is_admin` |
| `prompt-manager/app/routers/approvals.py` | **MODIFIED** | Replaced hardcoded role checks, fixed CSO gate |
| `prompt-manager/app/main.py` | **MODIFIED** | Health endpoint uses `app.version` instead of hardcoded |
| `docker-compose.yml` | **MODIFIED** | JWT_SECRET_KEY alignment for hie-manager |
| `docker-compose.dev.yml` | **MODIFIED** | JWT_SECRET_KEY alignment for hie-manager |
| `tests/e2e/test_v194_rbac_audit_approvals.py` | **NEW** | 38-test E2E suite (health, login, RBAC, audit, approvals) |
| `scripts/run_e2e_tests.sh` | **NEW** | Docker-based E2E test runner |
| `Makefile` | **MODIFIED** | E2E test targets |

### Pending Files (Phase 5)

| File | Phase | Purpose |
|------|-------|---------|
| `agent-runner/app/tools.py` | 5 | Add `hie_rollback_project` tool |
| `prompt-manager/app/models.py` | 5 | Add `ConfigSnapshot` model |

---

## 12. Verification & Acceptance Criteria

### Phase 1: Role-Based Tool Filtering

| Test | Expected Result |
|------|----------------|
| Developer sends "Deploy project X to production" | Agent responds it cannot deploy; tool not available |
| Developer sends "Build an ADT route" | Agent creates items, connections, routing rules successfully |
| Viewer sends "Create a new project" | Agent responds it cannot create projects |
| CSO sends "Run clinical safety review" | Agent runs review skill successfully |
| Admin sends "Stop project X" | Agent stops project successfully |
| No JWT token provided | Falls back to DEV_USER (platform_admin in dev) |

### Phase 2: Audit Logging

| Test | Expected Result |
|------|----------------|
| Any agent tool call | Audit log entry created with user, role, action, result |
| `GET /audit?action=hie_deploy_project` | Returns all deploy actions |
| Tool input contains NHS number | Audit log shows `[NHS_NUMBER]` not the actual number |

### Phase 3: Approval Workflows

| Test | Expected Result |
|------|----------------|
| Developer requests production deploy | DeploymentApproval created with status=pending |
| CSO approves via Portal | Deployment executes; audit log records approval |
| CSO rejects with notes | Developer notified; deployment does not execute |

### E2E Test Suite (38 Tests — All Passing)

Automated Docker-based E2E test suite covering all phases:

```bash
# Start all services
docker compose up -d --build

# Run v1.9.4 feature tests
make test-e2e-v194
```

| Section | Tests | Coverage |
|---------|-------|----------|
| Health Checks | 3 | All services healthy, version = 1.9.4 |
| Demo Login (FR-5) | 7 | All 7 demo users login successfully, receive valid JWT |
| Role Alignment (GR-1) | 8 | Each role resolves correctly via `/roles/me` — no silent fallback |
| Audit Logging (GR-2) | 5 | Create entry, PII sanitisation (NHS numbers), list with auth, stats |
| Approval Workflows (GR-3) | 7 | Create, list, approve, reject, role-gated access |
| RBAC Regression | 4 | Tool filtering per role, deploy blocked for developer, viewer read-only |
| Portal Pages | 3 | Audit + Approvals admin pages return 200 |
| Version Consistency | 1 | All services report version 1.9.4 |

**Test file:** `tests/e2e/test_v194_rbac_audit_approvals.py`
**Runner:** `scripts/run_e2e_tests.sh` (Docker-network, no host-side execution)

### Build Verification

```bash
# Agent runner starts without errors
docker compose -f docker-compose.dev.yml up -d --build hie-agent-runner
curl http://localhost:8082/health  # → {"status": "ok"}

# Portal builds without TypeScript errors
cd Portal && npm run build  # → 0 errors

# Prompt manager starts with new models
docker compose -f docker-compose.dev.yml up -d --build hie-prompt-manager
```

---

## 13. Open Questions & Design Decisions

> **Items below require stakeholder input before implementation.**

### Q1: Role Granularity

**Current design:** 7 fixed roles (platform_admin, tenant_admin, developer, clinical_safety_officer, operator, auditor, viewer) with DB-to-agent role mapping via `resolve_agent_role()`.

**Alternative:** Configurable roles where each tenant can define custom role → tool mappings.

**Decision:** 7 fixed roles implemented. Custom roles deferred — most NHS Trusts follow the same governance structure. Can be added later if needed.

### Q2: Codex Runner RBAC

**Current design:** RBAC enforcement is in the Claude agent-runner only. The Codex runner (`codex-runner/src/server.ts`) uses AGENTS.md context which doesn't enforce tool restrictions server-side.

**Options:**
- **A)** Add equivalent JWT extraction and tool filtering to the Codex runner TypeScript code
- **B)** Route all Codex requests through the Claude agent-runner as a proxy
- **C)** Accept that Codex runner is admin-only (dev/testing use) and restrict access at the Portal level

**Recommendation:** Option A for full parity, or Option C as a pragmatic first step. The Claude runner is the primary production agent.

### Q3: Staging vs Production Environment

**Current design:** The tool permission matrix references "staging only" for developer deploy, but the current HIE Manager API does not have an environment concept.

**Options:**
- **A)** Add `environment` field to projects (staging/production), enforce in hooks
- **B)** Use workspace naming convention (e.g., `st-thomas-staging` vs `st-thomas-production`)
- **C)** Add a separate `is_production` flag to projects

**Recommendation:** Option A — explicit environment field is clearest and most auditable.

### Q4: Rate Limiting

**Current state:** `hooks.py` defines `RATE_LIMITS` dict but does not enforce it.

**Question:** Should rate limiting be part of this feature or a separate effort?

**Recommendation:** Defer to a separate effort. RBAC + audit + approvals are the critical NHS compliance requirements. Rate limiting is a cost control measure that can follow.

### Q5: Multi-Runner Consistency

**Question:** If a user switches between Claude and Codex runners mid-workflow, should session state (permissions, context) be shared?

**Recommendation:** Each runner session is independent. The JWT token ensures the same role enforcement regardless of runner. No shared state needed.

---

## 14. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|-----------|
| JWT token not propagated from Portal to agent-runner | Medium | High — RBAC bypassed, falls back to DEV_USER | DEV_USER only available when `ENABLE_DEV_AUTH=true` (off in production) |
| AI model ignores role constraints in system prompt | Low | Medium — Model requests blocked tools | Layer 2 hook enforcement catches all violations regardless of model behavior |
| Audit log contains unsanitised PII | Low | High — NHS data breach | PII sanitisation tested with known patterns; regex patterns already proven in hooks.py |
| Approval workflow blocks urgent production changes | Medium | Medium — Delayed incident response | Platform Admin role bypasses approval; tenant admin can approve directly |
| Performance impact of hook validation on every tool call | Low | Low — Hooks are simple dict lookups | Permission check is O(1) set membership test; audit POST is async fire-and-forget |

---

## Appendix A: Existing Platform Skills Reference

| Skill | Purpose | Key Allowed Tools |
|-------|---------|------------------|
| `hl7-route-builder` | End-to-end HL7 route creation (10-step workflow) | All create/deploy/test tools |
| `fhir-mapper` | FHIR resource mapping and transformation | create_item, test_item, read/write_file |
| `clinical-safety-review` | DCB0129/DCB0160 compliance (32-item checklist) | get_project, project_status, test_item, read_file |
| `nhs-compliance-check` | NHS Digital standards (ITK3, MESH, Spine, HL7 UK) | get_project, list_item_types, read_file |
| `integration-test` | Test planning and execution with standard patients | test_item, project_status, read_file, bash |

## Appendix B: Current JWT Payload Structure

From `prompt-manager/app/auth.py`:
```json
{
  "sub": "user-uuid",
  "user_id": "user-uuid",
  "tenant_id": "tenant-uuid",
  "role": "developer",
  "exp": 1700000000
}
```

Both `sub` and `user_id` are accepted for backward compatibility. The `role` field maps directly to the RBAC role hierarchy defined in Section 5.1.
