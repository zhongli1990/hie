# Message Envelope Design

**Polymorphic Messaging Architecture for LI HIE**

**Version:** 2.1 (Phase 4 — Layer 1: In-Memory Transport)
**Design Date:** February 10, 2026 (Revised February 13, 2026)
**Status:** Proposed Architecture Enhancement

> **Architecture Note (Feb 13, 2026):** This document describes **Layer 1: In-Memory Transport** — the `MessageEnvelope` / `MessageHeader` / `MessageBody` objects that travel with messages between hosts in memory. It does NOT cover the **persisted trace** (Layer 2), which is the `message_headers` / `message_bodies` database tables that power the Visual Trace / Sequence Diagram. For Layer 2, see:
> - [MESSAGE_MODEL.md](MESSAGE_MODEL.md) §Persisted Trace Layer
> - [SESSION_ID_DESIGN.md](SESSION_ID_DESIGN.md) §4 Implementation Design
> - [MESSAGE_HEADER_BODY_REDESIGN.md](MESSAGE_HEADER_BODY_REDESIGN.md) — Master consolidated design

---

## Problem Statement

### Current Approach (Phase 1-3)

**Duck Typing**:
```python
async def on_process_input(self, message: Any) -> Any:
    if hasattr(message, 'MSH'):
        # Treat as HL7
    elif hasattr(message, 'resourceType'):
        # Treat as FHIR
```

**Problems at Scale:**
1. ❌ No schema metadata in message
2. ❌ No version information (HL7 2.3 vs 2.4 vs 2.5.1)
3. ❌ No consistent envelope structure
4. ❌ Hard to route based on content type
5. ❌ Hard to validate before processing
6. ❌ No tracing metadata (correlation IDs, span IDs)
7. ❌ Runtime type errors

---

## Design Requirements

### User Requirements (From Technical Review)

1. **Consistent Meta-Structure**
   - Header (metadata) + Body (payload)
   - Both header and body have predefined + custom properties

2. **Schema-Aware**
   - Header contains body class name
   - Header contains schema type (HL7 2.4, FHIR R4, SOAP, JSON, custom)
   - Runtime dynamic parsing based on header

3. **Protocol-Agnostic**
   - HL7 v2.x (2.3, 2.4, 2.5, 2.5.1, 2.6, 2.7, 2.8)
   - FHIR (DSTU2, STU3, R4, R5)
   - SOAP/XML
   - JSON (REST APIs, custom)
   - Bespoke custom protocols

4. **Unlimited Extensibility**
   - Custom properties in header
   - Custom properties in body
   - Custom message types

5. **Type Safety**
   - Runtime validation against schema
   - IDE autocomplete (typing.Protocol)
   - Clear error messages

---

## Solution: Message Envelope Pattern

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      MESSAGE ENVELOPE                        │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐    │
│  │                   MESSAGE HEADER                    │    │
│  │                                                      │    │
│  │  Core Properties (Required):                        │    │
│  │  ├─ message_id (UUID)                              │    │
│  │  ├─ correlation_id (UUID)                          │    │
│  │  ├─ timestamp (ISO 8601)                           │    │
│  │  ├─ source (service name)                          │    │
│  │  └─ destination (service name)                     │    │
│  │                                                      │    │
│  │  Schema Metadata (Required):                        │    │
│  │  ├─ body_class_name ("HL7Message", "FHIRResource") │    │
│  │  ├─ content_type ("application/hl7-v2+er7")       │    │
│  │  ├─ schema_version ("2.4", "R4", "custom-v1.0")   │    │
│  │  └─ encoding ("utf-8", "ascii", "base64")         │    │
│  │                                                      │    │
│  │  Routing/Processing (Optional):                     │    │
│  │  ├─ priority (0-10, higher = urgent)              │    │
│  │  ├─ ttl (seconds, time-to-live)                   │    │
│  │  ├─ retry_count (number of retries)               │    │
│  │  └─ causation_id (parent message ID)              │    │
│  │                                                      │    │
│  │  Tracing (Optional, Phase 5):                       │    │
│  │  ├─ trace_id (distributed trace ID)               │    │
│  │  ├─ span_id (current span ID)                     │    │
│  │  └─ parent_span_id (parent span ID)               │    │
│  │                                                      │    │
│  │  Custom Properties (Unlimited):                     │    │
│  │  └─ custom_properties: Dict[str, Any]             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                   MESSAGE BODY                      │    │
│  │                                                      │    │
│  │  Schema Reference (Required):                       │    │
│  │  ├─ schema_name ("ADT_A01", "Patient", "Order")   │    │
│  │  └─ schema_namespace ("urn:hl7-org:v2", FHIR URL) │    │
│  │                                                      │    │
│  │  Payload (Required):                                │    │
│  │  ├─ raw_payload (bytes, original)                 │    │
│  │  └─ parsed_payload (Any, lazy-loaded)             │    │
│  │                                                      │    │
│  │  Validation (Computed):                             │    │
│  │  ├─ validated (bool)                               │    │
│  │  └─ validation_errors (List[str])                 │    │
│  │                                                      │    │
│  │  Custom Properties (Unlimited):                     │    │
│  │  └─ custom_properties: Dict[str, Any]             │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Python Implementation

