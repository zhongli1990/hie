# Portal UI Configuration Guide

## Overview

The HIE Portal now exposes all Phase 2 enterprise concurrency and reliability settings through the Manager API. This guide explains how to configure items using the Portal UI with these advanced settings.

## API Integration

### Getting Item Type Schema

The Portal fetches item type configuration schemas from the Manager API:

```typescript
// GET /api/item-types/{type_id}
const response = await fetch(`/api/item-types/hl7.tcp.service`);
const itemType = await response.json();

// Response includes all settings
itemType.host_settings; // Array of SettingDefinition including Phase 2 settings
itemType.adapter_settings; // Adapter-specific settings
```

### Setting Structure

Each setting has this structure:

```typescript
interface SettingDefinition {
  key: string;              // Setting key (e.g., "ExecutionMode")
  label: string;            // Display label
  type: string;             // "select", "number", "boolean", "string", "multiselect"
  required: boolean;        // Whether required
  default: any;             // Default value
  description: string;      // Help text
  options?: Array<{         // For select/multiselect types
    value: string;
    label: string;
  }>;
  validation?: {            // For number types
    min?: number;
    max?: number;
  };
}
```

## Phase 2 Settings Reference

### 1. Execution Configuration

#### ExecutionMode
**Type**: Select
**Default**: "async"
**Options**:
- `async` - Event loop (best for I/O-bound)
- `multiprocess` - True OS processes (best for CPU-bound, bypasses GIL)
- `thread_pool` - Thread pool (best for blocking I/O)
- `single_process` - Single-threaded (debugging only)

**UI Rendering**:
```typescript
<Select
  label="Execution Mode"
  value={settings.ExecutionMode || "async"}
  options={[
    { value: "async", label: "Async (Event Loop) - Best for I/O-bound" },
    { value: "multiprocess", label: "Multiprocess (GIL Bypass) - Best for CPU-bound" },
    { value: "thread_pool", label: "Thread Pool - Best for blocking I/O" },
    { value: "single_process", label: "Single Process - Debug mode" },
  ]}
  helpText="How to execute message processing workers. Multiprocess bypasses Python GIL for true parallelism."
/>
```

#### WorkerCount
**Type**: Number
**Default**: 1
**Range**: 1-32

**Guidance**:
- For `multiprocess`: Match CPU cores (e.g., 4-8 for typical servers)
- For `thread_pool`: Can exceed CPU cores (e.g., 16-32 for I/O-bound)
- For `async`: Usually 1 (event loop is single-threaded)

### 2. Queue Configuration

#### QueueType
**Type**: Select
**Default**: "fifo"
**Options**:
- `fifo` - First-In-First-Out (strict ordering)
- `priority` - Priority-based routing
- `lifo` - Last-In-First-Out (stack)
- `unordered` - Maximum throughput

**Use Cases**:
- **FIFO**: Order-sensitive workflows (patient admissions, financial transactions)
- **Priority**: Mixed criticality (urgent lab results vs routine reports)
- **LIFO**: Most recent first (real-time dashboards, cache invalidation)
- **Unordered**: Maximum throughput (bulk data processing, analytics)

#### QueueSize
**Type**: Number
**Default**: 1000
**Range**: 1-100,000

**Guidance**:
- Small (100-1000): Low-latency services, memory-constrained
- Medium (1000-10000): Standard services
- Large (10000-100000): High-throughput, burst handling

#### OverflowStrategy
**Type**: Select
**Default**: "block"
**Options**:
- `block` - Wait for space (provides backpressure)
- `drop_oldest` - Remove oldest message to make space
- `drop_newest` - Reject incoming message
- `reject` - Raise exception

**Use Cases**:
- **Block**: Most services (provides natural backpressure)
- **Drop Oldest**: Real-time feeds where old data becomes stale
- **Drop Newest**: Rate limiting, prevent overload
- **Reject**: Strict capacity enforcement, monitoring

### 3. Auto-Restart Configuration

#### RestartPolicy
**Type**: Select
**Default**: "never"
**Options**:
- `never` - Manual intervention required
- `on_failure` - Only restart on ERROR state
- `always` - Restart regardless of reason

**Guidance**:
- **Development**: Use `never` to catch errors
- **Production Non-Critical**: Use `on_failure`
- **Production Mission-Critical**: Use `always`

