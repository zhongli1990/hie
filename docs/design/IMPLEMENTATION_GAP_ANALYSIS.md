# Implementation Gap Analysis - Topology Viewer

**Version:** 1.0.0
**Date:** February 12, 2026
**Status:** Analysis Complete
**Purpose:** Compare current MVP implementation against enterprise requirements

---

## Executive Summary

### Current Status: Phase 1 MVP (30% Complete)

**What We Have:**
- ✅ Basic graph topology view with ReactFlow
- ✅ Three node types (service, process, operation) with NHS colors
- ✅ Three edge types (standard, error, async)
- ✅ Basic toolbar (zoom, view mode, display options)
- ✅ Legend component
- ✅ Integrated into project detail page as "Diagram" tab
- ✅ TypeScript compilation successful

**What We're Missing:**
- ❌ **CRITICAL:** "Diagram" should be "Topology" (terminology)
- ❌ **CRITICAL:** Right-side detail panel with tabs (Config, Events, Messages, Metrics)
- ❌ **CRITICAL:** Message trace swimlanes (completely missing)
- ❌ **CRITICAL:** Tabular view (listed in toolbar but not implemented)
- ❌ Real-time status updates (polling)
- ❌ Search and filter functionality
- ❌ Drag-and-drop repositioning
- ❌ Context menus on right-click
- ❌ Hover tooltips with metrics
- ❌ Mini-map navigator
- ❌ Export capabilities (PNG, CSV, PDF)
- ❌ Keyboard navigation
- ❌ Accessibility features (ARIA labels, screen reader)

**Gap Score:** 70% of critical features missing

---

## Detailed Gap Analysis

### 1. Terminology and Branding

| Requirement | Current | Gap | Priority |
|-------------|---------|-----|----------|
| Tab named "Topology" | Named "Diagram" | ❌ Mismatch | **P0** |
| Use term "Topology" throughout | Uses "Diagram", "Production Diagram" | ❌ Inconsistent | **P0** |
| Component folder name | `ProductionDiagram` | ⚠️ Acceptable but should rename | P1 |

**Impact:** Confuses users familiar with IRIS terminology, inconsistent with hospital IT language

**Fix Required:**
1. Rename tab from "⭐ Diagram" → "⭐ Topology"
2. Update all UI text: "Diagram" → "Topology"
3. Consider renaming folder: `ProductionDiagram` → `TopologyViewer` (optional, would require refactor)

---

### 2. Layout and Space Utilization

| Requirement | Current | Gap |
|-------------|---------|-----|
| **Adaptive layout occupying most space** | Fixed canvas size, no adaptation | ❌ **CRITICAL** |
| Canvas should expand to viewport | Canvas has fixed height (600px) | ❌ **CRITICAL** |
| Right-side detail panel | Missing entirely | ❌ **CRITICAL** |
| Detail panel with 4 tabs | Not implemented | ❌ **CRITICAL** |
| Mini-map navigator | Not implemented | ⚠️ Phase 2 |
| Legend position (bottom-left) | Currently below canvas | ⚠️ Minor |

**Current Layout:**
```
┌──────────────────────────────────────┐
│ Toolbar (60px)                       │
├──────────────────────────────────────┤
│                                      │
│ Canvas (fixed 600px height)          │  ← NOT ADAPTIVE
│                                      │
│                                      │
├──────────────────────────────────────┤
│ Legend (below canvas)                │
└──────────────────────────────────────┘
```

**Required Layout:**
```
┌──────────────────────────────────────┬────────────────┐
│ Toolbar (60px)                       │                │
├──────────────────────────────────────┤  Detail Panel  │
│                                      │  (400px fixed) │
│ Canvas (calc(100vh - 260px))         │                │
│ ADAPTIVE - expands to fill viewport  │  [Config Tab]  │
│                                      │  [Events Tab]  │
│ ┌──────────┐  ┌──────────┐          │  [Msgs Tab]    │
│ │ Legend   │  │ Mini-map │          │  [Metrics Tab] │
│ └──────────┘  └──────────┘          │                │
└──────────────────────────────────────┴────────────────┘
```

**Fix Required:**
1. Change canvas height from 600px → `calc(100vh - 260px)` (viewport minus headers)
2. Implement resizable detail panel (400px default, 300-600px range)
3. When detail panel open: Canvas width = `calc(100vw - 400px - margins)`
4. When detail panel closed: Canvas width = `100% - margins`

---

### 3. Right-Side Detail Panel (MISSING - CRITICAL)

| Feature | Status | Priority |
|---------|--------|----------|
| **Panel framework** | Not implemented | **P0 - Blocking** |
| Slide-in animation | Not implemented | **P0** |
| Configuration tab | Not implemented | **P0** |
| Events/Logs tab | Not implemented | **P0** |
| Messages tab | Not implemented | **P0** |
| Metrics tab | Not implemented | **P0** |
| Resizable width | Not implemented | P1 |
| Persisted position | Not implemented | P1 |

