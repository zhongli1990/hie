# Changelog

All notable changes to OpenLI HIE (Healthcare Integration Engine) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.9.5] - 2026-02-13

### Added — Config Snapshots, Full CRUD, Environment Deploy & Rate Limiting

**Config Snapshots & Rollback (GR-4 Complete — last guardrail):**
- Auto-snapshot project config before every deployment into `project_versions` table
- New `ProjectVersionRepository` in `Engine/api/repositories.py` with full CRUD
- 3 new API endpoints: `GET /api/projects/{id}/versions`, `GET /api/projects/{id}/versions/{v}`, `POST /api/projects/{id}/rollback/{v}`
- 3 new agent tools: `hie_list_versions`, `hie_get_version`, `hie_rollback_project`
- Rollback restores all items, connections, and routing rules from snapshot
- **6 of 6 guardrails now fully implemented**

**Full CRUD Tools (FR-3, FR-10):**
- 6 new agent tools wiring to existing Manager API update/delete endpoints:
  - `hie_update_item`, `hie_delete_item` — modify/remove items
  - `hie_update_connection`, `hie_delete_connection` — modify/remove connections
  - `hie_update_routing_rule`, `hie_delete_routing_rule` — modify/remove routing rules
- PUT/DELETE support added to `_hie_api_call()` in `agent-runner/app/tools.py`
- RBAC: update/delete available to developer, tenant_admin, platform_admin only

**Environment-Aware Deployment (FR-11):**
- Added `environment` parameter to `hie_deploy_project` tool (staging/production)
- Developers can deploy to staging without approval
- Production deploys by developers still require CSO/Admin approval
- Operators and admins can deploy to any environment directly
- Environment passed through to Manager API and stored in deployment metadata

**Rate Limiting via Redis:**
- New `agent-runner/app/rate_limiter.py` — Redis sliding window counter
- Rate limits enforced per user per category: bash (30/min), file_writes (20/min), api_calls (60/min), hl7_sends (10/min)
- Graceful degradation: fails open if Redis is unavailable
- Wired into `pre_tool_use_hook()` in hooks.py

**Production Hardening:**
- New `DISABLE_DEV_USER` environment variable — when `true`, unauthenticated requests get `viewer` role instead of dev `platform_admin` fallback
- Added `REDIS_URL` to agent-runner config and docker-compose files

### Changed

- `agent-runner/app/tools.py` — PUT/DELETE support, 9 new tool definitions, environment param on deploy
- `agent-runner/app/roles.py` — Permissions for 9 new tools across all 7 roles
- `agent-runner/app/hooks.py` — Environment-aware approval gating, rate limit enforcement
- `agent-runner/app/config.py` — Added REDIS_URL
- `agent-runner/app/main.py` — DISABLE_DEV_USER flag, version bump to 1.9.5
- `Engine/api/repositories.py` — Added ProjectVersionRepository
- `Engine/api/routes/projects.py` — 3 version/rollback endpoints, auto-snapshot on deploy
- `Engine/api/models.py` — Added `environment` field to DeployRequest
- `docker-compose.yml` / `docker-compose.dev.yml` — Added REDIS_URL and DISABLE_DEV_USER env vars

### Version Bumps

All services bumped to **1.9.5**:
- `prompt-manager/app/main.py`
- `agent-runner/app/main.py`
- `Engine/api/server.py`
- `Portal/package.json`

---

## [1.9.4] - 2026-02-13

### Added - Unified RBAC, Demo Onboarding & E2E Lifecycle

**CRITICAL BUG FIX — Role Alignment (Phase 2):**
- Fixed silent role fallback bug: DB roles (`integration_engineer`, `operator`, `auditor`) now correctly mapped to agent-runner role keys (`developer`, `operator`, `auditor`) via `resolve_agent_role()` in `agent-runner/app/roles.py`
- Previously, `integration_engineer` users silently fell back to `viewer` (read-only) because the agent-runner couldn't find the DB role name
- Added `DB_ROLE_TO_AGENT_ROLE` mapping dictionary and `resolve_agent_role()` function
- Added `operator` role: can deploy/start/stop/monitor, but cannot create items/connections/rules
- Added `auditor` role: read-only with audit log access
- Full 7-role RBAC hierarchy: platform_admin → tenant_admin → developer / clinical_safety_officer / operator / auditor / viewer

**Audit Logging (Phase 3 — GR-2 Complete):**
- New `AuditLog` model in `prompt-manager/app/models.py` with tenant/user/session/run context
- New `audit_repo.py` with PII sanitisation — strips NHS numbers (10-digit Modulus 11 pattern) and UK postcodes before storage
- New `/audit` API: `POST /audit` (agent-runner hook), `GET /audit` (filtered list), `GET /audit/stats` (aggregate counts)
- New `002_audit_approvals_tables.py` Alembic migration for `audit_log` + `deployment_approvals` tables
- Agent-runner `post_tool_use_hook()` now POSTs audit entries to prompt-manager after every tool execution
- New Portal audit viewer (`Portal/src/app/(app)/admin/audit/page.tsx`): stats cards, filter tabs (All/Success/Denied/Error), expandable detail rows, CSV export, pagination

**Approval Workflows (Phase 4 — GR-3 Complete):**
- New `DeploymentApproval` model with status lifecycle (pending → approved/rejected)
- New `approval_repo.py` with `approve()` and `reject()` methods, reviewer and timestamp tracking
- New `/approvals` API: create, list, get detail, approve, reject (5 endpoints)
- Agent-runner hook intercept: developer requesting production deploy → creates approval request instead of deploying
- New Portal approvals page (`Portal/src/app/(app)/admin/approvals/page.tsx`): stats cards (pending/approved/rejected), filter tabs, approve/reject buttons with review notes modal, expandable config snapshot detail
- Role-gated: only CSO, Tenant Admin, and Platform Admin can approve/reject

**Demo Onboarding (Phase 4):**
- Added `clinical_safety_officer` role to `scripts/init-db.sql` (UUID `000...007`) with `approvals:approve`, `approvals:reject` permissions
- Added demo tenant: "St Thomas' Hospital NHS Foundation Trust" (code: STH, ODS code: RJ1)
- Added 6 demo users (all with password `Demo12345!`):
  - `trust.admin@sth.nhs.uk` — Sarah Thompson, IT Director (tenant_admin)
  - `developer@sth.nhs.uk` — James Chen, Integration Developer (integration_engineer)
  - `cso@sth.nhs.uk` — Dr. Priya Patel, Clinical Safety Officer (clinical_safety_officer)
  - `operator@sth.nhs.uk` — Mike Williams, Systems Operator (operator)
  - `viewer@sth.nhs.uk` — Emma Davis, Service Desk Analyst (viewer)
  - `auditor@sth.nhs.uk` — Robert Singh, IG Auditor (auditor)
- Added demo workspace: "STH Integrations" linked to STH tenant
- All SQL uses `ON CONFLICT DO NOTHING` for idempotent re-runs in Docker postgres entrypoint

**Guided Lifecycle Stepper (Phase 2):**
- 6-step horizontal stepper in QuickStartPanel: Design → Build → Test → Review → Deploy → Monitor
- Each step auto-generates contextual prompt when clicked
- Steps role-filtered: developers see steps 1-3+6, CSOs see steps 3-4+6, operators see steps 5-6
- State persisted in `sessionStorage` within tab session
- Integration pattern picker (ADT/ORM/ORU/FHIR/Custom) for Design step

**Portal Enhancements:**
- Sidebar: added Approvals (CheckCircle icon) and Audit Log (ClipboardList icon) links
- QuickStartPanel: expanded `AgentRole` type to 7 roles, added `ROLE_DISPLAY` entries for operator (cyan) and auditor (indigo)
- Agents page: explicit capability list blocks for operator and auditor roles

