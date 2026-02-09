"""
LI Metrics Module

Provides Prometheus metrics export for monitoring and alerting.
"""

from Engine.li.metrics.prometheus import (
    MetricsRegistry,
    Counter,
    Gauge,
    Histogram,
    get_metrics_registry,
    metrics_handler,
    record_message_received,
    record_message_sent,
    record_message_failed,
    record_processing_time,
    record_message_size,
    set_host_status,
    set_queue_depth,
)

__all__ = [
    "MetricsRegistry",
    "Counter",
    "Gauge",
    "Histogram",
    "get_metrics_registry",
    "metrics_handler",
    "record_message_received",
    "record_message_sent",
    "record_message_failed",
    "record_processing_time",
    "record_message_size",
    "set_host_status",
    "set_queue_depth",
]
