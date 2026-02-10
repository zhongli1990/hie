# Meta-Instantiation & Message Envelope Uplift Plan
**Enforcing Massively Flexible Meta-Instantiation and Protocol-Agnostic Messaging**

**Version:** 1.0.0
**Date:** February 10, 2026
**Status:** DRAFT - Ready for Review
**Target:** Phase 4 (Q3-Q4 2026)

---

## Executive Summary

This plan outlines the implementation strategy for two critical Phase 4 enhancements:

1. **Meta-Instantiation Enhancement**: Enable **ANY** Python class (built-in, predefined, or custom) to be dynamically instantiated as a configurable item with **unlimited flexibility**

2. **Message Envelope Uplift**: Implement protocol-agnostic messaging with schema metadata enabling **ANY** message type to be sent/received by **ANY** service

**Current State:**
- ✅ Basic meta-instantiation via ClassRegistry (Services, Processes, Operations)
- ✅ Simple Message class with envelope/payload separation
- ✅ Configuration-driven instantiation works for registered classes

**Target State:**
- 🎯 **Universal meta-instantiation**: Import and instantiate ANY Python class by fully qualified name
- 🎯 **MessageEnvelope pattern**: Schema-aware, protocol-agnostic messaging (HL7, FHIR, SOAP, JSON, custom)
- 🎯 **Polymorphic messaging**: ANY message class can be sent to ANY service
- 🎯 **Zero engine changes** required for custom routes and message types

---

## Part 1: Current State Assessment

### 1.1 Meta-Instantiation (Current)

**File**: `Engine/li/registry/class_registry.py`

**Current Capabilities** ✅:
```python
# 1. Manual registration
ClassRegistry.register_host("li.hosts.hl7.HL7TCPService", HL7TCPService)

# 2. Decorator-based registration
@register_host("li.hosts.hl7.HL7TCPService")
class HL7TCPService(BusinessService):
    pass

# 3. Alias support (IRIS compatibility)
ClassRegistry.register_alias("EnsLib.HL7.Service.TCPService", "li.hosts.hl7.HL7TCPService")

# 4. Lookup by name
host_class = ClassRegistry.get_host_class("li.hosts.hl7.HL7TCPService")
host = host_class(name="MyService", config=config)
```

**Limitations** ⚠️:
1. ❌ **Pre-registration required**: Classes must be registered before instantiation
2. ❌ **Limited to known types**: Only hosts, adapters, transforms, rules
3. ❌ **No dynamic import**: Cannot instantiate arbitrary Python classes
4. ❌ **Registry overhead**: Requires explicit registration for every class
5. ❌ **Custom classes need registration**: User must manually register custom business processes

### 1.2 Message Model (Current)

**File**: `Engine/core/message.py`

**Current Capabilities** ✅:
```python
# Phase 3 Message class
@dataclass
class Message:
    """Simple message with envelope and payload."""
    # Envelope
    message_id: UUID
    correlation_id: UUID
    created_at: datetime
    source: str
    destination: str | None
    priority: Priority

    # Payload
    raw: bytes  # THE AUTHORITATIVE CONTENT
    content_type: str
    encoding: str
    properties: dict[str, Property]  # Typed properties
```

**Limitations** ⚠️:
1. ❌ **No schema metadata**: Cannot determine message type at runtime
2. ❌ **No dynamic parsing**: Each service must manually check content_type and parse
3. ❌ **No validation state**: No built-in validation tracking
4. ❌ **Limited extensibility**: Properties are typed but cumbersome
5. ❌ **Not protocol-agnostic**: Designed primarily for HL7 v2.x

**Current Host Integration**:
```python
class Host(MessageBroker, ABC):
    async def on_message(self, message: Message) -> Any:
        """Process incoming message."""
        # Manual parsing required
        if message.content_type == "application/hl7-v2+er7":
            hl7_msg = HL7Message.parse(message.raw)
            # Process HL7 message
        elif message.content_type == "application/json":
            json_msg = json.loads(message.raw)
            # Process JSON message
        # ... manual type checking for each protocol
```

---

## Part 2: Meta-Instantiation Enhancement

### 2.1 Design Principles

1. **Universal Import**: Import ANY Python class by fully qualified name
2. **Zero Pre-Registration**: No manual registration required (but still supported for optimization)
3. **Graceful Fallback**: Try ClassRegistry first (fast), then dynamic import (flexible)
4. **Security Boundaries**: Configurable import restrictions (whitelist/blacklist)
5. **Type Safety**: Validate instantiated classes implement expected interfaces

### 2.2 Enhanced ClassRegistry

**New File**: `Engine/core/meta_instantiation.py`

