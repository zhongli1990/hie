"""
LI Hosts Module

Provides the Host hierarchy for message processing:
- Host: Base class for all hosts
- BusinessService: Inbound message processing
- BusinessProcess: Message transformation and routing
- BusinessOperation: Outbound message processing
- HL7TCPService: HL7v2 MLLP/TCP inbound
- HL7TCPOperation: HL7v2 MLLP/TCP outbound
- HL7FileService / HL7FileOperation: HL7v2 file-based
- HL7HTTPService / HL7HTTPOperation: HL7v2 HTTP-based
- FHIRRESTService: FHIR R4/R5 REST inbound
- FHIRRESTOperation: FHIR R4/R5 REST outbound
- FHIRRoutingEngine: FHIR resource routing
"""

from Engine.li.hosts.base import (
    Host,
    HostState,
    HostMetrics,
    BusinessService,
    BusinessProcess,
    BusinessOperation,
)
from Engine.li.hosts.hl7 import (
    HL7TCPService,
    HL7TCPOperation,
    HL7FileService,
    HL7FileOperation,
    HL7HTTPService,
    HL7HTTPOperation,
    HL7Message,
    SendResult,
    HL7SendError,
    HL7RetryError,
)
from Engine.li.hosts.routing import (
    HL7RoutingEngine,
    RoutingRule,
    RoutingResult,
    RuleAction,
    ConditionEvaluator,
    create_message_type_rule,
    create_facility_rule,
)
from Engine.li.hosts.fhir import (
    FHIRRESTService,
    FHIRRESTOperation,
    FHIRMessage,
    FHIRSendResult,
    FHIRSendError,
)
from Engine.li.hosts.fhir_routing import (
    FHIRRoutingEngine,
    FHIRRoutingRule,
    FHIRRoutingResult,
    FHIRRuleAction,
    FHIRConditionEvaluator,
    create_resource_type_rule,
    create_bundle_type_rule,
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
    "HL7FileService",
    "HL7FileOperation",
    "HL7HTTPService",
    "HL7HTTPOperation",
    "HL7Message",
    "SendResult",
    "HL7SendError",
    "HL7RetryError",
    # HL7 Routing
    "HL7RoutingEngine",
    "RoutingRule",
    "RoutingResult",
    "RuleAction",
    "ConditionEvaluator",
    "create_message_type_rule",
    "create_facility_rule",
    # FHIR hosts
    "FHIRRESTService",
    "FHIRRESTOperation",
    "FHIRMessage",
    "FHIRSendResult",
    "FHIRSendError",
    # FHIR Routing
    "FHIRRoutingEngine",
    "FHIRRoutingRule",
    "FHIRRoutingResult",
    "FHIRRuleAction",
    "FHIRConditionEvaluator",
    "create_resource_type_rule",
    "create_bundle_type_rule",
]