**Current Behavior:**
- Click node → Navigates to Items tab (loses topology context)
- User cannot view item details while staying in topology view

**Required Behavior:**
- Click node → Detail panel slides in from right (300ms)
- 4 tabs: Configuration, Events, Messages, Metrics
- Close with X button or Escape key
- Panel stays open when selecting different nodes

**Components to Create:**
```
ItemDetailPanel/
├── ItemDetailPanel.tsx          ← Main container (NEW)
├── ConfigurationTab.tsx         ← Read-only config display (NEW)
├── EventsTab.tsx                ← Live event log (NEW)
├── MessagesTab.tsx              ← Recent messages with trace link (NEW)
└── MetricsTab.tsx               ← Real-time metrics + charts (NEW)
```

**API Requirements:**
- `GET /api/projects/:id/items/:itemId/logs` (NEW - backend)
- `GET /api/projects/:id/items/:itemId/metrics` (NEW - backend)
- `GET /api/projects/:id/items/:itemId/messages` (NEW - backend)

---

### 4. Message Trace Swimlanes (MISSING - CRITICAL)

| Feature | Status | Priority |
|---------|--------|----------|
| **Swimlane modal** | Not implemented | **P0 - Blocking** |
| Horizontal timeline | Not implemented | **P0** |
| Stage indicators | Not implemented | **P0** |
| Message content viewer | Not implemented | **P0** |
| Diff viewer | Not implemented | **P0** |
| Performance metrics | Not implemented | P1 |
| Export trace | Not implemented | P1 |

**Current Behavior:**
- No way to trace messages end-to-end
- No visibility into message transformations
- Cannot diagnose failures visually

**Required Implementation:**
1. **Backend First:**
   - Database tables: `message_traces`, `message_trace_stages`
   - Instrumentation in Engine to log each stage
   - API endpoint: `GET /api/projects/:id/messages/:msgId/trace`

2. **Frontend:**
   - Create `MessageTraceSwimlane` modal component
   - Render horizontal swimlanes (one per item)
   - Show timeline with timestamps
   - Stage indicators with status icons
   - Click message in Messages tab → Opens swimlane

**Estimated Effort:** 20-30 hours (complex feature)

---

### 5. View Modes

| View Mode | Status | Gap |
|-----------|--------|-----|
| **Graph View** | ✅ Implemented | ✓ Working |
| **Table View** | ❌ Button exists but view missing | **CRITICAL** |
| Column View (auto-layout) | ⚠️ Basic implementation | Needs enhancement |
| Topology View (hierarchical) | ❌ Same as Column | Future |

