"""
LI Prometheus Metrics

Provides Prometheus-compatible metrics for monitoring LI Engine.
Exposes metrics via HTTP endpoint for Prometheus scraping.

Metrics include:
- Message throughput (received, sent, failed)
- Processing latency
- Queue depths
- Connection counts
- Host status
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from collections import defaultdict

import structlog

logger = structlog.get_logger(__name__)


# Global metrics registry
_registry: "MetricsRegistry | None" = None


def get_metrics_registry() -> "MetricsRegistry":
    """Get the global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


@dataclass
class MetricValue:
    """A single metric value with labels."""
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """
    A counter metric that only increases.
    
    Used for counting events like messages received, errors, etc.
    """
    
    def __init__(self, name: str, description: str, labels: list[str] | None = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
    
    def inc(self, value: float = 1, **labels) -> None:
        """Increment the counter."""
        key = self._make_key(labels)
        self._values[key] += value
    
    def get(self, **labels) -> float:
        """Get the current value."""
        key = self._make_key(labels)
        return self._values[key]
    
    def _make_key(self, labels: dict[str, str]) -> tuple:
        """Create a hashable key from labels."""
        return tuple(sorted(labels.items()))
    
    def collect(self) -> list[MetricValue]:
        """Collect all values for export."""
        result = []
        for key, value in self._values.items():
            labels = dict(key)
            result.append(MetricValue(value=value, labels=labels))
        return result


class Gauge:
    """
    A gauge metric that can increase or decrease.
    
    Used for values like queue depth, active connections, etc.
    """
    
    def __init__(self, name: str, description: str, labels: list[str] | None = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
    
    def set(self, value: float, **labels) -> None:
        """Set the gauge value."""
        key = self._make_key(labels)
        self._values[key] = value
    
    def inc(self, value: float = 1, **labels) -> None:
        """Increment the gauge."""
        key = self._make_key(labels)
        self._values[key] += value
    
    def dec(self, value: float = 1, **labels) -> None:
        """Decrement the gauge."""
        key = self._make_key(labels)
        self._values[key] -= value
    
    def get(self, **labels) -> float:
        """Get the current value."""
        key = self._make_key(labels)
        return self._values[key]
    
    def _make_key(self, labels: dict[str, str]) -> tuple:
        """Create a hashable key from labels."""
        return tuple(sorted(labels.items()))
    
    def collect(self) -> list[MetricValue]:
        """Collect all values for export."""
        result = []
        for key, value in self._values.items():
            labels = dict(key)
            result.append(MetricValue(value=value, labels=labels))
        return result


class Histogram:
    """
    A histogram metric for measuring distributions.
    
    Used for latency measurements, message sizes, etc.
    """
    
    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
        0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf")
    )
    
    def __init__(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        
        self._counts: dict[tuple, dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: dict[tuple, float] = defaultdict(float)
        self._totals: dict[tuple, int] = defaultdict(int)
    
    def observe(self, value: float, **labels) -> None:
        """Record an observation."""
        key = self._make_key(labels)
        
        self._sums[key] += value
        self._totals[key] += 1
        
        for bucket in self.buckets:
            if value <= bucket:
                self._counts[key][bucket] += 1
    
    def _make_key(self, labels: dict[str, str]) -> tuple:
        """Create a hashable key from labels."""
        return tuple(sorted(labels.items()))
    
    def collect(self) -> list[MetricValue]:
        """Collect all values for export."""
        result = []
        
        for key in self._counts.keys():
            labels = dict(key)
            
            # Bucket values
            for bucket, count in self._counts[key].items():
                bucket_labels = {**labels, "le": str(bucket)}
                result.append(MetricValue(
                    value=count,
                    labels=bucket_labels,
                ))
            
            # Sum
            sum_labels = {**labels}
            result.append(MetricValue(
                value=self._sums[key],
                labels={**sum_labels, "_type": "sum"},
            ))
            
            # Count
            result.append(MetricValue(
                value=self._totals[key],
                labels={**sum_labels, "_type": "count"},
            ))
        
        return result


class MetricsRegistry:
    """
    Registry for all metrics.
    
    Provides centralized metric management and export.
    """
    
    def __init__(self):
        self._metrics: dict[str, Counter | Gauge | Histogram] = {}
        self._prefix = "li"
        
        # Register default metrics
        self._register_default_metrics()
    
    def _register_default_metrics(self) -> None:
        """Register default LI Engine metrics."""
        # Message metrics
        self.register(Counter(
            "messages_received_total",
            "Total messages received",
            ["host", "message_type"],
        ))
        self.register(Counter(
            "messages_sent_total",
            "Total messages sent",
            ["host", "target"],
        ))
        self.register(Counter(
            "messages_failed_total",
            "Total messages failed",
            ["host", "error_type"],
        ))
        self.register(Counter(
            "messages_processed_total",
            "Total messages processed",
            ["host"],
        ))
        
        # Latency metrics
        self.register(Histogram(
            "message_processing_seconds",
            "Message processing latency",
            ["host"],
        ))
        self.register(Histogram(
            "message_size_bytes",
            "Message size in bytes",
            ["host", "direction"],
            buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, float("inf")),
        ))
        
        # Connection metrics
        self.register(Gauge(
            "connections_active",
            "Active connections",
            ["host", "adapter"],
        ))
        self.register(Counter(
            "connections_total",
            "Total connections",
            ["host", "adapter"],
        ))
        
        # Queue metrics
        self.register(Gauge(
            "queue_depth",
            "Current queue depth",
            ["host"],
        ))
        self.register(Gauge(
            "queue_processing",
            "Messages currently processing",
            ["host"],
        ))
        
        # Host metrics
        self.register(Gauge(
            "host_status",
            "Host status (1=running, 0=stopped)",
            ["host", "type"],
        ))
        self.register(Gauge(
            "host_workers",
            "Number of active workers",
            ["host"],
        ))
        
        # WAL metrics
        self.register(Gauge(
            "wal_pending",
            "Pending WAL entries",
            [],
        ))
        self.register(Counter(
            "wal_entries_total",
            "Total WAL entries",
            ["state"],
        ))
    
    def register(self, metric: Counter | Gauge | Histogram) -> None:
        """Register a metric."""
        full_name = f"{self._prefix}_{metric.name}"
        self._metrics[full_name] = metric
    
    def get(self, name: str) -> Counter | Gauge | Histogram | None:
        """Get a metric by name."""
        full_name = f"{self._prefix}_{name}"
        return self._metrics.get(full_name)
    
    def counter(self, name: str) -> Counter | None:
        """Get a counter metric."""
        metric = self.get(name)
        return metric if isinstance(metric, Counter) else None
    
    def gauge(self, name: str) -> Gauge | None:
        """Get a gauge metric."""
        metric = self.get(name)
        return metric if isinstance(metric, Gauge) else None
    
    def histogram(self, name: str) -> Histogram | None:
        """Get a histogram metric."""
        metric = self.get(name)
        return metric if isinstance(metric, Histogram) else None
    
    def export(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []
        
        for name, metric in self._metrics.items():
            # Add HELP and TYPE
            lines.append(f"# HELP {name} {metric.description}")
            
            if isinstance(metric, Counter):
                lines.append(f"# TYPE {name} counter")
            elif isinstance(metric, Gauge):
                lines.append(f"# TYPE {name} gauge")
            elif isinstance(metric, Histogram):
                lines.append(f"# TYPE {name} histogram")
            
            # Add values
            for mv in metric.collect():
                if mv.labels:
                    label_str = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                    lines.append(f"{name}{{{label_str}}} {mv.value}")
                else:
                    lines.append(f"{name} {mv.value}")
        
        return "\n".join(lines) + "\n"


async def metrics_handler(request: Any) -> tuple[str, int, dict[str, str]]:
    """
    HTTP handler for metrics endpoint.
    
    Returns Prometheus-formatted metrics.
    
    Usage with aiohttp:
        app.router.add_get('/metrics', metrics_handler)
    """
    registry = get_metrics_registry()
    body = registry.export()
    
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


# Convenience functions for recording metrics
def record_message_received(host: str, message_type: str = "unknown") -> None:
    """Record a message received."""
    registry = get_metrics_registry()
    counter = registry.counter("messages_received_total")
    if counter:
        counter.inc(host=host, message_type=message_type)


def record_message_sent(host: str, target: str) -> None:
    """Record a message sent."""
    registry = get_metrics_registry()
    counter = registry.counter("messages_sent_total")
    if counter:
        counter.inc(host=host, target=target)


def record_message_failed(host: str, error_type: str = "unknown") -> None:
    """Record a message failure."""
    registry = get_metrics_registry()
    counter = registry.counter("messages_failed_total")
    if counter:
        counter.inc(host=host, error_type=error_type)


def record_processing_time(host: str, seconds: float) -> None:
    """Record message processing time."""
    registry = get_metrics_registry()
    histogram = registry.histogram("message_processing_seconds")
    if histogram:
        histogram.observe(seconds, host=host)


def record_message_size(host: str, size: int, direction: str = "in") -> None:
    """Record message size."""
    registry = get_metrics_registry()
    histogram = registry.histogram("message_size_bytes")
    if histogram:
        histogram.observe(size, host=host, direction=direction)


def set_host_status(host: str, host_type: str, running: bool) -> None:
    """Set host status."""
    registry = get_metrics_registry()
    gauge = registry.gauge("host_status")
    if gauge:
        gauge.set(1 if running else 0, host=host, type=host_type)


def set_queue_depth(host: str, depth: int) -> None:
    """Set queue depth."""
    registry = get_metrics_registry()
    gauge = registry.gauge("queue_depth")
    if gauge:
        gauge.set(depth, host=host)
