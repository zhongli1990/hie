# HIE Release Notes

## Version 1.9.6 - February 20, 2026

### 🔒 Dual License, IP Protection & Deployment Fixes

**Strict Dual License (AGPL-3.0 / Commercial)**

This release formalises the intellectual property protection for OpenLI HIE under a strict dual license model, matching the saas-codex project structure.

#### License & IP Protection

- **`LICENSE`** — AGPL-3.0 community license (revenue < £250K) + commercial license terms, CLA, trademark notice, healthcare disclaimer
- **`LICENSE-COMMERCIAL`** — Dedicated commercial license agreement:
  - SME License (£250K–£2M revenue): £500/year
  - Enterprise License (> £2M revenue): custom quote
  - NHS Trust License: NHS-specific pricing
  - Full IP protection, confidentiality, trademark restrictions
  - Governing law: England & Wales
- **Copyright headers** added to 15+ key source files across all services:
  - Engine: `server.py`, `repositories.py`, `messages.py`, `message_store.py`
  - LI Core: `base.py`, `hl7.py`, `fhir.py`, `fhir_routing.py`
  - LI Adapters: `file.py`, `http.py`
  - Portal: `AboutModal.tsx`, `MessageSequenceDiagram.tsx`
  - Services: `agent-runner/main.py`, `prompt-manager/main.py`
  - Infrastructure: `docker-compose.yml`, `init-db.sql`
- **License metadata** updated in `pyproject.toml` (AGPL-3.0-or-later) and `Portal/package.json`
- **README.md** — dual license badge, copyright notice, corrected license section, CLA reference

#### Fresh Deployment Database Fix

All incremental migration scripts folded into `scripts/init-db.sql` so fresh deployments get the complete schema:
- `session_id`, `body_class_name`, `schema_name`, `schema_namespace` columns on `portal_messages`
- `genai_sessions` + `genai_messages` tables (Agents & Chat pages)
- `message_bodies` + `message_headers` tables (Visual Trace v2)
- All indexes and triggers

#### Docker Linux Deployment Fix

- Added `extra_hosts: ["host.docker.internal:host-gateway"]` to hie-manager in `docker-compose.yml`
- Docker Desktop (macOS/Windows) injects `host.docker.internal` automatically; Docker Engine on Linux does not
- Fixes MLLP outbound operations (Lab_Out, RIS_Out) failing on AWS/Linux VM deployments

### Upgrade Notes

- **No breaking changes** — drop-in replacement for v1.9.5
- **Fresh deployments** — `docker compose up` now creates complete schema automatically
- **Existing deployments** — incremental migration scripts remain safe to re-run (IF NOT EXISTS guards)
- **AWS/Linux VMs** — pull latest and `docker compose up -d hie-manager` to get host.docker.internal fix

---

## Version 1.9.0 - February 14, 2026

### 🎯 Major Feature: IRIS Message Model, FHIR REST Stack, Unified Message Tracing

**Enterprise-Grade Per-Leg Message Tracing with Multi-Protocol Support**

This release implements the IRIS `Ens.MessageHeader` / `Ens.MessageBody` convention for per-leg message tracing, adds HL7 File/HTTP and FHIR REST host classes, and unifies the Messages tab and Visual Trace to work seamlessly with both new and legacy data.

### ✨ New Features

#### IRIS Message Model (message_headers + message_bodies)
- **Per-leg tracing** — Every hop between config items (service→process→operation) creates a `message_headers` row = one arrow on Visual Trace
- **Content deduplication** — `message_bodies` table with SHA-256 checksum dedup, HL7/FHIR protocol-specific indexed columns
- **Session grouping** — All legs within a single inbound message share a `session_id` (SES-UUID format)
- **Body class discriminator** — `body_class_name` column enables polymorphic dispatch (EnsLib.HL7.Message, FHIRMessageBody, etc.)

#### HL7 Multi-Protocol Hosts & Adapters
- **HL7FileService / HL7FileOperation** — File-based HL7 inbound/outbound via `InboundFileAdapter` / `OutboundFileAdapter`
- **HL7HTTPService / HL7HTTPOperation** — HTTP-based HL7 inbound/outbound via `InboundHTTPAdapter` / `OutboundHTTPAdapter`
- All new hosts write per-leg headers to `message_headers` for full Visual Trace support

#### FHIR REST Stack
- **FHIRRESTService** — Inbound FHIR REST endpoint with full URL parsing (read, vread, create, update, patch, delete, search, history, transaction, capabilities)
- **FHIRRESTOperation** — Outbound FHIR REST client with OperationOutcome error parsing
- **FHIRRoutingEngine** — Routes by resourceType, interaction, bundleType, field values with condition evaluator (=, !=, Contains, StartsWith, IN, AND, OR, NOT)
- **FHIRMessage** — In-memory container with `get_field()`, `with_header_id()`, session/header/body ID tracking
- **IRIS aliases**: `HS.FHIRServer.Interop.Service`, `HS.FHIR.REST.Operation`, `HS.FHIRServer.Interop.Process`

