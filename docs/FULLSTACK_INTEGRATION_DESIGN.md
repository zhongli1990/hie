# HIE Full-Stack Integration Design Proposal

**Version:** 1.0.0  
**Date:** January 25, 2026  
**Status:** PENDING APPROVAL

---

## 1. Executive Summary

This document proposes the design for integrating the LI Engine backend with the HIE Management Portal frontend to deliver a complete, enterprise-grade healthcare integration platform.

### Goals

1. Enable users to create and manage workflow projects via the frontend UI
2. Persist all configurations to the database
3. Allow manual configuration of services, processes, and operations
4. Support IRIS XML configuration import
5. Run configurations through the LI Engine backend
6. Provide full lifecycle management (create, start, update, stop, save, remove)

---

## 2. Data Model

### 2.1 Entity Hierarchy

```
Workspace (Namespace)
└── Project (Production)
    ├── Items (Services, Processes, Operations)
    │   ├── Adapter Settings
    │   └── Host Settings
    ├── Connections (Routes between items)
    └── Routing Rules (Conditional routing)
```

### 2.2 Database Schema

```sql
-- Workspaces (Namespaces for multi-tenancy)
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    tenant_id UUID REFERENCES tenants(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    settings JSONB DEFAULT '{}'
);

-- Projects (Productions)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    state VARCHAR(50) DEFAULT 'stopped',
    version INTEGER DEFAULT 1,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    UNIQUE(workspace_id, name)
);

-- Project Items (Services, Processes, Operations)
CREATE TABLE project_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    item_type VARCHAR(50) NOT NULL, -- 'service', 'process', 'operation'
    class_name VARCHAR(255) NOT NULL,
    category VARCHAR(255),
    enabled BOOLEAN DEFAULT true,
    pool_size INTEGER DEFAULT 1,
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    adapter_settings JSONB DEFAULT '{}',
    host_settings JSONB DEFAULT '{}',
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- Project Connections (Routes between items)
CREATE TABLE project_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_item_id UUID NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
    target_item_id UUID NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
    connection_type VARCHAR(50) DEFAULT 'standard', -- 'standard', 'error', 'async'
    enabled BOOLEAN DEFAULT true,
    filter_expression JSONB,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Routing Rules
CREATE TABLE project_routing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    condition_expression TEXT,
    action VARCHAR(50) NOT NULL, -- 'send', 'transform', 'stop'
    target_items JSONB DEFAULT '[]',
    transform_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Versions (for config history)
CREATE TABLE project_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    config_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    comment TEXT,
    UNIQUE(project_id, version)
);

-- Indexes
CREATE INDEX idx_projects_workspace ON projects(workspace_id);
CREATE INDEX idx_project_items_project ON project_items(project_id);
CREATE INDEX idx_project_connections_project ON project_connections(project_id);
CREATE INDEX idx_project_versions_project ON project_versions(project_id);
```

---

## 3. API Design

### 3.1 Workspace APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspaces` | List all workspaces |
| POST | `/api/workspaces` | Create workspace |
| GET | `/api/workspaces/{id}` | Get workspace details |
| PUT | `/api/workspaces/{id}` | Update workspace |
| DELETE | `/api/workspaces/{id}` | Delete workspace |

### 3.2 Project APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspaces/{ws_id}/projects` | List projects in workspace |
| POST | `/api/workspaces/{ws_id}/projects` | Create project |
| GET | `/api/workspaces/{ws_id}/projects/{id}` | Get project with items |
| PUT | `/api/workspaces/{ws_id}/projects/{id}` | Update project |
| DELETE | `/api/workspaces/{ws_id}/projects/{id}` | Delete project |
| POST | `/api/workspaces/{ws_id}/projects/{id}/start` | Start project |
| POST | `/api/workspaces/{ws_id}/projects/{id}/stop` | Stop project |
| POST | `/api/workspaces/{ws_id}/projects/{id}/deploy` | Deploy to LI Engine |
| GET | `/api/workspaces/{ws_id}/projects/{id}/status` | Get runtime status |
| POST | `/api/workspaces/{ws_id}/projects/{id}/import` | Import IRIS XML |
| GET | `/api/workspaces/{ws_id}/projects/{id}/export` | Export config |

### 3.3 Item APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{proj_id}/items` | List items |
| POST | `/api/projects/{proj_id}/items` | Create item |
| GET | `/api/projects/{proj_id}/items/{id}` | Get item details |
| PUT | `/api/projects/{proj_id}/items/{id}` | Update item |
| DELETE | `/api/projects/{proj_id}/items/{id}` | Delete item |
| POST | `/api/projects/{proj_id}/items/{id}/start` | Start item |
| POST | `/api/projects/{proj_id}/items/{id}/stop` | Stop item |