```python
"""
Universal Meta-Instantiation System

Enables dynamic instantiation of ANY Python class from configuration.
Supports both registered classes (fast) and dynamic import (flexible).
"""

from __future__ import annotations

import importlib
import inspect
from abc import ABC
from typing import Any, Type, TypeVar, get_origin, get_args

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class ImportPolicy:
    """Security policy for dynamic imports."""

    def __init__(
        self,
        allowed_packages: list[str] | None = None,
        blocked_packages: list[str] | None = None,
        require_base_class: Type | None = None
    ):
        """
        Configure import policy.

        Args:
            allowed_packages: Whitelist of allowed package prefixes (None = allow all)
            blocked_packages: Blacklist of blocked package prefixes
            require_base_class: Require imported classes inherit from this base
        """
        self.allowed_packages = allowed_packages or []
        self.blocked_packages = blocked_packages or [
            "os",           # OS operations
            "sys",          # System operations
            "subprocess",   # Command execution
            "importlib",    # Dynamic imports (prevent recursive exploits)
            "pickle",       # Arbitrary code execution
            "__main__",     # Main module
        ]
        self.require_base_class = require_base_class

    def is_allowed(self, module_name: str) -> bool:
        """Check if module is allowed to be imported."""
        # Check blacklist first
        for blocked in self.blocked_packages:
            if module_name.startswith(blocked):
                return False

        # If whitelist exists, must match
        if self.allowed_packages:
            return any(module_name.startswith(allowed) for allowed in self.allowed_packages)

        return True

    def validate_class(self, cls: Type) -> bool:
        """Validate that class meets requirements."""
        if self.require_base_class:
            return issubclass(cls, self.require_base_class)
        return True


class MetaInstantiator:
    """
    Universal meta-instantiation system.

    Combines ClassRegistry (fast, pre-registered) with dynamic import (flexible, on-demand).
    """

    def __init__(self, policy: ImportPolicy | None = None):
        """
        Initialize meta-instantiator.

        Args:
            policy: Import security policy (default: restrictive)
        """
        self.policy = policy or ImportPolicy(
            allowed_packages=[
                "Engine.",           # HIE engine classes
                "demos.",            # Demo classes
                "custom.",           # User custom classes (by convention)
            ],
            require_base_class=None  # Will be set per context
        )

        # Import cache (avoid re-importing same class)
        self._class_cache: dict[str, Type] = {}

    def import_class(self, fully_qualified_name: str) -> Type:
        """
        Import a class by fully qualified name.

        Args:
            fully_qualified_name: Full class path (e.g., "Engine.li.hosts.hl7.HL7TCPService")

        Returns:
            The imported class

        Raises:
            ImportError: If class cannot be imported
            SecurityError: If import is not allowed by policy
            TypeError: If imported class does not meet requirements

        Examples:
            # Built-in host
            cls = import_class("Engine.li.hosts.hl7.HL7TCPService")

            # Custom business process
            cls = import_class("demos.nhs_trust.lib.nhs_validation_process.NHSValidationProcess")

            # User-defined custom class
            cls = import_class("custom.my_organization.MyCustomRouter")
        """
        # Check cache first
        if fully_qualified_name in self._class_cache:
            return self._class_cache[fully_qualified_name]

        # Parse fully qualified name
        parts = fully_qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            raise ImportError(f"Invalid class name: {fully_qualified_name}. Must be module.ClassName")

        module_name, class_name = parts

        # Security check
        if not self.policy.is_allowed(module_name):
            raise SecurityError(f"Import not allowed by policy: {module_name}")

        # Dynamic import
        try:
            logger.debug("importing_class", module=module_name, class_name=class_name)
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot import {fully_qualified_name}: {e}")

        # Validate class
        if not inspect.isclass(cls):
            raise TypeError(f"{fully_qualified_name} is not a class")

        if not self.policy.validate_class(cls):
            raise TypeError(
                f"{fully_qualified_name} does not meet requirements "
                f"(must inherit from {self.policy.require_base_class})"
            )

        # Cache and return
        self._class_cache[fully_qualified_name] = cls
        logger.info("class_imported", class_name=fully_qualified_name)

        return cls

    def instantiate(
        self,
        fully_qualified_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Import and instantiate a class in one step.

        Args:
            fully_qualified_name: Full class path
            *args: Positional arguments for class constructor
            **kwargs: Keyword arguments for class constructor

        Returns:
            Instance of the class

        Examples:
            # Instantiate with constructor arguments
            host = instantiate(
                "Engine.li.hosts.hl7.HL7TCPService",
                name="MyService",
                config=config
            )
        """
        cls = self.import_class(fully_qualified_name)

        try:
            instance = cls(*args, **kwargs)
            logger.info("class_instantiated", class_name=fully_qualified_name)
            return instance
        except Exception as e:
            raise RuntimeError(f"Failed to instantiate {fully_qualified_name}: {e}")


class SecurityError(Exception):
    """Raised when import is blocked by security policy."""
    pass


# Global instantiators for different contexts
_host_instantiator = None
_adapter_instantiator = None
_transform_instantiator = None


def get_host_instantiator() -> MetaInstantiator:
    """Get global host instantiator."""
    global _host_instantiator
    if _host_instantiator is None:
        from Engine.li.hosts.base import Host
        _host_instantiator = MetaInstantiator(
            policy=ImportPolicy(
                allowed_packages=["Engine.", "demos.", "custom."],
                require_base_class=Host
            )
        )
    return _host_instantiator


def get_adapter_instantiator() -> MetaInstantiator:
    """Get global adapter instantiator."""
    global _adapter_instantiator
    if _adapter_instantiator is None:
        from Engine.li.adapters.base import Adapter
        _adapter_instantiator = MetaInstantiator(
            policy=ImportPolicy(
                allowed_packages=["Engine.", "demos.", "custom."],
                require_base_class=Adapter
            )
        )
    return _adapter_instantiator


def import_host_class(fully_qualified_name: str) -> Type:
    """
    Import a host class by fully qualified name.

    Convenience function that uses the global host instantiator.
    """
    return get_host_instantiator().import_class(fully_qualified_name)


def instantiate_host(fully_qualified_name: str, *args, **kwargs) -> Any:
    """
    Import and instantiate a host class.

    Convenience function that uses the global host instantiator.
    """
    return get_host_instantiator().instantiate(fully_qualified_name, *args, **kwargs)
```

