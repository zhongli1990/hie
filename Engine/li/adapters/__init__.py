"""
LI Adapters Module

Provides adapter base classes for protocol-specific communication:
- InboundAdapter: Receives data from external systems
- OutboundAdapter: Sends data to external systems
- MLLPInboundAdapter: MLLP/TCP inbound for HL7v2
- MLLPOutboundAdapter: MLLP/TCP outbound for HL7v2
- InboundFileAdapter: File polling inbound
- OutboundFileAdapter: File writing outbound
- InboundHTTPAdapter: HTTP server inbound
- OutboundHTTPAdapter: HTTP client outbound
"""

from Engine.li.adapters.base import (
    Adapter,
    AdapterState,
    AdapterMetrics,
    InboundAdapter,
    OutboundAdapter,
)
from Engine.li.adapters.mllp import (
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
from Engine.li.adapters.file import (
    InboundFileAdapter,
    OutboundFileAdapter,
    FileAdapterError,
)
from Engine.li.adapters.http import (
    InboundHTTPAdapter,
    OutboundHTTPAdapter,
    HTTPAdapterError,
    HTTPRequest,
    HTTPResponse,
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
    # File adapters
    "InboundFileAdapter",
    "OutboundFileAdapter",
    "FileAdapterError",
    # HTTP adapters
    "InboundHTTPAdapter",
    "OutboundHTTPAdapter",
    "HTTPAdapterError",
    "HTTPRequest",
    "HTTPResponse",
]