### Changed

- `agent-runner/app/roles.py` — Expanded from 5 to 7 roles with DB-to-agent mapping layer
- `agent-runner/app/main.py` — `extract_user_context()` now resolves DB role names via `resolve_agent_role()`
- `agent-runner/app/agent.py` — Added operator and auditor role preambles
- `agent-runner/app/hooks.py` — Added audit POST integration and approval workflow intercept
- `prompt-manager/app/main.py` — Registered audit and approvals routers
- `scripts/init-db.sql` — Added CSO role, demo tenant, 6 demo users, demo workspace (885 lines total)

### Fixed

**JWT Secret Mismatch (infrastructure bug):**
- `hie-manager` used default JWT secret `hie-dev-secret-key-change-in-production` while agent-runner and prompt-manager used `hie-jwt-secret-key-change-in-production` — all cross-service JWT verification failed with 401
- Added `JWT_SECRET_KEY=hie-jwt-secret-key-change-in-production` to hie-manager environment in `docker-compose.yml` and `docker-compose.dev.yml`

**Prompt-Manager Auth Bugs:**
- Fixed null tenant_id handling: `str(None)` produced string `"None"` instead of Python `None`, crashing DB queries for super_admin users
- Fixed admin role recognition: hardcoded `("admin", "platform_admin")` checks didn't recognise `super_admin` or `tenant_admin` DB role names
- Added `ADMIN_ROLES` set and `is_admin` property to `CurrentUser` class in `prompt-manager/app/auth.py`
- Replaced all hardcoded role checks in `audit.py` and `approvals.py` with `user.is_admin`

**Prompt-Manager Health Endpoint:**
- `/health` returned hardcoded `"version": "1.9.0"` — changed to `app.version`

### Added — E2E Test Suite

- New `tests/e2e/test_v194_rbac_audit_approvals.py` — 38 Docker-based E2E tests covering health, demo login (FR-5), role alignment (GR-1), audit logging (GR-2), approval workflows (GR-3), RBAC regression, Portal pages, and version consistency
- New `scripts/run_e2e_tests.sh` — Docker test runner that builds a test image, mounts tests read-only, and runs inside the compose network using container DNS names
- New Makefile targets: `make test-e2e`, `make test-e2e-v194`, `make test-e2e-smoke`

### Version Bumps

All services bumped to **1.9.4**:
- `pyproject.toml`
- `Portal/package.json`
- `AboutModal.tsx` VERSION constant + version history entry
- `prompt-manager/app/main.py`

### Migration Notes

**Database Recreation Required (for demo users):**
```bash
# If existing data can be reset:
docker compose down -v  # removes postgres_data volume
docker compose up -d    # init-db.sql runs automatically on fresh postgres

# If existing data must be preserved:
docker exec -i hie-postgres psql -U hie -d hie < scripts/init-db.sql
# (ON CONFLICT DO NOTHING ensures idempotency)
```

**Docker Rebuild Required:**
```bash
docker compose build --no-cache hie-agent-runner hie-prompt-manager hie-portal
docker compose up -d
```

### Breaking Changes

None — 100% backward compatible. All SQL uses ON CONFLICT DO NOTHING.

### Files Changed

26 files changed (15 modified + 10 new + 1 deleted)

---

## [1.9.0] - 2026-02-14

### Added - IRIS Message Model, Multi-Protocol Hosts, FHIR REST Stack, Unified Message Tracing

**IRIS Ens.MessageHeader/MessageBody Convention (message_headers + message_bodies):**
- New `message_headers` table: one row per message leg (source→target), mirroring IRIS `Ens.MessageHeader`
- New `message_bodies` table: content storage with body_class_name discriminator, checksum dedup, HL7/FHIR protocol fields
- Migration `004_message_headers_bodies.sql` with full schema, indexes, and architectural documentation
- `store_message_header()`, `store_message_body()`, `update_header_status()` in `message_store.py`
- Per-leg tracing: every hop between config items creates a header row = one arrow on Visual Trace
- Session-based grouping: all legs share a `session_id` (SES-UUID format)

**HL7 Multi-Protocol Hosts & Adapters:**
- `HL7FileService` / `HL7FileOperation` — file-based HL7 inbound/outbound with `InboundFileAdapter` / `OutboundFileAdapter`
- `HL7HTTPService` / `HL7HTTPOperation` — HTTP-based HL7 inbound/outbound with `InboundHTTPAdapter` / `OutboundHTTPAdapter`
- All hosts write per-leg headers to `message_headers` for full Visual Trace support

**FHIR REST Stack:**
- `FHIRRESTService` — inbound FHIR REST endpoint with full URL parsing (read/vread/create/update/patch/delete/search/history/transaction/capabilities)
- `FHIRRESTOperation` — outbound FHIR REST client with OperationOutcome error parsing
- `FHIRRoutingEngine` — routes by resourceType, interaction, bundleType, field values with `FHIRConditionEvaluator`
- `FHIRMessage` in-memory container with `get_field()`, `with_header_id()`, session/header/body ID tracking
- IRIS aliases: `HS.FHIRServer.Interop.Service`, `HS.FHIR.REST.Operation`, `HS.FHIRServer.Interop.Process`

**Unified Message Listing (UNION ALL):**
- `list_by_project()` now queries `message_headers` (v2) UNION ALL `portal_messages` (v1) — all legs visible in Messages tab
- `list_sessions()` now queries `message_headers` (v2) UNION ALL `portal_messages` (v1) — all sessions visible in Topology pane
- Column mapping: v2 fields (source_config_name, time_created, etc.) mapped to v1 field names the frontend expects
- Deduplication: portal_messages sessions excluded if they also exist in message_headers

**Visual Trace V1/V2 Support:**
- `get_session_trace()` primary path: `message_headers` (v2) with per-leg arrows
- Fallback path 1: `portal_messages` by `session_id` (v1, old sessions with SES- prefix)
- Fallback path 2: `portal_messages` by message `id` (v1, old rows with NULL session_id)
- `trace_version` field in API response indicates which data source was used
- Frontend `buildSequenceDiagramV1` restored for rendering legacy portal_messages trace data
- `SessionTrace` interface accepts both `PortalMessage | TraceMessage` union

**E2E Test Suite:**
- `tests/e2e/test_visual_trace_e2e.py` — 11 async tests covering full HL7 pipeline
- `tests/e2e/run_visual_trace_e2e.sh` — bash script for quick manual verification (9 tests)
- Tests cover: MLLP send → message_headers creation → body storage → trace API → V1 fallback paths → 404 handling

**Documentation:**
- `docs/architecture/MESSAGE_HEADER_BODY_REDESIGN.md` — v2.1 design document (implemented)
- `docs/architecture/MULTI_PROTOCOL_HOSTS_AND_FHIR_DESIGN.md` — v2.0 design document (implemented)

### Changed

- **Visual Trace Layout** — Equal row spacing (70px per message) instead of time-proportional Y positioning; arrows and labels never overlap regardless of timing differences
- **SequenceTimeline** — Row-based time markers aligned with each message arrow instead of fixed 500ms interval ticks
- **_serialize_message()** — Added `Decimal` handling for PostgreSQL aggregate values (success_rate)
- **Messages tab** — Now shows all pipeline legs (PAS-In, ADT_Router, EPR_Out, RIS_Out, ACKs), not just Testharness
- **Topology Message pane** — Now shows sessions from message_headers with correct message counts

### Fixed

