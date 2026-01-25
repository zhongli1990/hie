# HIE Implementation Status

**Version:** 1.3.2  
**Last Updated:** January 25, 2026  
**Status:** Phase 5.1 Message Storage & Viewer Complete with Bug Fixes

---

## Executive Summary

The HIE (Healthcare Integration Engine) project has two parallel implementations:

1. **HIE Core Engine** (v0.2.0) - Original Python engine with management portal
2. **LI Engine** (v1.0.0) - Re-architected IRIS-compatible engine

This document provides the current implementation status across all components.

---

## 1. LI Engine Status (NEW - v1.0.0) ✅ COMPLETE

The LI (Lightweight Integration) Engine is a complete re-architecture designed for IRIS compatibility and enterprise-grade NHS deployments.

### Phase 1: Core Foundation ✅

| Component | Status | Location |
|-----------|--------|----------|
| IRIS XML Loader | ✅ Complete | `hie/li/config/iris_xml_loader.py` |
| Production Config Model | ✅ Complete | `hie/li/config/production_config.py` |
| Item Config Model | ✅ Complete | `hie/li/config/item_config.py` |
| Host Base Classes | ✅ Complete | `hie/li/hosts/base.py` |
| BusinessService | ✅ Complete | `hie/li/hosts/base.py` |
| BusinessProcess | ✅ Complete | `hie/li/hosts/base.py` |
| BusinessOperation | ✅ Complete | `hie/li/hosts/base.py` |
| Adapter Base Classes | ✅ Complete | `hie/li/adapters/base.py` |
| HL7 Schema System | ✅ Complete | `hie/li/schemas/hl7/` |
| Lazy HL7 Parsing | ✅ Complete | `hie/li/schemas/hl7/parsed_view.py` |
| Class Registry | ✅ Complete | `hie/li/registry/class_registry.py` |
| Schema Registry | ✅ Complete | `hie/li/registry/schema_registry.py` |

### Phase 2: HL7 Stack ✅

| Component | Status | Location |
|-----------|--------|----------|
| MLLP Framing | ✅ Complete | `hie/li/adapters/mllp.py` |
| MLLPInboundAdapter | ✅ Complete | `hie/li/adapters/mllp.py` |
| MLLPOutboundAdapter | ✅ Complete | `hie/li/adapters/mllp.py` |
| HL7TCPService | ✅ Complete | `hie/li/hosts/hl7.py` |
| HL7TCPOperation | ✅ Complete | `hie/li/hosts/hl7.py` |
| HL7RoutingEngine | ✅ Complete | `hie/li/hosts/routing.py` |
| Condition Evaluator | ✅ Complete | `hie/li/hosts/routing.py` |
| ACK Generation | ✅ Complete | `hie/li/schemas/hl7/schema.py` |

### Phase 3: Enterprise Features ✅

| Component | Status | Location |
|-----------|--------|----------|
| Write-Ahead Log (WAL) | ✅ Complete | `hie/li/persistence/wal.py` |
| Message Store | ✅ Complete | `hie/li/persistence/store.py` |
| File Storage Backend | ✅ Complete | `hie/li/persistence/store.py` |
| Redis Message Queue | ✅ Complete | `hie/li/persistence/queue.py` |
| Prometheus Metrics | ✅ Complete | `hie/li/metrics/prometheus.py` |
| Health Checks | ✅ Complete | `hie/li/health/checks.py` |
| Graceful Shutdown | ✅ Complete | `hie/li/health/shutdown.py` |

### Phase 4: Production Engine ✅

| Component | Status | Location |
|-----------|--------|----------|
| ProductionEngine | ✅ Complete | `hie/li/engine/production.py` |
| Engine Config | ✅ Complete | `hie/li/engine/production.py` |
| Host Lifecycle Management | ✅ Complete | `hie/li/engine/production.py` |
| Infrastructure Init | ✅ Complete | `hie/li/engine/production.py` |

### LI Engine Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_iris_xml_loader.py` | 22 | ✅ Pass |
| `test_hosts.py` | 20 | ✅ Pass |
| `test_schemas.py` | 31 | ✅ Pass |
| `test_mllp.py` | 17 | ✅ Pass |
| `test_hl7_hosts.py` | 30 | ✅ Pass |
| `test_integration.py` | 10 | ✅ Pass |
| `test_persistence.py` | 18 | ✅ Pass |
| `test_engine.py` | 15 | ✅ Pass |
| **Total** | **163** | ✅ Pass |

