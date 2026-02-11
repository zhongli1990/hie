"""
LI HL7 Routing Engine

Provides rule-based message routing for HL7v2 messages.
Routes messages to different targets based on message content.

This is the LI equivalent of IRIS EnsLib.HL7.MsgRouter.RoutingEngine.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

import structlog

from Engine.li.hosts.base import BusinessProcess
from Engine.li.hosts.hl7 import HL7Message
from Engine.li.schemas.hl7 import HL7ParsedView
from Engine.li.registry import ClassRegistry

if TYPE_CHECKING:
    from Engine.li.config import ItemConfig

logger = structlog.get_logger(__name__)


class RuleAction(str, Enum):
    """Action to take when a rule matches."""
    SEND = "send"       # Send to target
    TRANSFORM = "transform"  # Transform then send
    DELETE = "delete"   # Discard message
    DEFER = "defer"     # Defer processing


@dataclass
class RoutingRule:
    """
    A single routing rule.
    
    Rules are evaluated in order. First matching rule determines the action.
    """
    name: str
    condition: str  # Condition expression
    action: RuleAction
    target: str | None = None  # Target host name
    transform: str | None = None  # Transform class name
    enabled: bool = True
    description: str = ""
    
    # Compiled condition (cached)
    _compiled: Any = field(default=None, repr=False)


@dataclass
class RoutingResult:
    """Result of routing evaluation."""
    matched: bool
    rule_name: str | None = None
    action: RuleAction | None = None
    targets: list[str] = field(default_factory=list)
    transform: str | None = None
    
    def __repr__(self) -> str:
        return f"RoutingResult(matched={self.matched}, rule={self.rule_name}, targets={self.targets})"


class ConditionEvaluator:
    """
    Evaluates routing conditions against HL7 messages.
    
    Condition Syntax:
        - Field access: {MSH-9.1}, {PID-3.1}, {OBX(1)-5}
        - Comparisons: =, !=, <, >, <=, >=, Contains, StartsWith, EndsWith
        - Logical: AND, OR, NOT
        - Grouping: ( )
        - Wildcards: * (any), ? (single char)
    
    Examples:
        - {MSH-9.1} = "ADT"
        - {MSH-9.1} = "ADT" AND {MSH-9.2} = "A01"
        - {PID-3.1} StartsWith "NHS"
        - {MSH-9.1} IN ("ADT", "ORM", "ORU")
        - NOT ({MSH-9.1} = "ACK")
    """
    
    # Pattern to extract field references
    FIELD_PATTERN = re.compile(r'\{([A-Z]{2,3}(?:\(\d+\))?-\d+(?:\.\d+)*)\}')
    
    def __init__(self):
        self._cache: dict[str, Callable] = {}
    
    def evaluate(self, condition: str, message: HL7Message | HL7ParsedView) -> bool:
        """
        Evaluate a condition against a message.
        
        Args:
            condition: Condition expression
            message: HL7 message to evaluate
            
        Returns:
            True if condition matches
        """
        if not condition or condition.strip() == "":
            return True  # Empty condition always matches
        
        # Get parsed view
        if isinstance(message, HL7Message):
            parsed = message.parsed
        else:
            parsed = message
        
        if not parsed:
            return False
        
        try:
            # Replace field references with actual values
            evaluated = self._substitute_fields(condition, parsed)
            
            # Evaluate the expression
            return self._evaluate_expression(evaluated)
        
        except Exception as e:
            logger.warning("condition_evaluation_error", condition=condition, error=str(e))
            return False
    
    def _substitute_fields(self, condition: str, parsed: HL7ParsedView) -> str:
        """Replace field references with quoted values."""
        def replace_field(match):
            path = match.group(1)
            value = parsed.get_field(path, "")
            # Escape quotes and wrap in quotes
            if value is None:
                value = ""
            value = str(value).replace('"', '\\"')
            return f'"{value}"'
        
        return self.FIELD_PATTERN.sub(replace_field, condition)
    
    def _split_outside_parens(self, expr: str, delimiter: str) -> list[str]:
        """
        Split expression by delimiter, but only outside of parentheses.
        
        Args:
            expr: Expression to split
            delimiter: Delimiter to split on (case-insensitive)
            
        Returns:
            List of parts
        """
        parts = []
        current = []
        depth = 0
        i = 0
        delim_upper = delimiter.upper()
        
        while i < len(expr):
            c = expr[i]
            
            if c == "(":
                depth += 1
                current.append(c)
            elif c == ")":
                depth -= 1
                current.append(c)
            elif depth == 0:
                # Check if delimiter starts here (case-insensitive)
                remaining = expr[i:].upper()
                if remaining.startswith(delim_upper):
                    # Found delimiter outside parens
                    parts.append("".join(current).strip())
                    current = []
                    i += len(delimiter)
                    continue
                else:
                    current.append(c)
            else:
                current.append(c)
            
            i += 1
        
        # Add final part
        if current:
            parts.append("".join(current).strip())
        
        return [p for p in parts if p]
    
    def _evaluate_expression(self, expr: str) -> bool:
        """
        Evaluate a substituted expression.
        
        Supports: =, !=, <, >, <=, >=, Contains, StartsWith, EndsWith, IN, AND, OR, NOT
        """
        expr = expr.strip()
        
        # Handle empty
        if not expr:
            return True
        
        # Handle parentheses first - find matching pairs
        if expr.startswith("("):
            # Find matching closing paren
            depth = 0
            for i, c in enumerate(expr):
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        # Found matching paren
                        if i == len(expr) - 1:
                            # Entire expression is wrapped
                            return self._evaluate_expression(expr[1:-1])
                        else:
                            # There's more after the paren group
                            break
                        
        # Handle OR (lowest precedence) - but not inside parentheses
        or_parts = self._split_outside_parens(expr, " OR ")
        if len(or_parts) > 1:
            return any(self._evaluate_expression(p) for p in or_parts)
        
        # Handle AND - but not inside parentheses
        and_parts = self._split_outside_parens(expr, " AND ")
        if len(and_parts) > 1:
            return all(self._evaluate_expression(p) for p in and_parts)
        
        # Handle NOT
        if expr.upper().startswith("NOT "):
            return not self._evaluate_expression(expr[4:])
        
        # Handle IN operator
        in_match = re.match(r'^"([^"]*)"?\s+IN\s+\(([^)]+)\)$', expr, re.IGNORECASE)
        if in_match:
            value = in_match.group(1)
            items = [s.strip().strip('"') for s in in_match.group(2).split(",")]
            return value in items
        
        # Handle Contains
        contains_match = re.match(r'^"([^"]*)"?\s+Contains\s+"([^"]*)"$', expr, re.IGNORECASE)
        if contains_match:
            return contains_match.group(2) in contains_match.group(1)
        
        # Handle StartsWith
        starts_match = re.match(r'^"([^"]*)"?\s+StartsWith\s+"([^"]*)"$', expr, re.IGNORECASE)
        if starts_match:
            return starts_match.group(1).startswith(starts_match.group(2))
        
        # Handle EndsWith
        ends_match = re.match(r'^"([^"]*)"?\s+EndsWith\s+"([^"]*)"$', expr, re.IGNORECASE)
        if ends_match:
            return ends_match.group(1).endswith(ends_match.group(2))
        
        # Handle comparison operators
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
        
        # If just a quoted string, treat as truthy check
        if expr.startswith('"') and expr.endswith('"'):
            return bool(expr[1:-1])
        
        return False


class HL7RoutingEngine(BusinessProcess):
    """
    HL7v2 Message Routing Engine.
    
    Routes messages to different targets based on configurable rules.
    Supports complex conditions based on message content.
    
    This is the LI equivalent of IRIS EnsLib.HL7.MsgRouter.RoutingEngine.
    
    Settings (Host):
        BusinessRuleName: Name of the routing rule set
        Validation: Validation mode ("None", "Warn", "Error")
        BadMessageHandler: Target for invalid messages
        ResponseFrom: Which target's response to return
        AlertOnBadMessage: Alert on invalid messages (default: true)
    
    Example IRIS Config:
        <Item Name="HL7.Router" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true">
            <Setting Target="Host" Name="BusinessRuleName">BRI.HL7.Router.Rules</Setting>
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
        self._rules: list[RoutingRule] = []
        self._evaluator = ConditionEvaluator()
        self._validation = self.get_setting("Host", "Validation", "None")
        self._bad_message_handler = self.get_setting("Host", "BadMessageHandler")
        self._response_from = self.get_setting("Host", "ResponseFrom")
        
        self._log = logger.bind(
            host="HL7RoutingEngine",
            name=name,
            rule_name=self.business_rule_name,
        )
    
    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule."""
        self._rules.append(rule)
        self._log.debug("rule_added", rule_name=rule.name, condition=rule.condition)
    
    def add_rules(self, rules: list[RoutingRule]) -> None:
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
                    "name": "ADT_A01_Route",
                    "condition": "{MSH-9.1} = \"ADT\" AND {MSH-9.2} = \"A01\"",
                    "action": "send",
                    "target": "HL7.Out.PAS"
                },
                ...
            ]
        }
        """
        rules_config = config.get("rules", [])
        
        for rule_config in rules_config:
            rule = RoutingRule(
                name=rule_config.get("name", "Unnamed"),
                condition=rule_config.get("condition", ""),
                action=RuleAction(rule_config.get("action", "send")),
                target=rule_config.get("target"),
                transform=rule_config.get("transform"),
                enabled=rule_config.get("enabled", True),
                description=rule_config.get("description", ""),
            )
            self.add_rule(rule)
    
    async def on_start(self) -> None:
        """Initialize routing engine."""
        await super().on_start()
        
        # Load rules from business rule name if configured
        rule_name = self.business_rule_name
        if rule_name:
            # TODO: Load rules from rule repository
            self._log.info("routing_engine_started", rule_name=rule_name, rule_count=len(self._rules))
        else:
            self._log.info("routing_engine_started", rule_count=len(self._rules))
    
    async def on_message(self, message: Any) -> Any:
        """
        Route an HL7 message.
        
        Evaluates rules in order and routes to matching targets.
        
        Args:
            message: HL7Message to route
            
        Returns:
            RoutingResult with matched targets
        """
        if not isinstance(message, HL7Message):
            # Wrap raw bytes in HL7Message
            if isinstance(message, bytes):
                from Engine.li.schemas.hl7 import HL7Schema
                schema = HL7Schema(name="2.4")
                parsed = schema.parse(message)
                message = HL7Message(raw=message, parsed=parsed)
            else:
                return message
        
        # Validate if configured
        if self._validation != "None" and message.validation_errors:
            if self._validation == "Error":
                if self._bad_message_handler:
                    self._log.warning(
                        "routing_bad_message",
                        errors=len(message.validation_errors),
                        handler=self._bad_message_handler,
                    )
                    # TODO: Route to bad message handler
                return RoutingResult(matched=False)
            else:
                self._log.warning(
                    "routing_validation_warning",
                    errors=len(message.validation_errors),
                )
        
        # Evaluate rules
        result = self._evaluate_rules(message)
        
        self._log.debug(
            "routing_evaluated",
            message_type=message.message_type,
            matched=result.matched,
            rule=result.rule_name,
            targets=result.targets,
        )
        
        # Route to targets
        if result.matched and result.targets:
            for target in result.targets:
                await self._route_to_target(message, target, result.transform)
        
        # Store message in portal_messages for visibility
        project_id = getattr(self, 'project_id', None)
        if project_id:
            import asyncio
            asyncio.create_task(self._store_routing_message(
                project_id=project_id,
                message=message,
                result=result,
            ))
        
        return result
    
    async def _store_routing_message(
        self,
        project_id: UUID,
        message: HL7Message,
        result: RoutingResult,
    ) -> None:
        """Store routing decision in portal_messages for UI visibility."""
        try:
            from Engine.api.services.message_store import store_and_complete_message
            raw = message.raw if isinstance(message.raw, bytes) else str(message.raw).encode()
            status = "completed" if result.matched else "no_match"
            dest = ",".join(result.targets) if result.targets else None
            await store_and_complete_message(
                project_id=project_id,
                item_name=self.name,
                item_type="process",
                direction="inbound",
                raw_content=raw,
                status=status,
                source_item=getattr(message, 'source', None),
                destination_item=dest,
            )
        except Exception as e:
            self._log.warning("routing_message_storage_failed", error=str(e))

    def _evaluate_rules(self, message: HL7Message) -> RoutingResult:
        """
        Evaluate routing rules against a message.
        
        Returns the first matching rule's result.
        """
        for rule in self._rules:
            if not rule.enabled:
                continue
            
            try:
                if self._evaluator.evaluate(rule.condition, message):
                    targets = [rule.target] if rule.target else []
                    
                    return RoutingResult(
                        matched=True,
                        rule_name=rule.name,
                        action=rule.action,
                        targets=targets,
                        transform=rule.transform,
                    )
            
            except Exception as e:
                self._log.error(
                    "rule_evaluation_error",
                    rule=rule.name,
                    error=str(e),
                )
        
        # No rule matched - check for default target
        default_targets = self.target_config_names
        if default_targets:
            return RoutingResult(
                matched=True,
                rule_name="default",
                action=RuleAction.SEND,
                targets=default_targets,
            )
        
        return RoutingResult(matched=False)
    
    async def _route_to_target(
        self,
        message: HL7Message,
        target: str,
        transform: str | None = None,
    ) -> None:
        """
        Route a message to a target.
        
        Args:
            message: Message to route
            target: Target host name
            transform: Optional transform to apply
        """
        # Apply transform if specified
        if transform:
            # TODO: Apply transform
            pass
        
        # Send to target via Production
        if not self._production:
            self._log.warning("no_production_reference", host=self.name)
            return
        
        target_host = self._production.get_host(target)
        if target_host:
            try:
                await target_host.submit(message)
                self._log.debug("routed_to_target", target=target, message_type=message.message_type)
                self._metrics.messages_sent += 1
            except Exception as e:
                self._log.error("route_to_target_failed", target=target, error=str(e))
        else:
            self._log.warning("routing_target_not_found", target=target)


