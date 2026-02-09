# Changelog

All notable changes to HIE (Healthcare Integration Engine) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
