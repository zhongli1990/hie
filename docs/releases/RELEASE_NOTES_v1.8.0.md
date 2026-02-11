# OpenLI HIE v1.8.0 — Release Notes

**Release Date:** February 11, 2026  
**Branch:** `feature/agent-hie-skills-dev-scenarios`  
**Base:** `main` @ v1.7.3 (tag: `v1.7.3`)  
**Status:** Development — pending E2E testing before merge to main

---

## Overview

v1.8.0 transforms OpenLI HIE from an internal integration engine into a **developer platform**. External integration developers can now extend the engine with custom classes while the core product remains protected. The GenAI agent gains full lifecycle control over workspaces, projects, items, routing rules, and production management.

### Key Themes

1. **Developer Extensibility** — `custom.*` namespace with runtime enforcement
2. **Agent-Driven Integration** — 16 HIE tools for end-to-end route creation
3. **Documentation & Onboarding** — Comprehensive guides, workflow scenarios, IRIS comparisons

---

## What's New

### 1. Class Namespace Convention Enforcement

The ClassRegistry now enforces a strict separation between core product code and developer extensions:

| Namespace | Owner | Enforced | Purpose |
|-----------|-------|----------|---------|
| `li.*` | LI Product Team | 🔒 Protected | Core host classes |
| `Engine.li.*` | LI Product Team | 🔒 Protected | Same via fully-qualified path |
| `EnsLib.*` | IRIS Aliases | 🔒 Protected | Read-only compatibility |
| **`custom.*`** | **Developer** | ✅ Open | Custom extensions |

**Runtime enforcement:**
- `ClassRegistry._validate_custom_namespace()` — raises `ValueError` if a developer attempts to register in a protected namespace
- `ClassRegistry._register_internal()` — internal-only method for core class registration
- `register_host()`, `register_transform()`, `register_rule()` — all validate namespace

**Files changed:**
- `Engine/li/registry/class_registry.py` — Enforcement logic, constants, helpers
- `Engine/li/hosts/hl7.py` — Core registrations switched to `_register_internal()`
- `Engine/li/hosts/routing.py` — Core registrations switched to `_register_internal()`

### 2. Custom Developer Extension Framework

New `Engine/custom/` package provides a complete framework for developer extensions:

```
Engine/custom/
├── __init__.py              ← @register_host decorator, load_custom_modules()
├── nhs/
│   ├── __init__.py
│   └── validation.py        ← custom.nhs.NHSValidationProcess (reference impl)
└── _example/
    ├── __init__.py
    └── example_process.py   ← Copy-paste template for developers
```

**@register_host decorator:**
```python
from Engine.custom import register_host
from Engine.li.hosts.base import BusinessProcess

@register_host("custom.nhs.NHSValidationProcess")
class NHSValidationProcess(BusinessProcess):
    async def on_message(self, message):
        # Custom validation logic
        ...
```

**Auto-discovery:** `load_custom_modules()` walks `Engine/custom/` at startup, imports all modules, executing all `@register_host` decorators. Wired into `ProductionEngine._create_hosts()`.

**Reference implementation** (`custom.nhs.NHSValidationProcess`):
- NHS Number validation (Modulus 11 check digit)
- PDS demographic lookup stub (FHIR API ready)
- Duplicate message detection (sliding window)
- UK postcode validation
- Configurable fail mode: `nack_and_exception_queue` or `warn_and_continue`

### 3. Agent HIE Skills (16 Tools)

The GenAI agent now has full lifecycle control via 16 tools (was 10):

| Category | Tools | Status |
|----------|-------|--------|
| **Workspace** | `hie_list_workspaces`, `hie_create_workspace` | ✅ New |
| **Project** | `hie_list_projects`, `hie_create_project`, `hie_get_project` | ✅ (1 new) |
| **Items** | `hie_create_item` | ✅ Enhanced |
| **Connections** | `hie_create_connection` | ✅ |
| **Routing Rules** | `hie_create_routing_rule` | ✅ New |
| **Lifecycle** | `hie_deploy_project`, `hie_start_project`, `hie_stop_project` | ✅ (2 new) |
| **Monitoring** | `hie_project_status` | ✅ New |
| **Testing** | `hie_test_item` | ✅ Enhanced |
| **Registry** | `hie_list_item_types` | ✅ |

**System prompt** rewritten with:
- IRIS-aligned architecture mapping table
- Class namespace convention rules (CRITICAL section)
- Core class catalog with IRIS equivalents
- 10-step end-to-end route creation workflow
- ReplyCodeActions syntax reference