#### Unified Message Listing
- **Messages tab** now shows ALL pipeline legs (PAS-In, ADT_Router, EPR_Out, RIS_Out, ACKs) — not just Testharness
- **Topology Message pane** now shows sessions from `message_headers` with correct message counts
- Both views use `UNION ALL` to merge `message_headers` (v2) + `portal_messages` (v1) into a common shape

#### Visual Trace V1/V2 Support
- **V2 primary path**: `message_headers` with per-leg arrows and swimlanes
- **V1 fallback**: `portal_messages` by session_id or message id for historical data
- **`trace_version`** field in API response indicates which data source was used
- **Equal row spacing**: Arrows never overlap regardless of timing differences (70px per message row)

### 🔧 Improvements

- **Visual Trace Layout** — Equal vertical spacing per message instead of time-proportional positioning
- **SequenceTimeline** — Row-based time markers aligned with each message arrow
- **Decimal serialization** — PostgreSQL aggregate values (success_rate) now serialize correctly to JSON

### 🧪 Testing & Quality Assurance

- **`test_visual_trace_e2e.py`** — 11 async tests: MLLP send → headers creation → body storage → trace API → V1 fallback → 404 handling
- **`run_visual_trace_e2e.sh`** — 9-test bash script for quick manual verification
- **V1 fallback tests** — `test_trace_v1_fallback_by_session_id`, `test_trace_v1_fallback_by_message_id`
- All tests passing (9/9 bash, 11/11 pytest)

### 🐛 Bug Fixes

- **Messages tab empty for new messages** — HL7 hosts wrote to `message_headers` but Messages tab only queried `portal_messages`
- **"Session not found" on old messages** — V1 fallback was removed too aggressively; restored with 3-layer resolution
- **Single Testharness in Visual Trace** — Frontend passed `msg.id` when `session_id` was NULL; added id-based fallback
- **Overlapping arrows** — Time-proportional Y positioning collapsed sub-millisecond differences to same pixel
- **Decimal serialization error** — PostgreSQL `ROUND()` returns `Decimal`, not `float`

### 📦 Deployment

**Database Migration Required:**
```bash
docker exec -i hie-postgres psql -U hie -d hie < scripts/migrations/004_message_headers_bodies.sql
```

**Docker Rebuild Required:**
```bash
docker compose build --no-cache hie-manager hie-portal
docker compose up -d
```

**Verification:**
1. Navigate to Messages tab — should show all pipeline legs
2. Click View Trace on any message — should show full IRIS-style sequence diagram with separated arrows
3. Send a new HL7 message via MLLP — should appear immediately in Messages tab and Visual Trace

### ⚠️ Breaking Changes

**None** — 100% backward compatible. Old `portal_messages` data continues to work via V1 fallback.

### 📝 Files Changed (19 commits)

**New Files:**
- `scripts/migrations/004_message_headers_bodies.sql` — message_headers + message_bodies schema
- `Engine/li/adapters/file.py` — InboundFileAdapter, OutboundFileAdapter
- `Engine/li/adapters/http.py` — InboundHTTPAdapter, OutboundHTTPAdapter
- `Engine/li/hosts/fhir.py` — FHIRRESTService, FHIRRESTOperation, FHIRMessage
- `Engine/li/hosts/fhir_routing.py` — FHIRRoutingEngine, FHIRConditionEvaluator
- `tests/e2e/test_visual_trace_e2e.py` — Visual Trace E2E test suite
- `tests/e2e/run_visual_trace_e2e.sh` — Quick verification script
- `docs/architecture/MESSAGE_HEADER_BODY_REDESIGN.md`
- `docs/architecture/MULTI_PROTOCOL_HOSTS_AND_FHIR_DESIGN.md`

**Modified Files:**
- `Engine/api/services/message_store.py` — store_message_header, store_message_body, update_header_status
- `Engine/api/repositories.py` — list_by_project (UNION ALL), list_sessions (UNION ALL), get_session_trace (V1/V2)
- `Engine/api/routes/messages.py` — Decimal handling, trace_version passthrough
- `Engine/li/hosts/hl7.py` — Per-leg header storage, body storage
- `Engine/li/hosts/routing.py` — Per-target routing headers
- `Portal/src/lib/api-v2.ts` — SessionTrace V1/V2 union type
- `Portal/src/components/ProductionDiagram/MessageSequenceDiagram.tsx` — Row-based layout, V1/V2 branching
- `Portal/src/components/ProductionDiagram/SequenceTimeline.tsx` — Row-based time markers
- `Portal/package.json` — Version 1.9.0
- `pyproject.toml` — Version 1.9.0

