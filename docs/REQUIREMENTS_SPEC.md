# HIE Requirements Specification

## Healthcare Integration Engine - Technical Requirements

**Version:** 0.2.0  
**Last Updated:** January 21, 2026  
**Status:** User Management & Authentication Release

---

## 1. Functional Requirements

### 1.1 Production Management

#### FR-1.1.1 Production Lifecycle
- **REQ-001:** System SHALL support creating new productions via configuration files
- **REQ-002:** System SHALL support starting, stopping, pausing, and resuming productions
- **REQ-003:** System SHALL validate production configuration before starting
- **REQ-004:** System SHALL support graceful shutdown with configurable timeout
- **REQ-005:** System SHALL persist production state across restarts

#### FR-1.1.2 Production Configuration
- **REQ-006:** System SHALL support JSON configuration format for productions
- **REQ-007:** System SHALL support YAML configuration format for productions
- **REQ-008:** System SHALL validate configuration against defined schema
- **REQ-009:** System SHALL support configuration import/export
- **REQ-010:** System SHALL support configuration versioning

### 1.2 Item Management

#### FR-1.2.1 Item Types
- **REQ-011:** System SHALL support Business Services (Receivers) for inbound messages
- **REQ-012:** System SHALL support Business Processes (Processors) for message transformation
- **REQ-013:** System SHALL support Business Operations (Senders) for outbound messages
- **REQ-014:** System SHALL support custom item types via plugin mechanism

#### FR-1.2.2 Item Configuration
- **REQ-015:** System SHALL support unique item identifiers within a production
- **REQ-016:** System SHALL support item-specific configuration settings
- **REQ-017:** System SHALL support item enable/disable without removal
- **REQ-018:** System SHALL support configurable worker pool size per item
- **REQ-019:** System SHALL support configurable queue size per item
- **REQ-020:** System SHALL support configurable timeout per item

#### FR-1.2.3 Item Lifecycle
- **REQ-021:** System SHALL support individual item start/stop/pause/resume
- **REQ-022:** System SHALL track item state (created, starting, running, paused, stopping, stopped, error)
- **REQ-023:** System SHALL support automatic item restart on failure (configurable)
- **REQ-024:** System SHALL report item health status

### 1.3 Route Management

#### FR-1.3.1 Route Definition
- **REQ-025:** System SHALL support defining routes as ordered sequences of items
- **REQ-026:** System SHALL support route-level filtering based on message content
- **REQ-027:** System SHALL support multiple filter operators (equals, contains, regex, etc.)
- **REQ-028:** System SHALL support AND/OR logic for multiple filters
- **REQ-029:** System SHALL support error handler item per route
- **REQ-030:** System SHALL support dead letter queue per route

#### FR-1.3.2 Route Execution
- **REQ-031:** System SHALL execute routes asynchronously
- **REQ-032:** System SHALL support ordered message delivery (optional per route)
- **REQ-033:** System SHALL track message progress through route
- **REQ-034:** System SHALL support route-level timeout

### 1.4 Message Handling

#### FR-1.4.1 Message Model
- **REQ-035:** System SHALL separate message envelope (metadata) from payload (content)
- **REQ-036:** System SHALL preserve raw message content end-to-end
- **REQ-037:** System SHALL assign unique identifier to each message
- **REQ-038:** System SHALL support correlation ID for related messages
- **REQ-039:** System SHALL support causation ID for message lineage
- **REQ-040:** System SHALL support message priority levels
- **REQ-041:** System SHALL support message TTL/expiration
- **REQ-042:** System SHALL support typed message properties

#### FR-1.4.2 Message Processing
- **REQ-043:** System SHALL support at-least-once delivery guarantee
- **REQ-044:** System SHALL support configurable retry count and delay
- **REQ-045:** System SHALL support message transformation via scripts
- **REQ-046:** System SHALL parse messages only when explicitly required
- **REQ-047:** System SHALL support message serialization (MsgPack, JSON)

### 1.5 Protocol Support

#### FR-1.5.1 Inbound Protocols
- **REQ-048:** System SHALL support HTTP/REST inbound
- **REQ-049:** System SHALL support file system watching inbound
- **REQ-050:** System SHALL support MLLP inbound (HL7 over TCP)
- **REQ-051:** System SHALL support configurable content type validation

#### FR-1.5.2 Outbound Protocols
- **REQ-052:** System SHALL support MLLP outbound with ACK handling
- **REQ-053:** System SHALL support file system outbound
- **REQ-054:** System SHALL support HTTP/REST outbound
- **REQ-055:** System SHALL support connection pooling for outbound

### 1.6 Management Portal

#### FR-1.6.1 Dashboard
- **REQ-056:** Portal SHALL display production status overview
- **REQ-057:** Portal SHALL display real-time message statistics
- **REQ-058:** Portal SHALL display system health indicators
- **REQ-059:** Portal SHALL display recent activity feed