---

## 2. HIE Core Engine Status (v0.2.0)

The original HIE engine provides the foundation but needs integration with LI Engine.

### Core Components

| Component | Status | Location |
|-----------|--------|----------|
| Production Orchestrator | ✅ Complete | `hie/core/production.py` |
| Message Model | ✅ Complete | `hie/core/message.py` |
| Item Base Classes | ✅ Complete | `hie/core/item.py` |
| Route Model | ✅ Complete | `hie/core/route.py` |
| Config Schema | ✅ Complete | `hie/core/schema.py` |
| Config Loader | ✅ Complete | `hie/core/config_loader.py` |

### Items (Receivers/Processors/Senders)

| Component | Status | Location |
|-----------|--------|----------|
| HTTP Receiver | ✅ Complete | `hie/items/receivers/http.py` |
| File Receiver | ✅ Complete | `hie/items/receivers/file.py` |
| MLLP Sender | ✅ Complete | `hie/items/senders/mllp.py` |
| File Sender | ✅ Complete | `hie/items/senders/file.py` |
| Passthrough Processor | ✅ Complete | `hie/items/processors/passthrough.py` |
| Transform Processor | ✅ Complete | `hie/items/processors/transform.py` |

### Persistence

| Component | Status | Location |
|-----------|--------|----------|
| In-Memory Store | ✅ Complete | `hie/persistence/memory.py` |
| PostgreSQL Store | ✅ Complete | `hie/persistence/postgres.py` |
| Redis Store | ✅ Complete | `hie/persistence/redis.py` |

### API Server

| Component | Status | Location |
|-----------|--------|----------|
| Management API | ✅ Complete | `hie/api/server.py` |
| Auth Routes | ✅ Complete | `hie/auth/aiohttp_router.py` |
| CORS Middleware | ✅ Complete | `hie/api/server.py` |

---

## 3. Management Portal Status (v0.2.0)

### Portal Pages

| Page | Status | Location |
|------|--------|----------|
| Dashboard | ✅ Complete | `portal/src/app/(app)/dashboard/` |
| Productions List | ✅ Complete | `portal/src/app/(app)/productions/` |
| Production Detail | ✅ Complete | `portal/src/app/(app)/productions/[name]/` |
| Configure (Route Editor) | ✅ Complete | `portal/src/app/(app)/configure/` |
| Messages | ✅ Complete | `portal/src/app/(app)/messages/` |
| Monitoring | ✅ Complete | `portal/src/app/(app)/monitoring/` |
| Errors | ✅ Complete | `portal/src/app/(app)/errors/` |
| Logs | 🔲 Pending | `portal/src/app/(app)/logs/` |
| Settings | ✅ Complete | `portal/src/app/(app)/settings/` |
| Admin Users | ✅ Complete | `portal/src/app/(app)/admin/` |

### Authentication

| Feature | Status | Location |
|---------|--------|----------|
| Login Page | ✅ Complete | `portal/src/app/(auth)/login/` |
| Register Page | ✅ Complete | `portal/src/app/(auth)/register/` |
| Pending Approval | ✅ Complete | `portal/src/app/(auth)/pending/` |
| Auth Context | ✅ Complete | `portal/src/contexts/AuthContext.tsx` |
| Protected Routes | ✅ Complete | `portal/src/app/(app)/layout.tsx` |

---

## 4. Full-Stack Integration Status (IN PROGRESS)

### Phase 4.1: Database Schema ✅ COMPLETE

| Table | Status | Location |
|-------|--------|----------|
| workspaces | ✅ Complete | `hie/persistence/migrations/001_workspaces_projects.sql` |
| projects | ✅ Complete | `hie/persistence/migrations/001_workspaces_projects.sql` |
| project_items | ✅ Complete | `hie/persistence/migrations/001_workspaces_projects.sql` |
| project_connections | ✅ Complete | `hie/persistence/migrations/001_workspaces_projects.sql` |
| project_routing_rules | ✅ Complete | `hie/persistence/migrations/001_workspaces_projects.sql` |
| project_versions | ✅ Complete | `hie/persistence/migrations/001_workspaces_projects.sql` |
| engine_instances | ✅ Complete | `hie/persistence/migrations/001_workspaces_projects.sql` |