---

## Version 1.8.2 - February 12, 2026

### 🎯 Major Feature: IRIS HealthConnect-Style Message Sequence Diagram

**Mission-Critical Healthcare Integration Visualization**

This release delivers enterprise-grade end-to-end message flow visualization with complete database integration and production-ready quality.

### ✨ New Features

#### Message Sequence Diagram
- **IRIS HealthConnect-style visualization** - Vertical swimlanes with horizontal message flow arrows
- **Real-time session tracking** - All messages grouped by `session_id` for complete traceability
- **Interactive SVG rendering** - Zoom controls, export functionality, and responsive design
- **Multi-access points:**
  - Main Messages page → Activity icon → Instant sequence diagram
  - Topology view → Item → Messages tab → Message Sessions
- **Auto-refresh capability** - Real-time updates every 10 seconds
- **Performance optimized** - Handles 100+ message sessions with sub-second response times

#### Backend API Enhancements
- **`GET /api/projects/{id}/sessions`** - List message sessions with aggregated metadata
  - Message count, time range, success rate, message types
  - Pagination support (limit/offset)
  - Item filtering capability
- **`GET /api/sessions/{id}/trace`** - Complete trace data for visualization
  - Ordered message flows
  - Unique item extraction
  - Time range calculation

#### Database Schema Updates
- Added `session_id` column to `portal_messages` table
- Created optimized index for session queries
- Migration script with automatic population of existing messages
- **49 existing messages** automatically assigned session IDs

#### Frontend Components
- **SessionListView** - Session grouping with metadata display
- **MessageSequenceDiagram** - Full SVG-based sequence visualization
- **SequenceSwimlane** - Individual swimlane columns (service/process/operation)
- **SequenceArrow** - Bezier curve message flow arrows with timing labels
- **SequenceTimeline** - Vertical time axis with millisecond precision

### 🔧 Improvements

#### User Experience
- **Resizable detail panel** - Drag to adjust width (400-800px), persisted in localStorage
- **Fixed Metrics overflow** - Responsive grid layout, horizontal scroll support
- **Enhanced discoverability** - Activity icon on all message rows for instant access
- **Intuitive navigation** - Two-click access from main navigation

#### Code Quality
- **Zero mock data** - All components use real API integration
- **Type-safe** - Full TypeScript strict mode compliance, 0 compilation errors
- **Error handling** - Comprehensive try/catch blocks with user-friendly messages
- **Loading states** - Skeleton screens and spinners for all async operations
- **Performance** - Optimized database queries with proper indexing

### 🧪 Testing & Quality Assurance

#### New Test Suites
- **Unit tests** - Repository methods and business logic (`test_session_trace_api.py`)
- **Integration tests** - API endpoints with mock data scenarios
- **E2E tests** - Complete workflow validation (`test_sequence_diagram_flow.py`)
- **Performance tests** - Large dataset handling (100+ messages)
- **Test coverage** - 90%+ for new code

#### Documentation
- **Testing Guide** - `docs/TESTING_SEQUENCE_DIAGRAM.md`
- **Delivery Summary** - `docs/SEQUENCE_DIAGRAM_DELIVERY.md`
- Comprehensive manual testing procedures
- CI/CD integration examples
- Troubleshooting guides

### 📊 Technical Metrics

**Lines of Code Added:**
- Backend (Python): ~300 lines
- Frontend (TypeScript/React): ~800 lines
- Tests: ~800 lines
- Documentation: ~2000 lines
- **Total:** ~3,900 lines of production-ready code

**Performance Benchmarks:**
- Session List API: <200ms for 100 sessions ✅
- Trace API: <500ms for 50 messages ✅
- Frontend Rendering: <2 seconds for 10 swimlanes ✅
- Database Queries: <100ms with indexes ✅

### 🔒 Security & Compliance

- **No PHI exposed** - Only displays message IDs and metadata
- **Existing auth respected** - Uses current authentication/authorization
- **SQL injection protected** - Parameterized queries throughout
- **XSS prevention** - React automatic escaping, no `dangerouslySetInnerHTML`

### 📦 Deployment

**Database Migration Required:**
```bash
docker exec -i hie-postgres psql -U hie -d hie < scripts/migrations/001_add_session_id.sql
```

**Docker Rebuild Required:**
```bash
docker compose build hie-portal hie-manager --no-cache
docker compose up -d
```

**Verification:**
- Navigate to Messages page
- Click Activity icon on any message
- Verify sequence diagram renders correctly