### 3.4 Connection APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{proj_id}/connections` | List connections |
| POST | `/api/projects/{proj_id}/connections` | Create connection |
| PUT | `/api/projects/{proj_id}/connections/{id}` | Update connection |
| DELETE | `/api/projects/{proj_id}/connections/{id}` | Delete connection |

### 3.5 Item Type Registry API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/item-types` | List available item types |
| GET | `/api/item-types/{type}` | Get item type schema |

---

## 4. API Request/Response Schemas

### 4.1 Create Project

**Request:**
```json
POST /api/workspaces/{ws_id}/projects
{
  "name": "adt-integration",
  "displayName": "ADT Integration",
  "description": "ADT message routing for PAS",
  "enabled": true,
  "settings": {
    "actorPoolSize": 2,
    "gracefulShutdownTimeout": 30
  }
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "workspaceId": "...",
  "name": "adt-integration",
  "displayName": "ADT Integration",
  "state": "stopped",
  "version": 1,
  "createdAt": "2026-01-25T12:00:00Z"
}
```

### 4.2 Create Item

**Request:**
```json
POST /api/projects/{proj_id}/items
{
  "name": "HL7.In.PAS",
  "displayName": "PAS Inbound",
  "itemType": "service",
  "className": "EnsLib.HL7.Service.TCPService",
  "category": "PAS",
  "enabled": true,
  "poolSize": 2,
  "position": { "x": 100, "y": 200 },
  "adapterSettings": {
    "port": 2575,
    "readTimeout": 30
  },
  "hostSettings": {
    "messageSchemaCategory": "2.4",
    "targetConfigNames": ["HL7.Router"],
    "ackMode": "App"
  }
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "projectId": "...",
  "name": "HL7.In.PAS",
  "itemType": "service",
  "className": "li.hosts.hl7.HL7TCPService",
  "state": "stopped",
  "createdAt": "2026-01-25T12:00:00Z"
}
```

### 4.3 Import IRIS XML

**Request:**
```json
POST /api/workspaces/{ws_id}/projects/{id}/import
Content-Type: multipart/form-data

file: [IRIS .cls or .xml file]
```

**Response:**
```json
{
  "status": "imported",
  "projectId": "...",
  "itemsImported": 5,
  "connectionsImported": 4,
  "warnings": []
}
```

### 4.4 Deploy Project

**Request:**
```json
POST /api/workspaces/{ws_id}/projects/{id}/deploy
{
  "startAfterDeploy": true
}
```

**Response:**
```json
{
  "status": "deployed",
  "engineId": "li-engine-001",
  "state": "running",
  "itemsStarted": 5
}
```

---

## 5. Item Type Registry

### 5.1 Available Item Types

```json
{
  "itemTypes": [
    {
      "type": "hl7.tcp.service",
      "name": "HL7 TCP Service",
      "description": "Receives HL7v2 messages via MLLP/TCP",
      "category": "service",
      "irisClassName": "EnsLib.HL7.Service.TCPService",
      "liClassName": "li.hosts.hl7.HL7TCPService",
      "adapterSettings": [
        { "key": "port", "label": "Port", "type": "number", "required": true, "default": 2575 },
        { "key": "readTimeout", "label": "Read Timeout (s)", "type": "number", "default": 30 },
        { "key": "stayConnected", "label": "Stay Connected", "type": "number", "default": -1 }
      ],
      "hostSettings": [
        { "key": "messageSchemaCategory", "label": "HL7 Version", "type": "select", "options": ["2.3", "2.4", "2.5"], "default": "2.4" },
        { "key": "targetConfigNames", "label": "Target Items", "type": "multiselect", "required": true },
        { "key": "ackMode", "label": "ACK Mode", "type": "select", "options": ["App", "Immediate", "None"], "default": "App" }
      ]
    },
    {
      "type": "hl7.tcp.operation",
      "name": "HL7 TCP Operation",
      "description": "Sends HL7v2 messages via MLLP/TCP",
      "category": "operation",
      "irisClassName": "EnsLib.HL7.Operation.TCPOperation",
      "liClassName": "li.hosts.hl7.HL7TCPOperation",
      "adapterSettings": [
        { "key": "ipAddress", "label": "IP Address", "type": "string", "required": true },
        { "key": "port", "label": "Port", "type": "number", "required": true, "default": 2575 },
        { "key": "connectTimeout", "label": "Connect Timeout (s)", "type": "number", "default": 30 }
      ],
      "hostSettings": [
        { "key": "replyCodeActions", "label": "Reply Code Actions", "type": "string" },
        { "key": "retryInterval", "label": "Retry Interval (s)", "type": "number", "default": 5 },
        { "key": "failureTimeout", "label": "Failure Timeout (s)", "type": "number", "default": 15 }
      ]
    },
    {
      "type": "hl7.routing.engine",
      "name": "HL7 Routing Engine",
      "description": "Routes HL7 messages based on rules",
      "category": "process",
      "irisClassName": "EnsLib.HL7.MsgRouter.RoutingEngine",
      "liClassName": "li.hosts.routing.HL7RoutingEngine",
      "hostSettings": [
        { "key": "businessRuleName", "label": "Business Rule", "type": "string" },
        { "key": "validation", "label": "Validation", "type": "select", "options": ["", "Warn", "Error"], "default": "" }
      ]
    }
  ]
}
```