### 2.3 Enhanced ClassRegistry with Fallback

**Update File**: `Engine/li/registry/class_registry.py`

```python
# Add to ClassRegistry class

@classmethod
def get_or_import_host_class(cls, name: str) -> Type[Any]:
    """
    Get a host class by name with automatic import fallback.

    Strategy:
    1. Try ClassRegistry (fast, pre-registered)
    2. Try dynamic import (flexible, on-demand)
    3. Raise if neither works

    Args:
        name: Class name (can be alias, short name, or fully qualified name)

    Returns:
        Host class

    Examples:
        # Pre-registered class (fast path)
        cls = get_or_import_host_class("li.hosts.hl7.HL7TCPService")

        # Fully qualified name (dynamic import)
        cls = get_or_import_host_class("Engine.li.hosts.hl7.HL7TCPService")

        # Custom user class (dynamic import)
        cls = get_or_import_host_class("custom.my_org.MyCustomProcess")
    """
    # 1. Try registry first (fast)
    host_class = cls.get_host_class(name)
    if host_class is not None:
        logger.debug("host_class_from_registry", name=name)
        return host_class

    # 2. Try dynamic import (flexible)
    try:
        from Engine.core.meta_instantiation import import_host_class
        host_class = import_host_class(name)
        logger.info("host_class_dynamically_imported", name=name)

        # Cache in registry for future use
        cls.register_host(name, host_class)

        return host_class
    except Exception as e:
        raise ValueError(
            f"Cannot find or import host class '{name}'. "
            f"Not in registry and dynamic import failed: {e}"
        )
```

### 2.4 ProductionEngine Integration

**Update File**: `Engine/li/engine/production.py`

```python
class ProductionEngine:
    async def create_host_from_config(self, item_config: ItemConfig) -> Host:
        """
        Create host instance from configuration.

        Uses enhanced meta-instantiation with automatic import fallback.
        """
        class_name = item_config.class_name

        logger.info(
            "creating_host",
            name=item_config.name,
            class_name=class_name,
            type=item_config.item_type
        )

        # Get or import class (with automatic fallback)
        host_class = ClassRegistry.get_or_import_host_class(class_name)

        # Instantiate with configuration
        host = host_class(
            name=item_config.name,
            config=item_config
        )

        logger.info("host_created", name=item_config.name, class_name=class_name)

        return host
```

### 2.5 Portal UI Integration

**Configuration Form** (Portal UI):

```typescript
// Item configuration form - class name selection

// Built-in classes (dropdown)
<Select name="class_name" label="Class Type">
  <optgroup label="Built-in Services">
    <option value="Engine.li.hosts.hl7.HL7TCPService">HL7 TCP Service</option>
    <option value="Engine.li.hosts.file.FileService">File Service</option>
    <option value="Engine.li.hosts.http.HTTPService">HTTP Service</option>
  </optgroup>

  <optgroup label="Built-in Operations">
    <option value="Engine.li.hosts.hl7.HL7TCPOperation">HL7 TCP Operation</option>
    <option value="Engine.li.hosts.file.FileOperation">File Operation</option>
  </optgroup>

  <optgroup label="Built-in Processes">
    <option value="Engine.li.hosts.routing.RoutingEngine">Routing Engine</option>
  </optgroup>

  <optgroup label="Custom Classes">
    <option value="__custom__">Custom Class (Enter Fully Qualified Name)</option>
  </optgroup>
</Select>

// Custom class name input (shown when "Custom Class" selected)
<Input
  name="custom_class_name"
  label="Fully Qualified Class Name"
  placeholder="e.g., custom.my_org.MyCustomProcess"
  helperText="Enter the full Python import path (module.ClassName)"
  visible={classNameSelection === "__custom__"}
/>

// Examples help text
<Alert severity="info">
  <strong>Custom Class Examples:</strong>
  <ul>
    <li>Demo: <code>demos.nhs_trust.lib.nhs_validation_process.NHSValidationProcess</code></li>
    <li>Custom: <code>custom.my_organization.MyCustomRouter</code></li>
    <li>Third-party: <code>third_party.vendor.VendorIntegration</code></li>
  </ul>

  <strong>Requirements:</strong>
  <ul>
    <li>Must inherit from <code>Host</code> base class</li>
    <li>Must be importable from Python path</li>
    <li>Must implement required abstract methods</li>
  </ul>
</Alert>
```

### 2.6 Configuration Schema Updates

**Update**: `Engine/li/config/item_config.py`

