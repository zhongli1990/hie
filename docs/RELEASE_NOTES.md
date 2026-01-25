# HIE Release Notes

## v1.3.1 - Message Storage & Viewer Implementation

**Release Date:** January 25, 2026  
**Status:** Phase 5.1 Complete

---

### Overview

This release implements Phase 5.1 of the Enterprise UI Design - Message Storage & Viewer. Messages are now stored permanently in PostgreSQL and can be viewed, filtered, and resent through the Messages tab.

---

### New Features

#### Message Storage
- **Permanent Storage** - All messages stored in `portal_messages` PostgreSQL table
- **Message Tracking** - Track project, item, direction, status, latency, ACK responses
- **Housekeeping API** - `DELETE /api/messages/housekeeping?days=30` for purging old messages

#### Messages Tab - Real-Time Viewer
- **Project Selector** - Filter messages by project
- **Status Filters** - Filter by sent, completed, failed, error, received, processing
- **Direction Filters** - Filter by inbound/outbound
- **HL7 Syntax Highlighting** - Color-coded segments in detail view
- **ACK Display** - View ACK responses with type badges (AA, CA, AR, AE, CR)
- **Message Resend** - Retry failed messages with one click

#### Clickable Metrics
- **Item Metrics Navigation** - Click message counts on project items to navigate to filtered Messages view

---

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects/{id}/messages` | GET | List messages with filters |
| `/api/projects/{id}/messages/stats` | GET | Get message statistics |
| `/api/projects/{id}/messages/{msg_id}` | GET | Get message detail with content |
| `/api/projects/{id}/messages/{msg_id}/resend` | POST | Resend a message |
| `/api/messages/housekeeping` | DELETE | Purge old messages |

---

### Files Changed

- `scripts/init-db.sql` - Added `portal_messages` table schema
- `hie/api/repositories.py` - Added `PortalMessageRepository`
- `hie/api/routes/messages.py` - New messages API routes
- `hie/api/services/message_store.py` - Message storage service
- `hie/api/routes/items.py` - Integrated message storage in test_item
- `hie/api/server.py` - Register message routes and storage service
- `portal/src/lib/api-v2.ts` - Added message API functions
- `portal/src/app/(app)/messages/page.tsx` - Connected to real API
- `portal/src/app/(app)/projects/[id]/page.tsx` - Clickable metrics

---

## v1.3.0 - Enterprise UI Design Release

**Release Date:** January 25, 2026  
**Status:** Design Complete

---

### Overview

This release completes the enterprise UI design specification for the HIE Management Portal. It includes comprehensive designs for the Dashboard, Messages, Configure, and Monitoring tabs with real-time data integration, permanent message storage, and scalable chart components.

---

### Design Documents

- **UI Design Specification:** `docs/UI_DESIGN_SPEC.md` - Complete UI/UX design for all portal tabs

---

### Design Highlights

#### Messages Tab - Real-Time Message Viewer
- **Permanent Storage** - Messages stored in PostgreSQL (manual/automated housekeeping for purging)
- **HL7 Syntax Highlighting** - Color-coded segments (MSH=blue, PID=green, PV1=yellow, etc.)
- **Clickable Metrics** - Click item metrics → navigate to filtered Messages view
- **Message Resend** - Replay failed messages with one click
- **Parsed View** - JSON tree view of HL7 fields

#### Dashboard Tab - Live Metrics Hub
- **Real Data Integration** - Replace mock data with live API calls
- **Project Tree View** - Expandable project/item list with status
- **Throughput Sparkline** - Mini chart for message rate
- **Auto-Refresh** - Polling every 10 seconds with refresh button

#### Configure Tab - Sub-Tab Navigation
- **Workspaces** - Workspace CRUD management
- **Projects** - Project templates
- **Items** - Item type registry viewer
- **Schemas** - HL7/FHIR schema definitions
- **Transforms** - DTL transformation rules editor
- **Routing** - Routing rule definitions

#### Monitoring Tab - Prometheus Metrics
- **Simple Charts** - CSS/SVG bar charts (scalable placeholder for Recharts/Chart.js)
- **Per-Item Metrics** - Real data table
- **System Resources** - CPU/memory/disk usage

---

### Implementation Phases

| Phase | Focus | Effort | Priority |
|-------|-------|--------|----------|
| 5.1 | Message Storage & Viewer | 9h | High |
| 5.2 | Dashboard Real Data | 7h | High |
| 5.3 | Configure Sub-Tabs | 15h | Medium |
| 5.4 | Monitoring Charts | 7h | Medium |
| 5.5 | Advanced Features | 13h | Low |
| **Total** | | **51h** | |

---

### Enhanced HL7 Message Tester

Building on v1.2.2, this release also includes:

| Feature | Description |
|---------|-------------|
| Editable message textarea | Dark-themed monospace editor |
| HL7 segment color coding | MSH=blue, PID=green, PV1=yellow, etc. |
| Line numbers | Numbered segment display |
| ACK type badges | CA/AA/CR/AR/AE detection with color coding |
| Segment separator fix | Normalize \n to \r for MLLP compliance |
| Reset to default | Regenerate fresh test message |

---

### Files Added/Changed

| File | Change |
|------|--------|
| `docs/UI_DESIGN_SPEC.md` | **NEW** - Complete UI design specification |
| `docs/FEATURE_SPEC.md` | Updated with new UI features |
| `docs/IMPLEMENTATION_STATUS.md` | Added Phase 5 UI design tasks |
| `hie/api/routes/items.py` | Segment separator normalization |
| `portal/src/app/(app)/projects/[id]/page.tsx` | Enhanced HL7 Message Tester |

---

## v1.2.2 - HL7 Testing & Runtime Fixes Release

**Release Date:** January 25, 2026  
**Status:** Production Ready

---

### Overview

This release adds HL7 message testing capabilities and fixes critical runtime issues with adapter settings. Users can now send test messages through outbound operations directly from the UI and verify end-to-end connectivity with remote HL7 systems.

---

### New Features

#### HL7 Test Message Button
- **Test Button** - Purple play icon (▶) on outbound operation items
- **Auto-generated Test Message** - Sends ADT^A01 with realistic patient data
- **ACK Response Display** - Modal shows formatted HL7 ACK from remote system
- **Send Another** - Repeat test without closing modal
- **API Endpoint** - `POST /api/projects/{id}/items/{item_name}/test`

#### Full-Stack Test Flow
```
UI Button Click → Portal → API → Engine → MLLP Adapter → Remote System → ACK
```

---

### Bug Fixes

#### Critical: Adapter Settings Case-Sensitivity
- **Root Cause** - Database stores settings in camelCase (`port`, `ipAddress`) but adapter code looked up PascalCase (`Port`, `IPAddress`)
- **Fix** - Made `Adapter.get_setting()` case-insensitive with fallback matching
- **Impact** - HL7 receivers now bind to configured ports (was defaulting to 2575)
- **Impact** - HL7 senders now connect to configured remote hosts (was defaulting to localhost:2575)

#### Docker Port Mapping for macOS
- Reduced MLLP port range from 10001-19999 to 10001-10020 to avoid Docker timeout
- Reverted from `network_mode: host` (doesn't work on macOS Docker Desktop)
- Fixed portal API URL configuration for Docker service networking

#### Backend API Fixes
- Fixed `get_project` endpoint accessing host states dictionary incorrectly
- Fixed `start_project` to check if engine is already running before starting
- Fixed `deploy` route calling non-existent `add_setting` method (changed to `set_setting`)

---

### Files Changed

| File | Change |
|------|--------|
| `hie/li/adapters/base.py` | Case-insensitive `get_setting()` method |
| `hie/api/routes/items.py` | Added `test_item` endpoint |
| `hie/api/routes/projects.py` | Fixed deploy, start, get_project bugs |
| `portal/src/lib/api-v2.ts` | Added `testItem()` API function |
| `portal/src/app/(app)/projects/[id]/page.tsx` | Test button and result modal |
| `docker-compose.full.yml` | Fixed port mappings for macOS |

---

### Testing

#### Verified Working:
- HL7 receiver binds to configured port (10001)
- HL7 sender connects to configured remote (192.168.0.17:35001)
- Test message sent from UI receives ACK response
- Full end-to-end message flow confirmed

#### Test Commands:
```bash
# Test HL7 receiver port
nc -zv localhost 10001