### Phase 4.2: Backend APIs ✅ COMPLETE

| Component | Status | Location |
|-----------|--------|----------|
| API Models (Pydantic) | ✅ Complete | `hie/api/models.py` |
| Repository Layer | ✅ Complete | `hie/api/repositories.py` |
| Workspace CRUD Routes | ✅ Complete | `hie/api/routes/workspaces.py` |
| Project CRUD Routes | ✅ Complete | `hie/api/routes/projects.py` |
| Item/Connection CRUD Routes | ✅ Complete | `hie/api/routes/items.py` |
| Item Type Registry | ✅ Complete | `hie/api/routes/item_types.py` |
| Engine Manager (LI Integration) | ✅ Complete | `hie/api/routes/projects.py` |
| IRIS XML Import Endpoint | ✅ Complete | `hie/api/routes/projects.py` |

### Phase 4.3: Frontend ✅ COMPLETE

| Component | Status | Location |
|-----------|--------|----------|
| API Client v2 | ✅ Complete | `portal/src/lib/api-v2.ts` |
| WorkspaceContext | ✅ Complete | `portal/src/contexts/WorkspaceContext.tsx` |
| WorkspaceSelector | ✅ Complete | `portal/src/components/WorkspaceSelector.tsx` |
| Projects List Page | ✅ Complete | `portal/src/app/(app)/projects/page.tsx` |
| Project Detail Page | ✅ Complete | `portal/src/app/(app)/projects/[id]/page.tsx` |
| Item Management UI | ✅ Complete | `portal/src/app/(app)/projects/[id]/page.tsx` |
| Connection Management UI | ✅ Complete | `portal/src/app/(app)/projects/[id]/page.tsx` |
| IRIS Import Modal | ✅ Complete | `portal/src/app/(app)/projects/page.tsx` |
| Layout Integration | ✅ Complete | `portal/src/app/(app)/layout.tsx` |
| TopNav Integration | ✅ Complete | `portal/src/components/TopNav.tsx` |

### Phase 4.4: Docker Integration ✅ COMPLETE

| Component | Status | Notes |
|-----------|--------|-------|
| Database schema in init-db.sql | ✅ Complete | All tables created on container start |
| API proxy via Next.js rewrites | ✅ Complete | Browser requests proxied to backend |
| Sidebar navigation updated | ✅ Complete | Links to /projects instead of /productions |
| JSONB field parsing | ✅ Complete | Settings properly deserialized |

### Phase 4.5: Item Management ✅ COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Create Business Service | ✅ Complete | Via Add Item modal |
| Create Business Process | ✅ Complete | Via Add Item modal |
| Create Business Operation | ✅ Complete | Via Add Item modal |
| Delete Items | ✅ Complete | Via delete button |
| View Item Properties | ✅ Complete | Detail panel shows all settings |
| **Edit Item Properties** | ✅ Complete | Edit mode with save/cancel |
| Target Items field (optional) | ✅ Complete | Shows helpful message when empty |

### Phase 4.6: Hot Reload ✅ COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Update item settings at runtime | ✅ Complete | `PUT /api/projects/{id}/items/{item_id}` |
| Graceful item restart | ✅ Complete | `Host.reload_config()` method |
| Live config sync | ✅ Complete | `POST /api/projects/{id}/items/{item_id}/reload` |
| Hot reload button in UI | ✅ Complete | Green refresh icon in item detail panel |

**Hot Reload Flow:**
1. Pause item (stop accepting new messages)
2. Wait for in-flight messages to complete (30s timeout)
3. Stop adapter
4. Apply new configuration (pool_size, enabled, adapter_settings, host_settings)
5. Recreate adapter with new settings
6. Resume processing

**Key Files:**
- `hie/li/hosts/base.py` - `reload_config()` method
- `hie/li/engine/production.py` - `reload_host_config()` method
- `hie/api/routes/items.py` - `/reload` endpoint
- `portal/src/app/(app)/projects/[id]/page.tsx` - UI reload button

### Phase 4.7: HL7 Testing ✅ COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Test message endpoint | ✅ Complete | `POST /api/projects/{id}/items/{item_name}/test` |
| Test button in UI | ✅ Complete | Purple play icon for operations |
| ACK response modal | ✅ Complete | Shows formatted HL7 ACK |
| Auto-generated ADT^A01 | ✅ Complete | Realistic test patient data |
| Case-insensitive settings | ✅ Complete | Adapter settings lookup fixed |

