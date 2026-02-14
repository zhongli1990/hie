# Enterprise Production Topology Viewer - Requirements Specification

**Version:** 2.0.0
**Last Updated:** February 12, 2026
**Status:** Requirements Approved
**Target Release:** v1.8.0
**Classification:** Mission-Critical Healthcare System

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Stakeholders](#2-stakeholders)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [User Requirements](#5-user-requirements)
6. [System Requirements](#6-system-requirements)
7. [Compliance Requirements](#7-compliance-requirements)
8. [Acceptance Criteria](#8-acceptance-criteria)

---

## 1. Executive Summary

### 1.1 Purpose

Create an **enterprise-grade production topology viewer** for OpenLI HIE that enables hospital system administrators, integration engineers, and clinical staff to:

- Visualize message flow through integration engine productions
- Monitor real-time system health and message throughput
- Trace individual message transactions end-to-end
- Diagnose integration failures and bottlenecks
- Ensure compliance with NHS Digital standards
- Maintain 24/7 operational awareness of mission-critical healthcare integrations

### 1.2 Context

**Critical Hospital Systems Dependency:**
- Emergency Department ADT feeds (patient admissions/discharges)
- Laboratory result reporting to EPR systems
- Radiology orders and DICOM routing
- Pharmacy dispense notifications
- Vital signs monitoring integrations
- A&E triage system interfaces

**Downtime Impact:**
- Patient safety risks from delayed lab results
- Missed clinical alerts
- Duplicate medication errors
- Regulatory non-compliance (NHS Digital, CQC)
- Financial penalties for missed performance targets

**User Profile:**
- **Integration Engineers:** 60% - Build and maintain routes
- **System Administrators:** 25% - Monitor health and troubleshoot
- **Clinical Analysts:** 10% - Investigate data quality issues
- **NHS Digital Auditors:** 5% - Compliance verification

### 1.3 Success Criteria

| Criterion | Target | Critical Success Factor |
|-----------|--------|------------------------|
| **Time to Diagnose Issue** | < 2 minutes | From alert to root cause identification |
| **System Uptime Visibility** | 99.9% | Real-time status accuracy |
| **User Training Time** | < 30 minutes | Intuitive UI requires minimal training |
| **Message Trace Time** | < 5 seconds | End-to-end transaction visualization |
| **Concurrent Users** | 50+ | Multiple users viewing simultaneously |
| **Large Production Support** | 100+ items | No performance degradation |

---

## 2. Stakeholders

### 2.1 Primary Stakeholders

**1. Integration Engineers (Priority 1)**
- Need: Quickly build, configure, and troubleshoot HL7/FHIR routes
- Pain Points: Manually tracing messages through logs, unclear connection topology
- Success Metric: 50% reduction in troubleshooting time

**2. System Administrators (Priority 1)**
- Need: 24/7 monitoring, rapid incident response, capacity planning
- Pain Points: Lack of real-time visibility, manual log aggregation
- Success Metric: < 2 minute MTTD (Mean Time To Detect)

**3. Clinical Analysts (Priority 2)**
- Need: Investigate data quality issues, validate transformations
- Pain Points: Cannot see message content transformations, no audit trail
- Success Metric: 100% message traceability

**4. NHS Digital Auditors (Priority 2)**
- Need: Verify compliance with DCB standards, audit message flows
- Pain Points: Manual evidence collection, incomplete audit trails
- Success Metric: Automated compliance reporting

### 2.2 Secondary Stakeholders

- **Hospital CIOs:** ROI justification, strategic planning
- **Vendor Support Teams:** Remote troubleshooting capability
- **Regulatory Bodies:** CQC inspections, NHS Digital assessments

---

## 3. Functional Requirements

### 3.1 Production Topology Visualization

**FR-TOP-001: Adaptive Graph Topology View** ⭐ CRITICAL
- **Description:** Display production items (services, processes, operations) as nodes in an adaptive graph layout
- **Acceptance Criteria:**
  - Graph automatically adjusts to viewport size
  - Minimum 3-column layout (Services → Processes → Operations)
  - Nodes show: name, type, status, key settings, throughput metrics
  - Connections show: direction, type (standard/error/async), routing conditions
  - Color-coded by NHS palette (green=service, blue=process, purple=operation)
  - Status indicators: ● Running (green), ○ Stopped (gray), ⚠ Error (red)
- **Priority:** P0 (Must Have)
- **Dependencies:** ReactFlow library, ProjectDetail API
- **User Story:** "As an integration engineer, I need to see all items and connections at a glance so I can understand message flow topology"

**FR-TOP-002: Tabular List View** ⭐ CRITICAL
- **Description:** Alternative tabular view showing all items in sortable/filterable table
- **Acceptance Criteria:**
  - Columns: Name, Type, Status, Class, Pool Size, Metrics, Actions
  - Sortable by any column
  - Filterable by type, status, name
  - Export to CSV capability
  - Pagination for 100+ items
- **Priority:** P0 (Must Have)
- **Dependencies:** None
- **User Story:** "As a system administrator, I need a table view to quickly scan item statuses and sort by error count"

**FR-TOP-003: View Mode Switching**
- **Description:** Seamless switching between Graph and Tabular views
- **Acceptance Criteria:**
  - Toggle between views without data reload
  - View preference persisted per user
  - Keyboard shortcut: G (graph), T (table)
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-TOP-001, FR-TOP-002

**FR-TOP-004: Zoom and Pan Controls**
- **Description:** Intuitive navigation controls for graph view
- **Acceptance Criteria:**
  - Mouse scroll wheel zoom (10% increments)
  - Click-drag pan
  - Zoom In/Out/Fit buttons
  - Mini-map navigator for large productions
  - Keyboard shortcuts: +/- zoom, arrows pan
- **Priority:** P0 (Must Have)
- **Dependencies:** ReactFlow

**FR-TOP-005: Node Click Actions**
- **Description:** Interactive node selection and navigation
- **Acceptance Criteria:**
  - Click node → Opens detail panel (right side)
  - Double-click node → Opens full configuration page
  - Right-click node → Context menu (Test, Reload, Edit, Delete)
  - Hover node → Tooltip with metrics
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-TOP-001, FR-RHP-001

**FR-TOP-006: Connection Highlighting**
- **Description:** Visual feedback for connection paths
- **Acceptance Criteria:**
  - Hover connection → Highlights source and target nodes
  - Click connection → Shows routing rule details
  - Animated flow indicators during message transmission (optional)
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-TOP-001

**FR-TOP-007: Search and Filter**
- **Description:** Quickly locate items in complex productions
- **Acceptance Criteria:**
  - Global search box (Ctrl+F)
  - Search by: item name, class name, settings
  - Filter by: type, status, enabled/disabled
  - Highlight matching nodes in graph
  - Jump to first match
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-TOP-001

### 3.2 Right-Side Detail Panel

**FR-RHP-001: Detail Panel Framework** ⭐ CRITICAL
- **Description:** Sliding panel from right showing selected item details
- **Acceptance Criteria:**
  - Opens when node clicked (400px width)
  - Closes on X button, Escape key, or click outside
  - Resizable (300-600px range)
  - Position persisted across sessions
  - Contains 4 tabs: Configuration, Events, Messages, Metrics
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-TOP-005
- **User Story:** "As an integration engineer, I need immediate access to item configuration without leaving the topology view"

**FR-RHP-002: Configuration Tab**
- **Description:** Read-only view of item configuration
- **Acceptance Criteria:**
  - Displays: adapter settings, host settings, pool size, enabled status
  - Syntax highlighting for complex settings
  - Copy to clipboard button
  - Link to edit configuration page
  - Show effective vs. overridden settings
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-RHP-001

**FR-RHP-003: Events/Logs Tab** ⭐ CRITICAL
- **Description:** Live event log for selected item
- **Acceptance Criteria:**
  - Last 100 events (auto-scrolling)
  - Timestamp, log level, message
  - Color-coded by severity (ERROR=red, WARN=yellow, INFO=blue, DEBUG=gray)
  - Filter by log level
  - Search within logs
  - Export logs (CSV, JSON)
  - Auto-refresh every 5 seconds
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-RHP-001, Event Logging API
- **User Story:** "As a system administrator, I need to see real-time errors without SSH-ing to the server"

**FR-RHP-004: Messages Tab** ⭐ CRITICAL
- **Description:** Message log showing recent messages processed by item
- **Acceptance Criteria:**
  - Last 50 messages (paginated)
  - Columns: Timestamp, Session ID, Message Type, Status, Direction
  - Click message → Opens message trace swimlane (FR-MST-001)
  - Filter by: status, message type, date range
  - Export message list
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-RHP-001, Message Logging API, FR-MST-001
- **User Story:** "As a clinical analyst, I need to inspect individual messages to validate data transformations"

**FR-RHP-005: Metrics Tab**
- **Description:** Real-time and historical metrics for selected item
- **Acceptance Criteria:**
  - Current metrics: messages received, sent, errors, avg latency
  - Historical charts: throughput (hourly, daily, weekly)
  - Comparison: current vs. previous period
  - Threshold alerts visualization
  - Export metrics data (CSV)
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-RHP-001, Metrics API

### 3.3 Message Trace Swimlanes

**FR-MST-001: E2E Transaction Swimlane Diagram** ⭐ CRITICAL
- **Description:** Visualize complete message journey from ingestion to delivery
- **Acceptance Criteria:**
  - Horizontal swimlane diagram with time axis
  - One lane per item (service, process, operation)
  - Message flow shown as arrows between lanes
  - Timestamps at each stage
  - Color-coded by status (success=green, error=red, pending=yellow)
  - Total transaction time displayed
  - Drill-down to message content at each stage
  - Show transformations applied
- **Priority:** P0 (Must Have)
- **Dependencies:** Message Tracing API, Session Management
- **User Story:** "As an integration engineer, I need to trace a failed message through every item to identify where transformation failed"

**FR-MST-002: Message Content Viewer**
- **Description:** Display raw and transformed message content
- **Acceptance Criteria:**
  - Side-by-side comparison: input vs. output
  - Syntax highlighting (HL7, FHIR JSON, XML)
  - Segment-level diff highlighting
  - Copy to clipboard
  - Download original message
  - Validate against schema
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-MST-001

**FR-MST-003: Session Grouping**
- **Description:** Group related messages by transaction session
- **Acceptance Criteria:**
  - Master Session ID linking all related messages
  - Show parent-child relationships
  - Correlation ID tracking
  - Session timeline visualization
  - Filter by session ID
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-MST-001

**FR-MST-004: Error Analysis**
- **Description:** Highlight failures and suggest root causes
- **Acceptance Criteria:**
  - Red highlight on failed stages
  - Error message displayed
  - Suggested actions (e.g., "Validation failed: MSH-10 missing")
  - Link to relevant logs
  - Common error patterns detected (e.g., "Connection timeout", "Schema mismatch")
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-MST-001, FR-RHP-003

**FR-MST-005: Performance Metrics**
- **Description:** Timing breakdown for each processing stage
- **Acceptance Criteria:**
  - Time spent in each item
  - Queue wait times
  - Transformation duration
  - Network latency
  - Identify bottlenecks visually (red bars for slow stages)
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-MST-001

### 3.4 Real-Time Monitoring

**FR-RTM-001: Auto-Refresh Status**
- **Description:** Periodic polling for status updates
- **Acceptance Criteria:**
  - Poll interval: 10 seconds (configurable)
  - Update node status indicators
  - Update throughput metrics
  - Flash animation on status change
  - Pause auto-refresh when interacting
- **Priority:** P0 (Must Have)
- **Dependencies:** FR-TOP-001, Project Status API

**FR-RTM-002: Alert Notifications**
- **Description:** Visual alerts for critical events
- **Acceptance Criteria:**
  - Toast notification on: item stopped, error threshold exceeded
  - Badge count on Topology tab (e.g., "Topology (3 alerts)")
  - Alert history panel
  - Acknowledge/dismiss alerts
  - Alert sound (configurable)
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-RTM-001

**FR-RTM-003: WebSocket Live Updates (Future)**
- **Description:** Real-time push updates instead of polling
- **Acceptance Criteria:**
  - WebSocket connection to Engine
  - Instant status updates
  - Message count updates in real-time
  - Connection status indicator
- **Priority:** P2 (Nice to Have)
- **Dependencies:** Engine WebSocket support

### 3.5 Accessibility and Usability

**FR-ACC-001: Keyboard Navigation**
- **Description:** Full keyboard accessibility
- **Acceptance Criteria:**
  - Tab to navigate nodes
  - Enter to select
  - Arrow keys to pan
  - Keyboard shortcuts documented
  - Shortcuts help overlay (Ctrl+/)
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-TOP-001

**FR-ACC-002: Screen Reader Support**
- **Description:** ARIA labels and announcements
- **Acceptance Criteria:**
  - All nodes have descriptive ARIA labels
  - Status changes announced
  - Alternative text for visual indicators
  - Keyboard-accessible context menus
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-TOP-001

**FR-ACC-003: Responsive Design**
- **Description:** Adaptive layout for different screen sizes
- **Acceptance Criteria:**
  - Desktop (1920x1080): Full layout with detail panel
  - Laptop (1366x768): Collapsible detail panel
  - Tablet (1024x768): Detail panel as modal overlay
  - Mobile (768x1024): Table view only (graph too complex)
- **Priority:** P1 (Should Have)
- **Dependencies:** FR-TOP-001, FR-RHP-001

---

## 4. Non-Functional Requirements

### 4.1 Performance

**NFR-PRF-001: Initial Load Time** ⭐ CRITICAL
- **Requirement:** Topology view loads in < 2 seconds for 50-item production
- **Measurement:** Time from tab click to full render
- **Rationale:** User expects instant feedback; delays suggest system issues
- **Priority:** P0

**NFR-PRF-002: Interaction Responsiveness**
- **Requirement:** Node click opens detail panel in < 100ms
- **Measurement:** Time from click to panel visible
- **Rationale:** Must feel instantaneous for good UX
- **Priority:** P0

**NFR-PRF-003: Zoom/Pan Smoothness**
- **Requirement:** 60 FPS during zoom/pan operations
- **Measurement:** Frame rate during interactions
- **Rationale:** Choppy animations feel broken and unprofessional
- **Priority:** P0

**NFR-PRF-004: Large Production Support**
- **Requirement:** Support 100+ items without performance degradation
- **Measurement:** Load time, zoom smoothness with 100 nodes
- **Rationale:** Major hospitals have complex production topologies
- **Priority:** P0

**NFR-PRF-005: Message Trace Load Time**
- **Requirement:** Swimlane diagram renders in < 1 second
- **Measurement:** Time from message click to swimlane displayed
- **Rationale:** Tracing is time-critical during incidents
- **Priority:** P0

### 4.2 Reliability

**NFR-REL-001: Fault Tolerance**
- **Requirement:** Graceful degradation when API unavailable
- **Behavior:** Show cached data with "stale" indicator
- **Priority:** P0

**NFR-REL-002: Data Accuracy**
- **Requirement:** Status indicators 99.9% accurate
- **Measurement:** Status matches actual engine state
- **Priority:** P0

**NFR-REL-003: Browser Compatibility**
- **Requirement:** Works on Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Priority:** P0

### 4.3 Security

**NFR-SEC-001: Data Sanitization**
- **Requirement:** All message content sanitized to prevent XSS
- **Priority:** P0

**NFR-SEC-002: PHI Protection**
- **Requirement:** No patient-identifiable data in UI logs
- **Priority:** P0 (HIPAA compliance)

**NFR-SEC-003: RBAC Enforcement**
- **Requirement:** Respect user permissions (view-only vs. edit)
- **Priority:** P0

### 4.4 Maintainability

**NFR-MNT-001: Code Quality**
- **Requirement:** TypeScript strict mode, 0 `any` types in production code
- **Priority:** P1

**NFR-MNT-002: Documentation**
- **Requirement:** All components have JSDoc comments
- **Priority:** P1

**NFR-MNT-003: Testing**
- **Requirement:** 80% code coverage, E2E tests for critical paths
- **Priority:** P1

---

## 5. User Requirements

### 5.1 Integration Engineer Requirements

**UR-IE-001:** "I need to quickly identify which item is causing message delivery failures"
- **Related FR:** FR-MST-001, FR-MST-004

**UR-IE-002:** "I need to see the exact transformation applied to a message at each stage"
- **Related FR:** FR-MST-002

**UR-IE-003:** "I need to test message flow through the topology without sending to production systems"
- **Related FR:** Future - Test Mode

**UR-IE-004:** "I need to compare two production topologies to understand what changed"
- **Related FR:** Future - Diff View

### 5.2 System Administrator Requirements

**UR-SA-001:** "I need to see at a glance which items are running, stopped, or in error state"
- **Related FR:** FR-TOP-001, FR-RTM-001

**UR-SA-002:** "I need to be alerted immediately when an item stops or errors spike"
- **Related FR:** FR-RTM-002

**UR-SA-003:** "I need to export topology diagrams for incident reports"
- **Related FR:** Future - Export PNG/SVG

**UR-SA-004:** "I need to see historical message throughput to plan capacity"
- **Related FR:** FR-RHP-005

### 5.3 Clinical Analyst Requirements

**UR-CA-001:** "I need to validate that HL7 ADT messages are correctly transformed to FHIR"
- **Related FR:** FR-MST-002

**UR-CA-002:** "I need to find all messages for a specific patient (NHS number)"
- **Related FR:** Future - Patient-Centric Search

**UR-CA-003:** "I need to prove message delivery for audit trail"
- **Related FR:** FR-MST-001, FR-MST-003

---

## 6. System Requirements

### 6.1 Backend API Requirements

**SR-API-001: Project Detail API**
- **Endpoint:** `GET /api/projects/:id`
- **Response:** ProjectDetail with items, connections, routing_rules
- **Performance:** < 200ms response time

**SR-API-002: Item Metrics API**
- **Endpoint:** `GET /api/projects/:id/items/:itemId/metrics`
- **Response:** Real-time metrics (messages, errors, latency)
- **Performance:** < 100ms response time

**SR-API-003: Message Trace API**
- **Endpoint:** `GET /api/projects/:id/messages/:messageId/trace`
- **Response:** Complete message journey with timestamps
- **Performance:** < 500ms response time

**SR-API-004: Event Logs API**
- **Endpoint:** `GET /api/projects/:id/items/:itemId/logs`
- **Response:** Paginated event logs
- **Performance:** < 200ms response time

**SR-API-005: Update Item Position API**
- **Endpoint:** `PUT /api/projects/:id/items/:itemId`
- **Body:** `{ position: { x, y } }`
- **Performance:** < 100ms response time

### 6.2 Database Requirements

**SR-DB-001: Message Tracing**
- **Schema:** `message_traces` table with session_id, item_id, timestamp, content, status
- **Indexing:** Index on session_id, timestamp for fast lookups
- **Retention:** 30 days (configurable)

**SR-DB-002: Item Positions**
- **Schema:** `project_items.position_x`, `project_items.position_y`
- **Default:** NULL (auto-layout)

---

## 7. Compliance Requirements

### 7.1 NHS Digital Standards

**CR-NHS-001: DCB0160 - Clinical Risk Management**
- **Requirement:** All message failures must be logged and traceable
- **Evidence:** Message trace swimlanes provide complete audit trail

**CR-NHS-002: DCB0129 - Clinical Safety**
- **Requirement:** System must not obscure critical errors
- **Evidence:** Red status indicators, alert notifications

### 7.2 GDPR / UK GDPR

**CR-GDPR-001: Data Minimization**
- **Requirement:** Display minimum necessary PHI in UI
- **Implementation:** Mask patient identifiers by default (show/hide toggle)

**CR-GDPR-002: Audit Trail**
- **Requirement:** Log all user actions on patient data
- **Implementation:** Log message content views

### 7.3 HIPAA (for international deployments)

**CR-HIPAA-001: Access Control**
- **Requirement:** Enforce role-based access to message content
- **Implementation:** RBAC integration

---

## 8. Acceptance Criteria

### 8.1 Must-Have for v1.8.0 Release

✅ **Graph topology view** with adaptive layout
✅ **Tabular list view** with sort/filter
✅ **Right-side detail panel** with 4 tabs (Config, Events, Messages, Metrics)
✅ **Message trace swimlanes** for e2e transaction visualization
✅ **Real-time status updates** (10-second polling)
✅ **Zoom/pan/fit controls** for graph navigation
✅ **Node click actions** opening detail panel
✅ **Performance:** < 2s load time for 50-item production
✅ **NHS color palette** styling
✅ **Responsive layout** for 1366x768 and above

### 8.2 Should-Have for v1.8.0 or v1.9.0

- Search and filter functionality
- Alert notifications
- Keyboard navigation
- Export capabilities (CSV, PNG)
- Performance metrics charts
- Error analysis suggestions

### 8.3 Nice-to-Have for v2.0.0

- WebSocket live updates
- Test mode simulation
- Diff view for topology changes
- Patient-centric message search
- Automated compliance reports

---

## 9. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Performance degradation with 100+ items** | High | Medium | Implement virtualization, lazy loading |
| **Browser incompatibility (Safari)** | Medium | Low | Cross-browser testing, polyfills |
| **API response time > 2s** | High | Medium | Backend optimization, caching |
| **Message trace data not available** | High | Low | Implement message tracing in Engine first |
| **User training resistance** | Medium | Medium | Intuitive UI design, in-app help |

---

## 10. Glossary

**Item:** Service, Process, or Operation in a production
**Production:** Complete integration engine configuration with items and connections
**Topology:** Visual representation of production items and message flow
**Swimlane:** Horizontal timeline diagram showing message progression through items
**Session ID:** Unique identifier linking related messages in a transaction
**NHS Number:** UK national patient identifier (10 digits)
**HL7:** Health Level 7 - Healthcare messaging standard
**FHIR:** Fast Healthcare Interoperability Resources - Modern healthcare API standard
**MLLP:** Minimal Lower Layer Protocol - HL7 v2.x transport protocol
**EPR:** Electronic Patient Record
**ADT:** Admission, Discharge, Transfer message type

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-11 | System | Initial MVP requirements |
| 2.0.0 | 2026-02-12 | System | Enterprise-grade comprehensive requirements |

**Approval**

- [ ] Product Owner: ___________________ Date: ___________
- [ ] Integration Engineering Lead: ___________________ Date: ___________
- [ ] Hospital CIO: ___________________ Date: ___________