#### FR-1.6.2 Production Editor
- **REQ-060:** Portal SHALL support visual production configuration
- **REQ-061:** Portal SHALL support drag-drop item placement
- **REQ-062:** Portal SHALL support visual route definition
- **REQ-063:** Portal SHALL support item configuration forms
- **REQ-064:** Portal SHALL support configuration validation
- **REQ-065:** Portal SHALL support configuration export/import

#### FR-1.6.3 Message Viewer
- **REQ-066:** Portal SHALL support message search by criteria
- **REQ-067:** Portal SHALL display message details (envelope and payload)
- **REQ-068:** Portal SHALL support message trace visualization
- **REQ-069:** Portal SHALL support message resend/replay

#### FR-1.6.4 Administration
- **REQ-070:** Portal SHALL support user management
- **REQ-071:** Portal SHALL support role-based access control
- **REQ-072:** Portal SHALL display audit log

### 1.7 Persistence

#### FR-1.7.1 Message Storage
- **REQ-073:** System SHALL support in-memory message storage
- **REQ-074:** System SHALL support PostgreSQL message storage
- **REQ-075:** System SHALL support Redis message caching
- **REQ-076:** System SHALL support configurable message retention

#### FR-1.7.2 State Storage
- **REQ-077:** System SHALL persist item state
- **REQ-078:** System SHALL persist route state
- **REQ-079:** System SHALL support state recovery after restart

---

## 2. Non-Functional Requirements

### 2.1 Performance

- **NFR-001:** System SHALL process minimum 10,000 messages/second per node
- **NFR-002:** System SHALL achieve average latency <10ms for local processing
- **NFR-003:** System SHALL achieve 95th percentile latency <50ms
- **NFR-004:** System SHALL support messages up to 10MB in size
- **NFR-005:** System SHALL support 1,000+ concurrent connections

### 2.2 Reliability

- **NFR-006:** System SHALL achieve 99.99% availability target
- **NFR-007:** System SHALL recover from failures within 30 seconds
- **NFR-008:** System SHALL not lose messages during graceful shutdown
- **NFR-009:** System SHALL support automatic failover (clustered mode)
- **NFR-010:** System SHALL maintain message ordering when configured

### 2.3 Scalability

- **NFR-011:** System SHALL support horizontal scaling
- **NFR-012:** System SHALL support vertical scaling (more workers per item)
- **NFR-013:** System SHALL support 100+ items per production
- **NFR-014:** System SHALL support 50+ routes per production
- **NFR-015:** System SHALL support 1M+ messages in storage

### 2.4 Security

- **NFR-016:** System SHALL encrypt data in transit (TLS 1.2+)
- **NFR-017:** System SHALL support authentication for management API
- **NFR-018:** System SHALL support role-based authorization
- **NFR-019:** System SHALL log all administrative actions
- **NFR-020:** System SHALL not log sensitive message content by default

### 2.5 Maintainability

- **NFR-021:** System SHALL provide structured logging (JSON)
- **NFR-022:** System SHALL expose Prometheus-compatible metrics
- **NFR-023:** System SHALL support health check endpoints
- **NFR-024:** System SHALL provide comprehensive API documentation
- **NFR-025:** System SHALL achieve 80%+ code test coverage

### 2.6 Compatibility

- **NFR-026:** System SHALL run on Python 3.11+
- **NFR-027:** System SHALL run on Linux (primary), macOS, Windows
- **NFR-028:** System SHALL support Docker deployment
- **NFR-029:** System SHALL support Kubernetes deployment
- **NFR-030:** Portal SHALL support modern browsers (Chrome, Firefox, Safari, Edge)

### 2.7 Usability

- **NFR-031:** Portal SHALL be responsive (mobile-friendly)
- **NFR-032:** Portal SHALL provide contextual help
- **NFR-033:** Portal SHALL support keyboard navigation
- **NFR-034:** Configuration SHALL be human-readable (YAML/JSON)
- **NFR-035:** Error messages SHALL be actionable

---

## 3. Configuration Schema Requirements

### 3.1 Production Configuration Schema

The production configuration SHALL support the following structure:

```json
{
  "$schema": "https://hie.nhs.uk/schemas/production/v1",
  "production": {
    "name": "string (required)",
    "description": "string",
    "enabled": "boolean (default: true)",
    "settings": {
      "actorPoolSize": "integer (default: 1)",
      "gracefulShutdownTimeout": "integer (seconds, default: 30)",
      "healthCheckInterval": "integer (seconds, default: 10)"
    }
  },
  "items": [
    {
      "id": "string (required, unique)",
      "name": "string",
      "type": "string (required, e.g., 'receiver.http')",
      "className": "string (for custom items)",
      "enabled": "boolean (default: true)",
      "category": "string",
      "comment": "string",
      "settings": {
        "poolSize": "integer (default: 1)",
        "queueSize": "integer (default: 1000)",
        "timeout": "number (seconds, default: 30)",
        "...": "type-specific settings"
      }
    }
  ],
  "routes": [
    {
      "id": "string (required, unique)",
      "name": "string",
      "enabled": "boolean (default: true)",
      "source": "string (item id)",
      "targets": ["string (item ids)"],
      "filters": [
        {
          "field": "string (dot notation)",
          "operator": "string (eq, ne, contains, etc.)",
          "value": "any"
        }
      ],
      "filterMode": "string (all | any, default: all)",
      "errorHandler": "string (item id)",
      "deadLetter": "string (item id)",
      "ordered": "boolean (default: false)",
      "timeout": "number (seconds)"
    }
  ],
  "connections": [
    {
      "from": "string (item id)",
      "to": "string (item id)",
      "condition": "string (optional filter expression)"
    }
  ]
}
```

