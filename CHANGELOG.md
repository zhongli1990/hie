# Changelog

All notable changes to HIE (Healthcare Integration Engine) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/your-org/hie/releases/tag/v0.1.0