- Messages tab only showing Testharness messages (portal_messages was the sole data source, but HL7 hosts write to message_headers)
- Visual Trace "Session not found" error for old messages (V1 fallback was removed too aggressively)
- Visual Trace showing only single Testharness message instead of full pipeline (frontend passed msg.id when session_id was NULL)
- All message arrows stacking on same horizontal line in Visual Trace (time differences within a session are sub-millisecond)
- `Decimal` serialization error in sessions list API (PostgreSQL ROUND returns Decimal, not float)

### Migration Notes

**Database Migration Required:**
```bash
docker exec -i hie-postgres psql -U hie -d hie < scripts/migrations/004_message_headers_bodies.sql
```

**Docker Rebuild Required:**
```bash
docker compose build --no-cache hie-manager hie-portal
docker compose up -d
```

### Version Bumps

All services bumped to **1.9.0**:
- `Portal/package.json`
- `pyproject.toml`
- `AboutModal.tsx` VERSION constant + version history entry

### Breaking Changes

None — 100% backward compatible. Old portal_messages data continues to work via V1 fallback.

---

## [1.8.2] - 2026-02-12

### Added - IRIS HealthConnect-Style Message Sequence Diagram

**Message Sequence Visualization:**
- IRIS HealthConnect-style sequence diagram with vertical swimlanes and horizontal message flow arrows
- Real-time session tracking via `session_id` column in `portal_messages` table
- Interactive SVG rendering with Bezier curves, zoom controls (In/Out/Fit), and JSON export
- Auto-refresh capability (10-second intervals) for live session monitoring
- Millisecond-precision timeline with vertical time axis
- Activity icon on Messages page for instant one-click access to sequence diagrams

**Backend API Endpoints:**
- `GET /api/projects/{id}/sessions` — List message sessions with aggregated metadata (count, time range, success rate, message types)
- `GET /api/sessions/{id}/trace` — Retrieve complete trace data with ordered messages and unique item extraction
- Session filtering by item name with pagination support (limit/offset)
- Performance optimized: <200ms for 100 sessions, <500ms for 50-message traces

**Database Schema:**
- `session_id` VARCHAR(255) column added to `portal_messages` table
- Optimized index `idx_portal_messages_session` for session queries
- Migration script `scripts/migrations/001_add_session_id.sql`
- Automatic population of 49 existing messages with generated session IDs

**Frontend Components:**
- `SessionListView.tsx` — Session list with metadata cards (message count, time range, success rate, message types)
- `MessageSequenceDiagram.tsx` — SVG-based sequence visualization with zoom/pan controls
- `SequenceSwimlane.tsx` — Individual swimlane columns sorted by type (service → process → operation)
- `SequenceArrow.tsx` — Message flow arrows with timing labels (+450ms) and transformation indicators
- `SequenceTimeline.tsx` — Vertical time axis with 500ms interval markers
- Complete TypeScript type safety with `SessionSummary`, `SessionTrace`, and `SequenceDiagramData` interfaces

**Test Suites:**
- `tests/integration/test_session_trace_api.py` — Unit tests for repository methods and API endpoints
- `tests/e2e/test_sequence_diagram_flow.py` — End-to-end workflow tests and performance benchmarks
- `docs/TESTING_SEQUENCE_DIAGRAM.md` — Comprehensive testing guide with manual procedures and CI/CD examples
- 90%+ test coverage for new code

**Documentation:**
- `docs/SEQUENCE_DIAGRAM_DELIVERY.md` — Complete feature delivery summary with success criteria
- `docs/TESTING_SEQUENCE_DIAGRAM.md` — Testing procedures, sample data, and troubleshooting
- `RELEASE_NOTES.md` — Detailed release notes with migration guide and user/developer guides

### Changed

- **ItemDetailPanel** — Made resizable with drag handle (400-800px width range), width persisted in localStorage
- **Metrics Tab** — Fixed overflow with responsive grid layout (2 columns at 400px, 3 columns at 600px+)
- **Messages Tab** — Added sub-tabs: "All Messages" (existing list) | "Message Sessions" (new sequence diagram access)
- **Messages Page** — Added blue Activity icon to each message row for direct sequence diagram access
- **Panel Overflow** — Added horizontal scroll (`overflow-x: auto`) to prevent content cutoff
- **Version Numbers** — Bumped to 1.8.2 in `Portal/package.json` and `pyproject.toml`

### Fixed

- Panel width overflow causing Metrics tab content to render beyond right edge
- TypeScript compilation error: `Property 'session_id' does not exist on type 'PortalMessage'`
- TypeScript compilation error: `Type 'null' is not assignable to type 'SequenceMessage'` in message mapping
- Docker build cache preventing code updates (required `--no-cache` flag)
- Browser cache preventing new code visibility (required hard refresh Cmd+Shift+R)
- Message status mapping inconsistencies between API statuses ('sent'/'completed'/'failed') and UI states

### Removed

- **Mock Data Generators:**
  - `generateMockSessionData()` from SessionListView.tsx
  - `generateMockSequenceData()` from MessageSequenceDiagram.tsx
  - `generateMockMessages()` from ItemDetailPanel.tsx
  - All components now use 100% real API data

### Performance

- **Session List API:** <200ms response time for 100 sessions ✅
- **Trace API:** <500ms response time for 50 messages per session ✅
- **Frontend Rendering:** <2 seconds for diagram with 10 swimlanes ✅
- **Database Queries:** <100ms with optimized indexes ✅
- **Handles large sessions:** 100+ message sessions tested successfully

### Security

- SQL injection protection via parameterized queries in all repository methods
- XSS prevention through React automatic escaping (no `dangerouslySetInnerHTML`)
- No PHI/PII exposure (only message IDs, types, and metadata displayed)
- Existing authentication/authorization mechanisms fully respected
- CORS configuration uses existing security settings from `hie-manager` service

### Migration Notes

**Database Migration Required:**
```bash
docker exec -i hie-postgres psql -U hie -d hie < scripts/migrations/001_add_session_id.sql
```

**Docker Rebuild Required:**
```bash
docker compose build hie-portal hie-manager --no-cache
docker compose up -d
```

**Verification Steps:**
1. Navigate to http://localhost:3000/messages
2. Click Activity icon (⚡) on any message
3. Verify sequence diagram renders with swimlanes and arrows
4. Test zoom controls and export functionality

---

## [1.7.5] - 2026-02-11

### Added - End-to-End Message Routing Pipeline

**Message Routing Implementation:**
- `Host._production` reference for inter-host message forwarding via `ProductionEngine`
- `BusinessService.send_to_targets()` forwards messages from inbound services to configured targets
- `HL7TCPService._process_message()` calls `send_to_targets()` after ACK
- `HL7RoutingEngine._route_to_target()` submits routed messages to target hosts
- `EngineManager.deploy()` wires connections (UUID→name resolution) and routing rules into engine
- `ConditionEvaluator._translate_iris_paths()` converts IRIS virtual property paths to field references
- All-match rule evaluation: collects targets from ALL matching rules (not first-match-wins)

**Message Storage for All Host Types:**
- `HL7RoutingEngine._store_routing_message()` — process hosts now visible in Portal Messages tab
- `HL7TCPOperation._store_outbound_message()` — outbound operations now visible in Portal Messages tab
- `ManagedQueue.put_nowait()` and `join()` methods for queue interface completeness

**Portal — Routing Rules UI:**
- Routing Rules tab on project page with full CRUD (create, edit, delete, list)
- Condition expression editor, target item selection, priority ordering
- Rule count badge on tab header

**Documentation:**
- `docs/MESSAGE_ROUTING_WORKFLOW.md` — complete workflow implementation details
- `docs/RELEASE_NOTES_v1.7.5.md` — detailed release notes

### Fixed