**Test Flow:**
1. Click purple play button (▶) on outbound operation
2. System generates ADT^A01 test message
3. Message sent via MLLP to configured remote host
4. ACK response displayed in modal
5. Option to "Send Another" for repeated testing

**Key Files:**
- `hie/li/adapters/base.py` - Case-insensitive `get_setting()` method
- `hie/api/routes/items.py` - `test_item` endpoint
- `portal/src/lib/api-v2.ts` - `testItem()` API function
- `portal/src/app/(app)/projects/[id]/page.tsx` - Test button and modal

### Phase 4.8: Enhanced HL7 Message Tester ✅ COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Editable message textarea | ✅ Complete | Dark-themed monospace editor |
| HL7 segment color coding | ✅ Complete | MSH=blue, PID=green, etc. |
| Line numbers | ✅ Complete | Numbered segment display |
| ACK type badges | ✅ Complete | CA/AA/CR/AR/AE detection |
| Segment separator fix | ✅ Complete | Normalize \n to \r for MLLP |
| Reset to default | ✅ Complete | Regenerate test message |

---

## 5. Enterprise UI Design (v1.3.x) � IN PROGRESS

See `docs/UI_DESIGN_SPEC.md` for complete design specification.

### Phase 5.1: Message Storage & Viewer ✅ COMPLETE (v1.3.1)

| Task | Status | Effort | Notes |
|------|--------|--------|-------|
| Create messages table | ✅ Complete | 1h | `portal_messages` table in PostgreSQL |
| Add message storage service | ✅ Complete | 2h | `hie/api/services/message_store.py` |
| Create messages API endpoints | ✅ Complete | 2h | List, detail, stats, resend, housekeeping |
| Connect Messages tab to API | ✅ Complete | 3h | Real-time data with filters |
| Add clickable metrics | ✅ Complete | 1h | Navigate to Messages tab with project/item filter |

#### Database Schema

```sql
CREATE TABLE portal_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    item_type VARCHAR(50) NOT NULL CHECK (item_type IN ('service', 'process', 'operation')),
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('inbound', 'outbound', 'internal')),
    message_type VARCHAR(100),           -- HL7 message type (e.g., ADT^A01)
    correlation_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'received',
    raw_content BYTEA,                   -- Full message content
    content_preview TEXT,                -- First 500 chars for list view
    content_size INTEGER DEFAULT 0,
    source_item VARCHAR(255),
    destination_item VARCHAR(255),
    remote_host VARCHAR(255),
    remote_port INTEGER,
    ack_content BYTEA,                   -- ACK response content
    ack_type VARCHAR(20),                -- AA, CA, AR, AE, CR
    error_message TEXT,
    latency_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for efficient querying
CREATE INDEX idx_portal_messages_project ON portal_messages(project_id);
CREATE INDEX idx_portal_messages_item ON portal_messages(item_name);
CREATE INDEX idx_portal_messages_status ON portal_messages(status);
CREATE INDEX idx_portal_messages_type ON portal_messages(message_type);
CREATE INDEX idx_portal_messages_direction ON portal_messages(direction);
CREATE INDEX idx_portal_messages_received ON portal_messages(received_at DESC);
```

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects/{id}/messages` | GET | List messages with pagination and filters |
| `/api/projects/{id}/messages/stats` | GET | Get message statistics (total, success, failed, etc.) |
| `/api/projects/{id}/messages/{msg_id}` | GET | Get message detail with full content |
| `/api/projects/{id}/messages/{msg_id}/resend` | POST | Resend a message through its original item |
| `/api/messages/housekeeping` | DELETE | Purge messages older than N days |

**Query Parameters for List:**
- `item` - Filter by item name
- `status` - Filter by status (received, processing, sent, completed, failed, error)
- `type` - Filter by message type
- `direction` - Filter by direction (inbound, outbound)
- `limit` - Page size (default 50)
- `offset` - Pagination offset

#### Backend Components

**Repository (`hie/api/repositories.py`):**
```python
class PortalMessageRepository:
    async def create(self, project_id, item_name, item_type, direction, ...) -> UUID
    async def update_status(self, message_id, status, ack_content=None, ...) -> bool
    async def get_by_id(self, message_id) -> Optional[dict]
    async def list_by_project(self, project_id, filters, limit, offset) -> List[dict]
    async def get_content(self, message_id) -> Optional[dict]
    async def delete_old_messages(self, days) -> int
    async def get_stats(self, project_id) -> dict