**Current Behavior:**
- Click "Table" button → Nothing happens (button exists but view doesn't)
- Should show sortable/filterable table

**Fix Required:**
```tsx
// In ProductionDiagram.tsx, add table view:
if (viewMode === "table") {
  return (
    <div className="space-y-4">
      <DataTable
        data={items}
        columns={[
          { key: "name", label: "Name", sortable: true },
          { key: "item_type", label: "Type", sortable: true },
          { key: "enabled", label: "Status", sortable: true },
          { key: "pool_size", label: "Pool Size", sortable: true },
          { key: "metrics", label: "Metrics", sortable: false },
        ]}
        onRowClick={(item) => onNodeClick(item.id)}
      />
    </div>
  );
}
```

---

### 6. Interactive Features

| Feature | Current | Gap | Priority |
|---------|---------|-----|----------|
| **Node click opens detail panel** | Navigates to Items tab | ❌ Wrong behavior | **P0** |
| Drag-and-drop repositioning | Not implemented | ⚠️ Phase 2 | P1 |
| Right-click context menu | Not implemented | ⚠️ Phase 2 | P1 |
| Hover tooltips | Not implemented | ⚠️ Phase 2 | P1 |
| Search/filter | Not implemented | ⚠️ Phase 2 | P1 |
| Keyboard navigation | Not implemented | P1 |

**Current Node Click Handler:**
```tsx
onNodeClick={(itemId) => {
  const item = project.items.find(i => i.id === itemId);
  if (item) {
    setSelectedItem(item);
    setActiveTab('items'); // ❌ WRONG - leaves topology view
  }
}}
```

**Required Node Click Handler:**
```tsx
onNodeClick={(itemId) => {
  const item = project.items.find(i => i.id === itemId);
  if (item) {
    setSelectedItem(item);
    setDetailPanelOpen(true); // ✓ CORRECT - opens panel, stays in topology
  }
}}
```

---

### 7. Real-Time Monitoring

| Feature | Current | Gap |
|---------|---------|-----|
| **Auto-refresh status** | Not implemented | ❌ **CRITICAL** |
| Polling interval (10s) | Not implemented | ❌ **CRITICAL** |
| Status indicator updates | Static | ❌ **CRITICAL** |
| Metrics updates | Static | ❌ **CRITICAL** |
| Alert notifications | Not implemented | ⚠️ Phase 2 |
| WebSocket (future) | Not implemented | P2 |

**Current Behavior:**
- Status shows item.enabled (true/false)
- Never updates unless page refreshed
- No live metrics

**Required Implementation:**
```tsx
// In ProductionDiagram.tsx
useEffect(() => {
  if (activeTab !== 'topology') return;

  const interval = setInterval(async () => {
    // Fetch updated project detail
    const updated = await getProject(workspaceId, projectId);

    // Update node statuses
    setNodes(prevNodes =>
      prevNodes.map(node => {
        const item = updated.items.find(i => i.id === node.id);
        return {
          ...node,
          data: {
            ...node.data,
            status: item.enabled ? 'running' : 'stopped',
            metrics: item.metrics || {},
          },
        };
      })
    );
  }, 10000); // 10 seconds

  return () => clearInterval(interval);
}, [activeTab, projectId]);
```

---

### 8. Visual Design

| Element | Current | Gap | Priority |
|---------|---------|-----|----------|
| **NHS color palette** | ✅ Correctly applied | ✓ | - |
| Node styling | ✅ Good (green/blue/purple) | ✓ | - |
| Edge styling | ✅ Good (solid/dashed/dotted) | ✓ | - |
| Status indicators | ⚠️ Basic (no animation) | Minor | P2 |
| Mini-map | ❌ Not implemented | ⚠️ Phase 2 | P1 |
| Legend position | ⚠️ Below canvas (should be overlay) | Minor | P1 |

**Current Node:**
- Width: 220px ✓
- Color coding: ✓
- Status dot: ✓
- Metrics: ✓

**Gaps:**
- No pulsing animation on "Running" status
- No error shake animation
- No hover glow effect
- Adapter settings access uses `as any` (type safety issue)

---

### 9. Performance

| Requirement | Current | Gap |
|-------------|---------|-----|
| **Load time < 2s for 50 items** | Unknown (not tested) | ⚠️ Needs testing |
| 60 FPS zoom/pan | Likely OK (ReactFlow handles) | ✓ |
| Support 100+ items | Unknown | ⚠️ Needs testing |
| Virtualization | Not implemented | ⚠️ For large productions |

**Testing Needed:**
1. Create test production with 50 items
2. Measure initial render time
3. Measure zoom/pan FPS (use Chrome DevTools)
4. Test with 100 items (may need virtualization)

---

### 10. Accessibility

| Requirement | Current | Gap |
|-------------|---------|-----|
| **Keyboard navigation** | Not implemented | ❌ **CRITICAL** |
| ARIA labels | Not implemented | ❌ **CRITICAL** |
| Screen reader support | Not implemented | ❌ **CRITICAL** |
| Focus indicators | ReactFlow default | ⚠️ Needs custom styling |
| Color contrast | ✅ NHS palette meets WCAG AA | ✓ |
| Keyboard shortcuts | Not implemented | ⚠️ Phase 2 |

**Current Accessibility Score:** F (Fail)

**Required:**
- Add ARIA labels to all nodes
- Implement Tab navigation
- Focus indicators (2px blue outline)
- Screen reader announcements on status change

---

## Priority Matrix

### Must Fix for v1.8.0 (P0 - Blocking)

1. **Rename "Diagram" → "Topology"** (1 hour)
   - Update tab label
   - Update all UI text
   - Update documentation

2. **Implement Right-Side Detail Panel** (12-16 hours)
   - Panel framework with slide-in animation
   - Configuration tab (read-only display)
   - Events tab (live log streaming)
   - Messages tab (list with trace link)
   - Metrics tab (charts + real-time data)

3. **Implement Table View** (4-6 hours)
   - Sortable/filterable table component
   - Show all items with status
   - Click row → Open detail panel
   - Export to CSV

4. **Fix Node Click Behavior** (2 hours)
   - Click node → Open detail panel (not navigate away)
   - Panel stays in topology context

5. **Implement Adaptive Layout** (4 hours)
   - Canvas expands to viewport height
   - Canvas width adapts to detail panel open/close
   - Responsive breakpoints

6. **Implement Message Trace Swimlanes** (20-30 hours) ⚠️ **LARGE EFFORT**
   - Backend: Database schema, instrumentation, API
   - Frontend: Modal, swimlane rendering, stage indicators
   - Message viewer with diff
   - This is the BIGGEST gap

7. **Implement Real-Time Updates** (4 hours)
   - 10-second polling
   - Update node statuses
   - Update metrics
   - Flash animation on change

### Should Have for v1.8.0 (P1)

8. **Search and Filter** (6 hours)
9. **Hover Tooltips** (4 hours)
10. **Mini-map Navigator** (3 hours)
11. **Export Capabilities** (6 hours)
12. **Keyboard Navigation** (6 hours)
13. **Accessibility** (8 hours)

### Nice to Have for v1.9.0+ (P2)

14. Drag-and-drop repositioning
15. Right-click context menus
16. WebSocket live updates
17. Alert notifications
18. Performance optimizations

---

## Effort Estimation

| Phase | Features | Hours | Days (8h) |
|-------|----------|-------|-----------|
| **Phase 1: Critical Fixes** | Items 1-7 (P0) | 47-60h | 6-7.5 days |
| **Phase 2: Polish** | Items 8-13 (P1) | 33h | 4 days |
| **Phase 3: Advanced** | Items 14-18 (P2) | 30h | 4 days |
| **Total** | | 110-123h | 14-15 days |

**Most Complex Item:** Message Trace Swimlanes (30 hours, includes backend)

---

## Recommended Implementation Order

### Week 1: Foundation (Days 1-5)

**Day 1:**
- [x] ✓ Rename Diagram → Topology
- [x] ✓ Fix layout (adaptive canvas sizing)
- [x] ✓ Fix node click behavior

**Day 2-3:**
- [ ] Implement detail panel framework
- [ ] Configuration tab
- [ ] Events tab (with API)

**Day 4:**
- [ ] Messages tab
- [ ] Metrics tab (with API)

**Day 5:**
- [ ] Implement table view
- [ ] Real-time polling updates

### Week 2: Swimlanes (Days 6-10)

**Day 6-7: Backend**
- [ ] Database schema (message_traces, message_trace_stages)
- [ ] Engine instrumentation (log each stage)
- [ ] API endpoint (/messages/:id/trace)

**Day 8-9: Frontend**
- [ ] Swimlane modal component
- [ ] Timeline rendering
- [ ] Stage indicators

**Day 10:**
- [ ] Message viewer
- [ ] Diff viewer
- [ ] Export functions

### Week 3: Polish (Days 11-14)

**Day 11:**
- [ ] Search and filter
- [ ] Hover tooltips

**Day 12:**
- [ ] Mini-map navigator
- [ ] Export (PNG, CSV)

**Day 13:**
- [ ] Keyboard navigation
- [ ] ARIA labels

**Day 14:**
- [ ] Testing (E2E, accessibility)
- [ ] Performance optimization
- [ ] Documentation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Swimlanes too complex** | Break into smaller components, iterate |
| **Backend not ready** | Mock API responses for frontend development |
| **Performance issues** | Implement virtualization early, load test |
| **User confusion** | User testing with hospital staff |
| **Scope creep** | Strict P0/P1/P2 prioritization |

---

## Success Criteria

### Release Readiness Checklist

**Functional:**
- [ ] Topology tab shows graph and table views
- [ ] Detail panel opens on node click with 4 tabs
- [ ] Message trace swimlanes visualize e2e journey
- [ ] Real-time status updates (10s polling)
- [ ] Search/filter works
- [ ] Export to CSV works

**Performance:**
- [ ] Load time < 2s for 50 items
- [ ] 60 FPS zoom/pan
- [ ] No memory leaks (tested 1h continuous use)

**Quality:**
- [ ] TypeScript strict mode, 0 `any` types in production
- [ ] 80% code coverage
- [ ] E2E tests pass
- [ ] Accessibility audit passes (WCAG AA)

**Documentation:**
- [ ] User guide published
- [ ] Developer docs updated
- [ ] API docs complete

---

## Conclusion

**Current State:** Phase 1 MVP (30% complete, basic visualization only)

**Gaps:** 70% of critical features missing, most notably:
1. Detail panel with tabs (CRITICAL)
2. Message trace swimlanes (CRITICAL)
3. Table view (CRITICAL)
4. Real-time updates (CRITICAL)
5. Adaptive layout (CRITICAL)

**Recommendation:** Proceed with 2-3 week implementation sprint focusing on P0 items. Message trace swimlanes are the most complex and should be tackled early with backend collaboration.

**Next Steps:**
1. Review and approve this gap analysis
2. Assign backend engineer for swimlanes instrumentation
3. Begin Phase 1 implementation (Days 1-5)
4. Weekly progress reviews

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-12 | System | Initial gap analysis |

**Reviewed By:**
- [ ] Product Owner
- [ ] Integration Engineering Lead
- [ ] Backend Lead
- [ ] UX Designer
