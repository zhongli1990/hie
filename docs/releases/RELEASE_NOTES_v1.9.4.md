# Release Notes — OpenLI HIE v1.9.4

**Release Date:** 2026-02-13
**Branch:** `feature/nl-development-rbac`
**Commits:** `f75976a` (implementation) → `883caac` (docs/version bumps) → `bc272d4` (bug fixes + E2E tests)
**Type:** Feature Release — Unified RBAC, Demo Onboarding & E2E Lifecycle

---

## Overview

v1.9.4 delivers the **Unified RBAC, Demo Onboarding & E2E Lifecycle** — completing Phases 2-4 of the NL Development RBAC feature. This release fixes a critical role alignment bug, implements full audit logging and approval workflows for NHS compliance (DCB0129/DCB0160), seeds demo users for all 7 roles, and adds a guided lifecycle stepper to the Portal.

**Key outcomes:**
- 3 of 5 guardrails now fully implemented (GR-1 RBAC, GR-2 Audit, GR-3 Approvals)
- Every AI tool call is logged with PII sanitisation
- Production deployments require human approval from CSO/Admin
- 6 demo users + 1 demo NHS Trust tenant for onboarding and testing
- Critical bug fix: DB roles now correctly resolve to agent-runner permissions

---

## Critical Bug Fix: Role Alignment

**Problem:** The database defines 7 roles using NHS-appropriate terminology (`super_admin`, `tenant_admin`, `integration_engineer`, `clinical_safety_officer`, `operator`, `auditor`, `viewer`), but the agent-runner defined 5 different role keys (`platform_admin`, `tenant_admin`, `developer`, `clinical_safety_officer`, `viewer`). When an `integration_engineer` logged in, the JWT carried the DB role name verbatim — the agent-runner couldn't find the role key and **silently fell back to `viewer` (read-only)**. This meant developers could not build integrations via AI.

**Fix:** Added `DB_ROLE_TO_AGENT_ROLE` mapping dictionary and `resolve_agent_role()` function in `agent-runner/app/roles.py`. Wired into `extract_user_context()` in `main.py` so JWT role claims are always resolved before use.

| DB Role (JWT) | Agent Role | Was Working? |
|---|---|---|
| `super_admin` | `platform_admin` | Yes |
| `tenant_admin` | `tenant_admin` | Yes (identity map) |
| `integration_engineer` | `developer` | **NO — fell back to viewer** |
| `clinical_safety_officer` | `clinical_safety_officer` | Yes (identity map) |
| `operator` | `operator` | **NO — role didn't exist** |
| `auditor` | `auditor` | **NO — role didn't exist** |
| `viewer` | `viewer` | Yes (identity map) |

---

## New Features

### 1. 7-Role RBAC Hierarchy (Phase 2)

Expanded from 5 to 7 roles with two new permission sets:

**Operator** — Systems operators who manage deployments but don't create integrations:
- Can: deploy, start, stop, monitor projects; view workspaces/projects
- Cannot: create items, connections, routing rules, workspaces
- Use case: NHS Trust operations team managing live integrations

**Auditor** — Information Governance auditors with read-only access plus audit logs:
- Can: view workspaces, projects, project status, item types; read files
- Cannot: create, modify, deploy, or test anything
- Use case: IG officers reviewing compliance and audit trails

### 2. Audit Logging (Phase 3 — GR-2)

Every AI tool call is now logged to a persistent audit trail:

- **Backend:** `AuditLog` model with tenant_id, user_id, user_role, session_id, run_id, action (tool name), target_type/id, input/result summaries, result_status (success/denied/error)
- **PII Sanitisation:** NHS numbers (10-digit Modulus 11 pattern) and UK postcodes are stripped from input/output before storage
- **API:** `POST /audit` (internal, from agent-runner hooks), `GET /audit` (filtered list with pagination), `GET /audit/stats` (aggregate counts)
- **Portal Viewer:** Full audit log page with:
  - Stats cards showing total entries, successes, denied actions, errors
  - Filter tabs: All / Success / Denied / Error
  - Data table with expandable detail rows
  - CSV export for compliance reporting
  - Pagination with configurable page size

### 3. Approval Workflows (Phase 4 — GR-3)

Production deployments now require human approval:

- **Backend:** `DeploymentApproval` model with status lifecycle (pending → approved/rejected), safety_report JSON, config_snapshot JSON
- **API:** 5 endpoints — create approval, list (with status filter), get detail, approve, reject
- **Hook Intercept:** When a developer requests `hie_deploy_project` to production, the agent-runner hook creates an approval request instead of deploying
- **Portal Approvals Page:**
  - Stats cards: Pending (amber), Approved (green), Rejected (red)
  - Filter tabs: All / Pending / Approved / Rejected
  - Approve/Reject buttons for pending items (CSO + Admin only)
  - Review notes modal (required for rejections)
  - Expandable detail view with config snapshot and safety report
- **Role-gated:** Only `clinical_safety_officer`, `tenant_admin`, and `platform_admin` can approve/reject

### 4. Demo Onboarding Data

Pre-seeded NHS Trust demo environment for testing and demonstrations:

**Demo Tenant:**
- St Thomas' Hospital NHS Foundation Trust (code: STH, ODS code: RJ1)

**Demo Users (all with password `Demo12345!`):**

| Email | Name | Title | Role |
|-------|------|-------|------|
| `admin@hie.nhs.uk` | System Admin | Platform Admin | super_admin |
| `trust.admin@sth.nhs.uk` | Sarah Thompson | IT Director | tenant_admin |
| `developer@sth.nhs.uk` | James Chen | Integration Developer | integration_engineer |
| `cso@sth.nhs.uk` | Dr. Priya Patel | Clinical Safety Officer | clinical_safety_officer |
| `operator@sth.nhs.uk` | Mike Williams | Systems Operator | operator |
| `viewer@sth.nhs.uk` | Emma Davis | Service Desk Analyst | viewer |
| `auditor@sth.nhs.uk` | Robert Singh | IG Auditor | auditor |

**Demo Workspace:** "STH Integrations" linked to STH tenant

### 5. Guided Lifecycle Stepper

6-step horizontal stepper in the QuickStartPanel showing the complete integration lifecycle:

```
[1. DESIGN] → [2. BUILD] → [3. TEST] → [4. REVIEW] → [5. DEPLOY] → [6. MONITOR]
```

- Each step auto-generates a contextual prompt when clicked
- Design step includes integration pattern picker (ADT/ORM/ORU/FHIR/Custom)
- Steps are role-filtered: developers see 1-3+6, CSOs see 3-4+6, operators see 5-6
- State persisted in `sessionStorage` within tab session

### 6. Portal UI Enhancements

- **Sidebar:** Added Approvals (CheckCircle) and Audit Log (ClipboardList) navigation links
- **Role Display:** Added operator (cyan badge) and auditor (indigo badge) to role display system
- **Agents Page:** Explicit capability list blocks for operator and auditor roles

---

## Deployment Guide

### Fresh Installation

```bash
# Clone and start all services
git checkout feature/nl-development-rbac
docker compose up -d --build

# init-db.sql runs automatically on first postgres start
# Demo users and tenant are created automatically
```

### Upgrade from v1.9.0

```bash
# Rebuild services with new code
docker compose build --no-cache hie-agent-runner hie-prompt-manager hie-portal

# Apply demo data to existing database (idempotent)
docker exec -i hie-postgres psql -U hie -d hie < scripts/init-db.sql

# Restart services
docker compose up -d
```

### Verification

1. **Login as each demo user** — verify role badge and capabilities
2. **Developer lifecycle:** Login as `developer@sth.nhs.uk` → build integration → request deploy → see approval created
3. **CSO review:** Login as `cso@sth.nhs.uk` → navigate to Admin > Approvals → approve/reject with notes
4. **Audit trail:** Login as any admin → navigate to Admin > Audit Log → verify entries with filters
5. **Lifecycle stepper:** Use guided workflow on Agents page → walk through all 6 steps

### Default Credentials

| User | Password | Role |
|------|----------|------|
| `admin@hie.nhs.uk` | `Admin123!` | Super Admin (platform) |
| `trust.admin@sth.nhs.uk` | `Demo12345!` | Tenant Admin (STH) |
| `developer@sth.nhs.uk` | `Demo12345!` | Integration Engineer |
| `cso@sth.nhs.uk` | `Demo12345!` | Clinical Safety Officer |
| `operator@sth.nhs.uk` | `Demo12345!` | Systems Operator |
| `viewer@sth.nhs.uk` | `Demo12345!` | Service Desk Analyst |
| `auditor@sth.nhs.uk` | `Demo12345!` | IG Auditor |

