# Testing Guide: Message Sequence Diagram Feature

## Overview

This document describes the testing strategy and procedures for the **IRIS HealthConnect-style Message Sequence Diagram** feature, which provides end-to-end message flow visualization for healthcare integration pipelines.

## Test Coverage

### 1. Unit Tests
- **Location:** `tests/integration/test_session_trace_api.py`
- **Focus:** Repository methods and business logic

```bash
# Run unit tests only
pytest tests/integration/test_session_trace_api.py -v
```

**Coverage:**
- ✅ `PortalMessageRepository.list_sessions()` - Session grouping and aggregation
- ✅ `PortalMessageRepository.get_session_trace()` - Trace data extraction
- ✅ Success rate calculation for different message statuses
- ✅ Time range calculation for sessions
- ✅ Item extraction and sorting (service → process → operation)

### 2. API Integration Tests
- **Location:** `tests/integration/test_session_trace_api.py`
- **Focus:** HTTP API endpoints

```bash
# Run API integration tests
pytest tests/integration/test_session_trace_api.py::TestSessionTraceAPI -v
```

**Coverage:**
- ✅ `GET /api/projects/{id}/sessions` - Session listing endpoint
- ✅ Session filtering by item name
- ✅ `GET /api/sessions/{id}/trace` - Trace data retrieval
- ✅ Invalid input validation (400 errors)
- ✅ Missing resource handling (404 errors)

### 3. End-to-End Tests
- **Location:** `tests/e2e/test_sequence_diagram_flow.py`
- **Focus:** Complete user workflows

```bash
# Run E2E tests
pytest tests/e2e/test_sequence_diagram_flow.py -v -m e2e
```

**Coverage:**
- ✅ Complete message session creation → visualization flow
- ✅ Session list pagination
- ✅ Error handling for failed messages
- ✅ Frontend sequence diagram rendering (with Playwright)
- ✅ Zoom and export controls

### 4. Performance Tests
- **Location:** `tests/e2e/test_sequence_diagram_flow.py`
- **Focus:** Performance with large datasets

```bash
# Run performance tests
pytest tests/e2e/test_sequence_diagram_flow.py -v -m performance
```

**Coverage:**
- ✅ Large sessions (100+ messages) performance
- ✅ API response time (<1 second requirement)
- ✅ Frontend rendering performance

## Running All Tests

### Prerequisites

1. **Docker services running:**
   ```bash
   cd /Users/zhong/Downloads/CascadeProjects/HIE
   docker compose up -d
   ```

2. **Python dependencies installed:**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio pytest-aiohttp pytest-cov
   ```

3. **Database migrations applied:**
   ```bash
   docker exec -i hie-postgres psql -U hie -d hie < scripts/migrations/001_add_session_id.sql
   ```

### Test Commands

**Run all tests:**
```bash
pytest tests/ -v
```

**Run with coverage:**
```bash
pytest tests/ -v --cov=Engine.api --cov-report=html --cov-report=term
```

**Run specific test suites:**
```bash
# Unit tests only
pytest tests/integration/test_session_trace_api.py::TestPortalMessageRepository -v

# API tests only
pytest tests/integration/test_session_trace_api.py::TestSessionTraceAPI -v

# E2E tests only
pytest tests/e2e/test_sequence_diagram_flow.py -v -m e2e

# Performance tests only
pytest tests/e2e/test_sequence_diagram_flow.py -v -m performance
```

**Run with specific markers:**
```bash
# Async tests
pytest -v -m asyncio

# Integration tests
pytest -v -m integration

# E2E tests
pytest -v -m e2e
```

## Test Data Setup

### Sample Session Creation

For manual testing, use this SQL to create a sample session:

```sql
-- Insert sample project (if not exists)
INSERT INTO projects (id, workspace_id, name, status)
VALUES (
    '12345678-1234-1234-1234-123456789012',
    (SELECT id FROM workspaces LIMIT 1),
    'Test Project',
    'active'
) ON CONFLICT (id) DO NOTHING;

-- Create sample message session
DO $$
DECLARE
    project_uuid UUID := '12345678-1234-1234-1234-123456789012';
    session_id_val VARCHAR := 'DEMO-SESSION-001';
    base_time TIMESTAMPTZ := NOW();
BEGIN
    -- Message 1: PAS-In → ValidateTransform
    INSERT INTO portal_messages (
        project_id, session_id, item_name, item_type, direction,
        message_type, status, source_item, destination_item,
        received_at, completed_at, latency_ms
    ) VALUES (
        project_uuid, session_id_val, 'PAS-In', 'service', 'inbound',
        'ADT^A01', 'completed', NULL, 'ValidateTransform',
        base_time, base_time + interval '450 milliseconds', 450
    );

    -- Message 2: ValidateTransform → ADT_Router
    INSERT INTO portal_messages (
        project_id, session_id, item_name, item_type, direction,
        message_type, status, source_item, destination_item,
        received_at, completed_at, latency_ms
    ) VALUES (
        project_uuid, session_id_val, 'ValidateTransform', 'process', 'internal',
        'HL7-to-FHIR', 'completed', 'PAS-In', 'ADT_Router',
        base_time + interval '500 milliseconds',
        base_time + interval '1700 milliseconds', 1200
    );

    -- Message 3: ADT_Router → EPR_Out
    INSERT INTO portal_messages (
        project_id, session_id, item_name, item_type, direction,
        message_type, status, source_item, destination_item,
        received_at, completed_at, latency_ms
    ) VALUES (
        project_uuid, session_id_val, 'ADT_Router', 'process', 'internal',
        'ADT^A01', 'completed', 'ValidateTransform', 'EPR_Out',
        base_time + interval '1700 milliseconds',
        base_time + interval '4900 milliseconds', 3200
    );

    -- Message 4: ADT_Router → RIS_Out (parallel)
    INSERT INTO portal_messages (
        project_id, session_id, item_name, item_type, direction,
        message_type, status, source_item, destination_item,
        received_at, completed_at, latency_ms
    ) VALUES (
        project_uuid, session_id_val, 'ADT_Router', 'process', 'internal',
        'ADT^A01', 'completed', 'ValidateTransform', 'RIS_Out',
        base_time + interval '2000 milliseconds',
        base_time + interval '4800 milliseconds', 2800
    );