# Send test HL7 message via netcat
printf '\x0bMSH|^~\\&|TEST|TEST|HIE|HIE|20260125||ADT^A01|123|P|2.4\x1c\r' | nc localhost 10001

# Send test via API
curl -X POST "http://localhost:9302/api/projects/{project_id}/items/{item_name}/test"
```

---

## v1.2.1 - Item Editing & Hot Reload Release

**Release Date:** January 25, 2026  
**Status:** Production Ready

---

### Overview

This release adds item editing capabilities and hot reload functionality to the HIE Management Portal. Users can now edit item properties directly in the UI and apply changes to running engines without restarting.

---

### New Features

#### Item Editing
- **Edit Mode** - Click pencil icon to enter edit mode for any item
- **Editable Fields** - pool_size, enabled, adapter_settings, host_settings
- **Save/Cancel** - Save changes or cancel to revert

#### Hot Reload
- **Reload Button** - Green refresh icon to apply changes to running engine
- **Graceful Restart** - Pauses item, drains queue, applies config, resumes
- **No Message Loss** - Queue persists during reload
- **API Endpoint** - `POST /api/projects/{id}/items/{item_id}/reload`

#### Backend Implementation
- `Host.reload_config()` - Base class method for graceful config reload
- `ProductionEngine.reload_host_config()` - Engine-level reload orchestration

---

### Bug Fixes

- **ItemConfig category validation** - Allow `None` for optional category/comment fields
- **UI refresh after save** - Selected item now updates after saving changes
- Fixed JSONB field parsing in repositories (settings returned as dict, not string)
- Fixed API URL configuration for Docker environments (relative URLs for proxy)

---

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
