"""
Message Envelope Pattern (Phase 4)

Protocol-agnostic messaging with schema metadata enabling
runtime dynamic parsing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

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
                from Engine.core.meta_instantiation import MetaInstantiator, ImportPolicy

                # Create instantiator without base class requirement for message classes
                instantiator = MetaInstantiator(
                    policy=ImportPolicy(
                        allowed_packages=["Engine.", "demos.", "custom."],
                        require_base_class=None  # Allow any message class
                    )
                )

                # Import message class
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
            # FHIR parsing would go here in Phase 5
            import json
            self.body._parsed_payload = json.loads(self.body.raw_payload.decode(self.header.encoding))

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
        resource_json: bytes,
        resource_type: str,
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
            schema_name=resource_type,  # "Patient", "Observation", etc.
            schema_namespace="http://hl7.org/fhir",
            raw_payload=resource_json
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
        priority_map = {"low": 7, "normal": 5, "high": 3, "urgent": 1}

        header = MessageHeader(
            message_id=str(message.message_id),
            correlation_id=str(message.correlation_id),
            timestamp=message.created_at,
            source=message.source,
            destination=message.destination or "",
            content_type=message.content_type,
            encoding=message.encoding,
            priority=priority_map.get(message.priority.value if hasattr(message.priority, 'value') else str(message.priority), 5)
        )

        body = MessageBody(
            raw_payload=message.raw,
            custom_properties={k: v.value for k, v in message.properties.items()} if hasattr(message, 'properties') else {}
        )

        return cls(header=header, body=body)