---

## 6. Frontend UI Design

### 6.1 Navigation Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [Workspace Selector ▼]    HIE Management Portal    [User] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Sidebar:                    Main Content:                  │
│  ├── Dashboard               ┌─────────────────────────┐   │
│  ├── Projects ←NEW           │                         │   │
│  │   ├── List                │   Project Editor        │   │
│  │   └── [Project Name]      │   - Visual Canvas       │   │
│  │       ├── Configure       │   - Item Palette        │   │
│  │       ├── Items           │   - Properties Panel    │   │
│  │       └── Monitor         │                         │   │
│  ├── Messages                └─────────────────────────┘   │
│  ├── Monitoring                                             │
│  ├── Errors                                                 │
│  ├── Logs                                                   │
│  └── Settings                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Key UI Components

#### 6.2.1 Workspace Selector
- Dropdown in top navigation
- Shows current workspace name
- Lists all accessible workspaces
- "Create New Workspace" option

#### 6.2.2 Projects List Page
- Table of projects in current workspace
- Columns: Name, State, Items, Last Modified, Actions
- Actions: Start, Stop, Edit, Delete
- "Create Project" button
- "Import IRIS Config" button

#### 6.2.3 Project Editor Page
- **Visual Canvas** (center)
  - Drag-drop items from palette
  - Draw connections between items
  - Zoom/pan controls
  
- **Item Palette** (left sidebar)
  - Categorized item types
  - Search/filter
  - Drag to canvas
  
- **Properties Panel** (right sidebar)
  - Selected item configuration
  - Adapter settings form
  - Host settings form
  - Validation feedback

#### 6.2.4 Item Configuration Forms
- Dynamic forms based on item type schema
- Field validation
- Target item selector (multiselect)
- Advanced settings accordion

---

## 7. User Stories & Use Cases

### UC-1: Create New Project

**As a** integration engineer  
**I want to** create a new workflow project  
**So that** I can configure message routing for a new integration

**Steps:**
1. User selects workspace from dropdown (or creates new)
2. User clicks "Create Project" button
3. User enters project name, description
4. System creates project in database
5. User is redirected to project editor

**API Calls:**
- `POST /api/workspaces/{ws_id}/projects`

---

### UC-2: Add Service Item

**As a** integration engineer  
**I want to** add an HL7 TCP service to receive messages  
**So that** external systems can send HL7 messages to my integration

**Steps:**
1. User opens project editor
2. User drags "HL7 TCP Service" from palette to canvas
3. User configures port, HL7 version, target items
4. User clicks "Save"
5. System persists item to database

**API Calls:**
- `GET /api/item-types` (load palette)
- `POST /api/projects/{proj_id}/items`

---

### UC-3: Configure Routing Rules

**As a** integration engineer  
**I want to** configure routing rules for message types  
**So that** ADT messages go to one destination and ORU to another

**Steps:**
1. User selects HL7 Routing Engine item
2. User opens "Routing Rules" tab in properties
3. User adds rule: "If MSH-9.1 = ADT, send to HL7.Out.PAS"
4. User adds rule: "If MSH-9.1 = ORU, send to HL7.Out.Lab"
5. User saves project

**API Calls:**
- `POST /api/projects/{proj_id}/routing-rules`
- `PUT /api/projects/{proj_id}/items/{id}`

---

### UC-4: Import IRIS Configuration

**As a** integration engineer  
**I want to** import an existing IRIS production configuration  
**So that** I can migrate from IRIS to HIE

**Steps:**
1. User clicks "Import IRIS Config" button
2. User selects .cls or .xml file
3. System parses IRIS XML using IRISXMLLoader
4. System creates project with items and connections
5. User reviews imported configuration
6. User saves project

**API Calls:**
- `POST /api/workspaces/{ws_id}/projects/{id}/import`

---

### UC-5: Deploy and Run Project

**As a** integration engineer  
**I want to** deploy and run my project  
**So that** messages can flow through the integration

**Steps:**
1. User clicks "Deploy" button
2. System validates configuration
3. System creates LI ProductionEngine instance
4. System loads configuration into engine
5. User clicks "Start"
6. System starts all enabled items
7. UI shows real-time status updates

**API Calls:**
- `POST /api/workspaces/{ws_id}/projects/{id}/deploy`
- `POST /api/workspaces/{ws_id}/projects/{id}/start`
- WebSocket: `/ws/projects/{id}/events`