### 3.2 Item Type Registry

Each item type SHALL define:
- Type identifier (e.g., "receiver.http")
- Configuration schema
- Default values
- Validation rules
- UI form definition

### 3.3 Compatibility with IRIS/Ensemble

System SHALL support import of IRIS production XML with mapping:

| IRIS Element | HIE Element |
|--------------|-------------|
| `<Production>` | `production` |
| `<Item>` | `items[]` |
| `Name` attribute | `id` |
| `ClassName` attribute | `type` or `className` |
| `PoolSize` attribute | `settings.poolSize` |
| `Enabled` attribute | `enabled` |
| `<Setting>` elements | `settings.*` |

---

## 4. Interface Requirements

### 4.1 Management REST API

#### 4.1.1 Production Endpoints
- `GET /api/productions` - List all productions
- `GET /api/productions/{id}` - Get production details
- `POST /api/productions` - Create production
- `PUT /api/productions/{id}` - Update production
- `DELETE /api/productions/{id}` - Delete production
- `POST /api/productions/{id}/start` - Start production
- `POST /api/productions/{id}/stop` - Stop production
- `POST /api/productions/{id}/pause` - Pause production
- `POST /api/productions/{id}/resume` - Resume production

#### 4.1.2 Item Endpoints
- `GET /api/productions/{id}/items` - List items
- `GET /api/productions/{id}/items/{itemId}` - Get item
- `POST /api/productions/{id}/items` - Create item
- `PUT /api/productions/{id}/items/{itemId}` - Update item
- `DELETE /api/productions/{id}/items/{itemId}` - Delete item
- `POST /api/productions/{id}/items/{itemId}/start` - Start item
- `POST /api/productions/{id}/items/{itemId}/stop` - Stop item

#### 4.1.3 Route Endpoints
- `GET /api/productions/{id}/routes` - List routes
- `POST /api/productions/{id}/routes` - Create route
- `PUT /api/productions/{id}/routes/{routeId}` - Update route
- `DELETE /api/productions/{id}/routes/{routeId}` - Delete route

#### 4.1.4 Message Endpoints
- `GET /api/messages` - Search messages
- `GET /api/messages/{id}` - Get message
- `POST /api/messages/{id}/resend` - Resend message
- `GET /api/messages/{id}/trace` - Get message trace

#### 4.1.5 System Endpoints
- `GET /api/health` - Health check
- `GET /api/metrics` - Prometheus metrics
- `GET /api/config` - Current configuration

### 4.2 WebSocket API

- `ws://host/ws/events` - Real-time event stream
  - Production state changes
  - Item state changes
  - Message events
  - Error notifications

---

## 5. Data Requirements

### 5.1 Message Storage Schema

```sql
CREATE TABLE hie_messages (
    message_id UUID PRIMARY KEY,
    correlation_id UUID NOT NULL,
    causation_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    message_type VARCHAR(255),
    priority VARCHAR(20) NOT NULL,
    state VARCHAR(50) NOT NULL,
    route_id VARCHAR(255),
    source VARCHAR(255) NOT NULL,
    destination VARCHAR(255),
    retry_count INTEGER DEFAULT 0,
    content_type VARCHAR(255) NOT NULL,
    encoding VARCHAR(50) NOT NULL,
    payload_size INTEGER NOT NULL,
    raw_payload BYTEA NOT NULL,
    envelope_json JSONB NOT NULL,
    properties_json JSONB,
    stored_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 Audit Log Schema

```sql
CREATE TABLE hie_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    production_id VARCHAR(255),
    item_id VARCHAR(255),
    message_id UUID,
    details JSONB,
    ip_address INET
);
```

---

## 6. Acceptance Criteria

### 6.1 MVP Acceptance Criteria

1. ✅ Production can be started and stopped via CLI
2. ✅ HTTP receiver accepts HL7v2 messages
3. ✅ File receiver watches directories
4. ✅ MLLP sender delivers messages with ACK handling
5. ✅ File sender writes messages to directories
6. ✅ Routes connect items in sequence
7. ✅ Messages are persisted to PostgreSQL
8. ✅ Management portal displays production status
9. ✅ Management portal allows item configuration
10. ✅ Configuration can be exported/imported as JSON

### 6.2 Production-Ready Acceptance Criteria

1. 🔲 System handles 10,000 msg/sec sustained load
2. 🔲 System recovers from node failure within 30 seconds
3. ✅ All API endpoints are authenticated
4. 🔲 Audit log captures all administrative actions
5. 🔲 Prometheus metrics are exposed
6. 🔲 Kubernetes deployment is documented and tested

---

*This document is maintained by the HIE Core Team and updated with each release.*
