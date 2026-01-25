"""
LI Adapters Module

Provides adapter base classes for protocol-specific communication:
- InboundAdapter: Receives data from external systems
- OutboundAdapter: Sends data to external systems
"""

from hie.li.adapters.base import (
    Adapter,
    AdapterState,
    InboundAdapter,
    OutboundAdapter,
)

__all__ = [
    "Adapter",
    "AdapterState",
    "InboundAdapter",
    "OutboundAdapter",
]