- Connection UUID resolution in `EngineManager.deploy()` (source_item_id/target_item_id → names)
- IRIS condition syntax not recognized by `ConditionEvaluator` (HL7.MSH:MessageType → {MSH-9.1})
- First-match-wins routing prevented multi-target delivery for ADT^A01
- Routing rules API rejected item names (changed `target_items` from `list[UUID]` to `list[str]`)
- JSONB parsing for `target_items` in `get_full_config` and `RoutingRuleRepository`
- `ManagedQueue` missing `put_nowait` and `join` methods
- Extra closing parenthesis in Portal configure page

---

## [1.8.0] - 2026-02-11

### Added - Developer Platform, Agent HIE Skills, Class Namespace Enforcement

**Class Namespace Convention Enforcement** (core product protection):
- `PROTECTED_NAMESPACES` (`li.*`, `Engine.li.*`, `EnsLib.*`) — runtime-enforced, developers cannot register classes here
- `CUSTOM_NAMESPACE_PREFIX` (`custom.*`) — all developer extensions must use this namespace
- `ClassRegistry._validate_custom_namespace()` raises `ValueError` on protected namespace violations
- `ClassRegistry._register_internal()` for core engine class registration (bypasses validation)
- `register_host()`, `register_transform()`, `register_rule()` now validate namespace before registering
- `is_protected_namespace()` / `is_custom_namespace()` helper methods on ClassRegistry
- Fixed `get_or_import_host_class()` caching to use `_register_internal` for dynamic imports
- Fixed IRIS alias: `EnsLib.HL7.MsgRouter.RoutingEngine` → `li.hosts.routing.HL7RoutingEngine`
- Core class registrations in `hl7.py` and `routing.py` switched to `_register_internal()`

**Custom Developer Extension Framework** (`Engine/custom/`):
- `Engine/custom/__init__.py` — `@register_host` and `@register_transform` decorators with namespace validation
- `load_custom_modules()` auto-discovers and imports all modules in `Engine/custom/` at startup
- `ProductionEngine._create_hosts()` calls `load_custom_modules()` before host instantiation
- `Engine/custom/nhs/validation.py` — `custom.nhs.NHSValidationProcess` reference implementation:
  - NHS Number validation (Modulus 11 check digit algorithm)
  - PDS demographic lookup stub (FHIR API ready)
  - Duplicate message detection (sliding window)
  - UK postcode validation
  - Configurable fail mode: `nack_and_exception_queue` or `warn_and_continue`
- `Engine/custom/_example/example_process.py` — copy-paste template for developers

**Agent HIE Skills** (16 tools, was 10):
- New tools: `hie_list_workspaces`, `hie_create_workspace`, `hie_create_project`, `hie_create_routing_rule`, `hie_start_project`, `hie_stop_project`, `hie_project_status`
- Tools reorganized into `STANDARD_TOOLS` + `HIE_TOOLS` with namespace convention documentation
- All tool descriptions include class namespace guidance and IRIS equivalents
- `execute_tool()` handlers for all 16 tools with proper request body construction

**Agent System Prompt & Skills**:
- System prompt rewritten with IRIS-aligned architecture table
- Class namespace convention section (CRITICAL rules)
- Core class catalog with IRIS equivalents
- 10-step end-to-end route creation workflow
- ReplyCodeActions syntax reference
- `hl7-route-builder` skill v2.0: complete e2e examples, HL7 field reference, routing rule syntax

**GenAI Sessions** (Portal + Engine):
- GenAI sessions models, repositories, and API routes in Engine
- `002_genai_sessions.sql` migration
- Portal `/api/genai-sessions/` proxy
- `AppContext` for shared state across Portal pages
- Agent and Chat pages updated with session persistence

**Documentation**:
- `docs/guides/CUSTOM_CLASSES.md` — **New**: namespace rules, quick start, base class reference, Docker volume mount, IRIS comparison
- `docs/guides/LI_HIE_DEVELOPER_GUIDE.md` — Revised: expanded 3+2+3 route topology, FHIR inbound, agent guide section
- `docs/guides/NHS_TRUST_DEMO.md` — Revised: matching 3-inbound/2-process/3-outbound architecture
- `docs/DEVELOPER_WORKFLOW_SCENARIOS.md` — **New**: 8 developer/user workflow scenarios comparing HIE to IRIS/Rhapsody/Mirth

### Version Bumps

All services bumped to **1.8.0**:
- `agent-runner` FastAPI app + `/health` endpoint
- `prompt-manager` FastAPI app + `/health` endpoint
- `codex-runner` Express app + `/health` endpoint
- `Portal/package.json`
- `AboutModal.tsx` VERSION constant + version history entry

### Breaking Changes

None — 100% backward compatible with v1.7.3 configurations.

### Remaining Work (this branch)

- E2E testing: Agent conversation → HIE Engine API → production running
- Verify Manager API endpoints exist for all new tools (`/routing-rules`, `/start`, `/stop`, `/status`)
- Additional skills: `fhir-mapper`, `clinical-safety-review`, `nhs-compliance-check`, `integration-test`
- Portal UI: Show `custom.*` vs `li.*` distinction in item type picker
- Hot reload for custom classes without full engine restart

---

## [1.7.3] - 2026-02-11

### Added - Data-Driven Seed System, Hooks Config API, UI/UX Fixes

**Data-Driven Seed System** (replaces hardcoded Python templates):
- `prompt-manager/seeds/templates.json`: 10 healthcare integration templates (HL7 ADT/ORM/ORU routes, FHIR UK Core Patient Bundle, Clinical Safety Review DCB0129, NHS Compliance Audit, Integration Test Plan, Weekly Status Report, API Design Specification, FHIR Resource Mapping)
- `prompt-manager/seeds/skills.json`: 5 platform skills (hl7-route-builder, fhir-mapper, clinical-safety-review, nhs-compliance-check, integration-test)
- `POST /seed/templates` endpoint: Loads templates from JSON, idempotent (skips existing by name)
- `POST /seed/skills` endpoint: Loads skills from JSON, idempotent (skips existing by slug)
- Removed all hardcoded `SEED_TEMPLATES` from `prompt-manager/app/main.py`
- Updated `prompt-manager/Dockerfile` to `COPY seeds/` directory into container

**Hooks Configuration API** (fixes browser save error):
- `GET /hooks/config` on agent-runner: Returns current hooks configuration with sensible defaults
- `POST /hooks/config` on agent-runner: Saves hooks configuration to persistent JSON file
- Default config includes: security (blocked patterns, HL7 validation, TLS), audit (agent actions, message access, config changes), NHS compliance (NHS number detection, PII, data retention), clinical safety (message integrity, ACK confirmation, message loss alerts)
- Persistent storage at `/app/hooks_config.json` inside container

**Portal UI Enhancements**:
- **Prompts page**: "Load Samples" button in header + "Load Sample Templates" / "Create from Scratch" in empty state
- **Skills page**: "Load Samples" button in header + "Load Sample Skills" in empty state
- **Agents page**: Thread creation now sends workspace metadata (`workspaceId`, `workspaceName`, `projectId`, `runnerType`, `skipGitRepoCheck`) instead of filesystem paths
- **Agents page**: Error handler supports both codex (`parsed.message`) and claude (`parsed.payload?.message`) runner formats
- **Portal proxy**: POST handler gracefully handles no-body requests for seed endpoints

### Fixed

- **Platform data visibility**: `list_latest` in both `template_repo.py` and `skill_repo.py` now includes platform items (`tenant_id=NULL`) alongside tenant-specific items using `OR` filter. Previously, seeded templates/skills with no tenant were invisible to authenticated users.
- **Hooks save error**: Browser error when saving hooks configuration resolved by adding `GET`/`POST /hooks/config` endpoints to agent-runner.
- **Agents page crash**: Thread creation no longer sends filesystem paths; uses HIE workspace metadata instead.
- **Import ordering**: Cleaned up stdlib imports in `agent-runner/app/main.py`.