```python
from pydantic import BaseModel, Field, validator

class ItemConfig(BaseModel):
    """Item configuration with flexible class name."""

    name: str
    display_name: str | None = None
    class_name: str  # Fully qualified class name (any valid Python class)
    item_type: Literal["SERVICE", "PROCESS", "OPERATION"]
    enabled: bool = True

    # ... other fields

    @validator("class_name")
    def validate_class_name(cls, v):
        """Validate class name format."""
        parts = v.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(
                "class_name must be fully qualified (module.ClassName), "
                f"got: {v}"
            )

        module_name, class_name = parts

        # Validate class name is valid Python identifier
        if not class_name.isidentifier():
            raise ValueError(f"Invalid class name: {class_name}")

        return v
```

---

## Part 3: Message Envelope Uplift

### 3.1 Design Principles

1. **Schema-Aware**: Header contains schema metadata (content_type, schema_version, body_class_name)
2. **Protocol-Agnostic**: Works with ANY protocol (HL7, FHIR, SOAP, JSON, custom)
3. **Lazy Parsing**: Parse on demand, cache result
4. **Validation State**: Track validation status and errors
5. **Unlimited Extensibility**: Custom properties in both header and body
6. **Backward Compatible**: Phase 3 Message class still works

### 3.2 MessageEnvelope Implementation

**New File**: `Engine/core/message_envelope.py`

