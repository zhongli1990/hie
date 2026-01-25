"""
LI Hosts Module

Provides the Host hierarchy for message processing:
- Host: Base class for all hosts
- BusinessService: Inbound message processing
- BusinessProcess: Message transformation and routing
- BusinessOperation: Outbound message processing
- HL7TCPService: HL7v2 MLLP/TCP inbound
- HL7TCPOperation: HL7v2 MLLP/TCP outbound
"""

from hie.li.hosts.base import (
    Host,
    HostState,
    HostMetrics,
    BusinessService,
    BusinessProcess,
    BusinessOperation,
)
from hie.li.hosts.hl7 import (
    HL7TCPService,
    HL7TCPOperation,
    HL7Message,
    SendResult,
    HL7SendError,
    HL7RetryError,
)
from hie.li.hosts.routing import (
    HL7RoutingEngine,
    RoutingRule,
    RoutingResult,
    RuleAction,
    ConditionEvaluator,
    create_message_type_rule,
    create_facility_rule,
)

__all__ = [
    # Base classes
    "Host",
    "HostState",
    "HostMetrics",
    "BusinessService",
    "BusinessProcess",
    "BusinessOperation",
    # HL7 hosts
    "HL7TCPService",
    "HL7TCPOperation",
    "HL7Message",
    "SendResult",
    "HL7SendError",
    "HL7RetryError",
    # Routing
    "HL7RoutingEngine",
    "RoutingRule",
    "RoutingResult",
    "RuleAction",
    "ConditionEvaluator",
    "create_message_type_rule",
    "create_facility_rule",
]