```

**Message Store Service (`hie/api/services/message_store.py`):**
```python
async def store_message(project_id, item_name, item_type, direction, raw_content, ...) -> UUID
async def update_message_status(message_id, status, ack_content=None, ...) -> bool
async def store_and_complete_message(project_id, item_name, ...) -> UUID
def extract_hl7_message_type(content: bytes) -> Optional[str]
def extract_ack_type(ack_content: bytes) -> Optional[str]
```

#### Frontend Components

**Messages Page (`portal/src/app/(app)/messages/page.tsx`):**
- Project selector dropdown
- Status filter (all, sent, completed, failed, error, received, processing)
- Direction filter (all, inbound, outbound)
- Search by message type
- Paginated message table with:
  - Direction icon (inbound=blue arrow, outbound=green arrow)
  - Message type and ID
  - Item name and remote host
  - Status badge
  - Size, latency, timestamp
- Detail slide-over panel with:
  - Status and ACK type badges
  - Error message display (if failed)
  - Full metadata grid
  - Timeline (received → completed)
  - HL7 syntax-highlighted message content
  - ACK response content
  - Resend button for failed messages

**Clickable Metrics (`portal/src/app/(app)/projects/[id]/page.tsx`):**
- Message count metrics in item detail panel are now clickable
- Clicking navigates to Messages tab with `?project={id}&item={name}` filter

#### Files Changed

| File | Changes |
|------|---------|
| `scripts/init-db.sql` | Added `portal_messages` table schema with indexes |
| `hie/api/repositories.py` | Added `PortalMessageRepository` class (~180 lines) |
| `hie/api/routes/messages.py` | New file with 5 API endpoints (~300 lines) |
| `hie/api/services/__init__.py` | New package init |
| `hie/api/services/message_store.py` | New message storage service (~210 lines) |
| `hie/api/server.py` | Register message routes and set db pool for service |
| `hie/api/routes/items.py` | Integrated message storage in `test_item` endpoint |
| `portal/src/lib/api-v2.ts` | Added message API types and functions (~90 lines) |
| `portal/src/app/(app)/messages/page.tsx` | Complete rewrite for real API (~600 lines) |
| `portal/src/app/(app)/projects/[id]/page.tsx` | Added clickable metrics navigation |

### Phase 5.2: Dashboard Real Data 🔲 PENDING

| Task | Status | Effort | Notes |
|------|--------|--------|-------|
| Create dashboard API endpoints | 🔲 Pending | 2h | Stats, throughput, activity |
| Connect Dashboard to API | 🔲 Pending | 2h | Replace mock data |
| Add project tree view | 🔲 Pending | 2h | Expandable items |
| Add auto-refresh | 🔲 Pending | 1h | Polling every 10s with refresh button |

### Phase 5.3: Configure Sub-Tabs 🔲 PENDING

| Task | Status | Effort | Notes |
|------|--------|--------|-------|
| Create sub-tab navigation | 🔲 Pending | 1h | Tab component |
| Workspaces sub-tab | 🔲 Pending | 2h | CRUD UI |
| Items registry sub-tab | 🔲 Pending | 2h | Read-only list |
| Schemas sub-tab | 🔲 Pending | 3h | Schema viewer |
| Transforms sub-tab (DTL) | 🔲 Pending | 4h | Basic DTL editor |
| Routes sub-tab | 🔲 Pending | 3h | Routing rule editor |

**Design Decisions:**
- Configure tab has sub-tab menu for different configuration domains
- Sub-tabs: Workspaces, Projects, Items, Schemas, Transforms, Routing

### Phase 5.4: Monitoring Charts 🔲 PENDING

| Task | Status | Effort | Notes |
|------|--------|--------|-------|
| Create chart placeholder component | 🔲 Pending | 1h | Scalable wrapper for future library |
| Simple CSS bar charts | 🔲 Pending | 2h | Phase 1 charts |
| Per-item metrics table | 🔲 Pending | 2h | Real data |
| System resources display | 🔲 Pending | 2h | CPU/memory/disk |

**Design Decisions:**
- Start with simple CSS/SVG charts
- Scalable placeholder for Recharts/Chart.js in future

### Phase 5.5: Advanced Features 🔲 PENDING

| Task | Status | Effort | Notes |
|------|--------|--------|-------|
| WebSocket real-time updates | 🔲 Pending | 4h | Replace polling |
| Advanced charting library | 🔲 Pending | 3h | Recharts integration |
| Message trace visualization | 🔲 Pending | 4h | Flow diagram |
| Housekeeping UI | 🔲 Pending | 2h | Purge old messages |

---

## 6. Git Tags

| Tag | Description | Date |
|-----|-------------|------|
| `v0.1.0` | Initial HIE release | Jan 21, 2026 |
| `v0.2.0` | User Management & Auth | Jan 21, 2026 |
| `v0.1.0-li-phase1` | LI Core Foundation | Jan 25, 2026 |
| `v0.2.0-li-phase2` | LI HL7 Stack | Jan 25, 2026 |
| `v0.3.0-li-phase3` | LI Enterprise Features | Jan 25, 2026 |
| `v1.0.0-li` | LI Production Ready | Jan 25, 2026 |
| `v1.2.0` | Full-Stack Integration | Jan 25, 2026 |
| `v1.2.1` | Item Editing & Hot Reload | Jan 25, 2026 |
| `v1.2.2` | HL7 Testing & Runtime Fixes | Jan 25, 2026 |
| `v1.3.0` | Enterprise UI Design | Jan 25, 2026 |
| `v1.3.1` | Message Storage & Viewer | Jan 25, 2026 |
| `v1.3.2` | Inbound Message Storage & UI Fixes | Jan 25, 2026 |

---

## 6. Docker Deployment

### Running the Full Stack

```bash
# Start all services
docker-compose -f docker-compose.full.yml up -d

