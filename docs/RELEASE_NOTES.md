# HIE Release Notes

## v1.2.0 - Full-Stack Integration Release

**Release Date:** January 25, 2026  
**Status:** Production Ready

---

### Overview

This release completes the full-stack integration of the HIE (Healthcare Integration Engine), connecting the LI Engine backend with the Management Portal frontend. Users can now create workspaces, manage projects, add configuration items, and deploy integrations through the web UI.

---

### New Features

#### Backend APIs
- **Workspace Management** - Full CRUD operations for workspaces (namespaces)
- **Project Management** - Create, update, delete, deploy, start/stop projects
- **Item Management** - Add/edit/remove Business Services, Processes, and Operations
- **Connection Management** - Define connections between items
- **Routing Rules** - Configure message routing with conditions
- **Item Type Registry** - Dynamic form generation based on item type metadata
- **IRIS XML Import** - Import existing IRIS production configurations

#### Frontend Components
- **WorkspaceSelector** - Dropdown in TopNav for switching workspaces
- **WorkspaceContext** - React context for global workspace state
- **Projects List Page** - View all projects in current workspace
- **Project Detail Page** - Edit project items, connections, and settings
- **Dynamic Item Forms** - Auto-generated forms based on item type definitions
- **IRIS Import Modal** - Upload and import IRIS XML configurations

#### Database Schema
- `workspaces` - Namespace isolation for multi-tenant deployments
- `projects` - Integration project definitions
- `project_items` - Business Services, Processes, Operations
- `project_connections` - Item-to-item connections
- `project_routing_rules` - Message routing conditions
- `project_versions` - Configuration version history
- `engine_instances` - Running engine tracking

#### Docker Integration
- Full-stack Docker Compose deployment
- PostgreSQL database with automatic schema initialization
- Next.js API proxy for browser-to-backend communication
- Health checks for all services

---

### Bug Fixes

- Fixed JSONB field parsing in repositories (settings returned as dict, not string)
- Fixed API URL configuration for Docker environments (relative URLs for proxy)
- Fixed Sidebar navigation to use `/projects` instead of legacy `/productions`
- Fixed Dockerfile to include `next.config.js` for runtime rewrites

---

### Breaking Changes

None. This release is backward compatible with v1.0.0-li.

---

### Migration Guide

#### From v1.0.0-li

1. Pull the latest code
2. Run database migration:
   ```bash
   docker-compose -f docker-compose.full.yml down -v
   docker-compose -f docker-compose.full.yml up -d
   ```
3. Access portal at http://localhost:9303

---

### Known Issues

- Portal health check may show "unhealthy" briefly during startup (service still works)
- Real-time WebSocket events not yet implemented (polling used instead)
- Visual drag-drop editor pending future release

---

### API Reference

See `docs/IMPLEMENTATION_STATUS.md` Section 7 for complete API endpoint documentation.

---

### Contributors

- HIE Core Team

---

## Previous Releases

### v1.0.0-li - LI Engine Production Ready (Jan 25, 2026)
- Complete LI Engine implementation
- IRIS XML configuration loader
- HL7 MLLP protocol support
- Enterprise features (WAL, metrics, health checks)

### v0.2.0 - User Management & Auth (Jan 21, 2026)
- User registration and login
- Role-based access control
- Session management
- Admin user management

### v0.1.0 - Initial Release (Jan 21, 2026)
- Core HIE engine
- Basic message routing
- HTTP and file receivers/senders
- Management portal foundation
