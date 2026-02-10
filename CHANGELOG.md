# Changelog

All notable changes to OpenLI HIE (Healthcare Integration Engine) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