---

## Guardrail Status Summary

| Guardrail | Status | Phase |
|-----------|--------|-------|
| GR-1 Role-Based Tool Access | **DONE** | Phase 1 |
| GR-2 Audit Logging | **DONE** | Phase 3 |
| GR-3 Approval Workflows | **DONE** | Phase 4 |
| GR-4 Configuration Snapshots | Pending | Phase 5 |
| GR-5 Tenant Isolation | **DONE** | Phase 1 |
| GR-6 Namespace Enforcement | **DONE** | Phase 1 |

**5 of 6 guardrails implemented.** Only GR-4 (Configuration Snapshots & Rollback) remains for Phase 5.

---

## Bug Fixes (discovered during E2E testing)

### JWT Secret Mismatch Between Services

**Problem:** The `hie-manager` service (which issues JWTs) used the default secret from `Engine/auth/security.py` (`hie-dev-secret-key-change-in-production`), while `agent-runner` and `prompt-manager` both had `hie-jwt-secret-key-change-in-production` set in `docker-compose.yml`. All JWT-authenticated requests from agent-runner and prompt-manager to manager-issued tokens failed with 401.

**Fix:** Added `JWT_SECRET_KEY=hie-jwt-secret-key-change-in-production` to the `hie-manager` environment in both `docker-compose.yml` and `docker-compose.dev.yml`, aligning all three services.

### Prompt-Manager Auth: Null Tenant ID Handling

**Problem:** When a JWT carries `"tenant_id": null` (e.g., super_admin users with no tenant), the expression `str(payload.get("tenant_id", "")) or None` produced the string `"None"` (not Python `None`), because `payload.get("tenant_id", "")` returns Python `None` (not empty string) when the key exists with value null. `str(None)` = `"None"` which is truthy. This garbage string then crashed DB queries.

**Fix:** Changed to explicit null-safe extraction:
```python
tenant_id_raw = payload.get("tenant_id")
tenant_id = str(tenant_id_raw) if tenant_id_raw else None
```

### Prompt-Manager Auth: Admin Role Recognition

**Problem:** Role checks in audit and approvals routers used `user.role not in ("admin", "platform_admin")` which did not recognise `super_admin` or `tenant_admin` (the actual DB role names carried in JWTs). Admin users were denied access to their own audit logs and approval reviews.

**Fix:** Created `ADMIN_ROLES = {"admin", "platform_admin", "super_admin", "tenant_admin"}` set and `is_admin` property on `CurrentUser` class in `prompt-manager/app/auth.py`. Replaced all hardcoded role checks in `audit.py` and `approvals.py` with `user.is_admin`.

### Prompt-Manager Health Endpoint: Hardcoded Version

**Problem:** The `/health` endpoint returned `"version": "1.9.0"` even though the FastAPI app version was bumped to 1.9.4.

**Fix:** Changed to `"version": app.version` in `prompt-manager/app/main.py`.

---

## E2E Test Suite

### Docker-Based Test Infrastructure

Created a comprehensive Docker-based E2E test suite that runs inside the compose network — no tests run on the host macOS. Tests use container DNS names (`hie-manager`, `hie-agent-runner`, `hie-prompt-manager`, `hie-portal`) instead of localhost.

**Test runner:** `scripts/run_e2e_tests.sh` — builds a test image from `Dockerfile.dev`, mounts `tests/` read-only, connects to `hie_hie-network`, and executes pytest inside the container.

**Makefile targets:**
```bash
make test-e2e          # Run all E2E tests
make test-e2e-v194     # Run v1.9.4 feature tests only
make test-e2e-smoke    # Run smoke tests only
```

### Test Coverage (38 tests — all passing)

**`tests/e2e/test_v194_rbac_audit_approvals.py`** — organised by feature requirements:

| Section | Tests | Coverage |
|---------|-------|----------|
| Health Checks | 3 | All services healthy, version = 1.9.4 |
| Demo Login (FR-5) | 7 | All 7 demo users login successfully, receive valid JWT |
| Role Alignment (GR-1) | 8 | Each role resolves correctly via `/roles/me` — no silent fallback to viewer |
| Audit Logging (GR-2) | 5 | Create audit entry, verify PII sanitisation (NHS numbers), list with auth, stats endpoint |
| Approval Workflows (GR-3) | 7 | Create approval, list, approve, reject, role-gated access (CSO/Admin only, developer rejected) |
| RBAC Regression | 4 | Tool filtering per role, developer blocked from deploy, viewer read-only, admin full access |
| Portal Pages | 3 | Audit + Approvals admin pages return 200 |
| Version Consistency | 1 | All services report version 1.9.4 |

---

## Files Changed (full release)

### New Files (9)

| File | Lines | Purpose |
|------|-------|---------|
| `prompt-manager/app/repositories/audit_repo.py` | ~150 | Audit log CRUD with PII sanitisation |
| `prompt-manager/app/repositories/approval_repo.py` | ~120 | Approval lifecycle CRUD |
| `prompt-manager/app/routers/audit.py` | ~80 | Audit API endpoints |
| `prompt-manager/app/routers/approvals.py` | ~170 | Approval workflow API |
| `prompt-manager/alembic/versions/002_audit_approvals_tables.py` | ~60 | DB migration |
| `agent-runner/app/config.py` | ~10 | Inter-service config |
| `Portal/src/app/(app)/admin/audit/page.tsx` | ~450 | Audit log viewer |
| `Portal/src/app/(app)/admin/approvals/page.tsx` | ~500 | Approval review UI |
| `tests/e2e/test_v194_rbac_audit_approvals.py` | ~620 | 38-test E2E suite |

### New Scripts (1)

| File | Purpose |
|------|---------|
| `scripts/run_e2e_tests.sh` | Docker-based E2E test runner |

### Modified Files (15)

| File | Change |
|------|--------|
| `agent-runner/app/roles.py` | DB-to-agent role mapping, operator/auditor permissions |
| `agent-runner/app/main.py` | Wire `resolve_agent_role()` |
| `agent-runner/app/agent.py` | Operator/auditor role preambles |
| `agent-runner/app/hooks.py` | Audit POST + approval intercept |
| `prompt-manager/app/models.py` | AuditLog + DeploymentApproval models |
| `prompt-manager/app/main.py` | Register routers, fix health endpoint version |
| `prompt-manager/app/schemas.py` | Audit + approval Pydantic schemas |
| `prompt-manager/app/auth.py` | ADMIN_ROLES set, is_admin property, null tenant_id fix |
| `prompt-manager/app/routers/audit.py` | Use `user.is_admin` instead of hardcoded role checks |
| `prompt-manager/app/routers/approvals.py` | Use `user.is_admin`, fix CSO role gate |
| `scripts/init-db.sql` | CSO role, demo tenant, 6 users, workspace |
| `docker-compose.yml` | JWT_SECRET_KEY alignment for hie-manager |
| `docker-compose.dev.yml` | JWT_SECRET_KEY alignment for hie-manager |
| `Portal/src/components/AgentWorkflows/QuickStartPanel.tsx` | 7-role support, lifecycle stepper |
| `Portal/src/app/(app)/agents/page.tsx` | Operator/auditor capabilities |
| `Portal/src/components/Sidebar.tsx` | Audit + Approvals nav links |
| `Makefile` | E2E test targets (test-e2e, test-e2e-v194, test-e2e-smoke) |

### Documentation Files

| File | Purpose |
|------|---------|
| `docs/design/FEATURE_NL_DEVELOPMENT_RBAC.md` | Updated: Phases 2-4 DONE, E2E verification |
| `docs/releases/RELEASE_NOTES_v1.9.4.md` | This file |
| `docs/reference/TESTING_GUIDE.md` | Updated: E2E v1.9.4 section |
| `docs/INDEX.md` | Updated with v1.9.4 references |
| `CHANGELOG.md` | v1.9.4 entry |

---

## Breaking Changes

None — 100% backward compatible. All SQL seed data uses `ON CONFLICT DO NOTHING` for idempotent re-runs.

---

*OpenLI HIE v1.9.4 — Unified RBAC, Demo Onboarding & E2E Lifecycle*
*Licensed under AGPL-3.0 or Commercial by Lightweight Integration Ltd*
