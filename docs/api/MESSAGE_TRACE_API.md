# Message Trace API Specification

**Version**: 1.0
**Last Updated**: 2026-02-12
**Status**: Ready for Backend Implementation

## Overview

This document specifies the API endpoints required for the Message Trace Swimlanes feature in the Enterprise Topology Viewer. These endpoints enable end-to-end transaction tracking through the HIE integration engine.

---

## Database Schema

### Table: `message_traces`

Stores high-level information about message transactions.

```sql
CREATE TABLE message_traces (
  trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  message_id VARCHAR(255) NOT NULL UNIQUE,
  message_type VARCHAR(100) NOT NULL,
  started_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP,
  total_duration_ms INTEGER,
  status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_message_traces_session ON message_traces(session_id);
CREATE INDEX idx_message_traces_message_id ON message_traces(message_id);
CREATE INDEX idx_message_traces_started_at ON message_traces(started_at DESC);
CREATE INDEX idx_message_traces_status ON message_traces(status);
```

**Field Descriptions:**
- `trace_id`: Unique identifier for the trace
- `session_id`: Links to integration engine session
- `message_id`: Business message identifier (e.g., MSH-10 in HL7)
- `message_type`: Message type (e.g., "ADT^A01", "ORU^R01")
- `started_at`: When message entered the system
- `completed_at`: When message exited or failed (NULL if in progress)
- `total_duration_ms`: Total processing time in milliseconds
- `status`: `in_progress | success | error`
- `error_message`: Error description if status is 'error'

### Table: `message_trace_stages`

Stores individual processing stages for each message.

```sql
CREATE TABLE message_trace_stages (
  stage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id UUID NOT NULL REFERENCES message_traces(trace_id) ON DELETE CASCADE,
  item_id UUID NOT NULL REFERENCES project_items(id),
  sequence_number INTEGER NOT NULL,
  entered_at TIMESTAMP NOT NULL,
  exited_at TIMESTAMP,
  duration_ms INTEGER,
  queue_wait_ms INTEGER DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
  input_message TEXT,
  output_message TEXT,
  transformation VARCHAR(255),
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_message_trace_stages_trace ON message_trace_stages(trace_id, sequence_number);
CREATE INDEX idx_message_trace_stages_item ON message_trace_stages(item_id);
CREATE INDEX idx_message_trace_stages_entered_at ON message_trace_stages(entered_at);
```

**Field Descriptions:**
- `stage_id`: Unique identifier for the stage
- `trace_id`: References parent trace
- `item_id`: ID of the project item (service/process/operation)
- `sequence_number`: Order in the pipeline (1, 2, 3...)
- `entered_at`: When message entered this stage
- `exited_at`: When message exited this stage (NULL if in progress)
- `duration_ms`: Time spent in this stage
- `queue_wait_ms`: Time spent waiting in queue before processing
- `status`: `in_progress | success | error`
- `input_message`: Message content at stage entry
- `output_message`: Message content at stage exit (after transformation)
- `transformation`: Name of transformation applied (if any)
- `error_message`: Error description if stage failed

---

## API Endpoints

### 1. Get Message Trace

Retrieves complete trace information for a specific message.

**Endpoint:** `GET /api/projects/:projectId/messages/:messageId/trace`

**Path Parameters:**
- `projectId` (UUID): Project identifier
- `messageId` (string): Message identifier

**Response:** `200 OK`