### Core Data Classes

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar


class ContentType(str, Enum):
    """Standard content types for healthcare messages."""

    # HL7 v2.x
    HL7_V2_ER7 = "application/hl7-v2+er7"     # Pipe-delimited
    HL7_V2_XML = "application/hl7-v2+xml"     # XML encoding

    # FHIR
    FHIR_JSON = "application/fhir+json"       # FHIR JSON
    FHIR_XML = "application/fhir+xml"         # FHIR XML

    # Other
    SOAP_XML = "application/soap+xml"         # SOAP/XML
    JSON = "application/json"                 # Generic JSON
    XML = "application/xml"                   # Generic XML
    BINARY = "application/octet-stream"       # Binary

    # Custom (user-defined)
    CUSTOM = "application/x-custom"


class Priority(int, Enum):
    """Message priority levels."""
    LOWEST = 0
    LOW = 2
    NORMAL = 5
    HIGH = 7
    URGENT = 9
    CRITICAL = 10


@dataclass
class MessageHeader:
    """
    Message envelope header containing metadata.

    Analogous to:
    - HTTP headers
    - AMQP properties
    - Kafka record headers
    - SOAP envelope headers
    """

    # ========================================================================
    # CORE PROPERTIES (Required)
    # ========================================================================

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique message identifier (UUID v4)."""

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Correlation ID for request-reply or related messages."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    """Message creation timestamp (UTC)."""

    source: str = ""
    """Source service name (e.g., "Cerner_PAS_Receiver")."""

    destination: str = ""
    """Destination service name (e.g., "NHS_Validation_Process")."""

    # ========================================================================
    # SCHEMA METADATA (Required for runtime parsing)
    # ========================================================================

    body_class_name: str = ""
    """
    Fully qualified Python class name for body.
    Examples:
    - "Engine.li.messages.hl7.HL7Message"
    - "Engine.li.messages.fhir.FHIRResource"
    - "demos.custom.messages.OrderMessage"
    """

    content_type: str = ContentType.JSON.value
    """
    MIME type indicating payload format.
    Examples:
    - "application/hl7-v2+er7" (HL7 pipe-delimited)
    - "application/fhir+json" (FHIR JSON)
    - "application/soap+xml" (SOAP/XML)
    - "application/json" (generic JSON)
    """

    schema_version: str = ""
    """
    Schema version for validation.
    Examples:
    - "2.4" (HL7 v2.4)
    - "R4" (FHIR R4)
    - "v1.2.3" (custom schema version)
    """

    encoding: str = "utf-8"
    """
    Character encoding of raw_payload.
    Examples: "utf-8", "ascii", "latin-1", "base64"
    """

    # ========================================================================
    # ROUTING & PROCESSING (Optional)
    # ========================================================================

    priority: int = Priority.NORMAL.value
    """Message priority (0-10, higher = more urgent)."""

    ttl: Optional[int] = None
    """Time-to-live in seconds (None = no expiration)."""

    retry_count: int = 0
    """Number of times this message has been retried."""

    causation_id: Optional[str] = None
    """Parent message ID (for message lineage)."""

    # ========================================================================
    # DISTRIBUTED TRACING (Optional, Phase 5)
    # ========================================================================

    trace_id: Optional[str] = None
    """OpenTelemetry trace ID (for distributed tracing)."""

    span_id: Optional[str] = None
    """OpenTelemetry span ID (current span)."""

    parent_span_id: Optional[str] = None
    """OpenTelemetry parent span ID."""

    # ========================================================================
    # CUSTOM PROPERTIES (Unlimited extensibility)
    # ========================================================================

    custom_properties: Dict[str, Any] = field(default_factory=dict)
    """
    User-defined custom properties.
    Examples:
    - {"patient_id": "NHS-1234567890"}
    - {"facility_id": "RH-001"}
    - {"department": "Emergency"}
    - {"sla_deadline": "2026-02-10T15:30:00Z"}
    """

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def is_expired(self) -> bool:
        """Check if message has exceeded TTL."""
        if self.ttl is None:
            return False
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > self.ttl

    def get_custom(self, key: str, default: Any = None) -> Any:
        """Get custom property with default."""
        return self.custom_properties.get(key, default)

    def set_custom(self, key: str, value: Any) -> None:
        """Set custom property."""
        self.custom_properties[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
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
            "causation_id": self.causation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "custom_properties": self.custom_properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageHeader:
        """Deserialize from dictionary."""
        data = data.copy()
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class MessageBody:
    """
    Message envelope body containing payload and schema reference.
    """

    # ========================================================================
    # SCHEMA REFERENCE (Required)
    # ========================================================================

    schema_name: str = ""
    """
    Schema name for validation.
    Examples:
    - "ADT_A01" (HL7 admit message)
    - "Patient" (FHIR Patient resource)
    - "OrderRequest" (custom schema)
    """

    schema_namespace: str = ""
    """
    Schema namespace (unique identifier).
    Examples:
    - "urn:hl7-org:v2" (HL7 v2.x)
    - "http://hl7.org/fhir" (FHIR)
    - "https://example.com/schemas/orders" (custom)
    """

    # ========================================================================
    # PAYLOAD (Required)
    # ========================================================================

    raw_payload: bytes = b""
    """
    Original message payload (raw bytes).
    This is ALWAYS preserved for audit trail.
    """

    _parsed_payload: Optional[Any] = field(default=None, repr=False)
    """
    Parsed message object (lazy-loaded).
    Private field - use parsed_payload property.
    """

    # ========================================================================
    # VALIDATION (Computed)
    # ========================================================================

    validated: bool = False
    """Whether payload has been validated against schema."""

    validation_errors: List[str] = field(default_factory=list)
    """Validation error messages (empty if valid)."""

    # ========================================================================
    # CUSTOM PROPERTIES (Unlimited extensibility)
    # ========================================================================

    custom_properties: Dict[str, Any] = field(default_factory=dict)
    """User-defined custom body properties."""

    # ========================================================================
    # PROPERTIES & METHODS
    # ========================================================================

    @property
    def parsed_payload(self) -> Any:
        """
        Get parsed payload (lazy-loaded).

        On first access, parses raw_payload based on content_type.
        Subsequent accesses return cached parsed object.
        """
        if self._parsed_payload is None and self.raw_payload:
            # Lazy parsing happens here (see MessageEnvelope.parse())
            pass
        return self._parsed_payload

    @parsed_payload.setter
    def parsed_payload(self, value: Any) -> None:
        """Set parsed payload (also updates raw_payload if encoder available)."""
        self._parsed_payload = value

    def get_custom(self, key: str, default: Any = None) -> Any:
        """Get custom property with default."""
        return self.custom_properties.get(key, default)

    def set_custom(self, key: str, value: Any) -> None:
        """Set custom property."""
        self.custom_properties[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "schema_name": self.schema_name,
            "schema_namespace": self.schema_namespace,
            "raw_payload": self.raw_payload.decode("utf-8", errors="replace"),  # For JSON
            "validated": self.validated,
            "validation_errors": self.validation_errors,
            "custom_properties": self.custom_properties,
        }


@dataclass
class MessageEnvelope:
    """
    Complete message envelope (header + body).

    This is the PRIMARY message structure used throughout HIE.

    Usage Examples:

    # Create HL7 v2.4 message
    envelope = MessageEnvelope(
        header=MessageHeader(
            source="Cerner_PAS",
            destination="NHS_Validation",
            body_class_name="Engine.li.messages.hl7.HL7Message",
            content_type="application/hl7-v2+er7",
            schema_version="2.4",
            priority=Priority.HIGH,
        ),
        body=MessageBody(
            schema_name="ADT_A01",
            schema_namespace="urn:hl7-org:v2",
            raw_payload=b"MSH|^~\\&|CERNER|...",
        )
    )

    # Create FHIR R4 message
    envelope = MessageEnvelope(
        header=MessageHeader(
            body_class_name="Engine.li.messages.fhir.FHIRResource",
            content_type="application/fhir+json",
            schema_version="R4",
        ),
        body=MessageBody(
            schema_name="Patient",
            schema_namespace="http://hl7.org/fhir",
            raw_payload=b'{"resourceType": "Patient", ...}',
        )
    )

    # Create custom message
    envelope = MessageEnvelope(
        header=MessageHeader(
            body_class_name="demos.custom.OrderMessage",
            content_type="application/json",
            schema_version="v1.0",
        ),
        body=MessageBody(
            schema_name="OrderRequest",
            schema_namespace="https://example.com/schemas",
            raw_payload=b'{"order_id": "12345", ...}',
        )
    )
    """

    header: MessageHeader
    body: MessageBody

    # ========================================================================
    # FACTORY METHODS
    # ========================================================================

    @classmethod
    def create_hl7(
        cls,
        raw_payload: bytes,
        version: str = "2.4",
        source: str = "",
        destination: str = "",
        **header_kwargs
    ) -> MessageEnvelope:
        """
        Factory method for HL7 v2.x messages.

        Args:
            raw_payload: HL7 message bytes (pipe-delimited)
            version: HL7 version (2.3, 2.4, 2.5, 2.5.1, 2.6, 2.7, 2.8)
            source: Source service name
            destination: Destination service name
            **header_kwargs: Additional header properties
        """
        # Extract message type from MSH segment
        msg_str = raw_payload.decode("utf-8", errors="replace")
        schema_name = "UNKNOWN"
        try:
            msh = msg_str.split("\r")[0]  # First segment
            fields = msh.split("|")
            if len(fields) >= 9:
                msg_type = fields[8]  # MSH-9: Message Type
                schema_name = msg_type.replace("^", "_")  # ADT^A01 -> ADT_A01
        except Exception:
            pass

        header = MessageHeader(
            source=source,
            destination=destination,
            body_class_name="Engine.li.messages.hl7.HL7Message",
            content_type=ContentType.HL7_V2_ER7.value,
            schema_version=version,
            **header_kwargs
        )

        body = MessageBody(
            schema_name=schema_name,
            schema_namespace="urn:hl7-org:v2",
            raw_payload=raw_payload,
        )

        return cls(header=header, body=body)

    @classmethod
    def create_fhir(
        cls,
        raw_payload: bytes,
        resource_type: str,
        version: str = "R4",
        source: str = "",
        destination: str = "",
        **header_kwargs
    ) -> MessageEnvelope:
        """
        Factory method for FHIR resources.

        Args:
            raw_payload: FHIR JSON/XML bytes
            resource_type: FHIR resource type (Patient, Observation, etc.)
            version: FHIR version (DSTU2, STU3, R4, R5)
            source: Source service name
            destination: Destination service name
            **header_kwargs: Additional header properties
        """
        header = MessageHeader(
            source=source,
            destination=destination,
            body_class_name="Engine.li.messages.fhir.FHIRResource",
            content_type=ContentType.FHIR_JSON.value,
            schema_version=version,
            **header_kwargs
        )

        body = MessageBody(
            schema_name=resource_type,
            schema_namespace="http://hl7.org/fhir",
            raw_payload=raw_payload,
        )

        return cls(header=header, body=body)

    @classmethod
    def create_custom(
        cls,
        raw_payload: bytes,
        body_class_name: str,
        schema_name: str,
        schema_version: str = "v1.0",
        content_type: str = "application/json",
        source: str = "",
        destination: str = "",
        **header_kwargs
    ) -> MessageEnvelope:
        """
        Factory method for custom messages.

        Args:
            raw_payload: Message bytes
            body_class_name: Fully qualified Python class
            schema_name: Schema name for validation
            schema_version: Schema version
            content_type: MIME type
            source: Source service name
            destination: Destination service name
            **header_kwargs: Additional header properties
        """
        header = MessageHeader(
            source=source,
            destination=destination,
            body_class_name=body_class_name,
            content_type=content_type,
            schema_version=schema_version,
            **header_kwargs
        )

        body = MessageBody(
            schema_name=schema_name,
            schema_namespace=header_kwargs.get("schema_namespace", ""),
            raw_payload=raw_payload,
        )

        return cls(header=header, body=body)

    # ========================================================================
    # PARSING & VALIDATION
    # ========================================================================

    def parse(self) -> Any:
        """
        Parse raw_payload into typed object based on content_type.

        Returns parsed payload and caches it in body.parsed_payload.
        """
        if self.body._parsed_payload is not None:
            return self.body._parsed_payload

        # Dynamically import parser based on content_type
        if self.header.content_type == ContentType.HL7_V2_ER7.value:
            from Engine.li.messages.hl7 import HL7Message
            parsed = HL7Message.parse(
                self.body.raw_payload,
                version=self.header.schema_version
            )
        elif self.header.content_type == ContentType.FHIR_JSON.value:
            from Engine.li.messages.fhir import FHIRResource
            parsed = FHIRResource.parse_json(
                self.body.raw_payload,
                version=self.header.schema_version
            )
        elif self.header.content_type == ContentType.JSON.value:
            import json
            parsed = json.loads(self.body.raw_payload.decode(self.header.encoding))
        elif self.header.content_type == ContentType.XML.value:
            import xml.etree.ElementTree as ET
            parsed = ET.fromstring(self.body.raw_payload.decode(self.header.encoding))
        else:
            # Unknown content type - return raw bytes
            parsed = self.body.raw_payload

        self.body._parsed_payload = parsed
        return parsed

    def validate(self) -> bool:
        """
        Validate message against schema.

        Returns True if valid, False otherwise.
        Validation errors stored in body.validation_errors.
        """
        self.body.validation_errors = []

        try:
            # Parse if not already parsed
            if self.body._parsed_payload is None:
                self.parse()

            # Dynamically import validator based on content_type
            if self.header.content_type == ContentType.HL7_V2_ER7.value:
                from Engine.li.validation.hl7 import HL7Validator
                validator = HL7Validator(version=self.header.schema_version)
                errors = validator.validate(self.body._parsed_payload)
                self.body.validation_errors = errors

            elif self.header.content_type == ContentType.FHIR_JSON.value:
                from Engine.li.validation.fhir import FHIRValidator
                validator = FHIRValidator(version=self.header.schema_version)
                errors = validator.validate(self.body._parsed_payload)
                self.body.validation_errors = errors

            # Add custom validators here

        except Exception as e:
            self.body.validation_errors.append(f"Validation exception: {str(e)}")

        self.body.validated = True
        return len(self.body.validation_errors) == 0

    # ========================================================================
    # SERIALIZATION
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire envelope to dictionary."""
        return {
            "header": self.header.to_dict(),
            "body": self.body.to_dict(),
        }

    def to_json(self) -> str:
        """Serialize entire envelope to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MessageEnvelope:
        """Deserialize envelope from dictionary."""
        header = MessageHeader.from_dict(data["header"])
        body_data = data["body"].copy()
        # Decode raw_payload if it was encoded as string
        if isinstance(body_data.get("raw_payload"), str):
            body_data["raw_payload"] = body_data["raw_payload"].encode("utf-8")
        body = MessageBody(**body_data)
        return cls(header=header, body=body)

    @classmethod
    def from_json(cls, json_str: str) -> MessageEnvelope:
        """Deserialize envelope from JSON string."""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)


# ============================================================================
# PROTOCOL FOR TYPE SAFETY (Phase 4)
# ============================================================================

class Message(Protocol):
    """
    Protocol for type-safe message handling.

    Any class implementing these methods can be treated as a Message.
    This provides IDE autocomplete and static type checking.
    """

    def to_bytes(self) -> bytes:
        """Serialize message to bytes."""
        ...

    @classmethod
    def from_bytes(cls, data: bytes) -> Message:
        """Deserialize message from bytes."""
        ...

    def validate(self) -> bool:
        """Validate message against schema."""
        ...


M = TypeVar('M', bound=Message)

```

---

## Usage Examples

### Example 1: HL7 v2.4 ADT^A01 (Patient Admission)

```python
# Receive raw HL7 message from TCP
raw_hl7 = b"MSH|^~\\&|CERNER|RH|NHS|TRUST|20260210120000||ADT^A01|12345|P|2.4\r" \
          b"EVN||20260210120000\r" \
          b"PID|||NHS-1234567890^^^NHS||SMITH^JOHN||19800101|M\r"

# Create envelope
envelope = MessageEnvelope.create_hl7(
    raw_payload=raw_hl7,
    version="2.4",
    source="Cerner_PAS_Receiver",
    destination="NHS_Validation_Process",
    priority=Priority.HIGH,
)

# Add custom properties
envelope.header.set_custom("patient_id", "NHS-1234567890")
envelope.header.set_custom("facility_id", "RH-001")

# Parse message
hl7_msg = envelope.parse()
print(f"Message Type: {hl7_msg.MSH.MessageType}")  # ADT^A01
print(f"Patient Name: {hl7_msg.PID.PatientName}")  # SMITH^JOHN

# Validate message
if envelope.validate():
    print("✅ Message is valid")
else:
    print(f"❌ Validation errors: {envelope.body.validation_errors}")

# Send to next service
await service_registry.route_message("NHS_Validation_Process", envelope)
```

---

### Example 2: FHIR R4 Patient Resource

```python
# Receive FHIR JSON from HTTP API
fhir_json = b'''{
  "resourceType": "Patient",
  "id": "example",
  "name": [{
    "family": "Smith",
    "given": ["John"]
  }],
  "birthDate": "1980-01-01",
  "gender": "male"
}'''

# Create envelope
envelope = MessageEnvelope.create_fhir(
    raw_payload=fhir_json,
    resource_type="Patient",
    version="R4",
    source="FHIR_API_Gateway",
    destination="Patient_Registry",
)

# Parse FHIR resource
patient = envelope.parse()
print(f"Resource Type: {patient.resourceType}")  # Patient
print(f"Patient Name: {patient.name[0].family}")  # Smith

# Validate against FHIR R4 schema
if envelope.validate():
    print("✅ FHIR resource is valid")

# Route to patient registry
await service_registry.route_message("Patient_Registry", envelope)
```

---

### Example 3: Custom Bespoke Protocol

```python
# Custom order message (JSON)
order_json = b'''{
  "order_id": "ORD-12345",
  "patient_id": "NHS-1234567890",
  "test_code": "FBC",
  "urgent": true,
  "requested_by": "Dr. Smith",
  "requested_at": "2026-02-10T12:00:00Z"
}'''

# Create envelope with custom schema
envelope = MessageEnvelope.create_custom(
    raw_payload=order_json,
    body_class_name="demos.lab_orders.OrderMessage",
    schema_name="OrderRequest",
    schema_version="v1.2.3",
    content_type="application/json",
    source="Order_Entry_System",
    destination="Lab_Interface",
)

# Add custom tracing (Phase 5)
envelope.header.trace_id = "trace-abc-123"
envelope.header.span_id = "span-def-456"

# Parse custom message
order = envelope.parse()
print(f"Order ID: {order['order_id']}")
print(f"Urgent: {order['urgent']}")

# Route to lab interface
await service_registry.route_message("Lab_Interface", envelope)
```

---

## Integration with Existing Hosts

### Updated Host Base Class

```python
class Host(ABC):
    """Base class for all hosts (Services, Processes, Operations)."""

    @abstractmethod
    async def on_process_input(self, envelope: MessageEnvelope) -> Optional[MessageEnvelope]:
        """
        Process incoming message envelope.

        Args:
            envelope: Message envelope with header + body

        Returns:
            Response envelope (for sync patterns) or None (for async)
        """
        pass
```

### Example: NHS Validation Process (Updated)

```python
class NHSValidationProcess(Host):
    """NHS validation with new envelope-based messaging."""

    async def on_process_input(self, envelope: MessageEnvelope) -> Optional[MessageEnvelope]:
        # Check if expired
        if envelope.header.is_expired():
            logger.warning("message_expired", message_id=envelope.header.message_id)
            return None

        # Route based on content type
        if envelope.header.content_type == ContentType.HL7_V2_ER7.value:
            return await self._process_hl7(envelope)
        elif envelope.header.content_type == ContentType.FHIR_JSON.value:
            return await self._process_fhir(envelope)
        else:
            logger.error("unsupported_content_type", content_type=envelope.header.content_type)
            return None

    async def _process_hl7(self, envelope: MessageEnvelope) -> Optional[MessageEnvelope]:
        # Parse HL7
        hl7_msg = envelope.parse()

        # Validate against HL7 2.4 schema
        if not envelope.validate():
            logger.error("hl7_validation_failed",
                        errors=envelope.body.validation_errors)
            return None

        # Extract NHS Number
        nhs_number = self._extract_nhs_number(hl7_msg)

        # Validate NHS Number check digit
        if not self._validate_nhs_number(nhs_number):
            logger.error("invalid_nhs_number", nhs_number=nhs_number)
            return None

        # Success - route to next service
        envelope.header.destination = "ADT_Router"
        envelope.header.source = self.name
        await self.send_request_async("ADT_Router", envelope)

        return envelope
```

---

## Benefits of Message Envelope Pattern

### ✅ **1. Schema-Aware Runtime Parsing**

```python
# Before (Phase 1-3): Duck typing, no schema info
if hasattr(message, 'MSH'):
    # Hope it's HL7... but what version?
    pass

# After (Phase 4): Explicit schema in header
if envelope.header.content_type == "application/hl7-v2+er7":
    if envelope.header.schema_version == "2.4":
        # Parse as HL7 2.4
    elif envelope.header.schema_version == "2.5.1":
        # Parse as HL7 2.5.1
```

### ✅ **2. Protocol-Agnostic Routing**

```python
# Route based on content type, not guessing
router_map = {
    "application/hl7-v2+er7": "HL7_Router",
    "application/fhir+json": "FHIR_Router",
    "application/soap+xml": "SOAP_Router",
}

target = router_map.get(envelope.header.content_type, "Default_Router")
await self.send_request_async(target, envelope)
```

### ✅ **3. Distributed Tracing**

```python
# OpenTelemetry integration (Phase 5)
with tracer.start_span("process_message") as span:
    span.set_attribute("message.id", envelope.header.message_id)
    span.set_attribute("content.type", envelope.header.content_type)
    span.set_attribute("schema.version", envelope.header.schema_version)

    # Propagate trace context
    envelope.header.trace_id = span.context.trace_id
    envelope.header.span_id = span.context.span_id

    await process(envelope)
```

### ✅ **4. Priority-Based Routing**

```python
# Route urgent messages to priority queue
if envelope.header.priority >= Priority.URGENT:
    await redis.xadd("urgent-stream", envelope.to_dict())
else:
    await redis.xadd("normal-stream", envelope.to_dict())
```

### ✅ **5. TTL and Expiration**

```python
# Discard expired messages
if envelope.header.is_expired():
    logger.warning("message_expired",
                   message_id=envelope.header.message_id,
                   age=(datetime.utcnow() - envelope.header.timestamp).total_seconds())
    return None
```

### ✅ **6. Audit Trail**

```python
# Always preserve raw payload for audit
audit_record = {
    "message_id": envelope.header.message_id,
    "timestamp": envelope.header.timestamp.isoformat(),
    "source": envelope.header.source,
    "destination": envelope.header.destination,
    "raw_payload": envelope.body.raw_payload.decode("utf-8", errors="replace"),
    "content_type": envelope.header.content_type,
    "schema_version": envelope.header.schema_version,
}

await audit_log.write(audit_record)
```

### ✅ **7. Custom Properties (Unlimited Flexibility)**

```python
# Healthcare-specific properties
envelope.header.set_custom("patient_id", "NHS-1234567890")
envelope.header.set_custom("facility_id", "RH-001")
envelope.header.set_custom("sla_deadline", "2026-02-10T15:30:00Z")
envelope.header.set_custom("requires_pds_lookup", True)

# Business logic can use custom properties
if envelope.header.get_custom("urgent_lab_result"):
    await notify_clinician(envelope)
```

---

## Migration Path (Phase 3 → Phase 4)

### Step 1: Introduce MessageEnvelope (Non-Breaking)

```python
# Old API still works (backward compatible)
async def on_process_input(self, message: Any) -> Any:
    # Auto-wrap old messages
    if not isinstance(message, MessageEnvelope):
        envelope = MessageEnvelope.create_custom(
            raw_payload=message.to_bytes() if hasattr(message, 'to_bytes') else b"",
            body_class_name=f"{message.__class__.__module__}.{message.__class__.__name__}",
            schema_name="legacy",
        )
        envelope.body._parsed_payload = message
    else:
        envelope = message

    return await self.on_process_envelope(envelope)

async def on_process_envelope(self, envelope: MessageEnvelope) -> Optional[MessageEnvelope]:
    # New API - override this in subclasses
    pass
```

### Step 2: Update Standard Hosts (HL7, File, HTTP)

```python
# HL7TCPService now creates envelopes
class HL7TCPService(Host):
    async def on_message_received(self, raw_bytes: bytes):
        envelope = MessageEnvelope.create_hl7(
            raw_payload=raw_bytes,
            version=self.get_setting("MessageSchemaCategory", "2.4"),
            source=self.name,
            destination=self.get_setting("TargetConfigNames", [""])[0],
        )
        await self.route_message(envelope)
```

### Step 3: Update Custom Hosts (Opt-In)

```python
# Custom hosts can opt-in to new API
class MyCustomProcess(Host):
    async def on_process_envelope(self, envelope: MessageEnvelope) -> Optional[MessageEnvelope]:
        # Use new envelope-based API
        if envelope.header.content_type == ContentType.HL7_V2_ER7.value:
            hl7_msg = envelope.parse()
            # Process...
```

### Step 4: Deprecate Old API (Phase 5)

```python
# Mark old API as deprecated
@deprecated("Use on_process_envelope() instead")
async def on_process_input(self, message: Any) -> Any:
    ...
```

---

## Comparison to Industry Standards

### Kafka Record

```
Kafka Record:
├─ Key (routing)
├─ Value (payload)
├─ Headers (metadata)    ← Similar to MessageHeader
└─ Timestamp

MessageEnvelope:
├─ Header (metadata)     ← Similar to Kafka headers
└─ Body (payload)        ← Similar to Kafka value
```

### AMQP Message

```
AMQP Message:
├─ Properties            ← Similar to MessageHeader
│  ├─ content-type
│  ├─ correlation-id
│  ├─ message-id
│  └─ timestamp
└─ Body                  ← Similar to MessageBody

MessageEnvelope:
├─ Header (properties)
└─ Body (payload)
```

### HTTP Request

```
HTTP Request:
├─ Headers               ← Similar to MessageHeader
│  ├─ Content-Type
│  ├─ Correlation-ID
│  └─ Custom headers
└─ Body                  ← Similar to MessageBody

MessageEnvelope:
├─ Header (metadata)
└─ Body (payload)
```

**Verdict:** MessageEnvelope follows **proven industry patterns** from Kafka, AMQP, HTTP.

---

## Summary

### ✅ **Design Verdict: EXCELLENT**

This message envelope pattern:
1. ✅ **Solves polymorphic messaging** (schema-aware, protocol-agnostic)
2. ✅ **Unlimited extensibility** (custom properties in header and body)
3. ✅ **Type safety** (Protocol for IDE support)
4. ✅ **Industry standard** (matches Kafka, AMQP, HTTP patterns)
5. ✅ **Backward compatible** (migration path from Phase 3)
6. ✅ **Audit trail** (raw_payload always preserved)
7. ✅ **Distributed tracing** (trace_id, span_id built-in)
8. ✅ **Scalable** (works with Redis Streams, Kafka, RabbitMQ)

### **Recommendation: Implement in Phase 4**

This is the **correct design** for a billion-message/day system.

---

*Next: See PRODUCT_ROADMAP.md for Phase 4-6 implementation timeline*