```python
"""
Message Envelope Pattern (Phase 4)

Protocol-agnostic messaging with schema metadata enabling
runtime dynamic parsing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MessageHeader:
    """
    Message envelope header containing metadata.

    The header provides all information needed to route, process,
    and parse the message without inspecting the payload.
    """

    # Core identity
    message_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Routing
    source: str = ""
    destination: str = ""

    # Schema metadata (Phase 4 - enables runtime dynamic parsing)
    body_class_name: str = "Engine.core.message.GenericMessage"  # Fully qualified class name
    content_type: str = "application/octet-stream"                # MIME type
    schema_version: str = "1.0"                                   # Protocol version
    encoding: str = "utf-8"                                       # Character encoding

    # Delivery & priority
    priority: int = 5  # 0-9 (0 = highest, 9 = lowest)
    ttl: Optional[int] = None  # Time-to-live in seconds
    retry_count: int = 0

    # Custom properties (unlimited extensibility)
    custom_properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize header to dictionary."""
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "destination": self.destination,
            "body_class_name": self.body_class_name,
            "content_type": self.content_type,
            "schema_version": self.schema_version,
            "encoding": self.encoding,
            "priority": self.priority,
            "ttl": self.ttl,
            "retry_count": self.retry_count,
            "custom_properties": self.custom_properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageHeader:
        """Deserialize header from dictionary."""
        # Handle datetime
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return cls(**data)


@dataclass
class MessageBody:
    """
    Message envelope body containing payload.

    The body contains the actual message content (raw bytes)
    and optional parsed representation (lazy-loaded).
    """

    # Schema reference (Phase 4)
    schema_name: str = "GenericMessage"              # Logical schema name (e.g., "ADT_A01", "Patient")
    schema_namespace: str = "urn:hie:generic"        # Schema namespace/URI

    # Payload
    raw_payload: bytes = b""                         # THE AUTHORITATIVE CONTENT (always preserved)
    _parsed_payload: Any = None                      # Lazy-loaded parsed object (transient, not serialized)

    # Validation state (Phase 4)
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)

    # Custom properties (unlimited extensibility)
    custom_properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize body to dictionary.

        Note: _parsed_payload is NOT serialized (transient).
        Only raw_payload is preserved.
        """
        return {
            "schema_name": self.schema_name,
            "schema_namespace": self.schema_namespace,
            "raw_payload": self.raw_payload.hex(),  # Hex encode for JSON
            "validated": self.validated,
            "validation_errors": self.validation_errors,
            "custom_properties": self.custom_properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageBody:
        """Deserialize body from dictionary."""
        # Decode hex payload
        if "raw_payload" in data and isinstance(data["raw_payload"], str):
            data["raw_payload"] = bytes.fromhex(data["raw_payload"])

        return cls(**data)


@dataclass
class MessageEnvelope:
    """
    Complete message envelope (header + body).

    The envelope combines routing/schema metadata (header) with
    payload content (body), enabling protocol-agnostic messaging.
    """

    header: MessageHeader
    body: MessageBody

    def parse(self) -> Any:
        """
        Parse raw_payload into typed object based on content_type.

        Uses header.body_class_name for meta-instantiation if available,
        otherwise falls back to content_type-based parsing.

        Returns:
            Parsed message object (cached in _parsed_payload)
        """
        # Return cached if available
        if self.body._parsed_payload is not None:
            return self.body._parsed_payload

        logger.debug(
            "parsing_message",
            content_type=self.header.content_type,
            body_class_name=self.header.body_class_name
        )

        # Strategy 1: Use body_class_name for meta-instantiation
        if self.header.body_class_name != "Engine.core.message.GenericMessage":
            try:
                from Engine.core.meta_instantiation import get_host_instantiator

                # Import message class
                instantiator = get_host_instantiator()
                instantiator.policy.require_base_class = None  # Allow any message class

                message_class = instantiator.import_class(self.header.body_class_name)

                # Parse using class-specific parser
                if hasattr(message_class, 'parse'):
                    self.body._parsed_payload = message_class.parse(
                        self.body.raw_payload,
                        version=self.header.schema_version
                    )
                else:
                    # Instantiate directly
                    self.body._parsed_payload = message_class(self.body.raw_payload)

                logger.debug("message_parsed_via_class", class_name=self.header.body_class_name)
                return self.body._parsed_payload

            except Exception as e:
                logger.warning("class_parsing_failed", error=str(e), fallback="content_type")

        # Strategy 2: Fall back to content_type-based parsing
        if self.header.content_type == "application/hl7-v2+er7":
            from Engine.li.messages.hl7 import HL7Message
            self.body._parsed_payload = HL7Message.parse(
                self.body.raw_payload,
                version=self.header.schema_version
            )

        elif self.header.content_type == "application/fhir+json":
            from Engine.li.messages.fhir import FHIRResource
            self.body._parsed_payload = FHIRResource.parse_json(
                self.body.raw_payload,
                version=self.header.schema_version
            )

        elif self.header.content_type == "application/json":
            import json
            self.body._parsed_payload = json.loads(self.body.raw_payload.decode(self.header.encoding))

        elif self.header.content_type == "application/xml":
            import xml.etree.ElementTree as ET
            self.body._parsed_payload = ET.fromstring(self.body.raw_payload)

        else:
            # Generic/unknown type - return raw bytes
            self.body._parsed_payload = self.body.raw_payload

        logger.debug("message_parsed_via_content_type", content_type=self.header.content_type)

        return self.body._parsed_payload

    def validate(self) -> bool:
        """
        Validate message against schema.

        Returns:
            True if valid, False if validation failed
        """
        try:
            parsed = self.parse()

            # Call type-specific validation if available
            if hasattr(parsed, 'validate'):
                is_valid, errors = parsed.validate()
                self.body.validated = is_valid
                self.body.validation_errors = errors
                return is_valid
            else:
                # No validation available - assume valid
                self.body.validated = True
                return True

        except Exception as e:
            self.body.validated = False
            self.body.validation_errors = [f"Validation error: {str(e)}"]
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize envelope to dictionary."""
        return {
            "header": self.header.to_dict(),
            "body": self.body.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageEnvelope:
        """Deserialize envelope from dictionary."""
        return cls(
            header=MessageHeader.from_dict(data["header"]),
            body=MessageBody.from_dict(data["body"])
        )

    # Factory methods for convenience

    @classmethod
    def create_hl7(
        cls,
        raw_payload: bytes,
        version: str,
        source: str,
        destination: str,
        priority: int = 5
    ) -> MessageEnvelope:
        """Create HL7 v2.x message envelope."""
        header = MessageHeader(
            source=source,
            destination=destination,
            body_class_name="Engine.li.messages.hl7.HL7Message",
            content_type="application/hl7-v2+er7",
            schema_version=version,
            encoding="utf-8",
            priority=priority
        )

        body = MessageBody(
            schema_name="ADT",  # Will be refined after parsing
            schema_namespace="urn:hl7-org:v2",
            raw_payload=raw_payload
        )

        return cls(header=header, body=body)

    @classmethod
    def create_fhir(
        cls,
        resource: Any,  # FHIR Resource
        source: str,
        destination: str,
        fhir_version: str = "R4"
    ) -> MessageEnvelope:
        """Create FHIR message envelope."""
        header = MessageHeader(
            source=source,
            destination=destination,
            body_class_name="Engine.li.messages.fhir.FHIRResource",
            content_type="application/fhir+json",
            schema_version=fhir_version,
            encoding="utf-8",
            priority=5
        )

        body = MessageBody(
            schema_name=resource.resource_type,  # "Patient", "Observation", etc.
            schema_namespace="http://hl7.org/fhir",
            raw_payload=resource.json().encode("utf-8"),
            _parsed_payload=resource  # Cache parsed object
        )

        return cls(header=header, body=body)

    @classmethod
    def create_custom(
        cls,
        raw_payload: bytes,
        schema_name: str,
        schema_namespace: str,
        content_type: str,
        source: str,
        destination: str,
        body_class_name: str | None = None
    ) -> MessageEnvelope:
        """Create custom message envelope."""
        header = MessageHeader(
            source=source,
            destination=destination,
            body_class_name=body_class_name or "Engine.core.message.GenericMessage",
            content_type=content_type,
            schema_version="1.0",
            encoding="utf-8",
            priority=5
        )

        body = MessageBody(
            schema_name=schema_name,
            schema_namespace=schema_namespace,
            raw_payload=raw_payload
        )

        return cls(header=header, body=body)

    @classmethod
    def from_legacy_message(cls, message: Any) -> MessageEnvelope:
        """
        Convert Phase 3 Message to Phase 4 MessageEnvelope.

        Provides backward compatibility.
        """
        from Engine.core.message import Message

        if not isinstance(message, Message):
            raise TypeError(f"Expected Message, got {type(message)}")

        # Extract Phase 3 message fields
        header = MessageHeader(
            message_id=str(message.message_id),
            correlation_id=str(message.correlation_id),
            timestamp=message.created_at,
            source=message.source,
            destination=message.destination or "",
            content_type=message.content_type,
            encoding=message.encoding,
            priority={"low": 7, "normal": 5, "high": 3, "urgent": 1}.get(message.priority, 5)
        )

        body = MessageBody(
            raw_payload=message.raw,
            custom_properties={k: v.value for k, v in message.properties.items()}
        )

        return cls(header=header, body=body)
```