```typescript
{
  "trace": {
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "660e8400-e29b-41d4-a716-446655440001",
    "message_id": "MSG-20240210-001",
    "message_type": "ADT^A01",
    "started_at": "2024-02-10T12:00:00.000Z",
    "completed_at": "2024-02-10T12:00:02.450Z",
    "total_duration_ms": 2450,
    "status": "success",
    "error_message": null
  },
  "stages": [
    {
      "stage_id": "770e8400-e29b-41d4-a716-446655440002",
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "item_id": "880e8400-e29b-41d4-a716-446655440003",
      "item_name": "HL7.In.PAS",
      "item_type": "service",
      "sequence_number": 1,
      "entered_at": "2024-02-10T12:00:00.000Z",
      "exited_at": "2024-02-10T12:00:00.450Z",
      "duration_ms": 450,
      "queue_wait_ms": 0,
      "status": "success",
      "input_message": "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.4\n...",
      "output_message": "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.4\n...",
      "transformation": null,
      "error_message": null
    },
    {
      "stage_id": "990e8400-e29b-41d4-a716-446655440004",
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "item_id": "aa0e8400-e29b-41d4-a716-446655440005",
      "item_name": "Process.Transform.v23_to_v251",
      "item_type": "process",
      "sequence_number": 2,
      "entered_at": "2024-02-10T12:00:00.450Z",
      "exited_at": "2024-02-10T12:00:01.650Z",
      "duration_ms": 1200,
      "queue_wait_ms": 150,
      "status": "success",
      "input_message": "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.4",
      "output_message": "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.5.1",
      "transformation": "custom.transforms.hl7.v23_to_v251",
      "error_message": null
    },
    {
      "stage_id": "bb0e8400-e29b-41d4-a716-446655440006",
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "item_id": "cc0e8400-e29b-41d4-a716-446655440007",
      "item_name": "HL7.Out.EPR",
      "item_type": "operation",
      "sequence_number": 3,
      "entered_at": "2024-02-10T12:00:01.650Z",
      "exited_at": "2024-02-10T12:00:02.450Z",
      "duration_ms": 800,
      "queue_wait_ms": 50,
      "status": "success",
      "input_message": "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.5.1",
      "output_message": "MSH|^~\\&|HIE|HIE|EPR|HOSP|20240210120001||ADT^A01|MSG001|P|2.5.1\nMSA|AA|MSG001",
      "transformation": null,
      "error_message": null
    }
  ]
}
```

**Error Responses:**

```typescript
// 404 Not Found - Message trace doesn't exist
{
  "error": "Trace not found",
  "message": "No trace exists for message ID: MSG-20240210-001",
  "code": "TRACE_NOT_FOUND"
}

// 403 Forbidden - User doesn't have access to this project
{
  "error": "Forbidden",
  "message": "You don't have permission to access this project",
  "code": "INSUFFICIENT_PERMISSIONS"
}

// 500 Internal Server Error
{
  "error": "Internal server error",
  "message": "Failed to retrieve message trace",
  "code": "INTERNAL_ERROR"
}
```

---

### 2. List Recent Traces

Lists recent message traces for a project or specific item.

**Endpoint:** `GET /api/projects/:projectId/traces`

**Path Parameters:**
- `projectId` (UUID): Project identifier

**Query Parameters:**
- `item_id` (UUID, optional): Filter by specific item
- `status` (string, optional): Filter by status (`success | error | in_progress`)
- `message_type` (string, optional): Filter by message type
- `from` (ISO 8601, optional): Start date filter
- `to` (ISO 8601, optional): End date filter
- `limit` (integer, optional, default: 50, max: 500): Number of results
- `offset` (integer, optional, default: 0): Pagination offset

**Response:** `200 OK`

