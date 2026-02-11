# HIE Configuration Reference

## Overview

This document provides a comprehensive reference for all configuration options available in HIE's LI Engine (InterSystems IRIS-compatible layer).

## Production Configuration

### Item Configuration Structure

Items (Hosts) in a production are configured using the IRIS-compatible format:

```yaml
items:
  - name: "MyService"
    class_name: "Engine.li.hosts.tcp_service.TCPService"
    pool_size: 2
    enabled: true
    settings:
      - target: "Host"
        name: "SettingName"
        value: "SettingValue"
      - target: "Adapter"
        name: "AdapterSetting"
        value: "AdapterValue"
```

Or in XML format (IRIS-compatible):

```xml
<Item Name="MyService" ClassName="Engine.li.hosts.tcp_service.TCPService" PoolSize="2" Enabled="true">
  <Setting Target="Host" Name="SettingName">SettingValue</Setting>
  <Setting Target="Adapter" Name="AdapterSetting">AdapterValue</Setting>
</Item>
```

## Host Settings

Host-level settings control the behavior of the service/process/operation itself.

### Core Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `PoolSize` | int | 1 | Number of worker processes/threads |
| `Enabled` | bool | true | Whether the item is enabled |
| `Foreground` | bool | false | Run in foreground (blocking) |
| `Category` | str | "" | Category for UI grouping |
| `LogTraceEvents` | bool | false | Enable detailed trace logging |
| `Schedule` | str | "" | Schedule specification |

### Execution Settings

Controls how the host executes message processing.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ExecutionMode` | str | "async" | Execution strategy: `async`, `multiprocess`, `thread_pool`, `single_process` |
| `WorkerCount` | int | 1 | Number of worker processes/threads (overrides PoolSize if set) |

**ExecutionMode Values:**

- **`async`**: Single-process asyncio event loop (default, best for I/O-bound)
- **`multiprocess`**: True OS-level processes using `multiprocessing.Process` (bypasses GIL, best for CPU-bound)
- **`thread_pool`**: Thread pool using `concurrent.futures.ThreadPoolExecutor` (for blocking I/O)
- **`single_process`**: Single-threaded synchronous processing (for testing/debugging)

### Queue Configuration

Controls the message queue behavior for the host.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `QueueType` | str | "fifo" | Queue type: `fifo`, `priority`, `lifo`, `unordered` |
| `QueueSize` | int | 1000 | Maximum queue size (0 = unlimited) |
| `OverflowStrategy` | str | "block" | What to do when queue is full: `block`, `drop_oldest`, `drop_newest`, `reject` |

**QueueType Values:**

- **`fifo`**: First-In-First-Out (strict ordering)
- **`priority`**: Priority-based (requires messages with priority field)
- **`lifo`**: Last-In-First-Out (stack behavior)
- **`unordered`**: No ordering guarantees (best performance)

**OverflowStrategy Values:**

- **`block`**: Block until space available (default)
- **`drop_oldest`**: Remove oldest message to make space
- **`drop_newest`**: Drop the new incoming message
- **`reject`**: Raise exception

### Auto-Restart Configuration

Controls automatic restart behavior when a host fails.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `RestartPolicy` | str | "never" | When to restart: `never`, `always`, `on_failure` |
| `MaxRestarts` | int | 3 | Maximum number of restart attempts |
| `RestartDelay` | float | 5.0 | Delay in seconds before restarting |

**RestartPolicy Values:**

- **`never`**: Never auto-restart (default, manual intervention required)
- **`always`**: Always restart regardless of exit reason
- **`on_failure`**: Only restart if host entered ERROR state

**Example Configuration:**

```yaml
settings:
  - target: "Host"
    name: "RestartPolicy"
    value: "on_failure"
  - target: "Host"
    name: "MaxRestarts"
    value: "5"
  - target: "Host"
    name: "RestartDelay"
    value: "10.0"
```

This configuration will:
- Automatically restart the host if it fails
- Allow up to 5 restart attempts
- Wait 10 seconds between restart attempts
- Stop trying after 5 failures

### Messaging Configuration

Controls service-to-service messaging behavior.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `MessagingPattern` | str | "async_reliable" | Default pattern: `async_reliable`, `sync_reliable`, `concurrent_async`, `concurrent_sync` |
| `MessageTimeout` | float | 30.0 | Default timeout for sync messages (seconds) |

**MessagingPattern Values:**

- **`async_reliable`**: Non-blocking, event-driven, persisted (default)
- **`sync_reliable`**: Blocking request/reply with FIFO ordering
- **`concurrent_async`**: Parallel non-blocking without FIFO
- **`concurrent_sync`**: Parallel blocking workers

## Adapter Settings

Adapter-level settings control the behavior of the protocol adapter (TCP, HTTP, File, etc.).

### TCP Adapter Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `IPAddress` | str | "127.0.0.1" | IP address to bind to |
| `Port` | int | 2575 | TCP port number |
| `JobPerConnection` | bool | true | Create new job per connection |
| `ReadTimeout` | float | 30.0 | Read timeout in seconds |

### HTTP Adapter Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `URL` | str | "" | HTTP endpoint URL |
| `HTTPMethod` | str | "POST" | HTTP method to use |
| `ContentType` | str | "application/json" | Content-Type header |
| `Timeout` | float | 30.0 | Request timeout in seconds |

### File Adapter Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `FilePath` | str | "" | File path or directory |
| `FileNamePattern` | str | "*.*" | File name pattern for input |
| `ArchivePath` | str | "" | Archive processed files here |
| `WorkPath` | str | "" | Temporary work directory |

## Production-Level Settings

These settings apply to the entire production.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `AutoStartItems` | bool | true | Auto-start all enabled items |
| `GracefulShutdownTimeout` | float | 30.0 | Seconds to wait for graceful shutdown |
| `HealthCheckInterval` | float | 10.0 | Health check interval in seconds |
| `MonitoringEnabled` | bool | true | Enable host health monitoring |
| `MonitoringInterval` | float | 5.0 | Monitoring check interval in seconds |

## Complete Example

```yaml
production:
  name: "NHS-Integration-Production"
  description: "High-availability NHS integration"
  enabled: true
  auto_start_items: true
  graceful_shutdown_timeout: 30.0
  health_check_interval: 10.0