### 3.3 Host Base Class Integration

**Update File**: `Engine/li/hosts/base.py`

```python
class Host(MessageBroker, ABC):
    """
    Base class for all business hosts.

    Supports both Phase 3 Message and Phase 4 MessageEnvelope.
    """

    # Phase 4: New method (preferred)
    async def on_message_envelope(self, envelope: MessageEnvelope) -> Any:
        """
        Process message envelope (Phase 4 preferred method).

        Override this in subclasses for Phase 4 envelope support.
        Default implementation parses envelope and calls on_process_message_content.
        """
        logger.debug(
            "processing_envelope",
            message_id=envelope.header.message_id,
            source=envelope.header.source,
            content_type=envelope.header.content_type
        )

        # Parse if needed
        if self._host_settings.get("ParseMessages", False):
            parsed = envelope.parse()
        else:
            parsed = envelope.body.raw_payload

        # Process
        result = await self.on_process_message_content(parsed, envelope)

        return result

    # Phase 3: Legacy method (backward compatible)
    async def on_message(self, message: Message) -> Any:
        """
        Process message (Phase 3 legacy method).

        Automatically wraps in MessageEnvelope and delegates to on_message_envelope.
        Maintains backward compatibility with Phase 3 code.
        """
        logger.debug("wrapping_legacy_message", message_id=str(message.message_id))

        # Convert to envelope
        envelope = MessageEnvelope.from_legacy_message(message)

        # Delegate to new method
        return await self.on_message_envelope(envelope)

    # Subclasses override this
    @abstractmethod
    async def on_process_message_content(self, content: Any, envelope: MessageEnvelope) -> Any:
        """
        Process parsed message content.

        Args:
            content: Parsed message object (or raw bytes if parsing disabled)
            envelope: Full message envelope (access to header/body/metadata)

        Returns:
            Processing result (or new envelope to forward)
        """
        pass
```

---

## Part 4: Phased Implementation Plan

### Phase 4.1: Meta-Instantiation Enhancement (Sprints 1-2, 3 weeks)

**Week 1: Core Implementation**
- [ ] Create `Engine/core/meta_instantiation.py`
  - ImportPolicy class
  - MetaInstantiator class
  - Global instantiators (hosts, adapters, transforms)
- [ ] Update `Engine/li/registry/class_registry.py`
  - Add `get_or_import_host_class()` method
  - Add fallback logic
- [ ] Unit tests for meta-instantiation
  - Test import from Engine.*
  - Test import from demos.*
  - Test import from custom.*
  - Test security policy (blocked packages)
  - Test validation (must inherit from Host)

**Week 2: ProductionEngine Integration**
- [ ] Update `Engine/li/engine/production.py`
  - Use `get_or_import_host_class()` in `create_host_from_config()`
- [ ] Update `Engine/li/config/item_config.py`
  - Add class_name validator
- [ ] Integration tests
  - Test instantiation of built-in classes
  - Test instantiation of custom demo classes
  - Test error handling (invalid class, security violation)

**Week 3: Portal UI & Documentation**
- [ ] Update Portal UI item configuration form
  - Add custom class name input
  - Add validation
  - Add examples/help text
- [ ] Update Manager API
  - Validate class_name in ItemConfig
  - Return helpful error messages
- [ ] Documentation
  - Update LI_HIE_DEVELOPER_GUIDE.md
  - Add custom class development guide
  - Add examples

**Deliverables**:
- ✅ Universal meta-instantiation system
- ✅ Portal UI supports custom classes
- ✅ Documentation with examples
- ✅ Test coverage >90%

---

### Phase 4.2: Message Envelope Implementation (Sprints 3-4, 3 weeks)

**Week 4: MessageEnvelope Core**
- [ ] Create `Engine/core/message_envelope.py`
  - MessageHeader class
  - MessageBody class
  - MessageEnvelope class
  - Factory methods (create_hl7, create_fhir, create_custom)
  - from_legacy_message() for backward compatibility
- [ ] Unit tests for message envelope
  - Test header/body creation
  - Test serialization/deserialization
  - Test factory methods
  - Test legacy message conversion

**Week 5: Host Integration**
- [ ] Update `Engine/li/hosts/base.py`
  - Add `on_message_envelope()` method (Phase 4)
  - Update `on_message()` for backward compatibility (Phase 3)
  - Add `on_process_message_content()` abstract method
- [ ] Update existing host implementations
  - HL7TCPService
  - HL7TCPOperation
  - FileService
  - HTTPService
- [ ] Integration tests
  - Test envelope flow through services
  - Test backward compatibility (Phase 3 message still works)
  - Test parse() and validate()

**Week 6: Manager API & Portal UI**
- [ ] Update Manager API
  - Accept MessageEnvelope in /api/messages
  - Support both Phase 3 and Phase 4 formats
- [ ] Update Portal UI
  - Message inspector shows header/body separately
  - Display schema metadata
  - Show validation state