### Version Bumps

All services bumped to **1.7.3**:
- `agent-runner` FastAPI app + `/health` endpoint
- `prompt-manager` FastAPI app + `/health` endpoint
- `codex-runner` Express app + `/health` endpoint
- `Portal/package.json`
- `AboutModal.tsx` VERSION constant + version history entry
- Sidebar footer auto-updates via `VERSION` import

### Files Changed (11 files, ~500 insertions, ~216 deletions)

**New Files (2):**
- `prompt-manager/seeds/templates.json` (277 lines)
- `prompt-manager/seeds/skills.json` (267 lines)

**Modified Files (9):**
- `agent-runner/app/main.py` — Hooks config endpoints, version bump, import cleanup
- `prompt-manager/app/main.py` — Remove hardcoded seeds, add seed API, version bump
- `prompt-manager/app/repositories/template_repo.py` — Platform data visibility fix
- `prompt-manager/app/repositories/skill_repo.py` — Platform data visibility fix
- `prompt-manager/Dockerfile` — COPY seeds directory
- `Portal/src/app/(app)/prompts/page.tsx` — Load Samples button
- `Portal/src/app/(app)/admin/skills/page.tsx` — Load Sample Skills button
- `Portal/src/app/(app)/agents/page.tsx` — Workspace metadata + error handler fix
- `Portal/src/app/api/prompt-manager/[...path]/route.ts` — No-body POST support

### Breaking Changes

None - 100% backward compatible.

---

## [1.7.2] - 2026-02-11

### Added - E2E & Unit Test Suite (ported from saas-codex)

**Unit Tests** (`agent-runner/tests/`, 21 tests):
- Security hooks: rm -rf, sudo, chmod 777, fork bomb, curl|bash blocking
- Path escape: ../ and ..\\ traversal blocking, absolute path outside /workspaces
- Clinical safety: DROP TABLE, DELETE FROM patient, TRUNCATE blocking
- Pattern count verification: >=10 bash, >=2 path, >=4 SQL patterns
- Post-tool audit hook validation

**E2E Test Script** (`scripts/test_genai_features.sh`, 26 tests):
- Service health checks: agent-runner, codex-runner, prompt-manager, Portal
- Portal proxy routes: agent-runner, codex-runner, prompt-manager forwarding
- Skills system: loader, directory, events, tools module verification
- Hooks system: module, pattern counts, rm -rf/path escape/safe command/SQL injection
- Thread/run lifecycle: thread creation, invalid threadId 404, empty prompt 400, invalid runId 404
- Prompt Manager API: list templates, list skills, categories endpoint

**E2E Python Tests** (`tests/genai/`):
- `test_sse_streaming.py`: Runner health, Portal proxy, thread lifecycle, error handling
- `test_prompt_manager_api.py`: Template CRUD (create/get/update/publish/render/clone/delete), skills CRUD, categories
- `test_hooks.py`: Mirror of agent-runner unit tests for project-level reference

### Fixed

- **Portal proxy routing** (`next.config.js`): Rewrites were routing ALL `/api/*` to Manager API, blocking GenAI proxy routes. Fixed with `afterFiles`/`fallback` pattern so `/api/agent-runner`, `/api/codex-runner`, `/api/prompt-manager` hit Next.js API route handlers first.
- **Prompts page TypeScript error** (`prompts/page.tsx`): `Set` iteration `downlevelIteration` error fixed with `Array.from()`.
- **Agent runner Docker image**: Added pytest, pytest-asyncio, httpx to requirements; tests directory copied into image.

## [1.7.1] - 2026-02-11

### Added - Multi-Runner Architecture (Codex + Claude, plug-and-play)

**Codex Runner Service** (`codex-runner/`, port 9342):
- Node.js/TypeScript Express server using OpenAI Codex SDK (`@openai/codex-sdk`)
- Identical API contract to agent-runner: `POST /threads`, `POST /runs`, `GET /runs/:id/events`
- SSE streaming with event buffering and subscriber management
- Workspace path resolution and security validation
- Dockerfile with Codex CLI global install and config

**Runner Factory / Dispatch Pattern**:
- `getRunnerApiBase(runnerType)` dispatches to `/api/codex-runner` or `/api/agent-runner`
- Both runners expose identical API contracts for plug-and-play interoperability
- Thread/session state cleared on runner switch (different backends)
- Coming-soon runners blocked with alert: Gemini, Azure OpenAI, AWS Bedrock, OpenLI Agent, Custom

**Portal Frontend Updates**:
- `/api/codex-runner/[...path]` proxy route to codex-runner service with SSE support
- Agents page: full RUNNERS array (7 runners), dispatch to correct backend, clear state on switch
- Chat page: runner selector dropdown, dispatch to correct backend per session
- RunnerType expanded: claude, codex, gemini, azure, bedrock, openli, custom

**Docker Compose** (`docker-compose.yml`):
- Added hie-codex-runner service (9342:8081) with CODEX_API_KEY, OPENAI_API_KEY env vars
- Added CODEX_RUNNER_URL to Portal environment
- Added hie_workspaces shared volume for runner workspace access

## [1.7.0] - 2026-02-11

### Added - Full-Stack GenAI Backend Services (ported from saas-codex)

**Agent Runner Service** (`agent-runner/`, port 9340):
- FastAPI microservice for Claude/Anthropic agent execution with SSE streaming
- Thread/run lifecycle management with PostgreSQL persistence
- HIE-specific skills: hl7-route-builder, fhir-mapper, clinical-safety-review, nhs-compliance-check, integration-test
- Pre/post execution hooks for security, audit, compliance, and clinical safety
- Configurable tools, events system, and workspace context
- Dockerfile, requirements.txt, full app structure

**Prompt Manager Service** (`prompt-manager/`, port 9341):
- FastAPI microservice for prompt template and skill management
- Full CRUD with versioning, publishing, and category filtering
- Healthcare-specific categories: hl7, fhir, clinical, compliance, integration
- Skill sync-from-files for importing agent-runner SKILL.md files
- Usage logging and analytics endpoints
- Alembic migrations, async SQLAlchemy ORM, JWT auth forwarding
- Auto-seeding of HIE-specific prompt templates on startup

**Database Schema Additions** (`scripts/init-db.sql`):
- agent_sessions, agent_runs, agent_run_events, agent_messages tables
- hooks_config table with seed data for default security/audit/compliance hooks
- prompt_templates, skills, template_usage_log tables
- Indexes, triggers, and updated_at auto-update functions

**Portal Frontend Rewiring**:
- `/api/prompt-manager/[...path]` proxy route to prompt-manager service
- `/api/agent-runner/[...path]` proxy route with SSE streaming support
- New Prompts page (`/prompts`) with template CRUD, variable filling, preview, and "Send to Agent" flow
- Agents page rewired to agent-runner SSE streaming (thread → run → events)
- Chat page rewired to agent-runner SSE streaming with session persistence
- Skills page rewired to prompt-manager /skills API (DB-backed CRUD, sync-from-files)
- Hooks page rewired to agent-runner /hooks/config API (DB-backed load/save)
- Sidebar navigation updated with Prompts tab under GenAI section

**Docker Compose** (`docker-compose.yml`):
- Added hie-agent-runner service (9340:8082)
- Added hie-prompt-manager service (9341:8083)
- Portal environment updated with PROMPT_MANAGER_URL and AGENT_RUNNER_URL
- Skills volume mount: agent-runner/skills → prompt-manager /app/skills:ro

