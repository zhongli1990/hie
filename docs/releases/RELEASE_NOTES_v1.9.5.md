# Release Notes — OpenLI HIE v1.9.5

**Release Date:** 2026-02-13
**Branch:** `feature/nl-development-rbac`
**Type:** Feature Release — Config Snapshots, Full CRUD, Environment Deploy & Rate Limiting

---

## Overview

v1.9.5 completes the final guardrail (GR-4 Config Snapshots & Rollback) and fills the remaining tool gaps for full natural-language CRUD, environment-aware deployment, and rate limiting. After this release, **all 6 guardrails are fully implemented**.

**Key outcomes:**
- GR-4 (Config Snapshots & Rollback) — DONE. Auto-snapshot on every deploy, list/rollback API
- 6 new CRUD tools — items, connections, routing rules can now be updated and deleted via NL
- Environment-aware deploys — staging deploys skip approval, production requires it
- Redis rate limiting enforced — prevents resource abuse per user/category
- DEV_USER disable flag — production hardening for unauthenticated access

---

## New Features

### 1. Config Snapshots & Rollback (GR-4)

Every deployment now auto-snapshots the project config into the `project_versions` table. Users can list versions, inspect any snapshot, and rollback to restore items, connections, and routing rules.

**New API Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/versions` | List all config snapshots |
| GET | `/api/projects/{id}/versions/{v}` | Get specific snapshot |
| POST | `/api/projects/{id}/rollback/{v}` | Rollback to version |

**New Agent Tools:**
| Tool | RBAC | Description |
|------|------|-------------|
| `hie_list_versions` | All except viewer | List config snapshots |
| `hie_get_version` | All except viewer | Get specific snapshot |
| `hie_rollback_project` | Operator, tenant_admin, platform_admin | Rollback to version |

**NL Example:** *"Show me the version history for this project"* → `hie_list_versions`

### 2. Full CRUD Tools (FR-3, FR-10)

6 new tools expose the existing Manager API update/delete endpoints:

| Tool | HTTP | Endpoint | RBAC |
|------|------|----------|------|
| `hie_update_item` | PUT | `/api/projects/{id}/items/{id}` | developer+ |
| `hie_delete_item` | DELETE | `/api/projects/{id}/items/{id}` | developer+ |
| `hie_update_connection` | PUT | `/api/projects/{id}/connections/{id}` | developer+ |
| `hie_delete_connection` | DELETE | `/api/projects/{id}/connections/{id}` | developer+ |
| `hie_update_routing_rule` | PUT | `/api/projects/{id}/routing-rules/{id}` | developer+ |
| `hie_delete_routing_rule` | DELETE | `/api/projects/{id}/routing-rules/{id}` | developer+ |

**NL Example:** *"Change the port on the Cerner ADT receiver to 10005"* → `hie_update_item`

### 3. Environment-Aware Deployment

The `hie_deploy_project` tool now accepts an `environment` parameter:

| Environment | Developer | Operator | Admin |
|-------------|-----------|----------|-------|
| `staging` | Direct deploy | Direct deploy | Direct deploy |
| `production` | Approval required | Direct deploy | Direct deploy |

**NL Example:** *"Deploy this project to staging"* → deploys immediately.
*"Deploy this project to production"* → creates approval request.

### 4. Redis Rate Limiting

The rate limits previously defined but not enforced in `hooks.py` are now active:

| Category | Limit | Window |
|----------|-------|--------|
| bash | 30/min | 60s |
| file_writes | 20/min | 60s |
| api_calls | 60/min | 60s |
| hl7_sends | 10/min | 60s |

Rate limiting uses Redis sliding window counters. Fails open if Redis is unavailable.

### 5. DEV_USER Disable Flag

New `DISABLE_DEV_USER` environment variable for production deployments:
- `false` (default): unauthenticated requests get `platform_admin` (dev mode)
- `true`: unauthenticated requests get `viewer` (production mode — JWT required)

---

## Guardrail Status Summary

| Guardrail | Status | Phase |
|-----------|--------|-------|
| GR-1 Role-Based Tool Access | **DONE** | Phase 1 |
| GR-2 Audit Logging | **DONE** | Phase 3 |
| GR-3 Approval Workflows | **DONE** | Phase 4 |
| GR-4 Configuration Snapshots | **DONE** | Phase 5 |
| GR-5 Tenant Isolation | **DONE** | Phase 1 |
| GR-6 Namespace Enforcement | **DONE** | Phase 1 |

**All 6 guardrails fully implemented.**

---

## Files Changed

### New Files (2)

| File | Lines | Purpose |
|------|-------|---------|
| `agent-runner/app/rate_limiter.py` | ~65 | Redis sliding window rate limiter |
| `docs/releases/RELEASE_NOTES_v1.9.5.md` | — | This file |

### Modified Files (12)

| File | Change |
|------|--------|
| `agent-runner/app/tools.py` | PUT/DELETE in `_hie_api_call()`, 9 new tool definitions, environment param |
| `agent-runner/app/roles.py` | Permissions for 9 new tools across all 7 roles |
| `agent-runner/app/hooks.py` | Environment-aware approval, rate limit wiring |
| `agent-runner/app/config.py` | Added REDIS_URL |
| `agent-runner/app/main.py` | DISABLE_DEV_USER flag, version 1.9.5 |
| `Engine/api/repositories.py` | ProjectVersionRepository class |
| `Engine/api/routes/projects.py` | 3 version/rollback endpoints, auto-snapshot |
| `Engine/api/models.py` | `environment` field on DeployRequest |
| `Engine/api/server.py` | Version bump to 1.9.5 |
| `prompt-manager/app/main.py` | Version bump to 1.9.5 |
| `Portal/package.json` | Version bump to 1.9.5 |
| `docker-compose.yml` | REDIS_URL, DISABLE_DEV_USER env vars |
| `docker-compose.dev.yml` | REDIS_URL, DISABLE_DEV_USER env vars |

### Documentation Files

| File | Purpose |
|------|---------|
| `CHANGELOG.md` | v1.9.5 entry |
| `docs/releases/RELEASE_NOTES_v1.9.5.md` | This file |
| `docs/design/FEATURE_NL_DEVELOPMENT_RBAC.md` | GR-4 status → DONE |
| `docs/reference/TESTING_GUIDE.md` | v1.9.5 test section |
| `docs/INDEX.md` | v1.9.5 release link |

---

## Breaking Changes

None — 100% backward compatible. New tools are additive; existing tools unchanged. Environment parameter defaults to "staging" (same behaviour as before).

---

*OpenLI HIE v1.9.5 — Config Snapshots, Full CRUD, Environment Deploy & Rate Limiting*
*Licensed under AGPL-3.0 or Commercial by Lightweight Integration Ltd*
