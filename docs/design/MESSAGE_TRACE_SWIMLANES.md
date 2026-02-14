# Message Trace Swimlanes - Design Specification

**Version:** 1.0.0
**Last Updated:** February 12, 2026
**Status:** Design Ready for Implementation
**Purpose:** End-to-End Message Transaction Visualization

---

## Table of Contents

1. [Overview](#1-overview)
2. [User Stories](#2-user-stories)
3. [Swimlane Design](#3-swimlane-design)
4. [Data Model](#4-data-model)
5. [Visual Specifications](#5-visual-specifications)
6. [Interaction Patterns](#6-interaction-patterns)
7. [Implementation Architecture](#7-implementation-architecture)

---

## 1. Overview

### 1.1 Purpose

**Message Trace Swimlanes** provide a horizontal timeline visualization showing the complete journey of an HL7/FHIR message through the HIE production, from initial ingestion by a Service, through transformations in Processes, to final delivery via Operations.

### 1.2 Critical Use Cases

**1. Root Cause Analysis** (Highest Priority)
- **Scenario:** Message fails validation at Process stage
- **Need:** Identify exact transformation that caused failure
- **Current Pain:** Manual log correlation across multiple items
- **Solution:** Visual swimlane shows failure point with red indicator

**2. Performance Optimization**
- **Scenario:** Messages taking > 5 seconds end-to-end
- **Need:** Identify bottleneck item (slow transformation, queue backup)
- **Current Pain:** No timing breakdown visibility
- **Solution:** Bar chart showing time spent in each stage

**3. Compliance Auditing**
- **Scenario:** NHS Digital audit requires proof of message delivery
- **Need:** Complete audit trail from source to destination
- **Current Pain:** Manual log export and correlation
- **Solution:** Exportable swimlane diagram with timestamps

**4. Data Transformation Validation**
- **Scenario:** Clinical analyst verifies HL7 v2.3 → FHIR transformation accuracy
- **Need:** Side-by-side comparison of input vs. output
- **Current Pain:** Manual message inspection in separate tools
- **Solution:** Expandable diff view at each transformation stage

### 1.3 Design Goals

| Goal | Target | Success Metric |
|------|--------|----------------|
| **Fast Load** | < 1 second | Time from message click to swimlane visible |
| **Intuitive** | Zero training | 90% of users understand without explanation |
| **Comprehensive** | 100% trace | Every hop captured with timestamps |
| **Actionable** | 1-click drill-down | Click stage → View raw message content |
| **Accessible** | WCAG AA | Keyboard navigation, screen reader support |

---

## 2. User Stories

### 2.1 Integration Engineer Stories

**US-IE-001:** "As an integration engineer, I need to trace a failed ADT message to identify which validation rule failed"
- **Acceptance Criteria:**
  - Swimlane shows all stages (Service → Process1 → Process2 → Operation)
  - Failed stage highlighted in red
  - Error message displayed on hover
  - Link to validation rule configuration

**US-IE-002:** "As an integration engineer, I need to compare the original HL7 message with the transformed FHIR output"
- **Acceptance Criteria:**
  - Click any transformation stage opens diff viewer
  - Side-by-side: Input (left) | Output (right)
  - Syntax highlighting (HL7 segments, FHIR JSON)
  - Differences highlighted (additions in green, deletions in red)

**US-IE-003:** "As an integration engineer, I need to replay a failed message for debugging"
- **Acceptance Criteria:**
  - "Replay Message" button on swimlane
  - Injects message at original entry point
  - Shows replay trace in separate swimlane (orange color)

### 2.2 System Administrator Stories

**US-SA-001:** "As a system administrator, I need to identify which item is causing throughput bottlenecks"
- **Acceptance Criteria:**
  - Swimlane shows timing bars for each stage
  - Longest bar highlighted in yellow
  - Tooltip shows: "Spent 3.2s in NHS.Validator (80% of total time)"

**US-SA-002:** "As a system administrator, I need to export message traces for incident reports"
- **Acceptance Criteria:**
  - Export as PDF with swimlane diagram
  - Export as JSON with all message content
  - Includes: timestamps, content, errors, session metadata

### 2.3 Clinical Analyst Stories

**US-CA-001:** "As a clinical analyst, I need to verify patient data integrity through transformation pipeline"
- **Acceptance Criteria:**
  - Search for message by NHS Number
  - Swimlane shows all transformations
  - Highlight patient identifiers (PID.3, PID.5) at each stage
  - Validate: No data loss, correct mapping

---

## 3. Swimlane Design

### 3.1 Overall Layout

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ Message Trace - ADT^A01 - Session: abc-123-def             [Export] [Replay] [×]     │ Header
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│ ┌──────────────────────────────────────────────────────────────────────────────────┐│
│ │ Timeline: 15:45:18 ────────────────────────────────────────────▶ 15:45:23         ││
│ │           (Total: 5.2 seconds)                                                    ││
│ └──────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│ ┌─ HL7.Receiver.PAS ────────────────────────────────────────────────────────────────┐│
│ │                                                                                   ││
│ │ [●]─────▶                                                      15:45:18 (0.0s)    ││ Service Lane
│ │  Message                                                       Status: ✓ Received ││
│ │  Received                                                                         ││
│ └───────────────────────────────────────────────────────────────────────────────────┘│
│           │                                                                          │
│           ▼ (0.1s queue wait)                                                       │
│ ┌─ NHS.Validator ───────────────────────────────────────────────────────────────────┐│
│ │                                                                                   ││
│ │      [●]─────────────▶                                         15:45:19 (1.2s)    ││ Process Lane 1
│ │       Validated                                                Status: ✓ Success  ││
│ │       Transform: v23_to_FHIR                                                      ││
│ └───────────────────────────────────────────────────────────────────────────────────┘│
│           │                                                                          │
│           ▼ (0.05s queue wait)                                                      │
│ ┌─ ADT.Router ──────────────────────────────────────────────────────────────────────┐│
│ │                                                                                   ││
│ │           [●]──▶                                               15:45:20 (0.3s)    ││ Process Lane 2
│ │            Routed                                              Status: ✓ Matched  ││
│ │            Rule: ADT→RIS                                                          ││
│ └───────────────────────────────────────────────────────────────────────────────────┘│
│           │                                                                          │
│           ▼ (0.2s queue wait)                                                       │
│ ┌─ HL7.Sender.RIS ──────────────────────────────────────────────────────────────────┐│
│ │                                                                                   ││
│ │                [●]──────────────────────────────────▶          15:45:23 (3.5s)    ││ Operation Lane
│ │                 Sent to RIS                                    Status: ✓ ACK CA   ││
│ │                 ACK: MSA|CA|...                                                   ││
│ └───────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│ ┌─ Performance Summary ─────────────────────────────────────────────────────────────┐│
│ │ Total Time: 5.2s  │  Processing: 5.0s  │  Queue Wait: 0.35s  │  Slowest: HL7.Sender (3.5s) ││
│ └──────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘

Modal: 1200px width × 800px height (80% viewport)
```

### 3.2 Swimlane Dimensions

**Lane Height:** 100px per item
**Lane Padding:** 12px vertical, 16px horizontal
**Stage Indicator:** 16px circle
**Timeline Bar:** Height proportional to duration
**Minimum Bar Width:** 40px (even for < 100ms stages)

### 3.3 Color Coding

**Status Colors:**
```
✓ Success:       Green (#00c853)
✗ Error:         Red (#da291c)
⚠ Warning:       Yellow (#ffb81c)
⏳ In Progress:  Blue (#005eb8)
○ Skipped:       Gray (#9e9e9e)
```

**Lane Colors:**
```
Service Lane:    Green-50 background (#f0f9f5)
Process Lane:    Blue-50 background (#e8f4f8)
Operation Lane:  Purple-50 background (#f3e5ff)
```

**Timeline Bar Colors:**
```
< 100ms:    Green bar (fast)
100-500ms:  Yellow bar (acceptable)
> 500ms:    Orange bar (slow)
> 2s:       Red bar (bottleneck)
```

### 3.4 Stage Indicator Design

```
┌────────────────┐
│                │
│   [●]──▶       │   ← Stage circle (16px) + progress bar
│    ↑           │
│    │           │
│  Status        │
│  Icon          │
│                │
│ ✓ Success      │   ← Status text
│ 15:45:19       │   ← Timestamp
│ (1.2s)         │   ← Duration
│                │
└────────────────┘

Circle Style:
- Diameter: 16px
- Border: 2px solid (color by status)
- Fill: White
- Icon: ✓ (success), ✗ (error), ⚠ (warning)
- Animation: Pulse on hover

Progress Bar:
- Height: 4px
- Color: Status color
- Width: Proportional to duration
- Min Width: 40px
- Max Width: Lane width - 100px
```

---

## 4. Data Model

### 4.1 Message Trace Schema

```typescript
interface MessageTrace {
  trace_id: string;              // UUID
  session_id: string;            // Master session ID
  message_id: string;            // Original message ID
  message_type: string;          // "ADT^A01", "ORU^R01", etc.
  started_at: string;            // ISO timestamp
  completed_at: string | null;  // null if in progress
  total_duration_ms: number;
  status: "completed" | "error" | "in_progress";
  stages: MessageTraceStage[];
}

interface MessageTraceStage {
  stage_id: string;              // UUID
  item_id: string;               // Reference to ProjectItem
  item_name: string;             // "HL7.Receiver.PAS"
  item_type: "service" | "process" | "operation";
  sequence_number: number;       // 1, 2, 3, ...
  entered_at: string;            // ISO timestamp
  exited_at: string | null;      // null if failed/stuck
  duration_ms: number;
  queue_wait_ms: number;         // Time waiting before processing
  status: "success" | "error" | "warning" | "skipped";
  input_message: string;         // Raw message content (HL7/FHIR)
  output_message: string | null; // Transformed message (null if failed)
  transformation: string | null; // Transform name (e.g., "v23_to_FHIR")
  error_message: string | null;
  ack_message: string | null;    // For operations
  metadata: Record<string, any>; // Additional context
}
```

### 4.2 API Endpoint

**Endpoint:** `GET /api/projects/:projectId/messages/:messageId/trace`

**Response:**
```json
{
  "trace": {
    "trace_id": "abc-123-def",
    "session_id": "session-456",
    "message_id": "MSG001",
    "message_type": "ADT^A01",
    "started_at": "2026-02-12T15:45:18.123Z",
    "completed_at": "2026-02-12T15:45:23.456Z",
    "total_duration_ms": 5333,
    "status": "completed",
    "stages": [
      {
        "stage_id": "stage-1",
        "item_id": "item-001",
        "item_name": "HL7.Receiver.PAS",
        "item_type": "service",
        "sequence_number": 1,
        "entered_at": "2026-02-12T15:45:18.123Z",
        "exited_at": "2026-02-12T15:45:18.234Z",
        "duration_ms": 111,
        "queue_wait_ms": 0,
        "status": "success",
        "input_message": "MSH|^~\\&|PAS|STH|...",
        "output_message": "MSH|^~\\&|PAS|STH|...",
        "transformation": null,
        "error_message": null,
        "ack_message": null,
        "metadata": { "port": 2575 }
      },
      // ... more stages
    ]
  }
}
```

---

## 5. Visual Specifications

### 5.1 Lane Header Design

```
┌─ HL7.Receiver.PAS ────────────────────────────────────────┐
│ Service • Port 2575                           [View Config]│
├───────────────────────────────────────────────────────────-┤
│  [Content]                                                 │
└────────────────────────────────────────────────────────────┘

Style:
- Height: 40px
- Background: Gradient (lane color → white)
- Font: 14px bold
- Border-bottom: 1px solid gray-300
- Action Button: Small link button (right-aligned)
```

### 5.2 Stage Tooltip

```
┌────────────────────────────────────┐
│ NHS.Validator                      │
│ ────────────────────────────────── │
│ Status: ✓ Success                  │
│ Duration: 1.2 seconds              │
│ Transform: v23_to_FHIR             │
│ Queue Wait: 0.1 seconds            │
│                                    │
│ Input: 2.3 KB (HL7 v2.3)          │
│ Output: 5.7 KB (FHIR R4 JSON)     │
│                                    │
│ [View Input] [View Output] [Diff] │
└────────────────────────────────────┘

Style:
- Width: 320px
- Background: White
- Border: 1px solid gray-400
- Shadow: 0 4px 12px rgba(0,0,0,0.15)
- Padding: 12px
- Font: 12px
```

### 5.3 Error Stage Visual

```
┌─ NHS.Validator ───────────────────────────────────────────┐
│                                                            │
│      [✗]────────▶                      15:45:19 (1.2s)     │
│       │ FAILED                         Status: ✗ Error    │
│       │                                                    │
│       └─ Error: Validation failed                         │
│          MSH-10 missing (required field)                  │
│                                                            │
│       [View Error Details] [View Input Message]           │
│                                                            │
└────────────────────────────────────────────────────────────┘

Style:
- Lane Background: Red-50 (#ffebee)
- Stage Circle: Red border, red ✗ icon
- Progress Bar: Red dashed line (indicates failure)
- Error Text: Red-700, 12px
- Error Box: Red-100 bg, red-600 border, 8px padding
```

### 5.4 Timeline Axis

```
Timeline:  15:45:18 ──────┬─────┬──────┬───────▶ 15:45:23
           0.0s           1s    2s     3s        5.2s
                          ↓     ↓      ↓
                       Validator Router Sender
```

**Style:**
- Height: 40px
- Font: 11px monospace
- Tick Marks: 1-second intervals
- Axis Line: 2px solid gray-400
- Label Position: Above axis

---

## 6. Interaction Patterns

### 6.1 Open Swimlane

**Trigger:**
- Click message row in Messages tab (detail panel)
- Click "Trace" button on message in event log
- Direct link: `/projects/:id/messages/:msgId/trace`

**Action:**
- Open modal overlay (centered, 1200×800px)
- Backdrop: Black, 70% opacity
- Load trace data via API
- Show loading spinner if > 500ms
- Animate: Fade in + scale from 0.95 (300ms)

**Keyboard:**
- Escape: Close modal
- Arrow keys: Navigate between stages
- Enter: Expand stage details

### 6.2 Stage Click Actions

**Click Stage Circle:**
- **Action:** Expand stage details inline
- **Visual:** Lane expands vertically (+200px), shows:
  - Input message preview (first 500 chars)
  - Output message preview (first 500 chars)
  - Full error message (if any)
  - Metadata table
- **Animation:** Height expansion (300ms ease-out)

**Click "View Input" Button:**
- **Action:** Open Message Viewer modal
- **Content:** Full input message with syntax highlighting
- **Features:**
  - Copy to clipboard
  - Download as file
  - Search within message
  - Validate against schema

**Click "View Output" Button:**
- **Action:** Open Message Viewer modal
- **Content:** Full output message

**Click "Diff" Button:**
- **Action:** Open Diff Viewer modal
- **Content:** Side-by-side comparison
- **Highlighting:**
  - Green: Additions
  - Red: Deletions
  - Yellow: Modifications

### 6.3 Timeline Interaction

**Hover Timeline:**
- **Action:** Show vertical time marker
- **Visual:** Dashed line from cursor to bottom
- **Label:** Timestamp at cursor position

**Click Timeline:**
- **Action:** Highlight all stages at that time
- **Use Case:** "What was happening at 15:45:20?"

### 6.4 Export Options

**Export as PDF:**
- **Content:**
  - Swimlane diagram (rendered as vector)
  - Performance summary table
  - Full stage details
  - Message content (optional, checkbox)
- **Filename:** `message-trace-{message_id}-{timestamp}.pdf`

**Export as JSON:**
- **Content:** Complete MessageTrace object
- **Use Case:** Import into analysis tools, compliance archives
- **Filename:** `message-trace-{message_id}.json`

**Export as CSV:**
- **Content:** Flat table with one row per stage
- **Columns:** stage, item, duration_ms, status, error
- **Use Case:** Spreadsheet analysis

---

## 7. Implementation Architecture

### 7.1 Component Structure

```
MessageTraceSwimlane.tsx (Modal)
├── TraceHeader.tsx
│   ├── Title: "Message Trace - {type}"
│   ├── SessionInfo: Session ID, timestamps
│   └── Actions: Export, Replay, Close
│
├── TimelineAxis.tsx
│   ├── Time labels (0s, 1s, 2s, ...)
│   ├── Tick marks
│   └── Hover marker
│
├── SwimlaneCanvas.tsx (ScrollArea)
│   ├── SwimlaneItem.tsx (foreach stage)
│   │   ├── LaneHeader.tsx
│   │   │   ├── Item name + type
│   │   │   └── View Config link
│   │   │
│   │   ├── LaneContent.tsx
│   │   │   ├── StageIndicator.tsx
│   │   │   │   ├── Circle with status icon
│   │   │   │   ├── Progress bar
│   │   │   │   └── Timestamp + duration
│   │   │   │
│   │   │   └── StageDetails.tsx (expandable)
│   │   │       ├── Input/Output previews
│   │   │       ├── Error message
│   │   │       └── Action buttons
│   │   │
│   │   └── QueueWaitIndicator.tsx
│   │       └── Vertical arrow with wait time
│   │
│   └── PerformanceSummary.tsx
│       ├── Total time
│       ├── Processing vs. queue time
│       └── Slowest stage indicator
│
└── MessageViewer.tsx (Modal)
    ├── Content display (syntax highlighted)
    ├── Toolbar: Copy, Download, Validate
    └── Search box
```

### 7.2 State Management

```typescript
interface SwimlaneState {
  trace: MessageTrace | null;
  loading: boolean;
  error: string | null;
  expandedStages: Set<string>;      // Stage IDs
  selectedStage: string | null;     // For keyboard navigation
  timelineHoverPosition: number | null;
  viewerModal: {
    open: boolean;
    content: string;
    type: "input" | "output" | "diff";
  };
}

// Zustand store
const useSwimlaneStore = create<SwimlaneState>((set) => ({
  trace: null,
  loading: false,
  error: null,
  expandedStages: new Set(),
  selectedStage: null,
  timelineHoverPosition: null,
  viewerModal: { open: false, content: "", type: "input" },

  fetchTrace: async (messageId: string) => {
    set({ loading: true, error: null });
    try {
      const trace = await api.getMessageTrace(messageId);
      set({ trace, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  toggleStageExpansion: (stageId: string) => {
    set((state) => {
      const expanded = new Set(state.expandedStages);
      if (expanded.has(stageId)) {
        expanded.delete(stageId);
      } else {
        expanded.add(stageId);
      }
      return { expandedStages: expanded };
    });
  },
}));
```

### 7.3 Performance Optimizations

**1. Virtualization:**
- Only render visible lanes (react-window)
- Critical for productions with 20+ stages

**2. Lazy Load Messages:**
- Initially show metadata only
- Load full message content on expansion
- Cache loaded messages in memory

**3. Debounced Hover:**
- Debounce timeline hover (50ms)
- Prevent re-renders on rapid mouse movement

**4. Memoization:**
- Memoize stage indicators (React.memo)
- Memoize timeline calculations
- useMemo for derived state (total time, bottleneck detection)

### 7.4 Backend Requirements

**Database Tables:**

```sql
-- Message traces (master record)
CREATE TABLE message_traces (
  trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  message_id VARCHAR(255) NOT NULL,
  message_type VARCHAR(50),
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  total_duration_ms INTEGER,
  status VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX idx_session_id (session_id),
  INDEX idx_message_id (message_id)
);

-- Individual stages
CREATE TABLE message_trace_stages (
  stage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id UUID NOT NULL REFERENCES message_traces(trace_id) ON DELETE CASCADE,
  item_id UUID NOT NULL REFERENCES project_items(id),
  sequence_number INTEGER NOT NULL,
  entered_at TIMESTAMP NOT NULL,
  exited_at TIMESTAMP,
  duration_ms INTEGER,
  queue_wait_ms INTEGER DEFAULT 0,
  status VARCHAR(20),
  input_message TEXT,
  output_message TEXT,
  transformation VARCHAR(255),
  error_message TEXT,
  ack_message TEXT,
  metadata JSONB,
  INDEX idx_trace_id (trace_id),
  INDEX idx_item_id (item_id)
);
```

**Tracing Instrumentation:**

```python
# In Engine (Python/ObjectScript)
class MessageTracer:
    def start_trace(self, message_id: str, session_id: str) -> str:
        trace_id = uuid4()
        db.insert("message_traces", {
            "trace_id": trace_id,
            "session_id": session_id,
            "message_id": message_id,
            "message_type": extract_message_type(message),
            "started_at": datetime.now(),
            "status": "in_progress"
        })
        return trace_id

    def log_stage(self, trace_id: str, item_id: str, input_msg: str):
        stage_id = uuid4()
        db.insert("message_trace_stages", {
            "stage_id": stage_id,
            "trace_id": trace_id,
            "item_id": item_id,
            "sequence_number": get_next_sequence(trace_id),
            "entered_at": datetime.now(),
            "status": "in_progress",
            "input_message": input_msg
        })
        return stage_id

    def complete_stage(self, stage_id: str, output_msg: str, status: str):
        stage = db.get("message_trace_stages", stage_id)
        duration_ms = (datetime.now() - stage.entered_at).total_seconds() * 1000
        db.update("message_trace_stages", stage_id, {
            "exited_at": datetime.now(),
            "duration_ms": duration_ms,
            "output_message": output_msg,
            "status": status
        })
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Component Tests:**
- SwimlaneItem renders correctly with success status
- SwimlaneItem renders correctly with error status
- StageIndicator calculates bar width correctly
- TimelineAxis generates correct tick marks
- Export functions generate valid PDF/JSON/CSV

### 8.2 Integration Tests

**API Tests:**
- GET /api/projects/:id/messages/:msgId/trace returns 200
- Trace includes all stages in correct sequence
- Stage durations add up to total duration
- Error stages include error_message

**UI Tests:**
- Click message row opens swimlane modal
- Click stage expands details
- Click "View Input" opens message viewer
- Keyboard navigation works (arrows, enter, escape)
- Export generates downloadable file

### 8.3 E2E Tests (Cypress)

```javascript
describe('Message Trace Swimlanes', () => {
  it('displays complete message journey', () => {
    cy.visit('/projects/test-project');
    cy.findByText('Topology').click();
    cy.findByText('HL7.Receiver.PAS').click();
    cy.findByText('Messages').click();

    // Click first message
    cy.get('[data-testid="message-row"]').first().click();

    // Swimlane modal opens
    cy.findByRole('dialog', { name: /Message Trace/ }).should('be.visible');

    // All stages visible
    cy.findByText('HL7.Receiver.PAS').should('be.visible');
    cy.findByText('NHS.Validator').should('be.visible');
    cy.findByText('HL7.Sender.RIS').should('be.visible');

    // Performance summary
    cy.findByText(/Total Time: \d+\.\d+s/).should('be.visible');
  });

  it('expands stage details on click', () => {
    // ... (navigate to swimlane)

    cy.findByLabelText('Stage: NHS.Validator').click();
    cy.findByText('Input message preview').should('be.visible');
    cy.findByText('View Input').click();

    // Message viewer opens
    cy.findByRole('dialog', { name: /Message Viewer/ }).should('be.visible');
    cy.findByText(/MSH\|/).should('be.visible'); // HL7 content
  });
});
```

---

## 9. Accessibility Checklist

- [ ] Keyboard navigation: Tab through stages, Enter to expand
- [ ] Screen reader announcements: "Stage 2 of 4, NHS Validator, Success, 1.2 seconds"
- [ ] ARIA labels: All interactive elements
- [ ] Focus indicators: 2px blue outline on focus
- [ ] Color not sole indicator: Status icons (✓✗⚠) in addition to colors
- [ ] Alt text for diagrams: Full text description of swimlane
- [ ] Keyboard shortcuts documented: Help modal (Ctrl+/)

---

## 10. Future Enhancements

**Phase 2:**
- Real-time updates (WebSocket): Show in-progress messages
- Message replay: Re-inject failed message for debugging
- Batch trace: Compare multiple messages side-by-side

**Phase 3:**
- Predictive bottleneck detection (ML-based)
- Automated root cause suggestions
- Integration with JIRA (create ticket from error stage)

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-12 | System | Initial swimlane design |

**Approval**

- [ ] Integration Engineering Lead: ___________________
- [ ] UX Designer: ___________________
- [ ] Security Review: ___________________