- [ ] Documentation
  - Update message-model.md (already done)
  - Add migration guide (Phase 3 → Phase 4)
  - Add examples

**Deliverables**:
- ✅ MessageEnvelope pattern implemented
- ✅ Backward compatible with Phase 3
- ✅ All hosts support envelopes
- ✅ Portal UI envelope inspector
- ✅ Test coverage >90%

---

### Phase 4.3: End-to-End Testing & Documentation (Sprint 5, 2 weeks)

**Week 7: E2E Testing**
- [ ] NHS Trust demo with custom classes
  - Create `demos.nhs_trust.lib.nhs_validation_process.NHSValidationProcess`
  - Use MessageEnvelope throughout
  - Test HL7 v2.3 → v2.4 → v2.5 transformation
- [ ] Performance testing
  - MessageEnvelope overhead (<1ms per message)
  - Meta-instantiation cache effectiveness
  - Memory usage
- [ ] Load testing
  - 10,000 msg/sec with envelopes
  - Custom class instantiation under load

**Week 8: Documentation & Rollout**
- [ ] Update all architecture docs
  - ✅ PRODUCT_ROADMAP.md (already done)
  - ✅ MESSAGE_ENVELOPE_DESIGN.md (already done)
  - ✅ SCALABILITY_ARCHITECTURE.md (already done)
- [ ] Create migration guide
  - Phase 3 → Phase 4 upgrade steps
  - Code examples
  - Breaking changes (if any)
- [ ] Release notes
  - v2.0.0 features
  - Backward compatibility notes
  - Performance improvements

**Deliverables**:
- ✅ End-to-end demos working
- ✅ Performance benchmarks
- ✅ Complete documentation
- ✅ Release v2.0.0

---

## Part 5: Testing Strategy

### 5.1 Unit Tests

**Meta-Instantiation**:
```python
def test_import_host_class():
    """Test importing built-in host class."""
    instantiator = get_host_instantiator()
    cls = instantiator.import_class("Engine.li.hosts.hl7.HL7TCPService")
    assert cls.__name__ == "HL7TCPService"

def test_import_custom_class():
    """Test importing custom user class."""
    cls = instantiator.import_class("demos.nhs_trust.lib.nhs_validation_process.NHSValidationProcess")
    assert issubclass(cls, Host)

def test_import_security_blocked():
    """Test that blocked packages cannot be imported."""
    with pytest.raises(SecurityError):
        instantiator.import_class("os.system")

def test_import_invalid_base_class():
    """Test that non-Host classes are rejected."""
    with pytest.raises(TypeError):
        instantiator.import_class("datetime.datetime")
```

**MessageEnvelope**:
```python
def test_create_hl7_envelope():
    """Test creating HL7 message envelope."""
    envelope = MessageEnvelope.create_hl7(
        raw_payload=b"MSH|^~\\&|...",
        version="2.4",
        source="Test",
        destination="Target"
    )
    assert envelope.header.content_type == "application/hl7-v2+er7"
    assert envelope.header.schema_version == "2.4"

def test_parse_hl7_envelope():
    """Test parsing HL7 envelope."""
    envelope = MessageEnvelope.create_hl7(...)
    parsed = envelope.parse()
    assert isinstance(parsed, HL7Message)

def test_envelope_serialization():
    """Test envelope serialization round-trip."""
    original = MessageEnvelope.create_hl7(...)
    data = original.to_dict()
    restored = MessageEnvelope.from_dict(data)
    assert restored.header.message_id == original.header.message_id
    assert restored.body.raw_payload == original.body.raw_payload

def test_legacy_message_conversion():
    """Test Phase 3 Message → Phase 4 MessageEnvelope conversion."""
    legacy_msg = Message(...)
    envelope = MessageEnvelope.from_legacy_message(legacy_msg)
    assert envelope.header.message_id == str(legacy_msg.message_id)
```

### 5.2 Integration Tests

```python
async def test_custom_class_instantiation_e2e():
    """Test end-to-end custom class instantiation."""
    config = ItemConfig(
        name="MyCustomProcess",
        class_name="demos.nhs_trust.lib.nhs_validation_process.NHSValidationProcess",
        item_type="PROCESS",
        enabled=True
    )

    engine = ProductionEngine()
    host = await engine.create_host_from_config(config)

    assert isinstance(host, Host)
    assert host.name == "MyCustomProcess"

async def test_envelope_through_pipeline():
    """Test MessageEnvelope flowing through entire pipeline."""
    # Create envelope
    envelope = MessageEnvelope.create_hl7(
        raw_payload=b"MSH|^~\\&|...",
        version="2.4",
        source="Service1",
        destination="Service2"
    )

    # Send through service
    result = await service1.on_message_envelope(envelope)

    # Verify envelope preserved
    assert isinstance(result, MessageEnvelope)
    assert result.header.source == "Service1"
    assert result.body.raw_payload == envelope.body.raw_payload
```

### 5.3 Performance Tests