## [1.6.0] - 2026-02-11

### Added - OpenLI Rebrand, GenAI Agent Tabs, License & Skills/Hooks

**Rebranding to OpenLI HIE** (borrowed from saas-codex):
- Rebranded entire Portal UI from "HIE" to "OpenLI HIE - OpenLI Healthcare Integration Engine"
- New favicon.svg with NHS blue gradient and "LI" text (borrowed from saas-codex)
- Updated layout.tsx metadata with icons, applicationName, keywords, and description
- Sidebar logo updated: "LI" icon with NHS blue gradient, "OpenLI HIE" title
- AboutModal updated: v1.6.0, new product name, GenAI features listed
- TopNav About button tooltip updated
- Copyright updated to "Lightweight Integration Ltd"

**Dual License Strategy** (borrowed from saas-codex):
- New LICENSE file with AGPL-3.0 (community) + Commercial dual license
- Community license for organizations below £250K GBP annual revenue
- Commercial license tiers: SME (£500/yr), Enterprise (custom), NHS Trust (custom)
- Trademark notice for "OpenLI" and "OpenLI HIE" marks
- Contributor License Agreement included
- Healthcare disclaimer for regulatory compliance
- Contact: zhong@li-ai.co.uk

**GenAI Agent Console** (`/agents`) (borrowed & customized from saas-codex codex page):
- Full agent console for natural language HIE route configuration
- Workspace → Project selector with HIE hierarchy context
- Agent runner selector (Claude, Codex, Gemini, Custom)
- Transcript and Raw Events view modes
- Quick prompts for common HIE operations (HL7 receivers, MLLP senders, routing)
- Real-time streaming architecture (ready for backend connection)
- HIE context panel showing workspace, project, status, and item count

**Chat Interface** (`/chat`) (borrowed & customized from saas-codex chat page):
- Conversational interface for HIE integration building
- Session management with workspace/project scoping
- Message bubbles with user/assistant/tool/system roles
- Tool call display with expandable input/output details
- Simulated responses for route configuration, system status, and general help
- Markdown-formatted responses with code blocks and tables

**Integration Skills Management** (`/admin/skills`) (borrowed & customized from saas-codex skills page):
- 7 pre-built HIE integration skills: HL7 Route Builder, FHIR Integration, MLLP Connectivity, Content-Based Routing, NHS Trust Deployment, Message Transform, Production Monitoring
- Skills categorized by: protocol, routing, transform, monitoring, deployment, general
- Scope filtering: platform, tenant, project
- Full CRUD: create, view, edit, delete skills
- Skill content editor with markdown support
- Detailed skill content with example configurations and workflow steps

**Hooks Configuration** (`/admin/hooks`) (borrowed & customized from saas-codex hooks page):
- Platform hooks: Security (blocked patterns, HL7 validation, TLS enforcement), Audit (agent actions, message access, config changes)
- Tenant hooks: NHS Compliance (NHS number detection, PII detection, data retention), Clinical Safety (message integrity, ACK confirmation, message loss alerts)
- Configurable blocked command patterns with add/remove
- NHS-specific compliance references (DTAC, DSPT, DCB0129/DCB0160)
- Info box explaining hooks architecture and restart requirements

**Sidebar Navigation Updates**:
- New "GenAI" section with Agents (Bot icon) and Chat (MessagesSquare icon)
- Admin section expanded with Skills (BookOpen icon) and Hooks (Webhook icon)
- Footer updated to "OpenLI HIE v1.6.0 - Healthcare Integration Engine"

**Files Added** (~3000 lines):
- `Portal/public/favicon.svg` - OpenLI favicon with NHS blue gradient
- `Portal/src/app/(app)/agents/page.tsx` - GenAI Agent Console
- `Portal/src/app/(app)/chat/page.tsx` - Chat Interface
- `Portal/src/app/(app)/admin/skills/page.tsx` - Skills Management
- `Portal/src/app/(app)/admin/hooks/page.tsx` - Hooks Configuration
- `LICENSE` - Dual license (AGPL-3.0 + Commercial)

**Files Modified** (~200 lines):
- `Portal/src/app/layout.tsx` - Favicon, metadata, OpenLI branding
- `Portal/src/components/Sidebar.tsx` - GenAI/Admin sections, OpenLI branding
- `Portal/src/components/AboutModal.tsx` - v1.6.0, OpenLI branding, GenAI features
- `Portal/src/components/TopNav.tsx` - About tooltip update
- `CHANGELOG.md` - This entry

## [1.5.1] - 2026-02-10

### Added - Portal UI Uplift (About, Theme Mode, Collapsible Sidebar)

**About Modal with Version History** (borrowed from saas-codex):
- New AboutModal component with HIE information and 7 releases documented
- Info button added to top toolbar for easy access
- Two tabs: About (features, tech stack, capabilities) and Version History (v1.5.1 → v1.0.0)
- Responsive design with dark mode support

**Theme Mode Switcher** (borrowed from saas-codex):
- Three-mode switcher: Light, Dark, and System (auto-detect)
- ThemeProvider with localStorage persistence and system preference detection
- Theme switcher component added to top toolbar
- Full Tailwind dark mode integration throughout Portal

**Collapsible Sidebar** (borrowed from saas-codex):
- Toggle button to collapse/expand sidebar (16px ↔ 64px)
- Icon-only mode when collapsed with tooltips
- Smooth transitions (300ms)
- Mobile responsive overlay with slide-in animation

**Files Added** (560 lines):
- Portal/src/components/AboutModal.tsx (430 lines)
- Portal/src/components/ThemeProvider.tsx (67 lines)
- Portal/src/components/ThemeSwitcher.tsx (63 lines)

**Files Modified** (~200 lines):
- Portal/src/components/TopNav.tsx - About button + theme switcher
- Portal/src/components/AppShell.tsx - ThemeProvider wrapper + collapsible sidebar state
- Portal/src/components/Sidebar.tsx - Collapse functionality + dark mode
- Portal/tailwind.config.ts - Dark mode: "class" configuration

### Design Attribution

UI patterns borrowed from saas-codex/frontend/src/components/:
- AboutModal structure and styling
- ThemeProvider context pattern
- ThemeSwitcher three-button toggle
- Collapsible sidebar pattern
- Dark mode Tailwind classes

### Breaking Changes

None - 100% backward compatible.

---

## [1.5.0] - 2026-02-10

### Added - Phase 4 Meta-Instantiation & Message Envelope System

**Universal Meta-Instantiation:**
- New `Engine/core/meta_instantiation.py` module (248 lines)
  - `ImportPolicy` class for security boundaries (whitelist/blacklist packages)
  - `MetaInstantiator` class for dynamic class importing with caching
  - Global instantiators pre-configured for hosts, adapters, transforms
  - Security: Blocks dangerous modules (os, sys, subprocess, pickle)
  - Performance: <1ms cached imports, ~10ms first import
- ANY Python class can now be instantiated from configuration by fully qualified name
- Zero pre-registration required (automatic import fallback)
- Examples: `Engine.li.hosts.hl7.HL7TCPService`, `demos.nhs_trust.lib.NHSValidationProcess`, `custom.my_org.MyCustomRouter`

**Protocol-Agnostic Message Envelope:**
- New `Engine/core/message_envelope.py` module (383 lines)
  - `MessageHeader`: Core identity, routing, and schema metadata (content_type, schema_version, body_class_name)
  - `MessageBody`: Payload with lazy parsing and validation state tracking
  - `MessageEnvelope`: Complete envelope with parse() and validate() methods
  - Factory methods: `create_hl7()`, `create_fhir()`, `create_custom()`
  - `from_legacy_message()`: Phase 3 backward compatibility