items:
  # High-throughput TCP service with multiprocessing
  - name: "HL7_TCP_Service"
    class_name: "Engine.li.hosts.tcp_service.TCPService"
    pool_size: 4
    enabled: true
    settings:
      # Execution
      - target: "Host"
        name: "ExecutionMode"
        value: "multiprocess"
      - target: "Host"
        name: "WorkerCount"
        value: "4"

      # Queue configuration
      - target: "Host"
        name: "QueueType"
        value: "priority"
      - target: "Host"
        name: "QueueSize"
        value: "10000"
      - target: "Host"
        name: "OverflowStrategy"
        value: "drop_oldest"

      # Auto-restart
      - target: "Host"
        name: "RestartPolicy"
        value: "on_failure"
      - target: "Host"
        name: "MaxRestarts"
        value: "5"
      - target: "Host"
        name: "RestartDelay"
        value: "10.0"

      # Messaging
      - target: "Host"
        name: "MessagingPattern"
        value: "async_reliable"

      # TCP Adapter
      - target: "Adapter"
        name: "IPAddress"
        value: "0.0.0.0"
      - target: "Adapter"
        name: "Port"
        value: "2575"
      - target: "Adapter"
        name: "JobPerConnection"
        value: "true"

  # Critical business process with sync messaging
  - name: "PDS_Lookup_Process"
    class_name: "Engine.li.hosts.business_process.BusinessProcess"
    pool_size: 2
    enabled: true
    settings:
      # Use thread pool for blocking operations
      - target: "Host"
        name: "ExecutionMode"
        value: "thread_pool"
      - target: "Host"
        name: "WorkerCount"
        value: "2"

      # FIFO queue for ordered processing
      - target: "Host"
        name: "QueueType"
        value: "fifo"
      - target: "Host"
        name: "QueueSize"
        value: "1000"

      # Always restart (critical service)
      - target: "Host"
        name: "RestartPolicy"
        value: "always"
      - target: "Host"
        name: "MaxRestarts"
        value: "10"

      # Use sync reliable messaging
      - target: "Host"
        name: "MessagingPattern"
        value: "sync_reliable"
      - target: "Host"
        name: "MessageTimeout"
        value: "60.0"
```

## Best Practices

### Execution Mode Selection

- **I/O-bound services** (network, database): Use `async` (default)
- **CPU-intensive processing**: Use `multiprocess` to bypass GIL
- **Blocking third-party libraries**: Use `thread_pool`
- **Testing/debugging**: Use `single_process`

### Queue Configuration

- **Ordered processing required**: Use `fifo` queue
- **Priority-based routing**: Use `priority` queue with message priorities
- **Maximum throughput**: Use `unordered` queue
- **Limited memory**: Set `QueueSize` with appropriate `OverflowStrategy`

### Auto-Restart Policy

- **Development**: Use `RestartPolicy=never` to catch errors
- **Production critical services**: Use `RestartPolicy=always` with reasonable `MaxRestarts`
- **Non-critical services**: Use `RestartPolicy=on_failure`
- **Transient failures**: Set higher `RestartDelay` (30-60s) to allow recovery

### Messaging Patterns

- **Fire-and-forget**: Use `async_reliable` (non-blocking)
- **Request-reply**: Use `sync_reliable` (blocks for response)
- **Batch processing**: Use `concurrent_async` (parallel throughput)
- **Worker pool**: Use `concurrent_sync` (parallel workers)

## Performance Tuning

### High-Throughput Services

```yaml
settings:
  - target: "Host"
    name: "ExecutionMode"
    value: "multiprocess"
  - target: "Host"
    name: "WorkerCount"
    value: "8"  # Match CPU cores
  - target: "Host"
    name: "QueueType"
    value: "unordered"  # Fastest
  - target: "Host"
    name: "QueueSize"
    value: "50000"  # Large buffer
  - target: "Host"
    name: "MessagingPattern"
    value: "concurrent_async"
```

### Low-Latency Services

```yaml
settings:
  - target: "Host"
    name: "ExecutionMode"
    value: "async"  # Event loop
  - target: "Host"
    name: "QueueType"
    value: "fifo"  # Predictable
  - target: "Host"
    name: "QueueSize"
    value: "1000"  # Small buffer
  - target: "Host"
    name: "MessagingPattern"
    value: "sync_reliable"  # Direct reply
```

### Reliable Critical Services

```yaml
settings:
  - target: "Host"
    name: "ExecutionMode"
    value: "thread_pool"
  - target: "Host"
    name: "QueueType"
    value: "fifo"  # Ordered
  - target: "Host"
    name: "RestartPolicy"
    value: "always"  # Never stay down
  - target: "Host"
    name: "MaxRestarts"
    value: "100"  # High tolerance
  - target: "Host"
    name: "RestartDelay"
    value: "30.0"  # Allow recovery
```

## See Also

- [Message Patterns Specification](MESSAGE_PATTERNS_SPECIFICATION.md)
- [Architecture Overview](architecture/overview.md)
- [Implementation Status](IMPLEMENTATION_STATUS.md)