#### MaxRestarts
**Type**: Number
**Default**: 3
**Range**: 0-1000

**Guidance**:
- Development: 0-3 (fail fast to see errors)
- Production Standard: 5-10
- Mission-Critical: 100-1000 (never give up)

#### RestartDelay
**Type**: Number (seconds)
**Default**: 5.0
**Range**: 0-300

**Guidance**:
- Fast recovery: 1-5 seconds
- Transient issues: 10-30 seconds
- External dependencies: 30-60 seconds

### 4. Messaging Configuration

#### MessagingPattern
**Type**: Select
**Default**: "async_reliable"
**Options**:
- `async_reliable` - Non-blocking, persisted
- `sync_reliable` - Blocking request/reply
- `concurrent_async` - Parallel non-blocking
- `concurrent_sync` - Parallel blocking workers

**Use Cases**:
- **Async Reliable**: Standard HL7 routing, event-driven workflows
- **Sync Reliable**: PDS lookups, database queries (need response)
- **Concurrent Async**: Batch processing, high-volume analytics
- **Concurrent Sync**: API gateways, parallel I/O operations

#### MessageTimeout
**Type**: Number (seconds)
**Default**: 30.0
**Range**: 1-300

Only applies to sync patterns. Timeout for waiting on response.

## UI Form Organization

### Recommended Form Structure

Group settings into collapsible sections:

```
┌─ Basic Configuration (always visible) ─────────────────┐
│ • Name                                                  │
│ • Display Name                                          │
│ • Enabled                                               │
│ • Pool Size                                             │
└─────────────────────────────────────────────────────────┘

┌─ Adapter Settings (collapsed by default) ──────────────┐
│ • Port / IP Address / etc (adapter-specific)           │
└─────────────────────────────────────────────────────────┘

┌─ Host Settings (collapsed by default) ─────────────────┐
│ • Target Items / ACK Mode / etc (item-specific)        │
└─────────────────────────────────────────────────────────┘

┌─ Performance & Execution (collapsed, Phase 2) ─────────┐
│ • Execution Mode                                        │
│ • Worker Count                                          │
└─────────────────────────────────────────────────────────┘

┌─ Queue Configuration (collapsed, Phase 2) ─────────────┐
│ • Queue Type                                            │
│ • Queue Size                                            │
│ • Overflow Strategy                                     │
└─────────────────────────────────────────────────────────┘

┌─ Reliability & Auto-Restart (collapsed, Phase 2) ──────┐
│ • Restart Policy                                        │
│ • Max Restarts                                          │
│ • Restart Delay                                         │
└─────────────────────────────────────────────────────────┘

┌─ Messaging (collapsed, Phase 2) ───────────────────────┐
│ • Messaging Pattern                                     │
│ • Message Timeout                                       │
└─────────────────────────────────────────────────────────┘
```

## Configuration Presets

The Portal should provide presets for common scenarios:

### High-Throughput Service
```json
{
  "ExecutionMode": "multiprocess",
  "WorkerCount": 8,
  "QueueType": "unordered",
  "QueueSize": 50000,
  "OverflowStrategy": "drop_oldest",
  "RestartPolicy": "always",
  "MaxRestarts": 100,
  "RestartDelay": 5.0,
  "MessagingPattern": "concurrent_async"
}
```

### Mission-Critical Service
```json
{
  "ExecutionMode": "thread_pool",
  "WorkerCount": 2,
  "QueueType": "fifo",
  "QueueSize": 1000,
  "OverflowStrategy": "block",
  "RestartPolicy": "always",
  "MaxRestarts": 1000,
  "RestartDelay": 30.0,
  "MessagingPattern": "sync_reliable",
  "MessageTimeout": 60.0
}
```

### Low-Latency Service
```json
{
  "ExecutionMode": "async",
  "WorkerCount": 1,
  "QueueType": "fifo",
  "QueueSize": 1000,
  "OverflowStrategy": "block",
  "RestartPolicy": "on_failure",
  "MaxRestarts": 5,
  "RestartDelay": 5.0,
  "MessagingPattern": "async_reliable"
}
```

