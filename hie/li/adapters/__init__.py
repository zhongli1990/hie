"""
LI Adapters Module

Provides adapter base classes for protocol-specific communication:
- InboundAdapter: Receives data from external systems
- OutboundAdapter: Sends data to external systems
- MLLPInboundAdapter: MLLP/TCP inbound for HL7v2
- MLLPOutboundAdapter: MLLP/TCP outbound for HL7v2
"""

from hie.li.adapters.base import (
    Adapter,
    AdapterState,
    AdapterMetrics,
    InboundAdapter,
    OutboundAdapter,
)
from hie.li.adapters.mllp import (
    MLLPInboundAdapter,
    MLLPOutboundAdapter,
    MLLPFrameError,
    MLLPConnectionError,
    MLLPTimeoutError,
    mllp_wrap,
    mllp_unwrap,
    read_mllp_message,
    write_mllp_message,
    MLLP_START_BLOCK,
    MLLP_END_BLOCK,
    MLLP_CARRIAGE_RETURN,
)

__all__ = [
    # Base classes
    "Adapter",
    "AdapterState",
    "AdapterMetrics",
    "InboundAdapter",
    "OutboundAdapter",
    # MLLP adapters
    "MLLPInboundAdapter",
    "MLLPOutboundAdapter",
    # MLLP utilities
    "MLLPFrameError",
    "MLLPConnectionError",
    "MLLPTimeoutError",
    "mllp_wrap",
    "mllp_unwrap",
    "read_mllp_message",
    "write_mllp_message",
    "MLLP_START_BLOCK",
    "MLLP_END_BLOCK",
    "MLLP_CARRIAGE_RETURN",
]