# Services available:
# - Portal: http://localhost:9303
# - API: http://localhost:9302
# - PostgreSQL: localhost:9310
# - Redis: localhost:9311
```

### Default Credentials

- **Email:** admin@hie.nhs.uk
- **Password:** Admin123!

---

## 7. API Endpoints

### Workspace APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspaces` | List all workspaces |
| POST | `/api/workspaces` | Create workspace |
| GET | `/api/workspaces/{id}` | Get workspace |
| PUT | `/api/workspaces/{id}` | Update workspace |
| DELETE | `/api/workspaces/{id}` | Delete workspace |

### Project APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspaces/{ws_id}/projects` | List projects |
| POST | `/api/workspaces/{ws_id}/projects` | Create project |
| GET | `/api/workspaces/{ws_id}/projects/{id}` | Get project |
| PUT | `/api/workspaces/{ws_id}/projects/{id}` | Update project |
| DELETE | `/api/workspaces/{ws_id}/projects/{id}` | Delete project |
| POST | `/api/workspaces/{ws_id}/projects/{id}/deploy` | Deploy project |
| POST | `/api/workspaces/{ws_id}/projects/{id}/start` | Start project |
| POST | `/api/workspaces/{ws_id}/projects/{id}/stop` | Stop project |
| GET | `/api/workspaces/{ws_id}/projects/{id}/status` | Get status |
| POST | `/api/workspaces/{ws_id}/projects/import` | Import IRIS XML |

### Item APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/items` | List items |
| POST | `/api/projects/{id}/items` | Create item |
| GET | `/api/projects/{id}/items/{item_id}` | Get item |
| PUT | `/api/projects/{id}/items/{item_id}` | Update item |
| DELETE | `/api/projects/{id}/items/{item_id}` | Delete item |

### Item Type Registry

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/item-types` | List all item types |
| GET | `/api/item-types/{type}` | Get item type details |
| POST | `/api/projects/{id}/items/{item_id}/reload` | Hot reload item config |

---

## 8. Next Steps

1. ✅ ~~Create Full-Stack Integration Design~~ - Complete
2. ✅ ~~Implement Backend APIs~~ - Complete
3. ✅ ~~Integrate LI Engine~~ - Complete
4. ✅ ~~Uplift Frontend~~ - Complete
5. 🔄 **End-to-End Testing** - In Progress

---

*This document is maintained by the HIE Core Team.*