- Schema-aware messaging enables runtime dynamic parsing
- Support for HL7, FHIR, JSON, XML, and custom protocols
- Validation state tracked with error lists

**Enhanced ClassRegistry:**
- Added `get_or_import_host_class()` method to `Engine/li/registry/class_registry.py`
- Automatic fallback strategy: Try registry first (fast) → dynamic import (flexible) → raise error
- Auto-caching of dynamically imported classes for performance
- Eliminates need for manual class registration

**NHS Trust Demo:**
- New comprehensive demo: `demos/nhs_trust/` (2,086 lines total)
- `README.md` (715 lines): Complete walkthrough with architecture diagram, Portal UI steps, deployment guide
- `config/nhs_acute_trust_production.json` (313 lines): 8-item production configuration
- `lib/nhs_validation_process.py` (262 lines): NHS number, postcode, date validation
- `scripts/deploy_production.py` (371 lines): Automated deployment script
- `test_data/*.hl7` (5 files): Sample ADT messages including invalid cases

**Documentation:**
- New `docs/architecture/META_INSTANTIATION_UPLIFT_PLAN.md` (1,433 lines): Complete Phase 4 implementation plan
- New `docs/PRODUCT_ROADMAP.md` (1,791 lines): Phase 4-6 detailed roadmap
- New `docs/architecture/SCALABILITY_ARCHITECTURE.md` (884 lines): Technical scalability assessment
- New `docs/architecture/MESSAGE_ENVELOPE_DESIGN.md` (1,195 lines): Complete envelope pattern design
- New `docs/guides/LI_HIE_DEVELOPER_GUIDE.md` (800 lines): Developer guide
- New `docs/guides/NHS_TRUST_DEMO.md` (538 lines): Demo walkthrough
- Updated `docs/architecture/message-model.md`: Revised to reflect Phase 4 design

### Changed

**ProductionEngine:**
- Updated `_create_host_from_config()` in `Engine/li/engine/production.py`
- Now uses `get_or_import_host_class()` for universal instantiation
- Removed hardcoded class name mappings (HL7TCPService, HL7TCPOperation, HL7RoutingEngine)
- Better error logging with class name and error details

**Host Base Class:**
- Added `on_message_envelope()` method to `Engine/li/hosts/base.py` (Phase 4 optional)
- Added `on_process_message_content()` method (Phase 4 optional)
- Hosts can now opt-in to Phase 4 envelope support
- Default implementation delegates to existing `_process_message()` for backward compatibility
- Automatic parsing based on header content_type

**Architecture Documentation:**
- Moved and updated `docs/ARCHITECTURE_QA_REVIEW.md` → `docs/architecture/ARCHITECTURE_QA_REVIEW.md`
- Moved and updated `docs/IMPLEMENTATION_OPTIMIZATION_PLAN.md` → `docs/architecture/IMPLEMENTATION_OPTIMIZATION_PLAN.md`
- Updated status: Phase 1-3 now 100% COMPLETE
- Assessment: Production-ready for single-node NHS Trust deployments (10K-50K msg/sec)

### Technical Specifications

**Performance:**
- Meta-instantiation: <1ms cached, ~10ms first import
- Message envelope parsing: <1ms with caching
- Single-node throughput: 10,000-50,000 msg/sec (unchanged)

**Backward Compatibility:**
- 100% backward compatible with Phase 3 Message class
- Existing `_process_message()` implementations continue to work
- Phase 3 Message can be converted to Phase 4 MessageEnvelope via `from_legacy_message()`
- Gradual migration path - update hosts one at a time

**Security:**
- ImportPolicy blocks dangerous modules by default
- Whitelist approach for custom packages: Engine.*, demos.*, custom.*
- Base class validation: Imported hosts must inherit from Host base class

### Production Capabilities

**Current (Phase 4):**
- ✓ 10,000-50,000 msg/sec (single-node, multiprocess)
- ✓ Universal class loading (Engine.*, demos.*, custom.*)
- ✓ Protocol-agnostic messaging (HL7, FHIR, JSON, XML, custom)
- ✓ Enterprise execution modes (multiprocess, thread pools, priority queues)
- ✓ Auto-restart policies (never, always, on_failure)
- ✓ Hot reload configuration (without restart)
- ✓ Messaging patterns (async/sync reliable, concurrent async/sync)

**Future (Phase 5-6):**
- → NHS Spine integration (PDS, SCR, EPS, MESH)
- → FHIR R4 support (transformation, REST API, validation)
- → Distributed tracing (Jaeger)
- → Circuit breakers, rate limiting
- → Kafka sharding (1M+ msg/sec)
- → Multi-region deployment
- → ML-based routing
- → Target: 1B+ messages/day

### Migration Guide

**No migration required** - Phase 3 code continues to work unchanged.

**To adopt Phase 4 envelopes (optional):**

Before (Phase 3):
```python
# Manual registration
ClassRegistry.register_host("li.hosts.hl7.HL7TCPService", HL7TCPService)

# Simple message
message = Message(raw=b"MSH|...", content_type="application/hl7-v2+er7")

# Manual parsing
async def _process_message(self, message):
    if message.content_type == "application/hl7-v2+er7":
        parsed = HL7Message.parse(message.raw)
```

After (Phase 4):
```python
# No registration needed
config = ItemConfig(class_name="Engine.li.hosts.hl7.HL7TCPService")
# or custom:
config = ItemConfig(class_name="custom.my_org.MyCustomProcess")

# MessageEnvelope with metadata
envelope = MessageEnvelope.create_hl7(
    raw_payload=b"MSH|...",
    version="2.4",
    source="PAS",
    destination="EPR"
)

# Automatic parsing
async def on_message_envelope(self, envelope):
    parsed = envelope.parse()  # Automatic based on content_type
```

### Breaking Changes

None - 100% backward compatible.

### Files Summary

**New Files (7):**
- `Engine/core/meta_instantiation.py` (248 lines)
- `Engine/core/message_envelope.py` (383 lines)
- `demos/nhs_trust/README.md` (715 lines)
- `demos/nhs_trust/config/nhs_acute_trust_production.json` (313 lines)
- `demos/nhs_trust/lib/nhs_validation_process.py` (262 lines)
- `demos/nhs_trust/scripts/deploy_production.py` (371 lines)
- `demos/nhs_trust/test_data/*.hl7` (5 test files)

**New Documentation (7):**
- `docs/architecture/META_INSTANTIATION_UPLIFT_PLAN.md` (1,433 lines)
- `docs/PRODUCT_ROADMAP.md` (1,791 lines)
- `docs/architecture/SCALABILITY_ARCHITECTURE.md` (884 lines)
- `docs/architecture/MESSAGE_ENVELOPE_DESIGN.md` (1,195 lines)
- `docs/guides/LI_HIE_DEVELOPER_GUIDE.md` (800 lines)
- `docs/guides/NHS_TRUST_DEMO.md` (538 lines)
- `docs/architecture/CORE_PRINCIPLES.md` (575 lines)

**Modified Files (3):**
- `Engine/li/registry/class_registry.py` (+55 lines)
- `Engine/li/engine/production.py` (+54 lines)
- `Engine/li/hosts/base.py` (+90 lines)

**Total**: 12,505 lines added, 1,966 lines removed (net +10,539 lines)

### Contributors

- Implementation: Claude Sonnet 4.5 AI Assistant
- Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

---

## [0.3.1] - 2026-02-09

### Changed - Docker-Only Verification and Test Execution

