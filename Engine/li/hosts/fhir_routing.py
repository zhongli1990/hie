"""
LI FHIR Routing Engine

Routes FHIR messages to different targets based on configurable rules.
Supports routing by resource type, interaction, and FHIRPath-like field access.

IRIS equivalent: Custom routing process for FHIR (IRIS uses HS.FHIRServer
    routing internally; this provides production-level routing like
    EnsLib.HL7.MsgRouter.RoutingEngine but for FHIR resources).

Rhapsody equivalent: Route + FHIR filters
Mirth equivalent:    Channel routing with FHIR data type

The routing engine runs as a standalone async worker loop (BusinessProcess)
with configurable pool_size, queue-based message reception, and full callback
support (on_init, on_start, on_stop, on_teardown, on_before_process,
on_after_process, on_process_error). It can receive any message event and
call any other service item via send_to_targets / send_request_async /
send_request_sync using reliable/sync/async interaction patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING
from uuid import UUID

import structlog

from Engine.li.hosts.base import BusinessProcess
from Engine.li.hosts.fhir import FHIRMessage
from Engine.li.registry import ClassRegistry

if TYPE_CHECKING:
    from Engine.li.config import ItemConfig

logger = structlog.get_logger(__name__)


# =========================================================================
# Routing Data Structures
# =========================================================================

class FHIRRuleAction(str, Enum):
    """Action to take when a FHIR routing rule matches."""
    SEND = "send"
    TRANSFORM = "transform"
    DELETE = "delete"
    DEFER = "defer"


@dataclass
class FHIRRoutingRule:
    """
    A single FHIR routing rule.

    Rules are evaluated in order. ALL matching rules contribute targets
    (not first-match-wins), matching the HL7RoutingEngine behaviour.

    Condition Syntax:
        - Resource type:  resourceType = "Patient"
        - Interaction:    interaction = "create"
        - Field access:   {name.0.family} = "Smith"
        - Bundle type:    bundleType = "transaction"
        - Comparisons:    =, !=, Contains, StartsWith, EndsWith
        - Logical:        AND, OR, NOT
        - Grouping:       ( )
        - Wildcards:      * (always match)

    Examples:
        - resourceType = "Patient"
        - resourceType = "Patient" AND interaction = "create"
        - resourceType IN ("Patient", "Encounter", "Observation")
        - {identifier.0.system} = "https://fhir.nhs.uk/Id/nhs-number"
        - bundleType = "transaction"
    """
    name: str
    condition: str
    action: FHIRRuleAction
    target: str | None = None
    transform: str | None = None
    enabled: bool = True
    description: str = ""


@dataclass
class FHIRRoutingResult:
    """Result of FHIR routing evaluation."""
    matched: bool
    rule_name: str | None = None
    action: FHIRRuleAction | None = None
    targets: list[str] = field(default_factory=list)
    transform: str | None = None

    def __repr__(self) -> str:
        return (
            f"FHIRRoutingResult(matched={self.matched}, "
            f"rule={self.rule_name}, targets={self.targets})"
        )


# =========================================================================
# FHIR Condition Evaluator
# =========================================================================

class FHIRConditionEvaluator:
    """
    Evaluates routing conditions against FHIR messages.

    Supports:
        - Built-in properties: resourceType, interaction, bundleType,
          resourceId, fhirVersion, httpMethod
        - Field access via curly braces: {name.0.family}, {identifier.0.value}
        - Comparisons: =, !=, Contains, StartsWith, EndsWith
        - Set membership: IN ("Patient", "Encounter")
        - Logical: AND, OR, NOT
        - Grouping: ( )
        - Wildcard: * (always true)
    """

    # Pattern for {field.path} references
    FIELD_PATTERN = re.compile(r'\{([a-zA-Z0-9_.]+)\}')

    # Built-in message properties (accessed without curly braces)
    BUILTIN_PROPERTIES = frozenset({
        "resourceType", "interaction", "bundleType", "resourceId",
        "fhirVersion", "httpMethod", "httpPath", "contentType",
    })

    def evaluate(self, condition: str, message: FHIRMessage) -> bool:
        """
        Evaluate a condition against a FHIR message.

        Args:
            condition: Condition expression
            message: FHIRMessage to evaluate

        Returns:
            True if condition matches
        """
        if not condition or condition.strip() in ("", "*"):
            return True

        try:
            # Substitute built-in properties and field references
            substituted = self._substitute_all(condition, message)
            return self._evaluate_expression(substituted)
        except Exception as e:
            logger.warning(
                "fhir_condition_error",
                condition=condition,
                error=str(e),
            )
            return False

    def _substitute_all(self, condition: str, message: FHIRMessage) -> str:
        """Replace all property and field references with quoted values."""
        # Step 1: Replace {field.path} references
        def replace_field(match):
            path = match.group(1)
            value = message.get_field(path, "")
            if value is None:
                value = ""
            return f'"{str(value)}"'

        result = self.FIELD_PATTERN.sub(replace_field, condition)

        # Step 2: Replace built-in property names (unquoted identifiers)
        for prop in self.BUILTIN_PROPERTIES:
            # Only replace if it appears as an unquoted identifier
            # (not inside quotes, not already substituted)
            pattern = re.compile(rf'\b{prop}\b(?!["\'])')
            if pattern.search(result):
                value = self._get_builtin(prop, message)
                result = pattern.sub(f'"{value}"', result)

        return result

    def _get_builtin(self, prop: str, message: FHIRMessage) -> str:
        """Get a built-in property value from a FHIRMessage."""
        mapping = {
            "resourceType": message.resource_type or "",
            "interaction": message.interaction or "",
            "bundleType": message.bundle_type or "",
            "resourceId": message.resource_id or "",
            "fhirVersion": message.fhir_version or "",
            "httpMethod": message.http_method or "",
            "httpPath": message.http_path or "",
            "contentType": message.content_type or "",
        }
        return mapping.get(prop, "")

    def _split_outside_parens(self, expr: str, delimiter: str) -> list[str]:
        """Split expression by delimiter, only outside parentheses and quotes."""
        parts = []
        current: list[str] = []
        depth = 0
        in_quote = False
        i = 0
        delim_upper = delimiter.upper()

        while i < len(expr):
            c = expr[i]

            if c == '"' and (i == 0 or expr[i - 1] != '\\'):
                in_quote = not in_quote
                current.append(c)
            elif not in_quote:
                if c == "(":
                    depth += 1
                    current.append(c)
                elif c == ")":
                    depth -= 1
                    current.append(c)
                elif depth == 0:
                    remaining = expr[i:].upper()
                    if remaining.startswith(delim_upper):
                        parts.append("".join(current).strip())
                        current = []
                        i += len(delimiter)
                        continue
                    else:
                        current.append(c)
                else:
                    current.append(c)
            else:
                current.append(c)

            i += 1

        if current:
            parts.append("".join(current).strip())

        return [p for p in parts if p]

    def _evaluate_expression(self, expr: str) -> bool:
        """Evaluate a fully-substituted expression."""
        expr = expr.strip()

        if not expr:
            return True

        # Handle parentheses
        if expr.startswith("("):
            depth = 0
            for i, c in enumerate(expr):
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        if i == len(expr) - 1:
                            return self._evaluate_expression(expr[1:-1])
                        break

        # OR (lowest precedence)
        or_parts = self._split_outside_parens(expr, " OR ")
        if len(or_parts) > 1:
            return any(self._evaluate_expression(p) for p in or_parts)

        # AND
        and_parts = self._split_outside_parens(expr, " AND ")
        if len(and_parts) > 1:
            return all(self._evaluate_expression(p) for p in and_parts)

        # NOT
        if expr.upper().startswith("NOT "):
            return not self._evaluate_expression(expr[4:])

        # IN operator
        in_match = re.match(
            r'^"([^"]*)"?\s+IN\s+\(([^)]+)\)$', expr, re.IGNORECASE
        )
        if in_match:
            value = in_match.group(1)
            items = [s.strip().strip('"') for s in in_match.group(2).split(",")]
            return value in items

        # Contains
        contains_match = re.match(
            r'^"([^"]*)"?\s+Contains\s+"([^"]*)"$', expr, re.IGNORECASE
        )
        if contains_match:
            return contains_match.group(2) in contains_match.group(1)

        # StartsWith
        starts_match = re.match(
            r'^"([^"]*)"?\s+StartsWith\s+"([^"]*)"$', expr, re.IGNORECASE
        )
        if starts_match:
            return starts_match.group(1).startswith(starts_match.group(2))

        # EndsWith
        ends_match = re.match(
            r'^"([^"]*)"?\s+EndsWith\s+"([^"]*)"$', expr, re.IGNORECASE
        )
        if ends_match:
            return ends_match.group(1).endswith(ends_match.group(2))

        # Comparison operators
        for op, func in [
            ("!=", lambda a, b: a != b),
            ("<=", lambda a, b: a <= b),
            (">=", lambda a, b: a >= b),
            ("=", lambda a, b: a == b),
            ("<", lambda a, b: a < b),
            (">", lambda a, b: a > b),
        ]:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip().strip('"')
                    right = parts[1].strip().strip('"')
                    return func(left, right)

        # Truthy check
        if expr.startswith('"') and expr.endswith('"'):
            return bool(expr[1:-1])

        return False


# =========================================================================
# FHIR Routing Engine — BusinessProcess
# =========================================================================

class FHIRRoutingEngine(BusinessProcess):
    """
    FHIR Resource Routing Engine.

    Routes FHIR messages to different targets based on configurable rules.
    Supports routing by resource type, interaction, and field values.

    Runs as a standalone async worker loop (BusinessProcess) with configurable
    pool_size, queue-based message reception, and full callback support
    (on_init, on_start, on_stop, on_teardown, on_before_process,
    on_after_process, on_process_error).

    Can receive any FHIR or arbitrary message event, and call any other
    service item via send_to_targets / send_request_async / send_request_sync
    using reliable/sync/async interaction patterns.

    Settings (Host):
        BusinessRuleName:   Name of the routing rule set
        Validation:         Validation mode ("None", "Warn", "Error")
        BadMessageHandler:  Target for invalid messages
        ResponseFrom:       Which target's response to return
        AlertOnBadMessage:  Alert on invalid messages (default: true)
        TargetConfigNames:  Default targets if no rule matches

    Example Config:
        <Item Name="FHIR.Router" ClassName="li.hosts.fhir_routing.FHIRRoutingEngine" PoolSize="1" Enabled="true">
            <Setting Target="Host" Name="BusinessRuleName">FHIR.Router.Rules</Setting>
            <Setting Target="Host" Name="Validation">Warn</Setting>
        </Item>
    """

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        # Routing state
        self._rules: list[FHIRRoutingRule] = []
        self._evaluator = FHIRConditionEvaluator()
        self._validation = self.get_setting("Host", "Validation", "None")
        self._bad_message_handler = self.get_setting("Host", "BadMessageHandler")
        self._response_from = self.get_setting("Host", "ResponseFrom")

        self._log = logger.bind(
            host="FHIRRoutingEngine",
            name=name,
            rule_name=self.business_rule_name,
        )

    def add_rule(self, rule: FHIRRoutingRule) -> None:
        """Add a routing rule."""
        self._rules.append(rule)
        self._log.debug("fhir_rule_added", rule_name=rule.name, condition=rule.condition)

    def add_rules(self, rules: list[FHIRRoutingRule]) -> None:
        """Add multiple routing rules."""
        for rule in rules:
            self.add_rule(rule)

    def clear_rules(self) -> None:
        """Clear all routing rules."""
        self._rules.clear()

    def load_rules_from_config(self, config: dict[str, Any]) -> None:
        """
        Load routing rules from configuration.

        Config format:
        {
            "rules": [
                {
                    "name": "Patient_Create_Route",
                    "condition": "resourceType = \"Patient\" AND interaction = \"create\"",
                    "action": "send",
                    "target": "FHIR.Out.PAS"
                },
                {
                    "name": "All_Observations",
                    "condition": "resourceType = \"Observation\"",
                    "action": "send",
                    "target": "FHIR.Out.Analytics"
                }
            ]
        }
        """
        rules_config = config.get("rules", [])

        for rule_config in rules_config:
            rule = FHIRRoutingRule(
                name=rule_config.get("name", "Unnamed"),
                condition=rule_config.get("condition", ""),
                action=FHIRRuleAction(rule_config.get("action", "send")),
                target=rule_config.get("target"),
                transform=rule_config.get("transform"),
                enabled=rule_config.get("enabled", True),
                description=rule_config.get("description", ""),
            )
            self.add_rule(rule)

    async def on_start(self) -> None:
        """Initialize routing engine."""
        await super().on_start()

        rule_name = self.business_rule_name
        if rule_name:
            self._log.info(
                "fhir_routing_engine_started",
                rule_name=rule_name,
                rule_count=len(self._rules),
            )
        else:
            self._log.info(
                "fhir_routing_engine_started",
                rule_count=len(self._rules),
            )

    async def on_message(self, message: Any) -> Any:
        """
        Route a FHIR message.

        Evaluates rules and routes to matching targets.
        Creates per-leg message headers for the Visual Trace.

        Args:
            message: FHIRMessage to route

        Returns:
            FHIRRoutingResult with matched targets
        """
        # Wrap raw bytes or dicts in FHIRMessage if needed
        if not isinstance(message, FHIRMessage):
            if isinstance(message, bytes):
                import json as _json
                try:
                    parsed = _json.loads(message)
                    message = FHIRMessage(
                        raw=message,
                        parsed=parsed,
                        resource_type=parsed.get("resourceType"),
                        resource_id=parsed.get("id"),
                    )
                except Exception:
                    message = FHIRMessage(raw=message)
            elif isinstance(message, dict):
                raw = _json_encode(message)
                message = FHIRMessage(
                    raw=raw,
                    parsed=message,
                    resource_type=message.get("resourceType"),
                    resource_id=message.get("id"),
                )
            else:
                return message

        # Validate if configured
        if self._validation != "None" and message.validation_errors:
            if self._validation == "Error":
                if self._bad_message_handler:
                    self._log.warning(
                        "fhir_routing_bad_message",
                        errors=len(message.validation_errors),
                        handler=self._bad_message_handler,
                    )
                return FHIRRoutingResult(matched=False)
            else:
                self._log.warning(
                    "fhir_routing_validation_warning",
                    errors=len(message.validation_errors),
                )

        # Evaluate rules
        result = self._evaluate_rules(message)

        self._log.debug(
            "fhir_routing_evaluated",
            resource_type=message.resource_type,
            interaction=message.interaction,
            matched=result.matched,
            rule=result.rule_name,
            targets=result.targets,
        )

        # Store per-leg headers BEFORE routing
        target_headers: dict[str, Any] = {}
        project_id = getattr(self, 'project_id', None)
        if project_id and result.matched and result.targets:
            target_headers = await self._store_routing_headers(
                project_id=project_id,
                message=message,
                result=result,
            )

        # Route to targets with per-target header_id
        if result.matched and result.targets:
            for target in result.targets:
                routed_msg = message
                target_hdr = target_headers.get(target)
                if target_hdr and isinstance(message, FHIRMessage):
                    routed_msg = message.with_header_id(target_hdr)
                await self._route_to_target(routed_msg, target, result.transform)

        return result

    async def _store_routing_headers(
        self,
        project_id: UUID,
        message: FHIRMessage,
        result: FHIRRoutingResult,
    ) -> dict[str, UUID | None]:
        """
        Store routing decision using IRIS-convention per-leg trace model.

        Creates ONE header per matched target (not comma-joined).
        Each header has parent_header_id pointing to the inbound header.

        Returns dict mapping target_name -> header_id.
        """
        target_headers: dict[str, UUID | None] = {}
        try:
            from Engine.api.services.message_store import store_message_header

            session_id = message.session_id
            correlation_id = message.correlation_id
            parent_header_id = message.header_id
            body_id = message.body_id

            if not session_id or not result.targets:
                return target_headers

            for target_name in result.targets:
                # Determine target business type
                target_type = 'operation'
                if self._production:
                    target_host = self._production.get_host(target_name)
                    if target_host:
                        from Engine.api.services.message_store import get_business_type
                        target_type = get_business_type(target_host)

                header_id = await store_message_header(
                    project_id=project_id,
                    session_id=session_id,
                    source_config_name=self.name,
                    target_config_name=target_name,
                    source_business_type='process',
                    target_business_type=target_type,
                    message_body_id=body_id,
                    parent_header_id=parent_header_id,
                    message_type=message.message_type,
                    body_class_name='FHIRMessageBody',
                    status='Created',
                    correlation_id=correlation_id,
                    description=f"Rule: {result.rule_name}" if result.rule_name else None,
                )
                target_headers[target_name] = header_id

        except Exception as e:
            self._log.warning("fhir_routing_header_storage_failed", error=str(e))

        return target_headers

    def _evaluate_rules(self, message: FHIRMessage) -> FHIRRoutingResult:
        """
        Evaluate all routing rules against a FHIR message.

        Collects targets from ALL matching rules (not first-match-wins).
        """
        matched_targets: list[str] = []
        matched_rules: list[str] = []
        last_action = FHIRRuleAction.SEND
        last_transform = None

        for rule in self._rules:
            if not rule.enabled:
                continue

            try:
                if self._evaluator.evaluate(rule.condition, message):
                    if rule.target:
                        matched_targets.append(rule.target)
                    matched_rules.append(rule.name)
                    last_action = rule.action
                    if rule.transform:
                        last_transform = rule.transform

            except Exception as e:
                self._log.error(
                    "fhir_rule_evaluation_error",
                    rule=rule.name,
                    error=str(e),
                )

        if matched_targets:
            return FHIRRoutingResult(
                matched=True,
                rule_name=",".join(matched_rules),
                action=last_action,
                targets=matched_targets,
                transform=last_transform,
            )

        # No rule matched — check for default targets
        default_targets = self.target_config_names
        if default_targets:
            return FHIRRoutingResult(
                matched=True,
                rule_name="default",
                action=FHIRRuleAction.SEND,
                targets=default_targets,
            )

        return FHIRRoutingResult(matched=False)

    async def _route_to_target(
        self,
        message: FHIRMessage,
        target: str,
        transform: str | None = None,
    ) -> None:
        """Route a FHIR message to a target host."""
        if transform:
            # TODO: Apply FHIR transform (e.g., StructureMap)
            pass

        if not self._production:
            self._log.warning("no_production_reference", host=self.name)
            return

        target_host = self._production.get_host(target)
        if target_host:
            try:
                await target_host.submit(message)
                self._log.debug(
                    "fhir_routed_to_target",
                    target=target,
                    resource_type=message.resource_type,
                    interaction=message.interaction,
                )
                self._metrics.messages_sent += 1
            except Exception as e:
                self._log.error("fhir_route_to_target_failed", target=target, error=str(e))
        else:
            self._log.warning("fhir_routing_target_not_found", target=target)


# =========================================================================
# Convenience Functions
# =========================================================================

def _json_encode(obj: Any) -> bytes:
    """Encode object to JSON bytes."""
    import json
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def create_resource_type_rule(
    name: str,
    resource_type: str,
    target: str,
    interaction: str | None = None,
) -> FHIRRoutingRule:
    """
    Create a routing rule based on FHIR resource type.

    Args:
        name: Rule name
        resource_type: FHIR resource type (e.g., "Patient")
        target: Target host name
        interaction: Optional interaction filter (e.g., "create")

    Returns:
        FHIRRoutingRule
    """
    if interaction:
        condition = f'resourceType = "{resource_type}" AND interaction = "{interaction}"'
    else:
        condition = f'resourceType = "{resource_type}"'

    return FHIRRoutingRule(
        name=name,
        condition=condition,
        action=FHIRRuleAction.SEND,
        target=target,
    )


def create_bundle_type_rule(
    name: str,
    bundle_type: str,
    target: str,
) -> FHIRRoutingRule:
    """
    Create a routing rule based on Bundle type.

    Args:
        name: Rule name
        bundle_type: Bundle type (e.g., "transaction", "message")
        target: Target host name

    Returns:
        FHIRRoutingRule
    """
    return FHIRRoutingRule(
        name=name,
        condition=f'resourceType = "Bundle" AND bundleType = "{bundle_type}"',
        action=FHIRRuleAction.SEND,
        target=target,
    )


# =========================================================================
# ClassRegistry Registration
# =========================================================================

# Register core class (internal — protected namespace)
ClassRegistry._register_internal("li.hosts.fhir_routing.FHIRRoutingEngine", FHIRRoutingEngine)

# IRIS compatibility alias (IRIS doesn't have a direct equivalent,
# but we register a sensible alias for config import)
ClassRegistry.register_alias("HS.FHIRServer.Interop.Process", "li.hosts.fhir_routing.FHIRRoutingEngine")