---

### UC-6: Monitor Running Project

**As a** integration engineer  
**I want to** monitor my running project  
**So that** I can see message throughput and errors

**Steps:**
1. User opens project monitor page
2. UI shows real-time metrics per item
3. UI shows message flow visualization
4. UI shows error alerts
5. User can drill down to item details

**API Calls:**
- `GET /api/workspaces/{ws_id}/projects/{id}/status`
- WebSocket: `/ws/projects/{id}/metrics`

---

### UC-7: Stop and Update Project

**As a** integration engineer  
**I want to** stop, update, and restart my project  
**So that** I can make configuration changes

**Steps:**
1. User clicks "Stop" button
2. System gracefully stops all items
3. User makes configuration changes
4. User clicks "Save"
5. System persists changes to database
6. User clicks "Start"
7. System restarts with new configuration

**API Calls:**
- `POST /api/workspaces/{ws_id}/projects/{id}/stop`
- `PUT /api/projects/{proj_id}/items/{id}`
- `POST /api/workspaces/{ws_id}/projects/{id}/start`

---

## 8. Implementation Plan

### Phase 1: Backend APIs (Week 1)

| Task | Priority | Effort |
|------|----------|--------|
| Database schema migration | P0 | 2h |
| Workspace CRUD APIs | P0 | 4h |
| Project CRUD APIs | P0 | 4h |
| Item CRUD APIs | P0 | 4h |
| Connection CRUD APIs | P0 | 2h |
| Item type registry API | P0 | 2h |
| IRIS import endpoint | P1 | 4h |
| LI Engine integration | P0 | 8h |
| Deploy/Start/Stop APIs | P0 | 4h |

### Phase 2: Frontend - Projects (Week 2)

| Task | Priority | Effort |
|------|----------|--------|
| Workspace selector component | P0 | 4h |
| Projects list page | P0 | 4h |
| Create project wizard | P0 | 4h |
| Project editor layout | P0 | 4h |
| Item palette component | P0 | 4h |
| Properties panel component | P0 | 8h |

### Phase 3: Frontend - Visual Editor (Week 3)

| Task | Priority | Effort |
|------|----------|--------|
| Visual canvas (React Flow) | P1 | 8h |
| Drag-drop from palette | P1 | 4h |
| Connection drawing | P1 | 4h |
| Item configuration forms | P0 | 8h |
| Save/load project | P0 | 4h |

### Phase 4: Frontend - Runtime (Week 4)

| Task | Priority | Effort |
|------|----------|--------|
| Deploy button & flow | P0 | 4h |
| Start/Stop controls | P0 | 4h |
| Real-time status updates | P1 | 8h |
| Project monitor page | P1 | 8h |
| Error handling & alerts | P0 | 4h |

### Phase 5: Testing & Polish (Week 5)

| Task | Priority | Effort |
|------|----------|--------|
| API integration tests | P0 | 8h |
| E2E frontend tests | P1 | 8h |
| IRIS import testing | P0 | 4h |
| Performance testing | P1 | 4h |
| Documentation | P1 | 4h |

---

## 9. Technical Decisions

### 9.1 Backend

- **Framework:** aiohttp (existing)
- **Database:** PostgreSQL with asyncpg
- **Engine Integration:** LI ProductionEngine via Python API
- **Real-time:** WebSocket for status updates

### 9.2 Frontend

- **Framework:** Next.js 14 (existing)
- **State Management:** React Context + SWR for API
- **Visual Editor:** React Flow for canvas
- **Forms:** React Hook Form with Zod validation
- **UI Components:** Tailwind CSS + shadcn/ui

### 9.3 Data Flow

```
Frontend UI
    ↓ REST API
Backend API Server
    ↓ asyncpg
PostgreSQL (config persistence)
    ↓ Python API
LI ProductionEngine (runtime)
    ↓ 
Hosts/Adapters (message processing)
```

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex visual editor | High | Use React Flow library, start simple |
| Real-time sync issues | Medium | Optimistic updates, conflict resolution |
| IRIS import edge cases | Medium | Comprehensive test suite, fallback to manual |
| Performance with many items | Medium | Virtualization, pagination |

---

## 11. Approval Checklist

Please review and approve the following before implementation:

- [ ] Data model and database schema
- [ ] API endpoints and contracts
- [ ] Item type registry design
- [ ] UI navigation and layout
- [ ] User stories and use cases
- [ ] Implementation phases and timeline
- [ ] Technical decisions

---

## 12. Questions for Stakeholder

1. Should workspaces map to NHS Trusts (tenants)?
2. What is the maximum number of items per project?
3. Should we support project templates?
4. What IRIS versions need import support?
5. What is the priority for visual editor vs. form-based config?

---

*Awaiting approval to proceed with implementation.*