**hl7-route-builder skill v2.0:**
- Complete e2e examples for all 16 tools
- HL7 field reference table (MSH, PID, PV1, OBR, OBX)
- Routing rule condition syntax with examples
- ReplyCodeActions patterns and meanings
- Best practices for production deployments

### 4. GenAI Sessions

- GenAI sessions models, repositories, and API routes in Engine API
- `002_genai_sessions.sql` database migration
- Portal `/api/genai-sessions/` proxy route
- `AppContext` for shared state across Portal pages
- Agent and Chat pages updated with session persistence

### 5. Documentation

| Document | Status | Content |
|----------|--------|---------|
| `docs/guides/CUSTOM_CLASSES.md` | **New** | Namespace rules, quick start, base class reference, Docker volume mount, IRIS comparison |
| `docs/guides/LI_HIE_DEVELOPER_GUIDE.md` | **Revised** | Expanded 3+2+3 route topology, FHIR inbound, agent guide section |
| `docs/guides/NHS_TRUST_DEMO.md` | **Revised** | Matching 3-inbound/2-process/3-outbound architecture |
| `docs/DEVELOPER_WORKFLOW_SCENARIOS.md` | **New** | 8 developer/user workflow scenarios vs IRIS/Rhapsody/Mirth |

---

## Implementation Status

### ✅ Completed

| # | Feature | Files |
|---|---------|-------|
| 1 | Class namespace enforcement in ClassRegistry | `class_registry.py`, `hl7.py`, `routing.py` |
| 2 | Custom extension framework with decorators | `Engine/custom/__init__.py` |
| 3 | NHS reference implementation | `Engine/custom/nhs/validation.py` |
| 4 | Developer template | `Engine/custom/_example/example_process.py` |
| 5 | Auto-discovery wired into engine startup | `production.py` |
| 6 | 16 agent tools (workspace/project/item/routing/lifecycle) | `tools.py` |
| 7 | System prompt with namespace rules and e2e workflow | `skills.py` |
| 8 | hl7-route-builder skill v2.0 | `skills/hl7-route-builder/SKILL.md` |
| 9 | GenAI sessions API + Portal integration | `models.py`, `repositories.py`, Portal pages |
| 10 | Developer Guide revised (3+2+3 topology) | `LI_HIE_DEVELOPER_GUIDE.md` |
| 11 | NHS Trust Demo revised | `NHS_TRUST_DEMO.md` |
| 12 | Workflow Scenarios document | `DEVELOPER_WORKFLOW_SCENARIOS.md` |
| 13 | Custom Classes developer guide | `CUSTOM_CLASSES.md` |
| 14 | IRIS alias fix (RoutingEngine) | `class_registry.py` |
| 15 | Version bump to 1.8.0 across all services | 6 files |

### 🔲 Remaining (before merge to main)

| # | Task | Priority | Notes |
|---|------|----------|-------|
| 1 | **E2E testing**: Agent → API → Engine → running production | High | Full loop verification |
| 2 | **Manager API endpoints**: Verify `/routing-rules`, `/start`, `/stop`, `/status` exist | High | May need new routes in Engine API |
| 3 | **Additional skills**: `fhir-mapper`, `clinical-safety-review`, `nhs-compliance-check` | Medium | Skill markdown files |
| 4 | **Portal UI**: `custom.*` vs `li.*` distinction in item type picker | Medium | UX enhancement |
| 5 | **Hot reload**: Reload `custom/` modules without engine restart | Low | Developer experience |

---

## Version Bumps

All services: **1.7.3 → 1.8.0**

| Service | File | Field |
|---------|------|-------|
| Portal | `package.json` | `version` |
| Portal | `AboutModal.tsx` | `VERSION` constant + history entry |
| agent-runner | `main.py` | FastAPI `version` + `/health` |
| prompt-manager | `main.py` | FastAPI `version` + `/health` |
| codex-runner | `server.ts` | `/health` response |

---

## Git History

```
Branch: feature/agent-hie-skills-dev-scenarios

6d6a012  feat(portal/engine): GenAI sessions API, agent/chat page improvements
ee41278  docs: developer guides, workflow scenarios, and custom class documentation
c261570  feat(agent-runner): expand HIE tools and update system prompt for e2e workflow
abfd0ed  feat(engine): enforce class namespace conventions (li.* protected, custom.* developer)
24f8c71  (tag: v1.7.3, origin/main, main) release(v1.7.3)
```

---

## Compatibility

- **Backward compatible** with v1.7.3 configurations
- No database schema changes to existing tables (new `genai_sessions` tables only)
- Existing IRIS aliases continue to work unchanged
- Core classes registered via `_register_internal()` behave identically to before
- `custom/` directory is optional — engine starts normally without it