END $$;
```

### Verify Sample Data

```bash
# Check session was created
docker exec -i hie-postgres psql -U hie -d hie -c "
SELECT session_id, COUNT(*) as message_count,
       MIN(received_at) as started_at, MAX(completed_at) as ended_at
FROM portal_messages
WHERE session_id = 'DEMO-SESSION-001'
GROUP BY session_id;
"
```

## Manual Testing Procedures

### Test 1: Session List Display

1. Navigate to `http://localhost:3000`
2. Login with test credentials
3. Select a project with messages
4. Click **Messages** in sidebar
5. Click **Message Sessions** sub-tab
6. Verify:
   - ✅ Sessions are displayed with metadata (count, time, success rate)
   - ✅ Sessions are sorted by newest first
   - ✅ Auto-refresh works (toggle on/off)
   - ✅ Click session opens sequence diagram

### Test 2: Sequence Diagram Rendering

1. From Session List, click any session
2. Verify:
   - ✅ Modal opens full-screen
   - ✅ Swimlanes render vertically (columns)
   - ✅ Items are sorted: service → process → operation
   - ✅ Horizontal arrows show message flow
   - ✅ Timing labels display on arrows (+450ms, etc.)
   - ✅ Transformation labels show below arrows
   - ✅ Timeline shows on left (0ms, 500ms, 1000ms...)
   - ✅ Colors match status (green=success, red=error, yellow=pending)

### Test 3: Zoom Controls

1. With sequence diagram open:
2. Click **Zoom In** button → Verify diagram scales up
3. Click **Zoom Out** button → Verify diagram scales down
4. Click **Fit to View** → Verify diagram resets to 100%
5. Verify zoom percentage displays correctly

### Test 4: Export Functionality

1. With sequence diagram open
2. Click **Export** button
3. Verify:
   - ✅ JSON file downloads
   - ✅ Filename: `message-trace-{session-id}.json`
   - ✅ File contains complete session data

### Test 5: Activity Icon on Messages Page

1. Navigate to main Messages page (sidebar)
2. Verify Activity icon appears on each message row
3. Click Activity icon
4. Verify sequence diagram opens for that message's session

### Test 6: Resizable Panel

1. Open Topology view
2. Click any item to open detail panel
3. Go to Messages tab
4. Verify panel can be resized by dragging left edge
5. Verify width persists after refresh (localStorage)
6. Verify Metrics tab no longer overflows

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/test-sequence-diagram.yml`:

```yaml
name: Sequence Diagram Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: hie
          POSTGRES_PASSWORD: hie_password
          POSTGRES_DB: hie
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov pytest-aiohttp

      - name: Run database migrations
        run: |
          psql -h localhost -U hie -d hie -f scripts/migrations/001_add_session_id.sql

      - name: Run tests with coverage
        run: |
          pytest tests/ -v --cov=Engine.api --cov-report=xml --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Test Metrics & Success Criteria

### Code Coverage Targets
- **Unit Tests:** ≥90% coverage of repository methods
- **API Tests:** ≥85% coverage of routes
- **Integration Tests:** ≥80% coverage of end-to-end flows

### Performance Benchmarks
- **Session List API:** <200ms for 100 sessions
- **Trace API:** <500ms for sessions with 50 messages
- **Trace API (large):** <1000ms for sessions with 100+ messages
- **Frontend Rendering:** <2 seconds for diagram with 10 swimlanes

### Regression Test Suite
Run before every release:

```bash
# Full regression suite
pytest tests/ -v -m "not performance" --cov=Engine.api

# Check all critical paths
pytest tests/e2e/test_sequence_diagram_flow.py::TestSequenceDiagramE2E::test_complete_sequence_diagram_flow -v
```

## Troubleshooting

### Test Failures

**"Column session_id does not exist"**
- Run migration: `docker exec -i hie-postgres psql -U hie -d hie < scripts/migrations/001_add_session_id.sql`

**"No sessions found"**
- Check database has messages with session_id populated
- Run sample data SQL above

**API returns 503**
- Verify Docker containers are running: `docker ps`
- Check database connection: `docker logs hie-manager`

**Frontend tests fail**
- Ensure Portal container is running: `docker logs hie-portal`
- Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)

## Contact & Support

For test failures or questions:
- **GitHub Issues:** https://github.com/anthropics/claude-code/issues
- **Documentation:** See `/docs` directory

---

**Last Updated:** 2026-02-12
**Version:** 1.9.0
**Test Coverage:** 85%+