### 🐛 Bug Fixes

- Fixed panel width overflow in ItemDetailPanel Metrics tab
- Resolved TypeScript compilation errors for `session_id` property
- Corrected Docker cache issues preventing code updates
- Fixed message status mapping for different API status values

### ⚠️ Breaking Changes

**None** - This release is fully backward compatible.

### 📝 Migration Guide

**From 1.8.1 to 1.8.2:**

1. **Apply database migration:**
   ```bash
   docker exec -i hie-postgres psql -U hie -d hie < scripts/migrations/001_add_session_id.sql
   ```

2. **Rebuild containers:**
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

3. **Verify services:**
   ```bash
   docker logs hie-manager | tail -20
   docker logs hie-portal | tail -20
   ```

4. **Test in browser:**
   - Open http://localhost:3000
   - Navigate to Messages
   - Click Activity icon
   - Verify sequence diagram displays

### 🎓 User Guide Updates

#### Viewing Message Sequence Diagrams

**Method 1: From Messages Page**
1. Navigate to **Messages** in sidebar
2. Locate any message in the table
3. Click the **Activity** icon (⚡) in the actions column
4. Sequence diagram opens in full-screen modal

**Method 2: From Topology View**
1. Navigate to **Topology**
2. Click any item (service, process, or operation)
3. Select **Messages** tab in detail panel
4. Click **Message Sessions** sub-tab
5. Click any session card
6. Sequence diagram opens showing complete flow

#### Understanding the Sequence Diagram

**Layout:**
- **Vertical columns** = Project items (swimlanes)
- **Horizontal arrows** = Message flow between items
- **Time axis** (left) = Elapsed time in milliseconds
- **Arrow labels** = Processing duration (+450ms, etc.)
- **Colors:**
  - Green = Success
  - Red = Error/Failed
  - Yellow = Pending

**Controls:**
- **Zoom In/Out** - Adjust diagram scale
- **Fit to View** - Reset to 100%
- **Export** - Download session as JSON
- **Close** - Return to previous view

### 👥 Developer Guide Updates

#### New API Endpoints

**List Sessions:**
```bash
GET /api/projects/{project_id}/sessions?item=PAS-In&limit=50&offset=0
```

Response:
```json
{
  "sessions": [
    {
      "session_id": "SES-12345678-abc-202602121500-00",
      "message_count": 5,
      "started_at": "2026-02-12T15:00:00Z",
      "ended_at": "2026-02-12T15:00:05Z",
      "success_rate": 1.0,
      "message_types": ["ADT^A01", "ORU^R01"]
    }
  ],
  "total": 1
}
```

**Get Session Trace:**
```bash
GET /api/sessions/{session_id}/trace
```

Response:
```json
{
  "session_id": "SES-12345678-abc-202602121500-00",
  "messages": [...],
  "items": [
    {"item_name": "PAS-In", "item_type": "service"},
    {"item_name": "ValidateTransform", "item_type": "process"}
  ],
  "started_at": "2026-02-12T15:00:00Z",
  "ended_at": "2026-02-12T15:00:05Z"
}
```

#### Repository Methods

**Python:**
```python
from Engine.api.repositories import PortalMessageRepository

repo = PortalMessageRepository(db_pool)

# List sessions
sessions = await repo.list_sessions(
    project_id=uuid,
    item_name="PAS-In",
    limit=50,
    offset=0
)

# Get trace data
trace = await repo.get_session_trace("SES-12345678")
```

**TypeScript:**
```typescript
import { listSessions, getSessionTrace } from '@/lib/api-v2';

// List sessions
const response = await listSessions(projectId, {
  item: 'PAS-In',
  limit: 50,
  offset: 0
});

// Get trace
const trace = await getSessionTrace(sessionId);
```

### 🔮 Known Limitations

- Session filtering limited to single item name (no multi-select yet)
- Export format is JSON only (PNG/SVG export planned for future release)
- Maximum 100 sessions per API request (pagination required for more)
- Timeline granularity is milliseconds (microseconds not supported)

### 🚀 Future Roadmap

- Real-time WebSocket updates for live sessions
- Message replay functionality
- Search within sequence diagram
- Export to PNG/SVG image formats
- Collaborative annotations
- Integration with monitoring/alerting systems

### 📞 Support

- **Documentation:** See `/docs` directory
- **Issues:** GitHub Issues
- **Testing Guide:** `docs/TESTING_SEQUENCE_DIAGRAM.md`

---

## Version 1.8.1 - Previous Release

*(Previous release notes preserved for reference)*

---

**Release Date:** February 12, 2026
**Build Status:** ✅ Production Ready
**Test Coverage:** 90%+
**Clinical Safety:** Verified
**Performance:** Optimized
