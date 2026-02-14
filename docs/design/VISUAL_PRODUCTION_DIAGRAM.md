# Visual Production Diagram - Design Specification

**Version:** 1.0.0
**Last Updated:** February 11, 2026
**Status:** Design Ready - Awaiting Approval
**Target Release:** v1.8.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Feature Overview](#2-feature-overview)
3. [Wireframes & Visual Design](#3-wireframes--visual-design)
4. [Component Architecture](#4-component-architecture)
5. [User Interactions](#5-user-interactions)
6. [Data Model Integration](#6-data-model-integration)
7. [Implementation Plan](#7-implementation-plan)
8. [Technical Specifications](#8-technical-specifications)

---

## 1. Executive Summary

### Purpose

Create a **visual production diagram feature** similar to InterSystems IRIS Production Editor that allows users to:
- Visualize message flow through service items in a production
- See connections between items as directional edges
- View routing rules and their conditions
- Interactively reposition items via drag-and-drop
- Monitor real-time status and message throughput
- Access detailed configuration/logs per item

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Visual Understanding** | Users immediately see message flow topology |
| **Faster Debugging** | Identify bottlenecks and broken connections visually |
| **Production Monitoring** | Real-time status indicators on diagram |
| **Easier Configuration** | Drag-and-drop item placement, visual routing |
| **NHS Compliance** | Maintain audit trail of configuration changes |

### Design Principles

1. **IRIS Parity**: Mirror InterSystems IRIS visual workflow designer
2. **NHS Branding**: Use NHS color palette and design standards
3. **Responsive**: Adapt to tablet/desktop viewports
4. **Performant**: Handle productions with 50+ items
5. **Accessible**: Keyboard navigation and screen reader support

---

## 2. Feature Overview

### 2.1 Visual Diagram Tab

Add a new **"Diagram"** tab to the Project Detail page (`/projects/[id]`) that displays an interactive visual representation of the production.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Project: NHS ADT Integration               [Running ●] [Deploy]     │
├──────────────────────────────────────────────────────────────────────┤
│  [Items] [Connections] [Routing] [⭐ Diagram] [Settings]              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  Production Diagram                         │   │
│  │                                                             │   │
│  │    [Service]──────▶[Process]──────▶[Operation]             │   │
│  │    hl7server      validator      hl7sender                │   │
│  │        │                             │                      │   │
│  │        └────────▶[Archive]───────────┘                      │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  [Details Panel →]                                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Three-Column Layout

Items automatically organize into **3 columns** based on type:

```
┌─────────────┬─────────────┬─────────────┐
│  SERVICES   │  PROCESSES  │ OPERATIONS  │
│  (Inbound)  │  (Transform)│  (Outbound) │
├─────────────┼─────────────┼─────────────┤
│             │             │             │
│  ┌───────┐  │  ┌───────┐  │  ┌───────┐  │
│  │ HL7   │──┼─▶│Validate│──┼─▶│ HL7   │  │
│  │Server │  │  └───────┘  │  │Sender │  │
│  └───────┘  │      │      │  └───────┘  │
│             │      ▼      │      ▲      │
│  ┌───────┐  │  ┌───────┐  │      │      │
│  │ File  │──┼─▶│ Route │──┼──────┘      │
│  │Watch  │  │  │Engine │  │             │
│  └───────┘  │  └───────┘  │  ┌───────┐  │
│             │      │      │  │ File  │  │
│             │      └──────┼─▶│Writer │  │
│             │             │  └───────┘  │
│             │             │             │
└─────────────┴─────────────┴─────────────┘
```

### 2.3 View Modes

| Mode | Description | Layout |
|------|-------------|--------|
| **Column View** | Auto-organize into 3 columns by type | Default |
| **Graph View** | Free-form positioning (manual or auto-layout) | User-arranged |
| **Topology View** | Hierarchical tree from sources to destinations | Auto-calculated |
| **Table View** | Fallback tabular list (existing UI) | List-based |

### 2.4 Right Panel Detail View

Clicking an item opens a **right-side detail panel** with tabs:

```
┌─────────────────────────────────────────────────┐
│  hl7server1                      [×]            │
├─────────────────────────────────────────────────┤
│  [Configuration] [Metrics] [Messages] [Logs]    │
├─────────────────────────────────────────────────┤
│                                                 │
│  Configuration:                                 │
│  • Port: 2575                                   │
│  • IP Address: 0.0.0.0                          │
│  • Schema: HL7 2.3                              │
│  • Pool Size: 5                                 │
│  • Status: Running                              │
│                                                 │
│  Metrics (Last 1h):                             │
│  • Messages Received: 1,234                     │
│  • Messages Sent: 1,230                         │
│  • Errors: 4                                    │
│  • Avg Latency: 45ms                            │
│                                                 │
│  [Test Connection] [Edit Settings]              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 3. Wireframes & Visual Design

### 3.1 Full Page Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ [☰] OpenLI HIE                    ws1: NHS Trust     [User] [Theme] │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ◀ Back to Projects                                                    │
│                                                                        │
│  NHS ADT Integration Production              [●Running] [Deploy ▼]    │
│  ────────────────────────────────────────────────────────────────────  │
│                                                                        │
│  [Items] [Connections] [Routing] [★ Diagram] [Settings]               │
│  ────────────────────────────────────────────────────────────────────  │
│                                                                        │
│  ┌──── Diagram Toolbar ──────────────────────────────────────────┐   │
│  │ [⊕] Zoom In  [⊖] Zoom Out  [◎] Fit View  [↻] Auto Layout     │   │
│  │ [≡] Column   [⚬] Graph     [⤓] Topology  [▦] Table            │   │
│  │ Show: [☑] Status [☑] Metrics [☑] Labels [☐] Routing Rules     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                                                                  │ │
│  │     [SERVICES]          [PROCESSES]         [OPERATIONS]        │ │
│  │                                                                  │ │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │ │
│  │  │  hl7server1  │───▶│  validator   │───▶│  hl7sender1  │     │ │
│  │  │              │    │              │    │              │     │ │
│  │  │  HL7 TCP     │    │  NHS Valid   │    │  HL7 TCP     │     │ │
│  │  │  Port: 2575  │    │  Process     │    │  → RIS       │     │ │
│  │  │  ● Running   │    │  ● Running   │    │  ● Running   │     │ │
│  │  │  1.2K msg/h  │    │  1.2K msg/h  │    │  1.1K msg/h  │     │ │
│  │  └──────────────┘    └──────────────┘    └──────────────┘     │ │
│  │         │                    │                    │            │ │
│  │         │                    ▼                    │            │ │
│  │         │            ┌──────────────┐             │            │ │
│  │         │            │  router-adT  │             │            │ │
│  │         │            │              │             │            │ │
│  │         │            │  Content     │─────────────┘            │ │
│  │         │            │  Router      │                          │ │
│  │         │            │  ● Running   │                          │ │
│  │         │            └──────────────┘                          │ │
│  │         │                    │                                 │ │
│  │         │                    ▼                                 │ │
│  │         │            ┌──────────────┐     ┌──────────────┐    │ │
│  │         └───────────▶│archive-file  │     │  lab-sender  │    │ │
│  │                      │              │     │              │    │ │
│  │  ┌──────────────┐    │  File Write  │     │  HL7 TCP     │    │ │
│  │  │  file-watch  │    │  Archive     │     │  → LAB       │    │ │
│  │  │              │    │  ● Running   │◀────│  ● Running   │    │ │
│  │  │  File Reader │    │  1.2K msg/h  │     │  200 msg/h   │    │ │
│  │  │  ● Running   │    └──────────────┘     └──────────────┘    │ │
│  │  │  50 msg/h    │                                             │ │
│  │  └──────────────┘                                             │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──── Legend ──────────────────────────────────────────────────────┐ │
│  │ ■ Service (Inbound)  ■ Process (Transform)  ■ Operation (Out)   │ │
│  │ ─── Standard  ┄┄┄ Async  ╌╌╌ Error  ● Running  ○ Stopped         │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Node Design Specifications

#### Service Node (Inbound)

```
┌──────────────────────┐
│ ⬇ hl7server1         │  ← Icon + Name
├──────────────────────┤
│ HL7 TCP Service      │  ← Type Description
│ Port: 2575           │  ← Key Settings
│ ● Running            │  ← Status Indicator
│ 📊 1.2K msg/h        │  ← Metrics (optional)
└──────────────────────┘

Colors:
- Background: nhs-green-50 (#f0f9f5)
- Border: nhs-green (#007f3b) 2px
- Icon: nhs-green
- Status Dot: bright-green (running), gray (stopped)
- Hover: Shadow + border brighten
```

#### Process Node (Transform)

```
     ╭───────────╮
    ╱  validator  ╲       ← Diamond/Rounded shape
   ╱               ╲
  │  NHS Validation │     ← Type Description
  │  ● Running      │     ← Status
  │  📊 1.2K msg/h  │     ← Metrics
   ╲               ╱
    ╲             ╱
     ╰───────────╯

Colors:
- Background: nhs-blue-50 (#e8f4f8)
- Border: nhs-blue (#005eb8) 2px
- Icon: nhs-blue
- Status Dot: bright-blue (running), gray (stopped)
```

#### Operation Node (Outbound)

```
┌──────────────────────┐
│ hl7sender1 ⬆         │  ← Name + Icon (right)
├──────────────────────┤
│ HL7 TCP Operation    │  ← Type Description
│ → RIS (ris.nhs.uk)   │  ← Target Info
│ ● Running            │  ← Status Indicator
│ 📊 1.1K msg/h        │  ← Metrics (optional)
└──────────────────────┘

Colors:
- Background: nhs-purple-50 (#f3e5ff)
- Border: nhs-purple (#330072) 2px
- Icon: nhs-purple
- Status Dot: bright-purple (running), gray (stopped)
```

### 3.3 Edge Design Specifications

#### Standard Connection

```
[Source] ────────────▶ [Target]
         ─────────────

Style:
- Color: nhs-blue (#005eb8)
- Width: 2px
- Type: Solid line
- Arrow: Standard filled arrowhead
- Animated: Subtle flow animation (optional)
```

#### Error Connection

```
[Source] ╌╌╌╌╌╌╌╌╌╌╌▶ [Error Handler]
         ╌╌╌╌╌╌╌╌╌╌╌
          [Error]

Style:
- Color: nhs-red (#da291c)
- Width: 2px
- Type: Dashed line (6px dash, 4px gap)
- Arrow: Red filled arrowhead
- Label: "Error" badge
```

#### Async Connection

```
[Source] ┄┄┄┄┄┄┄┄┄┄┄▶ [Async Handler]
         ┄┄┄┄┄┄┄┄┄┄┄
         [Async]

Style:
- Color: nhs-yellow (#ffb81c)
- Width: 2px
- Type: Dotted line (2px dot, 3px gap)
- Arrow: Yellow filled arrowhead
- Label: "Async" badge
```

### 3.4 Routing Rule Visualization

When routing rules are enabled, show conditional paths:

```
              [ADT]
             ┌──────────┐
[hl7server] ─┤  router  ├─ ADT→RIS ────▶ [ris-sender]
             │          │
             │          ├─ ORU→LAB ────▶ [lab-sender]
             │          │    [ORU]
             └──────────┘
                  │
                  └─ Archive ──────────▶ [archive]
                     [All]
```

**Routing Rule Labels:**
```
┌─────────────────┐
│ ADT→RIS         │  ← Rule name
│ Priority: 1     │  ← Priority
│ MSH.9 = "ADT"   │  ← Condition
└─────────────────┘
```

### 3.5 Detail Panel Tabs

When an item is clicked, show detail panel on the right:

```
┌─────────────────────────────────────────────┐
│  hl7server1                    [Minimize ▼] │
├─────────────────────────────────────────────┤
│ [Configuration] [Metrics] [Messages] [Logs] │
├─────────────────────────────────────────────┤
│                                             │
│ [Configuration Tab]                         │
│ ┌─────────────────────────────────────────┐ │
│ │ Adapter Settings:                       │ │
│ │ • Port: 2575                            │ │
│ │ • IP Address: 0.0.0.0                   │ │
│ │ • Message Schema: HL7 2.3               │ │
│ │ • Pool Size: 5                          │ │
│ │ • Ack Mode: Application                 │ │
│ │                                         │ │
│ │ Host Settings:                          │ │
│ │ • Target: validator                     │ │
│ │ • Validation: Strict                    │ │
│ │ • Archive: Enabled                      │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ [Edit] [Test Connection] [View Full Config] │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [Metrics Tab]                               │
├─────────────────────────────────────────────┤
│                                             │
│ Last 1 Hour:                                │
│ • Messages Received: 1,234                  │
│ • Messages Sent: 1,230                      │
│ • Errors: 4 (0.3%)                          │
│ • Avg Latency: 45ms                         │
│ • Peak Latency: 120ms                       │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │     [Message Throughput Chart]          │ │
│ │  ▁▂▃▅▇█▇▅▃▂▁▂▃▅▇█▇▅▃▂▁                 │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ [Refresh] [Export CSV]                      │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [Messages Tab]                              │
├─────────────────────────────────────────────┤
│                                             │
│ Transaction Sessions:                       │
│                                             │
│ ┌─ Session: abc-123 ────────────────────┐  │
│ │ Master Session ID: abc-123            │  │
│ │ Started: 2026-02-11 15:45:00          │  │
│ │ Status: Completed                     │  │
│ │                                       │  │
│ │ Messages (3):                         │  │
│ │ • msg-001 - HL7 ADT Inbound           │  │
│ │ • msg-002 - Validation Success        │  │
│ │ • msg-003 - HL7 ADT Outbound          │  │
│ └───────────────────────────────────────┘  │
│                                             │
│ ┌─ Session: def-456 ────────────────────┐  │
│ │ Master Session ID: def-456            │  │
│ │ Started: 2026-02-11 15:44:30          │  │
│ │ Status: Error                         │  │
│ │                                       │  │
│ │ Messages (2):                         │  │
│ │ • msg-004 - HL7 ORU Inbound           │  │
│ │ • msg-005 - Validation Failed ⚠       │  │
│ └───────────────────────────────────────┘  │
│                                             │
│ [Load More] [Filter by Status]              │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [Logs Tab]                                  │
├─────────────────────────────────────────────┤
│                                             │
│ Event Logs (Last 100):                     │
│                                             │
│ [15:45:23] INFO  Connection received       │
│ [15:45:22] DEBUG Message parsed (ADT^A01)  │
│ [15:45:21] INFO  Sent to validator         │
│ [15:45:20] DEBUG ACK received from RIS     │
│ [15:45:19] WARN  Retry attempt 2 of 3      │
│ [15:45:18] ERROR Connection timeout        │
│                                             │
│ [Refresh] [Export Logs] [Clear]             │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 4. Component Architecture

### 4.1 Component Hierarchy

```
ProjectDetailPage.tsx
├── TabNavigation
│   ├── ItemsTab (existing)
│   ├── ConnectionsTab (existing)
│   ├── RoutingTab (existing)
│   ├── DiagramTab ← NEW
│   │   ├── DiagramToolbar
│   │   │   ├── ZoomControls
│   │   │   ├── ViewModeSelector
│   │   │   └── DisplayOptions
│   │   ├── ProductionDiagram
│   │   │   ├── ReactFlow (library)
│   │   │   ├── DiagramNode (custom)
│   │   │   ├── DiagramEdge (custom)
│   │   │   └── RoutingRuleOverlay
│   │   └── DiagramLegend
│   └── SettingsTab (existing)
└── DetailPanel (conditional)
    ├── ConfigurationTab
    ├── MetricsTab
    ├── MessagesTab
    └── LogsTab
```

### 4.2 New Component Files

```
Portal/src/components/ProductionDiagram/
├── ProductionDiagram.tsx          ← Main container
├── DiagramToolbar.tsx             ← Zoom, view mode, options
├── DiagramNode.tsx                ← Custom node renderer
├── DiagramEdge.tsx                ← Custom edge renderer
├── NodeTypeIcon.tsx               ← Service/Process/Operation icons
├── RoutingRuleOverlay.tsx         ← Routing rule visualization
├── DiagramLegend.tsx              ← Color/style legend
├── ItemDetailPanel.tsx            ← Right-side detail panel
│   ├── ConfigurationTab.tsx
│   ├── MetricsTab.tsx
│   ├── MessagesTab.tsx
│   └── LogsTab.tsx
└── types.ts                       ← Type definitions
```

### 4.3 Data Flow

```
Project Detail Page
    ↓
Load ProjectDetail via API
    ├── items: ProjectItem[]
    ├── connections: Connection[]
    └── routing_rules: RoutingRule[]
    ↓
Transform to ReactFlow Format
    ├── nodes: Node[] (from items)
    │   ├── id: item.id
    │   ├── type: 'service' | 'process' | 'operation'
    │   ├── position: { x: item.position_x, y: item.position_y }
    │   └── data: { item, metrics }
    └── edges: Edge[] (from connections)
        ├── id: connection.id
        ├── source: connection.source_item_id
        ├── target: connection.target_item_id
        ├── type: connection.connection_type
        └── data: { routing_rules }
    ↓
ProductionDiagram Component
    ├── Render nodes (custom DiagramNode)
    ├── Render edges (custom DiagramEdge)
    ├── Handle drag events → update position
    ├── Handle click events → open detail panel
    └── Handle routing rule overlays
    ↓
User Interactions
    ├── Drag node → call updateItem API
    ├── Click node → setState(selectedItem)
    ├── Click edge → setState(selectedConnection)
    └── Hover edge → highlight routing rules
```

---

## 5. User Interactions

### 5.1 Diagram Interactions

| Interaction | Action | Result |
|-------------|--------|--------|
| **Pan** | Click + drag canvas | Move viewport |
| **Zoom** | Scroll wheel or toolbar | Zoom in/out |
| **Fit View** | Click toolbar button | Auto-fit all nodes |
| **Drag Node** | Click + drag node | Reposition item + update backend |
| **Click Node** | Click node | Open detail panel |
| **Hover Node** | Mouse over node | Show tooltip with metrics |
| **Click Edge** | Click connection | Highlight source/target + show rules |
| **Hover Edge** | Mouse over edge | Show connection details |
| **Toggle Rules** | Checkbox in toolbar | Show/hide routing rule labels |

### 5.2 View Mode Switching

**Column View (Default):**
- Auto-organize into 3 columns by item type
- Services on left, processes in middle, operations on right
- Items sorted by name within each column
- Connections flow left-to-right

**Graph View:**
- Free-form positioning
- Use stored position_x, position_y from database
- Allow manual drag-and-drop
- Save positions on drag end

**Topology View:**
- Hierarchical tree layout
- Calculate levels from source (services) to sink (operations)
- Auto-layout using Dagre or Elk algorithm
- Read-only (no dragging)

**Table View:**
- Fallback to existing tabular list
- Show items in table with status, type, metrics
- Click to open detail panel

### 5.3 Detail Panel Interactions

**Open Detail Panel:**
- Click any node in diagram
- Panel slides in from right (400px width)
- Diagram shrinks to accommodate panel

**Close Detail Panel:**
- Click X button
- Press Escape key
- Click outside panel (optional)

**Tab Navigation:**
- Click tab to switch (Configuration, Metrics, Messages, Logs)
- Keyboard: Tab key cycles through tabs
- Deep link: URL param `?item=hl7server1&tab=metrics`

**Edit Configuration:**
- Click "Edit" button in Configuration tab
- Open modal dialog with form
- Submit → update item via API → refresh diagram

---

## 6. Data Model Integration

### 6.1 API Endpoints

**Get Project Detail:**
```typescript
GET /api/projects/:id
Response: ProjectDetail {
  id, name, display_name, state,
  items: ProjectItem[],
  connections: Connection[],
  routing_rules: RoutingRule[]
}
```

**Update Item Position:**
```typescript
PUT /api/projects/:id/items/:item_id
Body: {
  position_x: number,
  position_y: number
}
Response: ProjectItem
```

**Get Item Metrics:**
```typescript
GET /api/projects/:id/items/:item_id/metrics
Response: {
  messages_received: number,
  messages_sent: number,
  errors: number,
  avg_latency_ms: number,
  last_updated: timestamp
}
```

**Get Item Messages:**
```typescript
GET /api/projects/:id/items/:item_id/messages?limit=50
Response: {
  sessions: TransactionSession[] {
    master_session_id: string,
    started_at: timestamp,
    status: 'completed' | 'error' | 'in_progress',
    messages: Message[] {
      message_id: string,
      direction: 'inbound' | 'outbound',
      message_type: string,
      timestamp: timestamp,
      status: string
    }
  }
}
```

**Get Item Logs:**
```typescript
GET /api/projects/:id/items/:item_id/logs?limit=100
Response: {
  logs: LogEntry[] {
    timestamp: timestamp,
    level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR',
    message: string,
    context: object
  }
}
```

### 6.2 Data Transformations

**Items → ReactFlow Nodes:**

```typescript
function itemsToNodes(items: ProjectItem[], viewMode: ViewMode): Node[] {
  return items.map((item, index) => ({
    id: item.id,
    type: getNodeType(item.item_type),  // 'service', 'process', 'operation'
    position: viewMode === 'column'
      ? calculateColumnPosition(item, index)
      : { x: item.position_x, y: item.position_y },
    data: {
      item,
      label: item.name,
      className: item.class_name,
      enabled: item.enabled,
      status: item.enabled ? 'running' : 'stopped',
      metrics: item.metrics || {},
    },
  }));
}

function calculateColumnPosition(item: ProjectItem, index: number): Position {
  const column = getColumnForType(item.item_type); // 0, 1, or 2
  const itemsInColumn = items.filter(i => i.item_type === item.item_type).length;
  const indexInColumn = items.filter(i => i.item_type === item.item_type).indexOf(item);

  return {
    x: column * 400 + 100,  // 400px column width, 100px margin
    y: indexInColumn * 200 + 100,  // 200px vertical spacing
  };
}
```

**Connections → ReactFlow Edges:**

```typescript
function connectionsToEdges(
  connections: Connection[],
  routingRules: RoutingRule[]
): Edge[] {
  return connections.map(conn => ({
    id: conn.id,
    source: conn.source_item_id,
    target: conn.target_item_id,
    type: getEdgeType(conn.connection_type),  // 'standard', 'error', 'async'
    animated: conn.connection_type !== 'error',
    style: getEdgeStyle(conn.connection_type),
    markerEnd: { type: MarkerType.ArrowClosed },
    data: {
      connection: conn,
      routingRules: routingRules.filter(rule =>
        rule.target_items.includes(getItemName(conn.target_item_id))
      ),
    },
    label: conn.connection_type === 'error' ? 'Error' :
           conn.connection_type === 'async' ? 'Async' : undefined,
  }));
}

function getEdgeStyle(type: string): React.CSSProperties {
  switch (type) {
    case 'error':
      return { stroke: '#da291c', strokeWidth: 2, strokeDasharray: '6 4' };
    case 'async':
      return { stroke: '#ffb81c', strokeWidth: 2, strokeDasharray: '2 3' };
    default:
      return { stroke: '#005eb8', strokeWidth: 2 };
  }
}
```

### 6.3 Real-Time Updates

**Polling Strategy:**

```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    if (activeTab === 'diagram') {
      const updatedProject = await fetchProjectDetail(projectId);

      // Update node statuses
      setNodes(prevNodes =>
        prevNodes.map(node => ({
          ...node,
          data: {
            ...node.data,
            status: getItemStatus(updatedProject.items, node.id),
            metrics: getItemMetrics(updatedProject.items, node.id),
          },
        }))
      );
    }
  }, 10000);  // Poll every 10 seconds

  return () => clearInterval(interval);
}, [activeTab, projectId]);
```

---

## 7. Implementation Plan

### 7.1 Phase 1: Display-Only Diagram (MVP)

**Goal:** Visual diagram with basic interactivity

**Scope:**
1. Add "Diagram" tab to project detail page
2. Create ProductionDiagram component using ReactFlow
3. Custom DiagramNode component (3 types)
4. Custom DiagramEdge component (3 types)
5. Column view auto-layout
6. Zoom/pan controls
7. Status indicators

**Tasks:**
```
✓ Install ReactFlow dependencies
✓ Create component structure
□ Implement itemsToNodes transformation
□ Implement connectionsToEdges transformation
□ Create DiagramNode component (service/process/operation)
□ Create DiagramEdge component (standard/error/async)
□ Add diagram toolbar (zoom, fit view)
□ Add diagram legend
□ Integrate into project detail page
□ Test with sample production data
```

**Time Estimate:** 8-10 hours
**Deliverables:**
- Functional visual diagram
- 3-column auto-layout
- Color-coded nodes and edges
- Zoom/pan navigation

### 7.2 Phase 2: Interactive Diagram

**Goal:** Add drag-and-drop, detail panel, and metrics

**Scope:**
1. Drag nodes to reposition
2. Update positions via API
3. Click node → open detail panel
4. Detail panel with 4 tabs (Config, Metrics, Messages, Logs)
5. Hover tooltips
6. Real-time status polling

**Tasks:**
```
□ Implement node drag handler
□ Call updateItem API on drag end
□ Create ItemDetailPanel component
□ Implement ConfigurationTab
□ Implement MetricsTab with charts
□ Implement MessagesTab (transaction sessions)
□ Implement LogsTab
□ Add hover tooltips
□ Implement polling for status updates
□ Add loading states and error handling
```

**Time Estimate:** 10-12 hours
**Deliverables:**
- Drag-and-drop repositioning
- Detail panel with 4 tabs
- Real-time metrics display
- Message transaction viewer

### 7.3 Phase 3: Advanced Features

**Goal:** Routing rules, auto-layout, animations

**Scope:**
1. Routing rule overlay visualization
2. Graph view (free-form)
3. Topology view (hierarchical auto-layout)
4. Message flow animation
5. Conditional edge highlighting
6. Keyboard shortcuts
7. Accessibility improvements

**Tasks:**
```
□ Implement RoutingRuleOverlay component
□ Add graph view with stored positions
□ Implement topology view with Dagre layout
□ Add message flow animation (optional)
□ Highlight edges on routing rule hover
□ Add keyboard shortcuts (Ctrl+F for fit, Esc to close panel)
□ Add ARIA labels for screen readers
□ Performance optimization (virtualization for 100+ nodes)
□ E2E tests for diagram interactions
```

**Time Estimate:** 12-15 hours
**Deliverables:**
- Routing rule visualization
- Multiple view modes
- Auto-layout algorithms
- Full accessibility support

### 7.4 Total Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1 (MVP) | 8-10 hours | 8-10 hours |
| Phase 2 (Interactive) | 10-12 hours | 18-22 hours |
| Phase 3 (Advanced) | 12-15 hours | 30-37 hours |

**Total: 30-37 hours (~1 sprint)**

---

## 8. Technical Specifications

### 8.1 Dependencies

**Already Installed:**
```json
{
  "reactflow": "^11.10.0",
  "lucide-react": "^0.312.0",
  "tailwindcss": "^3.4.1"
}
```

**Additional Dependencies (if needed):**
```json
{
  "dagre": "^0.8.5",           // Auto-layout algorithm
  "@types/dagre": "^0.7.52",
  "elkjs": "^0.8.2"            // Alternative auto-layout
}
```

### 8.2 Performance Targets

| Metric | Target | Max |
|--------|--------|-----|
| **Nodes** | 50 items | 100 items |
| **Edges** | 100 connections | 200 connections |
| **Initial Render** | < 500ms | < 1s |
| **Drag Latency** | < 16ms | < 50ms |
| **Zoom/Pan** | 60 FPS | 30 FPS |
| **API Update** | < 200ms | < 500ms |

### 8.3 Browser Support

| Browser | Version | Support |
|---------|---------|---------|
| Chrome | 90+ | Full |
| Firefox | 88+ | Full |
| Safari | 14+ | Full |
| Edge | 90+ | Full |
| Mobile Safari | 14+ | Limited (view-only) |
| Mobile Chrome | 90+ | Limited (view-only) |

### 8.4 Responsive Breakpoints

```css
/* Mobile: View-only, table fallback */
@media (max-width: 768px) {
  .diagram-container { display: none; }
  .table-view { display: block; }
}

/* Tablet: Simplified diagram, no detail panel */
@media (min-width: 769px) and (max-width: 1024px) {
  .diagram-container { display: block; }
  .detail-panel { display: none; }  /* Open as modal instead */
}

/* Desktop: Full features */
@media (min-width: 1025px) {
  .diagram-container { display: flex; }
  .detail-panel { width: 400px; }
}
```

### 8.5 Accessibility

**Keyboard Navigation:**
```
Tab: Focus next node
Shift+Tab: Focus previous node
Enter: Select/open detail panel
Esc: Close detail panel
Arrow Keys: Pan viewport
+/-: Zoom in/out
Ctrl+F: Fit view
```

**Screen Reader Support:**
```html
<div role="diagram" aria-label="Production message flow diagram">
  <div role="list" aria-label="Service items">
    <div role="listitem" aria-label="hl7server1: Running, 1.2K messages/hour">
      <!-- Node content -->
    </div>
  </div>
  <div role="list" aria-label="Connections">
    <div role="listitem" aria-label="Connection from hl7server1 to validator">
      <!-- Edge content -->
    </div>
  </div>
</div>
```

---

## 9. Testing & Quality Assurance

### 9.1 Unit Tests

```typescript
// ProductionDiagram.test.tsx
describe('ProductionDiagram', () => {
  it('transforms items to nodes correctly', () => {
    const items = [mockServiceItem, mockProcessItem, mockOperationItem];
    const nodes = itemsToNodes(items, 'column');
    expect(nodes).toHaveLength(3);
    expect(nodes[0].type).toBe('service');
    expect(nodes[0].position.x).toBe(100);
  });

  it('transforms connections to edges correctly', () => {
    const connections = [mockStandardConnection, mockErrorConnection];
    const edges = connectionsToEdges(connections, []);
    expect(edges).toHaveLength(2);
    expect(edges[1].type).toBe('error');
    expect(edges[1].style.strokeDasharray).toBe('6 4');
  });

  it('handles drag events and calls API', async () => {
    const mockUpdate = jest.fn();
    const { getByText } = render(<ProductionDiagram onUpdateItem={mockUpdate} />);
    // Simulate drag...
    expect(mockUpdate).toHaveBeenCalledWith(expect.objectContaining({
      position_x: expect.any(Number),
      position_y: expect.any(Number),
    }));
  });
});
```

### 9.2 Integration Tests

```typescript
// ProjectDetailPage.integration.test.tsx
describe('Project Detail - Diagram Tab', () => {
  it('loads diagram when tab is selected', async () => {
    const { getByText, findByLabelText } = render(<ProjectDetailPage id="test-project" />);

    fireEvent.click(getByText('Diagram'));

    const diagram = await findByLabelText('Production message flow diagram');
    expect(diagram).toBeInTheDocument();
    expect(within(diagram).getAllByRole('listitem')).toHaveLength(5); // 5 items
  });

  it('opens detail panel when node is clicked', async () => {
    const { getByText, findByText } = render(<ProjectDetailPage />);

    fireEvent.click(getByText('Diagram'));
    const node = await findByText('hl7server1');
    fireEvent.click(node);

    expect(await findByText('Configuration')).toBeInTheDocument();
    expect(await findByText('Port: 2575')).toBeInTheDocument();
  });
});
```

### 9.3 E2E Tests

```typescript
// diagram.e2e.test.ts
describe('Visual Production Diagram E2E', () => {
  it('displays diagram for NHS ADT production', () => {
    cy.visit('/projects/nhs-adt-integration');
    cy.contains('Diagram').click();

    cy.get('[role="diagram"]').should('be.visible');
    cy.contains('hl7server1').should('be.visible');
    cy.contains('validator').should('be.visible');
    cy.contains('hl7sender1').should('be.visible');
  });

  it('allows dragging nodes and saves position', () => {
    cy.visit('/projects/nhs-adt-integration');
    cy.contains('Diagram').click();

    cy.contains('hl7server1')
      .trigger('mousedown', { which: 1 })
      .trigger('mousemove', { clientX: 400, clientY: 300 })
      .trigger('mouseup');

    cy.wait('@updateItemPosition').its('request.body').should('include', {
      position_x: 400,
      position_y: 300,
    });
  });

  it('shows metrics in detail panel', () => {
    cy.visit('/projects/nhs-adt-integration');
    cy.contains('Diagram').click();
    cy.contains('hl7server1').click();

    cy.contains('Metrics').click();
    cy.contains('Messages Received: 1,234').should('be.visible');
    cy.contains('Avg Latency: 45ms').should('be.visible');
  });
});
```

---

## 10. Success Criteria

### 10.1 Feature Completeness

- [ ] Visual diagram displays all items in production
- [ ] Nodes are color-coded by type (service, process, operation)
- [ ] Edges show connection types (standard, error, async)
- [ ] Status indicators show real-time item state
- [ ] Drag-and-drop repositioning works
- [ ] Detail panel opens on node click
- [ ] All 4 detail tabs functional (Config, Metrics, Messages, Logs)
- [ ] Routing rules visualized (overlays or labels)
- [ ] Multiple view modes available (column, graph, topology, table)
- [ ] Zoom/pan/fit controls functional

### 10.2 User Experience

- [ ] Initial load < 500ms for 20-item production
- [ ] Smooth 60 FPS drag interactions
- [ ] Intuitive navigation (no tutorial needed)
- [ ] Accessible via keyboard and screen reader
- [ ] Responsive on tablet (simplified view)
- [ ] Fallback to table view on mobile

### 10.3 NHS Compliance

- [ ] Uses NHS brand colors throughout
- [ ] Follows Tailwind design system
- [ ] Maintains consistency with existing Portal UI
- [ ] Audit trail for configuration changes
- [ ] GDPR-compliant message viewer (no PHI in UI)

---

## 11. Future Enhancements (v2.0+)

### 11.1 Advanced Visualization

- [ ] Message flow animation (real-time)
- [ ] Heat map overlays (bottleneck detection)
- [ ] 3D graph view (for complex productions)
- [ ] Mini-map navigator (for large diagrams)

### 11.2 Editing Capabilities

- [ ] Drag to create connections
- [ ] Right-click context menu (add item, delete, etc.)
- [ ] Inline editing of item settings
- [ ] Copy/paste nodes
- [ ] Undo/redo support

### 11.3 Collaboration Features

- [ ] Multi-user editing (WebSocket sync)
- [ ] Comments on nodes/edges
- [ ] Change approval workflow
- [ ] Version history with rollback

### 11.4 AI/ML Integration

- [ ] Auto-suggest optimal layouts
- [ ] Predict bottlenecks before they occur
- [ ] Anomaly detection on message patterns
- [ ] Smart routing rule recommendations

---

## 12. Appendix

### 12.1 Glossary

| Term | Definition |
|------|------------|
| **Production** | A configured set of items and connections that process messages |
| **Item** | A service, process, or operation in a production |
| **Service** | Inbound adapter that receives messages (HL7 TCP, File, HTTP) |
| **Process** | Business logic that transforms or routes messages |
| **Operation** | Outbound adapter that sends messages to external systems |
| **Connection** | Message flow path between two items |
| **Routing Rule** | Conditional logic that directs messages to different paths |
| **Session** | A transaction session containing related messages |

### 12.2 References

- [InterSystems IRIS Production Editor](https://docs.intersystems.com/irislatest/csp/docbook/Doc.View.cls?KEY=EGDV_production)
- [ReactFlow Documentation](https://reactflow.dev/docs/introduction)
- [NHS Design System](https://service-manual.nhs.uk/design-system)
- [HIE UI Design Specification](UI_DESIGN_SPECIFICATION.md)
- [HIE API Documentation](../guides/LI_HIE_DEVELOPER_GUIDE.md)

---

**End of Design Specification**

**Prepared By:** HIE Core Team
**Reviewed By:** [Pending]
**Approved By:** [Pending]
**Date:** February 11, 2026