# Convenience function to create common routing rules
def create_message_type_rule(
    name: str,
    message_type: str,
    target: str,
    trigger_event: str | None = None,
) -> RoutingRule:
    """
    Create a routing rule based on message type.
    
    Args:
        name: Rule name
        message_type: Message type (e.g., "ADT", "ORM")
        target: Target host name
        trigger_event: Optional trigger event (e.g., "A01", "O01")
        
    Returns:
        RoutingRule
    """
    if trigger_event:
        condition = f'{{MSH-9.1}} = "{message_type}" AND {{MSH-9.2}} = "{trigger_event}"'
    else:
        condition = f'{{MSH-9.1}} = "{message_type}"'
    
    return RoutingRule(
        name=name,
        condition=condition,
        action=RuleAction.SEND,
        target=target,
    )


def create_facility_rule(
    name: str,
    sending_facility: str,
    target: str,
) -> RoutingRule:
    """
    Create a routing rule based on sending facility.
    
    Args:
        name: Rule name
        sending_facility: Sending facility code
        target: Target host name
        
    Returns:
        RoutingRule
    """
    return RoutingRule(
        name=name,
        condition=f'{{MSH-4}} = "{sending_facility}"',
        action=RuleAction.SEND,
        target=target,
    )


# Register core classes with ClassRegistry (internal — protected namespace)
ClassRegistry._register_internal("li.hosts.routing.HL7RoutingEngine", HL7RoutingEngine)

# IRIS compatibility aliases
ClassRegistry.register_alias("EnsLib.HL7.MsgRouter.RoutingEngine", "li.hosts.routing.HL7RoutingEngine")
