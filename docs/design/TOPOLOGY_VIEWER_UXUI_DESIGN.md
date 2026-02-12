# Enterprise Production Topology Viewer - UI/UX Design Specification

**Version:** 2.0.0
**Last Updated:** February 12, 2026
**Status:** Design Ready for Implementation
**Design System:** NHS Digital Service Manual + OpenLI HIE

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Information Architecture](#2-information-architecture)
3. [Visual Design System](#3-visual-design-system)
4. [Layout Specifications](#4-layout-specifications)
5. [Component Wireframes](#5-component-wireframes)
6. [Interaction Patterns](#6-interaction-patterns)
7. [Responsive Behavior](#7-responsive-behavior)
8. [Accessibility Guidelines](#8-accessibility-guidelines)

---

## 1. Design Principles

### 1.1 Core Principles for Mission-Critical Healthcare UI

**1. Clarity Over Cleverness**
- **Rationale:** In hospital emergency scenarios, ambiguity costs lives
- **Application:** Direct labeling, no hidden features, predictable interactions
- **Anti-Pattern:** Avoid "innovative" gestures that require learning

**2. Status-First Information Hierarchy**
- **Rationale:** Operational status is the most critical information
- **Application:** Status indicators are largest, brightest visual elements
- **Example:** ● Running (green 12px dot) vs. text "Status: Running" (gray 10px)

**3. Progressive Disclosure**
- **Rationale:** Overwhelming users with all data leads to cognitive overload
- **Application:** Summary view → Detail panel → Deep dive modals
- **Example:** Node shows name + status → Panel shows config → Modal shows full logs

**4. Fail-Safe Design**
- **Rationale:** System failures must be immediately obvious
- **Application:** Red color reserved exclusively for errors, not branding
- **Example:** Gray node with ⚠ icon, not just red outline

**5. Muscle Memory Optimization**
- **Rationale:** Operators use this UI 40+ hours/week
- **Application:** Consistent placement, keyboard shortcuts, predictable workflows
- **Example:** Detail panel always opens right side, Escape always closes

### 1.2 NHS Digital Design System Alignment

**Color Palette:**
- NHS Blue: #005eb8 (primary actions, processes)
- NHS Green: #007f3b (success, services)
- NHS Purple: #330072 (operations)
- NHS Red: #da291c (errors, critical alerts)
- NHS Yellow: #ffb81c (warnings, async)
- NHS Grey: #425563 (neutral, disabled)

**Typography:**
- Font Family: "Frutiger", "Helvetica Neue", Arial, sans-serif
- Headings: 16px bold (h3), 14px bold (h4), 12px bold (h5)
- Body: 14px regular (primary), 12px regular (secondary)
- Mono: "Courier New", monospace (logs, code)

**Spacing:**
- Base Unit: 8px
- Vertical Rhythm: 8px, 16px, 24px, 32px, 48px
- Horizontal: 12px (compact), 16px (default), 24px (spacious)

---

## 2. Information Architecture

### 2.1 Page Structure Hierarchy

```
Project Detail Page
├── Header (persistent)
│   ├── Breadcrumb: Home > Workspaces > NHS Trust > Projects > [Project Name]
│   ├── Project Title + Status Badge
│   └── Action Buttons: Deploy, Start/Stop
│
├── Tab Navigation (persistent)
│   ├── Items (3)
│   ├── Connections (5)
│   ├── Routing (2)
│   ├── ★ Topology ← NEW (highlighted)
│   └── Settings
│
└── Topology Tab Content (full height)
    ├── Toolbar (sticky top, 60px)
    │   ├── View Mode: [Graph] [Table]
    │   ├── Controls: Zoom In | Zoom Out | Fit | Search
    │   └── Options: ☑ Status ☑ Metrics ☑ Labels
    │
    ├── Main Content Area (adaptive)
    │   │
    │   ├─ IF Graph View:
    │   │  ├── Topology Canvas (full width - detail panel)
    │   │  │   ├── ReactFlow Container (zoom/pan)
    │   │  │   ├── Mini-map (bottom-right, 150x100px)
    │   │  │   └── Legend (bottom-left, 400x80px)
    │   │  │
    │   │  └── Detail Panel (right side, 400px, collapsible)
    │   │      ├── Header: [Item Name] [×]
    │   │      ├── Tabs: Configuration | Events | Messages | Metrics
    │   │      └── Tab Content (scrollable)
    │   │
    │   └─ IF Table View:
    │      └── Data Table (full width)
    │          ├── Toolbar: Filter | Export CSV
    │          └── Sortable Columns
    │
    └── Status Bar (bottom, 32px, optional)
        ├── Connection Status: ● Live
        ├── Last Updated: 2s ago
        └── Item Count: 8 items (7 running, 1 stopped)
```

### 2.2 Navigation Flow

**Primary Flows:**

```
1. Monitor Health Flow:
   Topology Tab → View Graph → Scan for Red Nodes → Click Error Node → Events Tab → See Error Log

2. Trace Message Flow:
   Topology Tab → Messages Tab (any item) → Click Message Row → Message Trace Swimlane Modal

3. Troubleshoot Failure Flow:
   Alert Badge → Topology Tab → Click Failed Node → Events Tab → Filter ERROR → Copy Log → Search KB

4. Configure Item Flow:
   Topology Tab → Click Node → Configuration Tab → View Settings → Click "Edit" → Edit Modal
```

### 2.3 Mental Model Alignment

**User Mental Model:** "Production is like a factory assembly line"
- **Services** = Raw material intake docks (inbound HL7)
- **Processes** = Assembly stations (validation, transformation)
- **Operations** = Shipping docks (outbound HL7, file writes)
- **Connections** = Conveyor belts moving messages
- **Status** = Green light (running), Red light (stopped), Flashing red (error)

**Visual Metaphor:**
```
┌─────────────────────────────────────────────────────────────────┐
│  INBOUND ZONE     │    PROCESSING ZONE   │   OUTBOUND ZONE      │
│  (Services)       │    (Processes)       │   (Operations)       │
│                   │                      │                      │
│  🟢 HL7 Receiver  ─────→ 🟦 Validator ─────→ 🟣 HL7 Sender     │
│                   │                      │                      │
│  🟢 File Watcher  ─────→ 🟦 Router    ─────→ 🟣 File Writer    │
│                   │                      │                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Visual Design System

### 3.1 Node Design Specifications

#### Service Node (Inbound)

```
┌─────────────────────────────────────┐
│ ⬇  HL7.Receiver.PAS         ● Running│  ← Header (Green bg #e8f5e9)
├─────────────────────────────────────┤
│ HL7 TCP Service                      │  ← Type (12px gray)
│ Port: 2575  IP: 0.0.0.0              │  ← Key Settings (10px gray)
│ 📊 1.2K msg/h  ⚡ 45ms avg           │  ← Metrics (10px blue)
└─────────────────────────────────────┘
   ↓ (connection handle)

Style:
- Width: 220px (fixed)
- Height: Auto (min 100px)
- Border: 2px solid #007f3b (green)
- Border-radius: 8px
- Background: #f0f9f5 (green-50)
- Shadow: 0 2px 4px rgba(0,0,0,0.1)
- Hover: Shadow 0 4px 8px, border brightens
- Selected: Ring 2px #005eb8, shadow 0 6px 12px
```

#### Process Node (Transform)

```
      ╭─────────────────────╮
     ╱  🔀 NHS.Validator    ╲         ← Diamond shape (visual distinction)
    ╱    ● Running           ╲
   ╱                          ╲
  │  NHS Validation Process   │       ← Type
  │  ValidateNHSNumber: true  │       ← Key Setting
  │  📊 1.2K msg/h  ⚡ 120ms   │       ← Metrics
   ╲                          ╱
    ╲                        ╱
     ╰─────────────────────╯
        ↓ (connection handle)

Style:
- Width: 220px
- Shape: Rounded diamond (border-radius on corners)
- Border: 2px solid #005eb8 (blue)
- Background: #e8f4f8 (blue-50)
- Icon: Transform/GitBranch icon (16px)
- Same shadow/hover/selected as Service
```

#### Operation Node (Outbound)

```
┌─────────────────────────────────────┐
│ HL7.Sender.RIS              ⬆  ● Running│  ← Header (Purple bg #f3e5ff)
├─────────────────────────────────────┤
│ HL7 TCP Operation                    │  ← Type
│ → ris.nhs.uk:2576                    │  ← Target (bold)
│ 📊 1.1K msg/h  ⚡ 230ms              │  ← Metrics
└─────────────────────────────────────┘

Style:
- Width: 220px
- Border: 2px solid #330072 (purple)
- Background: #f3e5ff (purple-50)
- Icon: ArrowUpFromLine (outbound indicator)
- Target URL in bold (most important info for operations)
```

#### Status Indicators

```
● Running      - Green dot (12px, #00c853, pulsing animation)
○ Stopped      - Gray outline circle (12px, #9e9e9e)
⚠ Error        - Red warning triangle (14px, #da291c, shake animation)
⏸ Paused      - Yellow pause icon (12px, #ffb81c)
🔄 Restarting  - Blue spinner (12px, rotating)
```

### 3.2 Connection Design Specifications

**Standard Connection:**
```
[Service] ──────────────────→ [Process]
          ───────────────────
Style:
- Color: #005eb8 (NHS Blue)
- Width: 2px
- Type: Solid
- Arrow: Filled triangle (10px)
- Animation: Subtle flow (3s, optional)
- Hover: Width 3px, arrow scales 1.2x
```

**Error Connection:**
```
[Process] ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌→ [ErrorHandler]
          ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
            [ERROR]       ← Red label
Style:
- Color: #da291c (NHS Red)
- Width: 2px
- Type: Dashed (6px dash, 4px gap)
- Label: Red badge "ERROR" (10px)
- Arrow: Red filled triangle
- Animation: None (errors are static)
```

**Async Connection:**
```
[Service] ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄→ [Queue]
          ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
           [ASYNC]      ← Yellow label
Style:
- Color: #ffb81c (NHS Yellow)
- Width: 2px
- Type: Dotted (2px dot, 3px gap)
- Label: Yellow badge "ASYNC" (10px)
- Arrow: Yellow filled triangle
```

**Routing Rule Label (optional overlay):**
```
            ┌───────────────────┐
[Router] ───┤ ADT → RIS         │──→ [RIS.Sender]
            │ Priority: 1       │
            │ MSH.9 = "ADT"     │
            └───────────────────┘
Style:
- Background: White, 90% opacity
- Border: 1px solid #ccc
- Padding: 8px
- Font: 10px monospace
- Position: Centered on edge
- Show on: Edge hover or "Show Routing Rules" checkbox
```

### 3.3 Color Palette Usage Matrix

| UI Element | Primary Color | Hover | Active/Selected | Error |
|------------|---------------|-------|-----------------|-------|
| Service Node | Green-50 bg, Green border | Green-100 bg | Blue ring | Red border flash |
| Process Node | Blue-50 bg, Blue border | Blue-100 bg | Blue ring | Red border flash |
| Operation Node | Purple-50 bg, Purple border | Purple-100 bg | Blue ring | Red border flash |
| Button Primary | Blue-600 | Blue-700 | Blue-800 | N/A |
| Button Secondary | White, Blue-600 text | Blue-50 bg | Blue-100 bg | N/A |
| Button Danger | Red-50, Red-600 text | Red-100 | Red-200 | N/A |
| Status Running | Green-500 | N/A | N/A | N/A |
| Status Error | Red-500 | N/A | N/A | N/A |
| Connection Standard | Blue-600 | Blue-700 (thicker) | N/A | N/A |
| Connection Error | Red-600 | Red-700 | N/A | N/A |

---

## 4. Layout Specifications

### 4.1 Desktop Layout (1920x1080)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ [☰] OpenLI HIE        ws1: NHS Trust          [User Menu] [Theme] [Help]    [×][□][−]│ 40px
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Home > Workspaces > NHS Trust > Projects > ADT Integration                          │ 32px
│                                                                                      │
│ ◀ Back to Projects                                                                  │
│                                                                                      │
│ ADT Integration Production            [●Running] [Deploy ▼] [Stop]                 │ 80px
│ ─────────────────────────────────────────────────────────────────────────────────── │
│                                                                                      │
│ [Items (8)] [Connections (12)] [Routing (3)] [★ Topology] [Settings]               │ 48px
│ ─────────────────────────────────────────────────────────────────────────────────── │
│                                                                                      │
│ ┌─ Toolbar ──────────────────────────────────────────────────────────────────────┐ │
│ │ View: [Graph]● [Table]  | ⊕ ⊖ ◎ | 🔍 Search | Show: ☑Status ☑Metrics ☑Labels │ │ 60px
│ └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│ ┌────────────────────────────────────────────────────────┬─────────────────────────┐│
│ │                                                        │ [Node Name]       [×]   ││
│ │                                                        ├─────────────────────────┤│
│ │                                                        │ [Config][Events][Msgs]  ││
│ │                                                        │ [Metrics]               ││
│ │                                                        ├─────────────────────────┤│
│ │                                                        │                         ││
│ │         Topology Canvas                               │   Detail Panel Content  ││
│ │         (Adaptive, zoom/pan)                          │   (Scrollable)          ││
│ │                                                        │                         ││ 800px
│ │  ┌───────┐     ┌───────┐     ┌───────┐               │                         ││
│ │  │Service│────▶│Process│────▶│  Oper │               │                         ││
│ │  └───────┘     └───────┘     └───────┘               │                         ││
│ │                                                        │                         ││
│ │  [Legend]                                             │                         ││
│ │  [Mini-map]                                           │                         ││
│ │                                                        │                         ││
│ └────────────────────────────────────────────────────────┴─────────────────────────┘│
│ ● Live | Last updated: 2s ago | 8 items (7 running, 1 stopped)                     │ 32px
└─────────────────────────────────────────────────────────────────────────────────────┘

Layout Measurements:
- Canvas Width: calc(100vw - 400px - 32px) // viewport - detail panel - margins
- Canvas Height: calc(100vh - 260px) // viewport - header - toolbar - status
- Detail Panel: 400px fixed width, full height, right-aligned
- Detail Panel Resizable: Yes (300px - 600px range)
- Mini-map: 150px × 100px, bottom-right, 16px margin
- Legend: 400px × 80px, bottom-left, 16px margin
```

### 4.2 Laptop Layout (1366x768)

```
Same as desktop BUT:
- Detail Panel: Collapsible (hamburger icon to hide/show)
- When collapsed: Canvas expands to full width
- When expanded: Panel overlays canvas (not side-by-side)
- Mini-map: Hidden (too small)
- Legend: Compact (300px × 60px)
```

### 4.3 Tablet Layout (1024x768)

```
Same as laptop BUT:
- Detail Panel: Always modal overlay (not side panel)
- Opens centered (600px × 80vh)
- Backdrop: Semi-transparent black (60% opacity)
- Close: Click backdrop or X button
- Toolbar: Single row, compact icons
```

---

## 5. Component Wireframes

### 5.1 Topology Toolbar

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│  View Mode:  [Graph]●  [Table]       Zoom: [⊕] [⊖] [◎ Fit]       🔍 [Search___]│
│                                                                                  │
│  Display:  ☑ Status Indicators  ☑ Throughput Metrics  ☑ Connection Labels      │
│            ☐ Routing Rules  ☐ Error Paths Only                                  │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

Components:
1. View Mode Segmented Control
   - Width: 200px
   - Height: 36px
   - Active: Blue bg, white text
   - Inactive: White bg, blue text

2. Zoom Button Group
   - Icon buttons (32px square each)
   - Tooltips: "Zoom In (Ctrl++)", "Zoom Out (Ctrl+-)", "Fit View (Ctrl+0)"
   - Disabled state: Gray, 50% opacity

3. Search Input
   - Width: 250px
   - Height: 36px
   - Placeholder: "Search items, settings..."
   - Icon: Magnifying glass (left)
   - Clear button (right, appears when text entered)
   - Keyboard: Focus on Ctrl+F

4. Display Options Checkboxes
   - Grouped in fieldset
   - Inline layout
   - Toggle immediately updates canvas
```

### 5.2 Detail Panel - Configuration Tab

```
┌──────────────────────────────────────────────────────┐
│ HL7.Receiver.PAS                              [×]    │ ← Header (sticky)
├──────────────────────────────────────────────────────┤
│ [Configuration]● [Events] [Messages] [Metrics]       │ ← Tab Bar
├──────────────────────────────────────────────────────┤
│                                                      │
│ General Settings                                     │ ← Section Header
│ ┌────────────────────────────────────────────────┐   │
│ │ Name:         HL7.Receiver.PAS                 │   │
│ │ Type:         Service                          │   │
│ │ Class:        li.hosts.hl7.HL7TCPService       │   │
│ │ Pool Size:    5                                │   │
│ │ Enabled:      Yes                              │   │
│ │ Status:       ● Running                        │   │
│ └────────────────────────────────────────────────┘   │
│                                                      │
│ Adapter Settings                                     │
│ ┌────────────────────────────────────────────────┐   │
│ │ Port:             2575                         │   │
│ │ IP Address:       0.0.0.0                      │   │
│ │ Schema:           HL7 2.3                      │   │
│ │ Ack Mode:         Application                  │   │
│ │ Stay Connected:   60                           │   │
│ └────────────────────────────────────────────────┘   │
│                                                      │
│ Host Settings                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ Target:           NHS.Validator               │   │
│ │ Validation:       Strict                       │   │
│ │ Archive:          Enabled                      │   │
│ └────────────────────────────────────────────────┘   │
│                                                      │
│ [Edit Configuration] [Test Connection] [Reload]      │ ← Actions
│                                                      │
└──────────────────────────────────────────────────────┘

Style:
- Panel Width: 400px
- Padding: 16px
- Section Headers: 14px bold, 24px margin-top
- Setting Boxes: Gray-50 bg, 12px padding, 8px rounded
- Label: 12px gray-600, right-aligned (80px width)
- Value: 12px gray-900, left-aligned, truncate with ellipsis
- Actions: Button group, 100% width, 8px gap
```

### 5.3 Detail Panel - Events Tab

```
┌──────────────────────────────────────────────────────┐
│ HL7.Receiver.PAS                              [×]    │
├──────────────────────────────────────────────────────┤
│ [Configuration] [Events]● [Messages] [Metrics]       │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Filter: [All Levels ▼] [Last 1 Hour ▼]  [Refresh]  │ ← Toolbar
│                                                      │
│ ┌────────────────────────────────────────────────┐   │
│ │ 15:45:23  INFO   Connection received          │   │ ← Log Entry
│ │ 15:45:22  DEBUG  Message parsed (ADT^A01)     │   │
│ │ 15:45:21  INFO   Sent to NHS.Validator        │   │
│ │ 15:45:20  DEBUG  ACK received                 │   │
│ │ 15:45:19  WARN   Retry attempt 2 of 3         │   │ ← Warning (yellow)
│ │ 15:45:18  ERROR  Connection timeout           │   │ ← Error (red)
│ │ 15:45:17  INFO   Reconnecting...              │   │
│ │ 15:45:16  DEBUG  Socket closed                │   │
│ │ ...                                            │   │
│ └────────────────────────────────────────────────┘   │
│                                                      │
│ [Load More (100 older)] [Export Logs] [Clear]       │ ← Footer Actions
│                                                      │
└──────────────────────────────────────────────────────┘

Log Entry Style:
- Font: 11px monospace "Courier New"
- Background: Zebra striping (gray-50 / white)
- Padding: 4px 8px
- Hover: Gray-100 bg
- Colors:
  - ERROR: Red-700 text, Red-50 bg
  - WARN: Yellow-700 text, Yellow-50 bg
  - INFO: Blue-700 text, White bg
  - DEBUG: Gray-600 text, White bg
- Timestamp: Gray-500 (60px width)
- Level: Bold, colored (50px width)
- Message: Gray-900, wrap-anywhere
```

### 5.4 Detail Panel - Messages Tab

```
┌──────────────────────────────────────────────────────┐
│ HL7.Receiver.PAS                              [×]    │
├──────────────────────────────────────────────────────┤
│ [Configuration] [Events] [Messages]● [Metrics]       │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Recent Messages (Last 50)                            │
│ Filter: [All Status ▼] [Today ▼]                    │
│                                                      │
│ ┌────────────────────────────────────────────────┐   │
│ │┌──────────────────────────────────────────────┐│  │
│ ││ 15:45:23  ADT^A01  ✓ Success  Inbound       ││  │ ← Message Row
│ ││ Session: abc-123  Latency: 45ms             ││  │
│ │└──────────────────────────────────────────────┘│  │
│ │┌──────────────────────────────────────────────┐│  │
│ ││ 15:44:30  ORU^R01  ✗ Error    Inbound       ││  │
│ ││ Session: def-456  Validation failed         ││  │ ← Error (red border)
│ │└──────────────────────────────────────────────┘│  │
│ │┌──────────────────────────────────────────────┐│  │
│ ││ 15:43:15  ADT^A08  ✓ Success  Inbound       ││  │
│ ││ Session: ghi-789  Latency: 52ms             ││  │
│ │└──────────────────────────────────────────────┘│  │
│ │ ...                                            │   │
│ └────────────────────────────────────────────────┘   │
│                                                      │
│ [Load More] [Export CSV]                             │
│                                                      │
└──────────────────────────────────────────────────────┘

Message Row Style:
- Height: 56px (two lines)
- Border: 1px solid gray-200
- Border-radius: 6px
- Padding: 8px 12px
- Margin: 4px 0
- Cursor: pointer
- Hover: Shadow, blue border
- Click: Opens Message Trace Swimlane modal

Success Row:
- Left border: 4px solid green-500

Error Row:
- Left border: 4px solid red-500
- Background: Red-50
```

### 5.5 Table View Layout

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ HL7 Production Items (8)                                                           │
│ ─────────────────────────────────────────────────────────────────────────────────  │
│                                                                                    │
│ Filter: [All Types ▼] [All Status ▼]  Search: [________]  [Export CSV]           │
│                                                                                    │
│ ┌────────────────────────────────────────────────────────────────────────────────┐│
│ │ Name ▲        │ Type      │ Status    │ Pool │ Metrics       │ Actions       ││
│ ├────────────────────────────────────────────────────────────────────────────────┤│
│ │ HL7.Recv.PAS  │ Service   │ ● Running │  5   │ 1.2K msg/h   │ [View] [Test] ││
│ │ NHS.Validator │ Process   │ ● Running │  4   │ 1.2K msg/h   │ [View] [Edit] ││
│ │ HL7.Send.RIS  │ Operation │ ● Running │  2   │ 1.1K msg/h   │ [View] [Test] ││
│ │ File.Archive  │ Operation │ ○ Stopped │  1   │ 0 msg/h      │ [View] [Start]││ ← Stopped
│ │ ADT.Router    │ Process   │ ⚠ Error   │  2   │ 5 errors/h   │ [View] [Fix]  ││ ← Error
│ │ ...           │           │           │      │              │               ││
│ └────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                    │
│ Showing 1-10 of 8  [< Previous] [Next >]                                          │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘

Table Style:
- Font: 12px
- Row Height: 48px
- Header: Gray-100 bg, bold, sticky
- Rows: Zebra striping (white / gray-50)
- Hover: Gray-100 bg, cursor pointer
- Sort: Click column header, arrow indicator
- Status column: Colored dot + text
- Actions: Icon buttons (View, Edit, Test, etc.)
```

---

## 6. Interaction Patterns

### 6.1 Node Interactions

**Single Click:**
- **Action:** Select node, open detail panel (right side)
- **Visual Feedback:** Blue ring around node, detail panel slides in (300ms ease-out)
- **Keyboard Equivalent:** Tab to node, Enter to select

**Double Click:**
- **Action:** Open full configuration page (navigate to Items tab)
- **Visual Feedback:** Fade out topology, fade in Items tab (400ms)
- **Use Case:** Quick access to full edit mode

**Right Click (Context Menu):**
```
┌────────────────────────┐
│ HL7.Receiver.PAS       │
├────────────────────────┤
│ ⚙ Configure            │
│ 🔄 Reload               │
│ ▶ Start                 │  (if stopped)
│ ⏸ Stop                  │  (if running)
│ 🧪 Test Message         │
│ 📋 Copy Config          │
│ ───────────────         │
│ 🗑 Delete               │  (red text)
└────────────────────────┘
```

**Hover:**
- **Action:** Show tooltip with metrics
- **Delay:** 500ms hover delay
- **Tooltip Content:**
  - Name
  - Status
  - Messages/hour (last 1h)
  - Avg latency
  - Last error (if any)
- **Position:** Below node, arrow pointing up

**Drag (Graph View only):**
- **Action:** Reposition node, update position in database
- **Visual Feedback:** Node follows cursor, semi-transparent, drop shadow
- **Snap:** Snap to grid (optional, 20px grid)
- **Save:** On drag end, call updateItem API with new position

### 6.2 Connection Interactions

**Hover:**
- **Action:** Highlight connection and connected nodes
- **Visual Feedback:**
  - Connection: Width increases 2px → 4px, color brightens
  - Source node: Blue glow
  - Target node: Blue glow
- **Tooltip:** "Connection from [Source] to [Target]"

**Click:**
- **Action:** Show routing rule details (if any)
- **Modal:** Small popover showing:
  - Connection type
  - Routing rules applied
  - Message count (last 1h)
  - Edit button (navigates to Routing tab)

### 6.3 Zoom/Pan Interactions

**Mouse Scroll:**
- **Action:** Zoom in/out (10% per scroll tick)
- **Center:** Zoom toward mouse cursor position
- **Limits:** Min 25%, Max 400%

**Pinch (Touchpad/Touch):**
- **Action:** Zoom in/out
- **Two-finger drag:** Pan canvas

**Keyboard:**
- **Ctrl + Plus:** Zoom in 25%
- **Ctrl + Minus:** Zoom out 25%
- **Ctrl + 0:** Fit view (reset zoom, center all nodes)
- **Arrow Keys:** Pan 50px in direction

**Fit View Button:**
- **Action:** Auto-fit all nodes in viewport
- **Animation:** Smooth zoom/pan (500ms ease-in-out)
- **Padding:** 50px margin around nodes

### 6.4 Search Interactions

**Open Search:**
- **Trigger:** Ctrl+F or click search box
- **Focus:** Search input, clear existing text
- **Highlight:** Search box border blue

**Type Query:**
- **Live Search:** Filter as you type (debounce 300ms)
- **Match:** Item name, class name, settings (partial, case-insensitive)
- **Visual Feedback:**
  - Matching nodes: Blue highlight
  - Non-matching nodes: 30% opacity
  - Match count: "3 matches" below search box

**Navigate Results:**
- **Enter:** Jump to next match (cycle through)
- **Shift+Enter:** Jump to previous match
- **Escape:** Clear search, restore full visibility

**Close Search:**
- **Trigger:** Escape or click X button
- **Action:** Clear filter, restore full visibility
- **Animation:** Fade opacity back to 100% (300ms)

### 6.5 Detail Panel Interactions

**Open:**
- **Trigger:** Click node
- **Animation:** Slide in from right (300ms ease-out)
- **Canvas:** Shrinks to accommodate panel (animated resize)

**Resize:**
- **Drag:** Left edge of panel (vertical resize handle)
- **Range:** 300px - 600px
- **Persist:** Save width to localStorage

**Switch Tabs:**
- **Trigger:** Click tab label
- **Animation:** Fade out old content (150ms), fade in new (150ms)
- **Keyboard:** Tab cycles through tabs, Enter selects

**Close:**
- **Trigger:** X button, Escape key, or click canvas (optional)
- **Animation:** Slide out to right (300ms ease-in)
- **Canvas:** Expands to full width (animated resize)

---

## 7. Responsive Behavior

### 7.1 Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| **Desktop** | ≥ 1920px | Full layout, detail panel side-by-side |
| **Laptop** | 1366px - 1919px | Detail panel collapsible |
| **Tablet** | 1024px - 1365px | Detail panel as modal overlay |
| **Mobile** | < 1024px | Table view only, no graph |

### 7.2 Detail Panel Responsive Behavior

**Desktop (≥ 1920px):**
- Panel: 400px fixed width, always visible (can close)
- Canvas: Full width - 400px - margins
- Mini-map: Visible (150x100px)

**Laptop (1366px - 1919px):**
- Panel: 400px, collapsible via hamburger icon
- Canvas: Adaptive (full width when panel closed)
- Mini-map: Hidden (too small)
- Transition: Smooth width animation (300ms)

**Tablet (1024px - 1365px):**
- Panel: Modal overlay, 600px width, 80vh height
- Canvas: Always full width
- Panel opens: Backdrop (black, 60% opacity), panel centered
- Swipe down: Close panel (touch gesture)

**Mobile (< 1024px):**
- Topology: Not available (too complex for small screens)
- Default View: Table only
- Warning: "Topology view requires larger screen (≥1024px)"

### 7.3 Font Scaling

**Desktop:**
- Base font: 14px
- Headings: 16px (h3), 14px (h4), 12px (h5)
- Mono: 12px

**Laptop:**
- Base font: 13px
- Headings: 15px (h3), 13px (h4), 11px (h5)
- Mono: 11px

**Tablet:**
- Base font: 14px (same as desktop, larger touch targets compensate)
- Headings: 16px, 14px, 12px
- Mono: 12px

---

## 8. Accessibility Guidelines

### 8.1 WCAG 2.1 Level AA Compliance

**Color Contrast:**
- Text on white: Minimum 4.5:1 (7:1 preferred)
- NHS Blue (#005eb8) on white: 7.1:1 ✓
- NHS Green (#007f3b) on white: 5.2:1 ✓
- NHS Purple (#330072) on white: 10.4:1 ✓
- NHS Red (#da291c) on white: 4.8:1 ✓
- Status indicators: Not relying solely on color (+ icon/text)

**Keyboard Navigation:**
- All interactive elements: Tab-accessible
- Focus indicators: 2px blue outline, 2px offset
- Logical tab order: Top → Bottom, Left → Right
- Skip links: "Skip to topology canvas"

**Screen Reader:**
- Node labels: `<div role="listitem" aria-label="HL7 Receiver PAS, Service, Running, 1200 messages per hour">`
- Status updates: `<div aria-live="polite">` for status changes
- Buttons: Descriptive labels (not just icons)
- Links: Unique labels (not "Click here")

**Focus Management:**
- Modal opens: Focus first focusable element
- Modal closes: Return focus to trigger
- Search opens: Focus search input
- Detail panel opens: Focus first tab

### 8.2 Keyboard Shortcuts Summary

| Shortcut | Action | Context |
|----------|--------|---------|
| **Ctrl+F** | Open search | Global |
| **Escape** | Close search/panel/modal | Global |
| **Tab** | Navigate nodes | Canvas focus |
| **Enter** | Select node | Node focus |
| **Arrow Keys** | Pan canvas | Canvas focus |
| **Ctrl + Plus** | Zoom in | Canvas focus |
| **Ctrl + Minus** | Zoom out | Canvas focus |
| **Ctrl + 0** | Fit view | Canvas focus |
| **G** | Switch to Graph view | Toolbar focus |
| **T** | Switch to Table view | Toolbar focus |
| **Ctrl + /** | Show shortcuts help | Global |

### 8.3 Error States and Feedback

**Loading State:**
```
┌──────────────────────────────────────┐
│                                      │
│         ⏳ Loading Topology...       │
│                                      │
│    [Spinner animation]               │
│                                      │
│    Fetching items and connections    │
│                                      │
└──────────────────────────────────────┘
```

**Empty State:**
```
┌──────────────────────────────────────┐
│                                      │
│    📊 No Items Configured Yet        │
│                                      │
│    This production has no items.     │
│    Add services, processes, and      │
│    operations to see the topology.   │
│                                      │
│    [+ Add Item]                      │
│                                      │
└──────────────────────────────────────┘
```

**Error State:**
```
┌──────────────────────────────────────┐
│                                      │
│    ⚠ Failed to Load Topology         │
│                                      │
│    Could not fetch project data.     │
│    Please try again.                 │
│                                      │
│    Error: Connection timeout         │
│                                      │
│    [Retry] [View Error Details]      │
│                                      │
└──────────────────────────────────────┘
```

---

## 9. Animation and Motion

### 9.1 Animation Principles

**Performance-First:**
- Only animate: transform, opacity (GPU-accelerated)
- Never animate: width, height, top, left (CPU-bound, laggy)
- Use will-change for complex animations

**Purposeful Motion:**
- Guide attention (slide-in panels indicate new content)
- Provide feedback (button press: scale 0.95)
- Maintain context (zoom origin from cursor position)

**Respect User Preferences:**
- Detect: `prefers-reduced-motion: reduce`
- Fallback: Instant transitions (0ms duration)

### 9.2 Animation Catalog

| Element | Animation | Duration | Easing |
|---------|-----------|----------|--------|
| **Detail Panel Open** | Slide in from right | 300ms | ease-out |
| **Detail Panel Close** | Slide out to right | 300ms | ease-in |
| **Tab Switch** | Fade out/in | 150ms | linear |
| **Node Select** | Ring scale 0→1 | 200ms | ease-out |
| **Button Hover** | Background color | 150ms | ease |
| **Button Active** | Scale 0.95 | 100ms | ease |
| **Zoom** | Transform origin cursor | 400ms | ease-in-out |
| **Fit View** | Zoom + pan | 500ms | ease-in-out |
| **Status Change** | Flash border | 300ms | ease (3 pulses) |
| **Loading Spinner** | Rotate 360° | 1s | linear (infinite) |
| **Toast Notification** | Slide in from top | 250ms | ease-out |

### 9.3 CSS Animation Examples

```css
/* Detail Panel Slide In */
.detail-panel-enter {
  transform: translateX(100%);
  opacity: 0;
}
.detail-panel-enter-active {
  transform: translateX(0);
  opacity: 1;
  transition: transform 300ms ease-out, opacity 300ms ease-out;
}

/* Node Selection Ring */
.node-selected {
  box-shadow: 0 0 0 2px #005eb8;
  animation: node-ring-pulse 200ms ease-out;
}
@keyframes node-ring-pulse {
  0% { box-shadow: 0 0 0 0 #005eb8; }
  100% { box-shadow: 0 0 0 2px #005eb8; }
}

/* Status Error Flash */
.node-error {
  animation: node-error-flash 300ms ease 3;
}
@keyframes node-error-flash {
  0%, 100% { border-color: #da291c; }
  50% { border-color: #ff6b6b; }
}

/* Reduced Motion Fallback */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 10. Future Enhancements (Post-v1.8.0)

**Phase 2 Enhancements:**
- Drag-and-drop repositioning with auto-save
- Live message flow animation (pulsing dots along connections)
- Thumbnail preview on hover (mini-screenshot of item)
- Export topology as PNG/SVG

**Phase 3 Enhancements:**
- Topology comparison (diff between versions)
- Test mode (simulate message without sending)
- Predictive alerts (ML-based bottleneck detection)
- Collaborative annotations (comments on nodes/connections)

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2026-02-12 | System | Enterprise-grade UI/UX design |

**Design Review Checklist**

- [ ] Meets NHS Digital design standards
- [ ] Passes WCAG 2.1 Level AA
- [ ] Reviewed by Integration Engineers
- [ ] Reviewed by UX Team
- [ ] Prototyped in Figma
- [ ] User testing completed (5+ participants)
- [ ] Accessibility audit passed
- [ ] Performance benchmarked (< 2s load)