```typescript
{
  "traces": [
    {
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "message_id": "MSG-20240210-001",
      "message_type": "ADT^A01",
      "started_at": "2024-02-10T12:00:00.000Z",
      "completed_at": "2024-02-10T12:00:02.450Z",
      "total_duration_ms": 2450,
      "status": "success",
      "stage_count": 3
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

---

### 3. Export Trace Data

Exports trace data in various formats (JSON, CSV, PDF).

**Endpoint:** `GET /api/projects/:projectId/messages/:messageId/trace/export`

**Query Parameters:**
- `format` (string, required): Export format (`json | csv | pdf`)

**Response:**
- **JSON**: `200 OK` with `Content-Type: application/json`
- **CSV**: `200 OK` with `Content-Type: text/csv`
- **PDF**: `200 OK` with `Content-Type: application/pdf`

---

## Integration Engine Instrumentation

To populate the message trace tables, the integration engine must be instrumented to log events at key points:

### Required Instrumentation Points

1. **Message Received** (Service Items)
   ```python
   # When message enters service
   trace_id = create_message_trace(
       session_id=session.id,
       message_id=extract_message_id(message),
       message_type=extract_message_type(message)
   )

   create_trace_stage(
       trace_id=trace_id,
       item_id=service.id,
       sequence_number=1,
       input_message=message
   )
   ```

2. **Stage Entry** (All Items)
   ```python
   # When message enters processing queue
   update_trace_stage(
       stage_id=stage.id,
       queue_wait_ms=calculate_queue_wait()
   )
   ```

3. **Stage Exit** (All Items)
   ```python
   # When processing completes
   complete_trace_stage(
       stage_id=stage.id,
       output_message=transformed_message,
       transformation=transformation_name,
       status="success" | "error",
       error_message=error if failed
   )
   ```

4. **Message Completed**
   ```python
   # When message exits system
   complete_message_trace(
       trace_id=trace_id,
       status="success" | "error"
   )
   ```

---

## Performance Considerations

### Database Indexes
- Primary indexes on `trace_id`, `message_id`, `session_id`
- Composite index on `(trace_id, sequence_number)` for stage ordering
- Index on `started_at` for time-based queries
- Index on `status` for filtering

### Data Retention
- **Hot Data**: Last 30 days - full content stored
- **Warm Data**: 30-90 days - message content archived, metadata retained
- **Cold Data**: 90+ days - compressed archive
- **Purge**: After 1 year (configurable)

### Archival Strategy
```sql
-- Archive old message content
UPDATE message_trace_stages
SET input_message = NULL, output_message = NULL
WHERE entered_at < NOW() - INTERVAL '90 days';
```

### Query Optimization
- Use pagination for list endpoints
- Implement caching for frequently accessed traces
- Consider read replicas for trace queries
- Use connection pooling

---

## Security Considerations

### Data Protection
- **PHI/PII**: Message content may contain protected health information
- **Encryption**: Encrypt `input_message` and `output_message` columns at rest
- **Access Control**: Enforce project-level permissions
- **Audit Logging**: Log all trace access attempts

### Authentication
- Require valid session token
- Verify user has read access to project
- Rate limiting: 100 requests/minute per user

---

## Testing Requirements

### Unit Tests
- Trace creation and retrieval
- Stage lifecycle management
- Error handling scenarios
- Data validation

### Integration Tests
- End-to-end message flow tracking
- Concurrent trace updates
- Query performance with large datasets

### Load Tests
- 1000 concurrent traces
- 10,000 stages per trace
- Query response time < 500ms

---

## Implementation Checklist

- [ ] Create database tables and indexes
- [ ] Implement trace creation endpoint
- [ ] Implement stage tracking functions
- [ ] Add instrumentation to integration engine
- [ ] Implement GET /trace endpoint
- [ ] Implement GET /traces list endpoint
- [ ] Add export functionality
- [ ] Configure data retention policies
- [ ] Set up archival jobs
- [ ] Implement encryption for message content
- [ ] Add comprehensive logging
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Performance testing
- [ ] Security audit
- [ ] Documentation review

---

## Frontend Integration

The frontend is **ready** to consume this API. Key integration points:

1. **MessageTraceSwimlane Component**: `/Portal/src/components/ProductionDiagram/MessageTraceSwimlane.tsx`
2. **API Call Location**: `fetchTraceData()` function (line ~35)
3. **Mock Data**: Currently using `generateMockTraceData()` for demonstration

**To Enable:**
Replace mock call with:
```typescript
const response = await fetch(`/api/projects/${projectId}/messages/${messageId}/trace`);
const data = await response.json();
setTrace(data.trace);
setStages(data.stages);
```

---

## Support

For questions or issues, contact the HIE Platform Team.

**Document Owner**: Enterprise Integration Team
**Reviewers**: Backend Team, Security Team, DBA Team