### Development/Debug
```json
{
  "ExecutionMode": "single_process",
  "WorkerCount": 1,
  "QueueType": "fifo",
  "QueueSize": 100,
  "OverflowStrategy": "reject",
  "RestartPolicy": "never",
  "MaxRestarts": 0,
  "MessagingPattern": "sync_reliable"
}
```

## Saving Configuration

When saving, the Portal sends `host_settings` as a flat dictionary:

```typescript
const itemData = {
  name: "HL7_TCP_Service",
  display_name: "HL7 TCP Service",
  item_type: "SERVICE",
  class_name: "li.hosts.hl7.HL7TCPService",
  pool_size: 4,
  enabled: true,
  adapter_settings: {
    port: 2575,
    readTimeout: 30,
  },
  host_settings: {
    // Item-specific
    targetConfigNames: ["Router", "Processor"],
    ackMode: "App",
    // Phase 2 settings
    ExecutionMode: "multiprocess",
    WorkerCount: 4,
    QueueType: "priority",
    QueueSize: 10000,
    OverflowStrategy: "drop_oldest",
    RestartPolicy: "always",
    MaxRestarts: 10,
    RestartDelay: 5.0,
    MessagingPattern: "async_reliable",
  }
};

await fetch(`/api/projects/${projectId}/items`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(itemData),
});
```

## Validation

### Client-Side Validation

The Portal should validate:

1. **Required fields**: Check `required: true` settings
2. **Number ranges**: Enforce `validation.min` and `validation.max`
3. **Enum values**: Ensure selected values are in `options`
4. **Logical consistency**:
   - If `ExecutionMode=multiprocess`, recommend `WorkerCount` matches CPU cores
   - If `QueueType=priority`, recommend `MessagingPattern` uses priorities
   - If `RestartPolicy=never`, disable `MaxRestarts` and `RestartDelay`

### Server-Side Validation

The Manager API validates all settings. If validation fails, the API returns:

```json
{
  "error": "Validation error: WorkerCount must be between 1 and 32"
}
```

## Hot Reload

Phase 2 settings support hot reload without restarting the production:

```typescript
// After updating settings
await fetch(`/api/projects/${projectId}/items/${itemId}/reload`, {
  method: 'POST',
});
```

**Note**: Some settings (like `ExecutionMode`) require a full restart to take effect. The API should indicate this in the response.

## Monitoring & Metrics

The Portal should display runtime metrics for Phase 2 features:

### Execution Metrics
- Current execution mode
- Active worker count
- CPU utilization per worker

### Queue Metrics
- Current queue size
- Queue utilization (current / max)
- Overflow count (messages dropped/rejected)
- Average wait time in queue

### Auto-Restart Metrics
- Restart count
- Last restart time
- Restart policy in effect
- Time until next restart (if applicable)

### Messaging Metrics
- Active messaging pattern
- Sync request count
- Sync timeout count
- Average response time

## Best Practices

1. **Start Simple**: Use defaults for new items, only customize for specific needs
2. **Use Presets**: Start with a preset and tweak as needed
3. **Monitor First**: Deploy with defaults, monitor, then optimize
4. **Document Choices**: Add comments explaining why specific settings were chosen
5. **Test Changes**: Use hot reload to test setting changes without full restart
6. **Review Regularly**: Revisit settings as load patterns change

## Troubleshooting

### High CPU Usage
- Check `ExecutionMode` - use `multiprocess` for CPU-bound workloads
- Reduce `WorkerCount` if over-subscribed

### High Memory Usage
- Reduce `QueueSize`
- Use `OverflowStrategy=drop_oldest` instead of `block`

### Message Loss
- Change `OverflowStrategy` from `drop_*` to `block`
- Increase `QueueSize`
- Add more workers

### Service Keeps Crashing
- Check `RestartPolicy` - should be `on_failure` or `always`
- Increase `RestartDelay` for transient issues
- Review logs to fix underlying issue

### Slow Response Times
- Use `sync_reliable` messaging pattern for critical paths
- Increase `WorkerCount`
- Use `QueueType=priority` and prioritize urgent messages

## See Also

- [Configuration Reference](CONFIGURATION_REFERENCE.md) - Complete setting documentation
- [Message Patterns Specification](MESSAGE_PATTERNS_SPECIFICATION.md) - Messaging pattern details
- [Implementation Status](IMPLEMENTATION_STATUS.md) - Feature status and roadmap