```python
def test_meta_instantiation_performance():
    """Test meta-instantiation cache performance."""
    instantiator = get_host_instantiator()

    # First import (slow - dynamic import)
    start = time.time()
    cls1 = instantiator.import_class("Engine.li.hosts.hl7.HL7TCPService")
    first_time = time.time() - start

    # Second import (fast - cached)
    start = time.time()
    cls2 = instantiator.import_class("Engine.li.hosts.hl7.HL7TCPService")
    cached_time = time.time() - start

    assert cached_time < first_time * 0.1  # Cached should be 10x+ faster
    assert cached_time < 0.001  # < 1ms

def test_envelope_overhead():
    """Test MessageEnvelope parsing overhead."""
    envelope = MessageEnvelope.create_hl7(...)

    iterations = 1000
    start = time.time()

    for _ in range(iterations):
        parsed = envelope.parse()

    elapsed = time.time() - start
    avg_time = elapsed / iterations

    assert avg_time < 0.001  # < 1ms per parse (with caching)
```

---

## Part 6: Migration Guide

### 6.1 Phase 3 → Phase 4 Migration

**Old (Phase 3)**:
```python
# Manual class import and registration
from Engine.li.hosts.hl7 import HL7TCPService
ClassRegistry.register_host("li.hosts.hl7.HL7TCPService", HL7TCPService)

# Simple message
message = Message(
    message_id=uuid4(),
    source="Service1",
    raw=b"MSH|...",
    content_type="application/hl7-v2+er7"
)

# Manual parsing
async def on_message(self, message: Message):
    if message.content_type == "application/hl7-v2+er7":
        hl7_msg = HL7Message.parse(message.raw)
```

**New (Phase 4)**:
```python
# No registration needed - dynamic import
config = ItemConfig(
    class_name="Engine.li.hosts.hl7.HL7TCPService",
    # or custom class:
    # class_name="custom.my_org.MyCustomProcess"
)

# MessageEnvelope with schema metadata
envelope = MessageEnvelope.create_hl7(
    raw_payload=b"MSH|...",
    version="2.4",
    source="Service1",
    destination="Service2"
)

# Automatic parsing based on content_type
async def on_message_envelope(self, envelope: MessageEnvelope):
    parsed = envelope.parse()  # Automatically selects parser
```

### 6.2 Backward Compatibility

Phase 4 maintains **100% backward compatibility** with Phase 3:

1. **Phase 3 Message still works**: `on_message(message: Message)` automatically wraps in MessageEnvelope
2. **No breaking changes**: Existing hosts continue to work unchanged
3. **Gradual migration**: Update hosts one at a time to use `on_message_envelope()`

---

## Part 7: Success Criteria

### 7.1 Meta-Instantiation

- ✅ Any Python class can be instantiated by fully qualified name
- ✅ No pre-registration required (but supported for optimization)
- ✅ Security policy prevents malicious imports
- ✅ Portal UI supports custom class configuration
- ✅ Performance: Cached imports < 1ms

### 7.2 Message Envelope

- ✅ Protocol-agnostic messaging (HL7, FHIR, SOAP, JSON, custom)
- ✅ Schema-aware parsing (automatic parser selection)
- ✅ Validation state tracked
- ✅ Backward compatible with Phase 3 Message
- ✅ Performance: Envelope overhead < 1ms

### 7.3 End-to-End

- ✅ NHS Trust demo with custom NHSValidationProcess works
- ✅ MessageEnvelope flows through entire pipeline
- ✅ 10,000 msg/sec with envelopes
- ✅ Zero engine changes for custom routes

---

## Part 8: Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Security vulnerability in dynamic import** | Critical | Medium | Strict ImportPolicy, whitelist approach, no eval/exec |
| **Performance degradation** | High | Low | Aggressive caching, benchmarking, profiling |
| **Breaking changes for Phase 3 code** | High | Low | 100% backward compatibility, comprehensive testing |
| **Complex error messages** | Medium | Medium | Clear error messages, validation, examples |
| **Custom class bugs break engine** | Medium | Medium | Isolation, try/catch, graceful degradation |

---

## Conclusion

This implementation plan provides:

1. **Universal Meta-Instantiation**: ANY Python class can be instantiated from configuration
2. **Protocol-Agnostic Messaging**: ANY message type can be sent to ANY service
3. **Zero Engine Changes**: Custom routes require no engine modifications
4. **Backward Compatible**: Phase 3 code continues to work
5. **Production-Ready**: Enterprise-grade security, performance, testing

**Timeline**: 8 weeks (2 months)
**Team**: 2 senior engineers
**Cost**: ~£50K (engineering time)

**ROI**: Enables unlimited extensibility without vendor dependency. NHS trusts can develop custom business processes without modifying engine code.

---

**Document Owner:** HIE Core Team
**Last Updated:** February 10, 2026
**Version:** 1.0.0
**Next Review:** After Phase 4 Sprint 1

---

## References

- [MESSAGE_ENVELOPE_DESIGN.md](MESSAGE_ENVELOPE_DESIGN.md) - Detailed message envelope design
- [SCALABILITY_ARCHITECTURE.md](SCALABILITY_ARCHITECTURE.md) - Technical scalability assessment
- [PRODUCT_ROADMAP.md](../PRODUCT_ROADMAP.md) - Phase 4-6 roadmap
- [ARCHITECTURE_QA_REVIEW.md](ARCHITECTURE_QA_REVIEW.md) - Current architecture assessment