- Enabled running `pytest` inside the `docker-compose.yml` stack by mounting `./tests` into the `hie-engine` container.
- Fixed `Payload` property handling in `Engine/core/message.py` to align dataclass fields with test expectations.
- Updated async fixture usage in `tests/integration/test_http_receiver.py` to work with pytest-asyncio strict mode.
- Added Docker-network E2E smoke tests under `tests/e2e/` to validate `hie-manager`, `hie-portal` proxy, and `hie-engine` health.
- Added `docs/TESTING.md` and updated `README.md` with exact Docker-only test commands.

## [0.3.0] - 2026-02-09

### Changed - Project Restructure for Production Readiness

**Folder Structure:**
- Renamed `hie/` → `Engine/` - Backend microservice cluster
- Renamed `portal/` → `Portal/` - Frontend service
- Removed 16+ empty placeholder directories
- Established clear Frontend/Backend separation

**Service Naming:**
- Renamed service: `hie-api` → `hie-manager` (Management orchestrator)
- Container: `hie-api` → `hie-manager`

**Docker Configuration:**
- Promoted `docker-compose.full.yml` → `docker-compose.yml` (primary)
- Archived original → `docker-compose.minimal.yml`
- Renamed `Dockerfile.api` → `Dockerfile.manager`
- Updated all build contexts and volume paths

**Python Package:**
- Updated import paths: `from hie.` → `from Engine.`
- Updated package configuration in `pyproject.toml`
- Updated CLI entry points
- Package install name remains `pip install hie` for compatibility

**Benefits:**
- Production-ready folder structure
- Clear separation of concerns
- Enterprise-grade naming conventions
- Eliminated technical debt (empty directories)
- Improved developer experience

---

## [0.2.0] - 2026-01-21

### 🔐 User Management & Authentication

This release introduces a complete user management system with multi-tenancy support, RBAC, and secure authentication.

### Added

#### Authentication System
- **JWT Authentication** - Secure token-based authentication with configurable expiry
- **Password Security** - bcrypt hashing with 12 rounds, password policy enforcement
- **Account Lockout** - Automatic lockout after 5 failed login attempts for 30 minutes
- **Session Management** - Token-based sessions with secure logout

#### User Management
- **User Registration** - Self-service registration with admin approval workflow
- **User Lifecycle** - States: pending, active, inactive, locked, rejected
- **User Approval** - Admin workflow for approving/rejecting new registrations
- **User Actions** - Activate, deactivate, unlock user accounts

#### Role-Based Access Control (RBAC)
- **System Roles** - Super Admin, Tenant Admin, Operator, Developer, Viewer, Auditor
- **Permissions** - Granular permissions for tenants, users, productions, messages, config, audit, settings
- **Multi-Tenancy** - Tenant isolation with NHS Trust support (prepared for future use)

#### Portal Authentication Pages
- **Login Page** - Email/password authentication with error handling
- **Registration Page** - User registration with password validation
- **Pending Page** - Informational page for users awaiting approval

#### Portal Security
- **Auth Protection** - All app routes require authentication
- **Auth Guard** - Automatic redirect to login for unauthenticated users
- **User Menu** - Dropdown with user info, settings, and sign out
- **Notifications** - Bell icon with notification panel

#### API Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User authentication
- `GET /api/auth/me` - Get current user
- `POST /api/auth/change-password` - Change password
- `POST /api/auth/logout` - Logout
- `GET /api/admin/users` - List users (admin)
- `GET /api/admin/users/{id}` - Get user details
- `POST /api/admin/users/{id}/approve` - Approve user
- `POST /api/admin/users/{id}/reject` - Reject user
- `POST /api/admin/users/{id}/activate` - Activate user
- `POST /api/admin/users/{id}/deactivate` - Deactivate user
- `POST /api/admin/users/{id}/unlock` - Unlock user
- `GET /api/admin/roles` - List roles

#### Database Schema
- `hie_tenants` - Multi-tenant organization support
- `hie_roles` - Role definitions with permissions
- `hie_users` - User accounts with full profile
- `hie_password_history` - Password reuse prevention (prepared)
- `hie_sessions` - Session tracking (prepared)
- `hie_audit_log` - Audit trail (prepared)

### Default Credentials
- **Email:** admin@hie.nhs.uk
- **Password:** Admin123!
- **Role:** Super Administrator

### Technical Details
- JWT tokens with 24-hour expiry
- bcrypt password hashing (12 rounds)
- Password policy: 12+ chars, uppercase, lowercase, digit, special char
- Account lockout: 5 attempts, 30 minute duration

---

## [0.1.0] - 2026-01-21

### 🎉 Initial Release

First public release of HIE - Healthcare Integration Engine, a next-generation healthcare integration platform designed for NHS acute trust environments.

### Added

#### Core Engine
- **Production Orchestrator** - Full lifecycle management (start, stop, pause, resume)
- **Message Model** - Immutable envelope/payload separation with raw-first design
- **HTTP Receiver** - REST API endpoint for inbound HL7v2 messages
- **File Receiver** - Directory watching for file-based message ingestion
- **MLLP Sender** - HL7 over TCP with ACK handling and connection pooling
- **File Sender** - Write messages to configurable output directories
- **Route Engine** - Content-based routing with filter rules (equals, contains, regex)
- **PostgreSQL Store** - Durable message persistence with full envelope/payload storage
- **Redis Store** - High-speed message caching and queue management
- **Configuration System** - YAML and JSON configuration support

#### Management Portal (Next.js)
- **Dashboard** - Real-time metrics, production status cards, activity feed
- **Productions** - List view with status indicators, detail view with item metrics
- **Configure** - Route editor with visual flow display, items table management
- **Messages** - Search and filtering, pagination, status badges, detail slide-over
- **Monitoring** - System metrics (CPU, memory), throughput charts, resource usage bars
- **Errors** - Severity-based tracking (critical/error/warning), stack traces, resolution workflow
- **Logs** - Real-time streaming, level/source filtering, terminal-style viewer
- **Settings** - General, notifications, security, database, API keys, email configuration

#### Management API
- Production CRUD operations
- Item management endpoints
- Route configuration endpoints
- Message search and retrieval
- Health check endpoints

#### Infrastructure
- **Docker Support** - Multi-stage Dockerfile for optimized images
- **Docker Compose** - Full stack deployment with all services
- **Port Allocation** - Standardized port range (9300-9350)
- **Echo Servers** - MLLP and HTTP echo servers for E2E testing
- **Database Tools** - Adminer and Redis Commander for debugging

#### Documentation
- Product Vision document
- Feature Specification with status tracking
- Requirements Specification
- Architecture Overview
- Message Model documentation
- Development Roadmap

### Technical Details

#### Services and Ports
| Service | Port | Description |
|---------|------|-------------|
| HIE Engine | 9300 | HTTP receiver for HL7 messages |
| HIE Engine | 9301 | MLLP receiver (reserved) |
| Management API | 9302 | REST API for portal |
| Management Portal | 9303 | Next.js web application |
| PostgreSQL | 9310 | Message persistence |
| Redis | 9311 | Caching and queues |
| MLLP Echo | 9320 | Test MLLP server |
| HTTP Echo | 9321 | Test HTTP server |
| Adminer | 9330 | Database UI |
| Redis Commander | 9331 | Redis UI |

#### Technology Stack
- **Backend**: Python 3.11+, asyncio, aiohttp
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 16, Redis 7
- **Deployment**: Docker, Docker Compose

### Known Limitations
- Authentication system not yet implemented
- Visual drag-drop production editor planned for v0.2.0
- Message trace visualization planned for v0.2.0
- Prometheus metrics export planned for v0.2.0

---

[0.2.0]: https://github.com/your-org/hie/releases/tag/v0.2.0
[0.1.0]: https://github.com/your-org/hie/releases/tag/v0.1.0
